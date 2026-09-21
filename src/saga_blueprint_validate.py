from __future__ import annotations

import argparse
import copy
import difflib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import ValidationError

from src.saga_blueprint_contract import CharacterNarrativeBlueprint, validate_blueprint_payload


VALIDATOR_VERSION = "saga-blueprint-static-validator-v1"

SEQUENCE_RE = re.compile(
    r"\b(?:story|chapter|episode|hikaye|bölüm)\s*#?\s*\d+\b",
    re.IGNORECASE,
)
FORCED_FUTURE_RE = re.compile(
    r"\b(?:the character|character|karakter|[A-Z][a-z]{2,})\s+will\s+"
    r"(?:marry|travel|go|choose|decide|discover|become|leave|join|fight|investigate|find)\b"
    r"|\bmust\s+(?:go|investigate|choose|marry|travel|follow|discover)\b"
    r"|\bkarakter\s+(?:kesinlikle|mutlaka)\b",
    re.IGNORECASE,
)
FORCED_WORLD_CREATION_RE = re.compile(
    r"\b(?:only\s+to\s+force|to\s+force\s+(?:the\s+)?(?:character|saga|story)|must\s+create)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Literal["critical", "high", "medium", "review"]
    hard_block: bool
    path: str
    message: str


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9ğüşöçıİĞÜŞÖÇ]+", " ", text.casefold()).split())


def _walk_strings(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path or "/", value
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}/{index}")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}/{key}")


def _strict_parse(payload: dict[str, Any]) -> tuple[CharacterNarrativeBlueprint | None, list[Finding]]:
    try:
        return validate_blueprint_payload(payload), []
    except ValidationError as exc:
        findings = []
        for error in exc.errors(include_input=False):
            loc = "/" + "/".join(str(item) for item in error.get("loc") or [])
            findings.append(
                Finding(
                    code="SCHEMA_OR_REFERENCE_INVALID",
                    severity="critical",
                    hard_block=True,
                    path=loc,
                    message=error.get("msg", "strict blueprint validation failed"),
                )
            )
        return None, findings


def validate_static(payload: dict[str, Any]) -> dict[str, Any]:
    blueprint, findings = _strict_parse(payload)
    if blueprint is None:
        return _report(findings)

    data = blueprint.model_dump(mode="json", by_alias=True)

    for path, text in _walk_strings(data):
        if SEQUENCE_RE.search(text):
            findings.append(
                Finding(
                    code="FIXED_STORY_SEQUENCE_LANGUAGE",
                    severity="critical",
                    hard_block=True,
                    path=path,
                    message="Blueprint contains explicit numbered story/chapter sequencing.",
                )
            )
        if FORCED_FUTURE_RE.search(text):
            findings.append(
                Finding(
                    code="FORCED_FUTURE_CHOICE_LANGUAGE",
                    severity="critical",
                    hard_block=True,
                    path=path,
                    message="Blueprint contains explicit language that precommits a future character choice/event.",
                )
            )

    for thread_index, thread in enumerate(blueprint.saga_blueprint.threads):
        tpath = f"/saga_blueprint/threads/{thread_index}"
        if not thread.seeds:
            findings.append(
                Finding(
                    code="THREAD_HAS_NO_SEEDS",
                    severity="high",
                    hard_block=True,
                    path=f"{tpath}/seeds",
                    message="Saga thread has no breadcrumb entry points.",
                )
            )
        if not thread.milestones:
            findings.append(
                Finding(
                    code="THREAD_HAS_NO_MILESTONES",
                    severity="medium",
                    hard_block=False,
                    path=f"{tpath}/milestones",
                    message="Saga thread has no possible milestone and needs semantic review.",
                )
            )

        summaries: list[tuple[int, str, str]] = []
        for seed_index, seed in enumerate(thread.seeds):
            spath = f"{tpath}/seeds/{seed_index}"
            normalized = _norm(seed.summary)
            for prior_index, prior_key, prior_summary in summaries:
                if normalized == prior_summary:
                    findings.append(
                        Finding(
                            code="DUPLICATE_SEED_CONTENT",
                            severity="high",
                            hard_block=True,
                            path=f"{spath}/summary",
                            message=f"Seed duplicates narrative content of {prior_key}.",
                        )
                    )
                else:
                    ratio = difflib.SequenceMatcher(
                        None, normalized, prior_summary
                    ).ratio()
                    if ratio >= 0.92:
                        findings.append(
                            Finding(
                                code="NEAR_DUPLICATE_SEED_CONTENT",
                                severity="review",
                                hard_block=False,
                                path=f"{spath}/summary",
                                message=(
                                    f"Seed is near-duplicate of {prior_key} "
                                    f"(similarity={ratio:.3f})."
                                ),
                            )
                        )
            summaries.append((seed_index, seed.key, normalized))

            if seed.key in seed.may_unlock:
                findings.append(
                    Finding(
                        code="SELF_UNLOCKING_SEED",
                        severity="high",
                        hard_block=True,
                        path=f"{spath}/may_unlock",
                        message="Seed cannot unlock itself.",
                    )
                )

            vis = seed.visibility_policy
            allowed = {_norm(item) for item in vis.allowed_usage}
            forbidden = {_norm(item) for item in vis.forbidden_usage}
            overlap = sorted((allowed & forbidden) - {""})
            if overlap:
                findings.append(
                    Finding(
                        code="REVEAL_POLICY_CONTRADICTION",
                        severity="critical",
                        hard_block=True,
                        path=f"{spath}/visibility_policy",
                        message="The same usage is both allowed and forbidden.",
                    )
                )
            if (
                vis.initial_visibility in {"HIDDEN", "FORESHADOW_ONLY"}
                and not vis.forbidden_usage
            ):
                findings.append(
                    Finding(
                        code="REVEAL_GUARD_EMPTY",
                        severity="high",
                        hard_block=True,
                        path=f"{spath}/visibility_policy/forbidden_usage",
                        message="Hidden/foreshadow seed requires explicit forbidden usage.",
                    )
                )

        for milestone_index, milestone in enumerate(thread.milestones):
            mpath = f"{tpath}/milestones/{milestone_index}"
            if milestone.required:
                findings.append(
                    Finding(
                        code="MANDATORY_MILESTONE",
                        severity="critical",
                        hard_block=True,
                        path=f"{mpath}/required",
                        message="Saga milestones may not be mandatory future events.",
                    )
                )
                if len(set(milestone.possible_entry_points)) <= 1:
                    findings.append(
                        Finding(
                            code="SINGLE_ROUTE_MANDATORY_THREAD",
                            severity="critical",
                            hard_block=True,
                            path=f"{mpath}/possible_entry_points",
                            message="Mandatory milestone depends on at most one entry route.",
                        )
                    )
            if milestone.key in milestone.unlocks:
                findings.append(
                    Finding(
                        code="SELF_UNLOCKING_MILESTONE",
                        severity="high",
                        hard_block=True,
                        path=f"{mpath}/unlocks",
                        message="Milestone cannot unlock itself.",
                    )
                )

        for branch_index, branch in enumerate(thread.branches):
            if len(branch.paths) < 2:
                findings.append(
                    Finding(
                        code="BRANCH_WITHOUT_ALTERNATIVE",
                        severity="high",
                        hard_block=True,
                        path=f"{tpath}/branches/{branch_index}/paths",
                        message="A branch must provide at least two valid paths.",
                    )
                )

    for index, binding in enumerate(blueprint.world_integration.proposed_bindings):
        if FORCED_WORLD_CREATION_RE.search(binding.description):
            findings.append(
                Finding(
                    code="FORCED_WORLD_CREATION_LANGUAGE",
                    severity="critical",
                    hard_block=True,
                    path=f"/world_integration/proposed_bindings/{index}/description",
                    message="World binding explicitly exists to force Saga progression.",
                )
            )

    return _report(findings)


