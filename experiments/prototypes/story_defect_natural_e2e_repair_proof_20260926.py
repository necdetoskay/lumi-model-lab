from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story


FIXTURE = Path("experiments/fixtures/story_defect_natural_e2e_repair_proof.v1.json")
SOURCE_POOL = Path("experiments/fixtures/story_defect_source_pool.tr-age4.v1.json")
CLEAN_ADMISSION = Path("experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json")
OUT = Path("runs/story-defect-natural-e2e-repair-proof/result.json")

DETECTOR_MODEL = "anthropic/claude-sonnet-5"
REPAIR_MODEL = "anthropic/claude-sonnet-5"
VERIFY_MODEL = "anthropic/claude-haiku-4.5"

REPAIR_SCOPES = {"LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"}
SCOPE_ALIASES = {"LOCAL": "LOCAL_REPAIR", "STRUCTURAL": "STRUCTURAL_REPAIR"}


DETECTOR_SYSTEM = r"""
You are a strict publication-defect auditor for one finished Turkish read-aloud story for an exact-age-4 child.

Audit the current story blindly. You are not told whether the story is a benchmark, clean control, or known defective story.

You MUST evaluate EVERY requested canonical defect family separately before deciding that the story is clean:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

For every requested family return exactly one evaluation with present=true or present=false.
Do not skip a family. Do not collapse the audit into one overall impression.

If present=true:
- severity must be serious or critical;
- classify the MINIMUM safe repair scope:
  - LOCAL_REPAIR: a small number of exact supplied sentences can be changed while the rest stays untouched.
  - STRUCTURAL_REPAIR: coordinated changes across a wider story region or dependent beats are required, while the premise/plan can remain.
  - REPLAN: the underlying plan or causal architecture is broken enough that sentence-level editing is not reliable.
- cite the smallest exact supplied sentence-ID evidence span that proves the defect.

If present=false:
- severity must be null;
- repair_scope must be null;
- span_ids must be [];
- give one brief reason why the family is not publication-blocking.

Judgment rules:
- Report only serious or critical semantic defects, never grammar, style, word count, repetition, optional polish, or taste.
- Do not call ordinary fantasy a defect when the story establishes the fantasy rule.
- Do not invent hidden height, strength, distance, knowledge, or world constraints.
- response_causality: occupied hands or task load must not be treated by the narrator/story as inability to hear or answer. This also applies when the story implicitly endorses busy hands as the explanation for repeated silence while the same character can still speak under the same physical constraint. Mere voluntary prioritization is not a defect.
- A character may temporarily make a mistaken inference from another character's silence. That misunderstanding is legitimate story content and is NOT itself a response_causality defect when the narration does not endorse it as true and the story later provides a coherent explanation.
- closure_integrity: a terminal ending must not be needlessly reopened afterward.
- Do not rewrite the story.

Return JSON only:
{
  "evaluations": [
    {
      "family": "physical_feasibility",
      "present": false,
      "severity": null,
      "repair_scope": null,
      "span_ids": [],
      "reason": "brief evidence-based reason"
    }
  ]
}
""".strip()


LOCAL_REPAIR_SYSTEM = r"""
You repair exactly ONE confirmed LOCAL_REPAIR semantic defect in an otherwise accepted Turkish read-aloud story for an exact-age-4 child.

This is a bounded edit, not a rewrite.

Hard rules:
- You may change ONLY sentence IDs present in target_segments.
- Every non-target sentence is read-only.
- Use the fewest replacements necessary.
- Preserve names, events, object state, causal rules, tone, age fit, and ending except where the confirmed defect itself requires a local correction.
- Add no subplot, canon, object, character, explanation, moral, or extra payoff.
- Do not improve style outside the defect.
- For response_causality, NEVER write that occupied hands, holding an object, gripping something, or task load makes a character unable to hear, speak, answer, look, or turn the head.
- Do NOT use attention, concentration, focus, or occupied hands as if they make speech physically impossible.
- If silence must remain because downstream misunderstanding is outside the authorized span, frame it as voluntary prioritization/choice: the character may hear the other person but choose to postpone answering while handling the urgent task.
- The narrator may know that the character heard even if another character in read-only downstream text still mistakenly thinks they were not heard; preserve that point-of-view distinction.
- Do not add a direct spoken acknowledgement if it would contradict read-only downstream misunderstanding.
- A replacement may be an empty string only when deleting the target sentence is clearly the smallest safe repair.
- Do not return replacements for unchanged target sentences.

Return JSON only:
{
  "replacements": [
    {
      "id": "S001",
      "replacement_text": "replacement sentence or empty string"
    }
  ],
  "repair_note": "one short sentence"
}
""".strip()