def _report(findings: list[Finding]) -> dict[str, Any]:
    hard = [finding for finding in findings if finding.hard_block]
    review = [finding for finding in findings if not finding.hard_block]
    if hard:
        status = "FAIL"
    elif review:
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"
    return {
        "schema_version": 1,
        "validator_version": VALIDATOR_VERSION,
        "status": status,
        "semantic_evaluation_eligible": not hard,
        "hard_finding_count": len(hard),
        "review_finding_count": len(review),
        "findings": [asdict(finding) for finding in findings],
    }


def _resolve_pointer(document: Any, pointer: str) -> tuple[Any, str | int]:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer}")
    parts = [
        part.replace("~1", "/").replace("~0", "~")
        for part in pointer.lstrip("/").split("/")
    ]
    current = document
    for part in parts[:-1]:
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    final = int(parts[-1]) if isinstance(current, list) else parts[-1]
    return current, final


def apply_mutations(base: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    payload = copy.deepcopy(base)
    for operation in operations:
        op = operation["op"]
        parent, key = _resolve_pointer(payload, operation["path"])
        if op == "set":
            parent[key] = copy.deepcopy(operation["value"])
        elif op == "append_copy":
            if not isinstance(parent[key], list):
                raise ValueError("append_copy target must be a list")
            source_index = int(operation["source_index"])
            item = copy.deepcopy(parent[key][source_index])
            for field, value in (operation.get("overrides") or {}).items():
                item[field] = copy.deepcopy(value)
            parent[key].append(item)
        else:
            raise ValueError(f"unsupported mutation op: {op}")
    return payload


def run_falsification_suite(
    *,
    base_payload: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    results = []
    suite_pass = True
    for case in spec["cases"]:
        mutated = apply_mutations(base_payload, case["operations"])
        report = validate_static(mutated)
        observed_codes = {item["code"] for item in report["findings"]}
        expected_codes = set(case["expected_codes"])
        codes_ok = expected_codes.issubset(observed_codes)
        block_ok = (report["status"] == "FAIL") == bool(case["expect_block"])
        passed = codes_ok and block_ok
        suite_pass = suite_pass and passed
        results.append(
            {
                "case_id": case["case_id"],
                "passed": passed,
                "expected_codes": sorted(expected_codes),
                "observed_codes": sorted(observed_codes),
                "expect_block": case["expect_block"],
                "observed_status": report["status"],
            }
        )
    return {
        "schema_version": 1,
        "validator_version": VALIDATOR_VERSION,
        "suite_id": spec["suite_id"],
        "status": "PASS" if suite_pass else "FAIL",
        "case_count": len(results),
        "pass_count": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Saga Blueprint statically.")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--falsification-spec", type=Path)
    parser.add_argument("--base-fixture-response", type=Path)
    args = parser.parse_args()

    if args.falsification_spec:
        if not args.base_fixture_response:
            parser.error("--base-fixture-response is required with --falsification-spec")
        base = json.loads(args.base_fixture_response.read_text(encoding="utf-8"))["blueprint"]
        spec = json.loads(args.falsification_spec.read_text(encoding="utf-8"))
        report = run_falsification_suite(base_payload=base, spec=spec)
    else:
        if not args.input:
            parser.error("--input is required unless --falsification-spec is used")
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        report = validate_static(payload)

    if args.output:
        _write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