SAME_DEFECT_RECHECK_SYSTEM = r"""
You verify whether ONE previously confirmed serious semantic defect remains after a bounded repair.

You receive:
- the original confirmed finding (family, reason, original span IDs);
- the full repaired story with fresh sentence IDs.

Judge only that SAME defect family and causal problem. Do not search for unrelated defects here.
A repair is NOT resolved if it merely restates the same bad causal rule in different words.
For response_causality specifically, occupied hands, holding/gripping, task load, attention, concentration, or focus must not be used as the reason a character cannot hear or speak. A character may voluntarily postpone answering while handling an urgent task; that is acceptable only when framed as a choice/prioritization rather than inability.

Return JSON only:
{
  "resolved": true,
  "remaining_span_ids": [],
  "reason": "brief evidence-based explanation"
}
""".strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def meta_cost(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    cost = meta.get("cost")
    if isinstance(cost, dict) and isinstance(cost.get("usd"), (int, float)):
        return float(cost["usd"])
    if isinstance(cost, (int, float)):
        return float(cost)
    return 0.0


def normalize_scope(value: Any) -> str:
    scope = SCOPE_ALIASES.get(str(value), str(value))
    if scope not in REPAIR_SCOPES:
        raise RuntimeError(f"repair_scope_invalid:{scope}")
    return scope


def normalize_findings(
    payload: dict[str, Any],
    valid_ids: set[str],
    requested_families: list[str],
) -> list[dict[str, Any]]:
    evaluations = payload.get("evaluations")
    if not isinstance(evaluations, list):
        raise RuntimeError("evaluations_missing")

    requested = list(requested_families)
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, raw in enumerate(evaluations):
        if not isinstance(raw, dict):
            raise RuntimeError(f"evaluation_{index}_not_object")

        family = str(raw.get("family") or "")
        if family not in requested:
            raise RuntimeError(f"evaluation_{index}_family_unrequested:{family}")
        if family in seen:
            raise RuntimeError(f"evaluation_{index}_family_duplicate:{family}")
        seen.add(family)

        present = raw.get("present")
        if not isinstance(present, bool):
            raise RuntimeError(f"evaluation_{index}_present_invalid:{present}")

        reason = str(raw.get("reason") or "").strip()
        if not reason:
            raise RuntimeError(f"evaluation_{index}_reason_missing")

        spans = raw.get("span_ids")
        if not isinstance(spans, list):
            raise RuntimeError(f"evaluation_{index}_span_invalid")
        spans = [str(value) for value in spans]

        if not present:
            if spans:
                raise RuntimeError(f"evaluation_{index}_false_with_spans:{spans}")
            continue

        severity = str(raw.get("severity") or "")
        if severity not in {"serious", "critical"}:
            raise RuntimeError(f"evaluation_{index}_severity_invalid:{severity}")
        if not spans:
            raise RuntimeError(f"evaluation_{index}_span_missing")
        if not set(spans).issubset(valid_ids):
            raise RuntimeError(f"evaluation_{index}_span_invalid:{spans}")

        normalized.append({
            "family": family,
            "severity": severity,
            "repair_scope": normalize_scope(raw.get("repair_scope")),
            "span_ids": spans,
            "reason": reason,
        })

    missing = [family for family in requested if family not in seen]
    if missing:
        raise RuntimeError(f"evaluations_missing_families:{missing}")

    return normalized


def call_detector(
    *,
    api_key: str,
    model: str,
    story_id: str,
    story_family: str,
    story_text: str,
    seed: int,
    request_class: str,
    audit_families: list[str] | None = None,
    audit_round: str = "primary",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    segments = segment_story(story_text)
    payload, meta = structured_call(
        api_key=api_key,
        model=model,
        system=DETECTOR_SYSTEM,
        payload={
            "story_id": story_id,
            "story_family": story_family,
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "audit_families": audit_families or list(DEFECT_FAMILIES),
            "audit_round": audit_round,
            "story_segments": segments,
        },
        seed=seed,
        max_tokens=2600,
        request_class=request_class,
    )
    requested_families = list(audit_families or DEFECT_FAMILIES)
    findings = normalize_findings(
        payload,
        {row["id"] for row in segments},
        requested_families,
    )
    return findings, meta


def blind_detect_with_zero_confirmation(
    *,
    api_key: str,
    story_id: str,
    story_family: str,
    story_text: str,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    first_findings, first_meta = call_detector(
        api_key=api_key,
        model=DETECTOR_MODEL,
        story_id=f"{story_id}_blind_primary",
        story_family=story_family,
        story_text=story_text,
        seed=seed,
        request_class="editorial_audit",
        audit_round="blind_primary",
    )
    rounds = [
        {
            "round": "blind_primary",
            "findings": first_findings,
            "meta": first_meta,
        }
    ]
    total_cost = meta_cost(first_meta)

    if first_findings:
        return first_findings, {
            "strategy": "blind_primary_then_zero_confirmation",
            "selected_round": "blind_primary",
            "rounds": rounds,
            "cost": {"usd": round(total_cost, 6)},
        }

    second_findings, second_meta = call_detector(
        api_key=api_key,
        model=DETECTOR_MODEL,
        story_id=f"{story_id}_blind_zero_confirmation",
        story_family=story_family,
        story_text=story_text,
        seed=seed + 7919,
        request_class="editorial_audit",
        audit_round="blind_independent_second_read_after_zero",
    )
    rounds.append({
        "round": "blind_independent_second_read_after_zero",
        "findings": second_findings,
        "meta": second_meta,
    })
    total_cost += meta_cost(second_meta)
    return second_findings, {
        "strategy": "blind_primary_then_zero_confirmation",
        "selected_round": (
            "blind_independent_second_read_after_zero"
            if second_findings
            else "confirmed_zero"
        ),
        "rounds": rounds,
        "cost": {"usd": round(total_cost, 6)},
    }


def call_same_defect_recheck(
    *,
    api_key: str,
    story_id: str,
    story_family: str,
    repaired_story: str,
    original_finding: dict[str, Any],
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    segments = segment_story(repaired_story)
    payload, meta = structured_call(
        api_key=api_key,
        model=VERIFY_MODEL,
        system=SAME_DEFECT_RECHECK_SYSTEM,
        payload={
            "story_id": story_id,
            "story_family": story_family,
            "exact_age": 4,
            "original_confirmed_finding": original_finding,
            "repaired_story_segments": segments,
        },
        seed=seed,
        max_tokens=1200,
        request_class="judge",
    )
    resolved = payload.get("resolved")
    if not isinstance(resolved, bool):
        raise RuntimeError("same_defect_recheck_resolved_missing")
    remaining = payload.get("remaining_span_ids") or []
    if not isinstance(remaining, list):
        raise RuntimeError("same_defect_recheck_spans_invalid")
    valid_ids = {row["id"] for row in segments}
    remaining = [str(value) for value in remaining]
    if not set(remaining).issubset(valid_ids):
        raise RuntimeError(f"same_defect_recheck_span_invalid:{remaining}")
    return {
        "resolved": resolved,
        "remaining_span_ids": remaining,
        "reason": str(payload.get("reason") or "").strip(),
    }, meta


def expected_match(findings: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any] | None:
    expected_spans = set(spec["expected_span_ids"])
    for finding in findings:
        if (
            finding["family"] == spec["expected_family"]
            and expected_spans.intersection(finding["span_ids"])
        ):
            return finding
    return None


def apply_local_repair(
    story: str,
    segments: list[dict[str, Any]],
    target_ids: list[str],
    repair_payload: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, str]]]:
    raw = repair_payload.get("replacements")
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("replacements_missing")

    by_id = {row["id"]: row["text"] for row in segments}
    allowed = set(target_ids)
    seen: set[str] = set()
    replacements: list[dict[str, str]] = []

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise RuntimeError(f"replacement_{index}_not_object")
        sid = str(item.get("id") or item.get("span_id") or "")
        if sid not in allowed:
            raise RuntimeError(f"replacement_outside_detector_span:{sid}")
        if sid in seen:
            raise RuntimeError(f"replacement_duplicate_id:{sid}")
        seen.add(sid)
        new = str(item.get("replacement_text") or "")
        old = by_id[sid]
        if new == old:
            continue
        replacements.append({"id": sid, "old": old, "new": new})

    if not replacements:
        raise RuntimeError("repair_changed_nothing")

    repaired = story
    for item in replacements:
        if repaired.count(item["old"]) != 1:
            raise RuntimeError(f"target_sentence_not_unique:{item['id']}")
        repaired = repaired.replace(item["old"], item["new"], 1)

    non_target_unchanged = all(
        row["text"] in repaired
        for row in segments
        if row["id"] not in allowed
    )
    changed_ids = [item["id"] for item in replacements]
    mechanical = {
        "detector_target_ids": target_ids,
        "changed_ids": changed_ids,
        "changed_ids_subset_of_detector_span": set(changed_ids).issubset(allowed),
        "non_target_sentences_present_exactly": non_target_unchanged,
        "changed_sentence_count": len(changed_ids),
        "outside_detector_span_changed": False,
    }
    return repaired, mechanical, replacements


def write_progress(results: list[dict[str, Any]], total_cost: float, status: str) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "schema_version": "story-defect-natural-e2e-repair-proof-result.v1",
                "status": status,
                "completed": len(results),
                "results": results,
                "total_cost_usd": round(total_cost, 6),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]

    fixture = load_json(FIXTURE)
    source_pool = load_json(SOURCE_POOL)
    admission = load_json(CLEAN_ADMISSION)

    source_by_id = {row["source_id"]: row for row in source_pool["sources"]}
    admitted_clean = {
        row["source_id"]
        for row in admission["entries"]
        if row["admitted_as_clean_source"] is True
    }

    requested = [
        value.strip()
        for value in os.environ.get("NATURAL_PROOF_IDS", "").split(",")
        if value.strip()
    ]
    cases = fixture["cases"]
    if requested:
        by_id = {row["proof_id"]: row for row in cases}
        unknown = [proof_id for proof_id in requested if proof_id not in by_id]
        if unknown:
            raise RuntimeError(f"unknown_proof_ids:{unknown}")
        cases = [by_id[proof_id] for proof_id in requested]

    results: list[dict[str, Any]] = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, spec in enumerate(cases):
        proof_id = spec["proof_id"]
        source = source_by_id[spec["source_id"]]
        story = source["story"]
        row: dict[str, Any] = {
            "proof_id": proof_id,
            "kind": spec["kind"],
            "source_id": spec["source_id"],
            "story_family": source["family"],
            "pass": False,
        }

        try:
            detector_findings, detector_meta = blind_detect_with_zero_confirmation(
                api_key=api_key,
                story_id=proof_id,
                story_family=source["family"],
                story_text=story,
                seed=2026150000 + index,
            )
            total_cost += meta_cost(detector_meta)
            row["detector"] = {
                "model": DETECTOR_MODEL,
                "findings": detector_findings,
                "meta": detector_meta,
            }

            if spec["kind"] == "clean":
                if spec["source_id"] not in admitted_clean:
                    raise RuntimeError(f"clean_source_not_admitted:{spec['source_id']}")
                verifier_findings, verifier_meta = call_detector(
                    api_key=api_key,
                    model=VERIFY_MODEL,
                    story_id=f"{proof_id}_full_regression",
                    story_family=source["family"],
                    story_text=story,
                    seed=2026160000 + index,
                    request_class="judge",
                )
                total_cost += meta_cost(verifier_meta)
                row["repair"] = {"skipped": True}
                row["full_regression"] = {
                    "model": VERIFY_MODEL,
                    "findings": verifier_findings,
                    "meta": verifier_meta,
                }
                row["pass"] = not detector_findings and not verifier_findings
                if not row["pass"]:
                    row["failure_stage"] = "CLEAN_FALSE_POSITIVE"
                results.append(row)
                write_progress(results, total_cost, "IN_PROGRESS")
                continue

            matched = expected_match(detector_findings, spec)
            row["gold_scoring"] = {
                "expected_family": spec["expected_family"],
                "expected_repair_scope": spec["expected_repair_scope"],
                "expected_span_ids": spec["expected_span_ids"],
                "expected_family_and_span_overlap": matched is not None,
            }
            if matched is None:
                row["failure_stage"] = "DETECTION"
                results.append(row)
                write_progress(results, total_cost, "IN_PROGRESS")
                continue

            scope_match = matched["repair_scope"] == spec["expected_repair_scope"]
            row["gold_scoring"]["repair_scope_match"] = scope_match
            if not scope_match:
                row["failure_stage"] = "REPAIR_SCOPE_CLASSIFICATION"
                results.append(row)
                write_progress(results, total_cost, "IN_PROGRESS")
                continue

            if matched["repair_scope"] != "LOCAL_REPAIR":
                row["failure_stage"] = "REPAIR_SCOPE_NOT_YET_ENABLED"
                results.append(row)
                write_progress(results, total_cost, "IN_PROGRESS")
                continue

            original_segments = segment_story(story)
            by_id = {seg["id"]: seg for seg in original_segments}
            target_segments = [by_id[sid] for sid in matched["span_ids"]]

            repair_attempts: list[dict[str, Any]] = []
            previous_replacements: list[dict[str, str]] = []
            verifier_feedback: dict[str, Any] | None = None
            repaired_story = story
            mechanical: dict[str, Any] = {}
            replacements: list[dict[str, str]] = []
            same_defect_result: dict[str, Any] = {
                "resolved": False,
                "remaining_span_ids": [],
                "reason": "not yet checked",
            }
            same_defect_meta: dict[str, Any] = {}

            for attempt in range(1, 3):
                repair_payload, repair_meta = structured_call(
                    api_key=api_key,
                    model=REPAIR_MODEL,
                    system=LOCAL_REPAIR_SYSTEM,
                    payload={
                        "story_id": proof_id,
                        "story_family": source["family"],
                        "attempt": attempt,
                        "confirmed_finding": matched,
                        "target_segments": target_segments,
                        "full_story_read_only": original_segments,
                        "previous_attempt_replacements": previous_replacements,
                        "same_defect_feedback_from_previous_attempt": verifier_feedback,
                    },
                    seed=2026155000 + index * 10 + attempt,
                    max_tokens=1800,
                    request_class="editorial_audit",
                )
                total_cost += meta_cost(repair_meta)

                repaired_story, mechanical, replacements = apply_local_repair(
                    story,
                    original_segments,
                    matched["span_ids"],
                    repair_payload,
                )

                same_defect_result, same_defect_meta = call_same_defect_recheck(
                    api_key=api_key,
                    story_id=f"{proof_id}_same_defect_recheck_attempt_{attempt}",
                    story_family=source["family"],
                    repaired_story=repaired_story,
                    original_finding=matched,
                    seed=2026160000 + index * 10 + attempt,
                )
                total_cost += meta_cost(same_defect_meta)

                repair_attempts.append({
                    "attempt": attempt,
                    "repair_note": str(repair_payload.get("repair_note") or ""),
                    "replacements": replacements,
                    "mechanical": mechanical,
                    "repair_meta": repair_meta,
                    "same_defect_recheck": {
                        **same_defect_result,
                        "meta": same_defect_meta,
                    },
                })

                if same_defect_result["resolved"]:
                    break

                previous_replacements = replacements
                verifier_feedback = same_defect_result

            row["repair"] = {
                "model": REPAIR_MODEL,
                "max_attempts": 2,
                "attempts": repair_attempts,
                "attempts_used": len(repair_attempts),
                "final_replacements": replacements,
                "mechanical": mechanical,
                "repaired_story": repaired_story,
            }
            row["same_defect_recheck"] = {
                "model": VERIFY_MODEL,
                "family": spec["expected_family"],
                **same_defect_result,
                "meta": same_defect_meta,
                "pass": bool(same_defect_result["resolved"]),
            }
            if not same_defect_result["resolved"]:
                row["failure_stage"] = "SAME_DEFECT_RECHECK"
                results.append(row)
                write_progress(results, total_cost, "IN_PROGRESS")
                continue

            regression_findings, regression_meta = call_detector(
                api_key=api_key,
                model=VERIFY_MODEL,
                story_id=f"{proof_id}_full_regression",
                story_family=source["family"],
                story_text=repaired_story,
                seed=2026165000 + index,
                request_class="judge",
            )
            total_cost += meta_cost(regression_meta)
            row["full_regression"] = {
                "model": VERIFY_MODEL,
                "findings": regression_findings,
                "meta": regression_meta,
                "pass": len(regression_findings) == 0,
            }

            row["pass"] = (
                mechanical["changed_ids_subset_of_detector_span"]
                and mechanical["non_target_sentences_present_exactly"]
                and row["same_defect_recheck"]["pass"]
                and not regression_findings
            )
            if not row["pass"]:
                row["failure_stage"] = "FULL_REGRESSION"

        except Exception as exc:
            row["failure_stage"] = "RUNTIME"
            row["error"] = f"{type(exc).__name__}: {exc}"

        results.append(row)
        write_progress(results, total_cost, "IN_PROGRESS")

    passes = sum(bool(row.get("pass")) for row in results)
    output = {
        "schema_version": "story-defect-natural-e2e-repair-proof-result.v1",
        "status": "PASS" if passes == len(results) else "FAIL",
        "mode": "SELECTED_CASES" if requested else "FULL_FIVE_STORY_PROOF",
        "requested_proof_ids": requested,
        "models": {
            "detector": DETECTOR_MODEL,
            "repair": REPAIR_MODEL,
            "same_defect_recheck": VERIFY_MODEL,
            "full_regression": VERIFY_MODEL,
        },
        "summary": {
            "cases": len(results),
            "passes": passes,
            "failures": len(results) - passes,
            "selected_cases_all_pass": passes == len(results),
            "full_five_story_gate_pass": (not requested and passes == len(results) == 5),
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "mode": output["mode"],
        "summary": output["summary"],
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
        "case_results": [
            {
                "proof_id": item["proof_id"],
                "pass": item.get("pass"),
                "failure_stage": item.get("failure_stage"),
            }
            for item in results
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
