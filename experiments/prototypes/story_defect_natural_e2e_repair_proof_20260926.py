from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_defect_e2e_repair_proof_20260926 import (
    DETECTOR_MODEL,
    POST_VERIFY_MODEL,
    call_detector,
    meta_cost,
)
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import segment_story

FIXTURE = Path("experiments/fixtures/story_defect_natural_e2e_repair_proof.v1.json")
NATURAL = Path("experiments/fixtures/story_defect_natural_positive_pool.tr-age4.v0.1.json")
SOURCE_POOL = Path("experiments/fixtures/story_defect_source_pool.tr-age4.v1.json")
CLEAN_ADMISSION = Path("experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json")
OUT = Path("runs/story-defect-natural-e2e-repair-proof/result.json")

REPAIR_MODEL = "anthropic/claude-sonnet-5"

REPAIR_SYSTEM = r"""
You repair exactly ONE confirmed serious semantic defect in a Turkish read-aloud story for an exact-age-4 child.

The caller gives:
- the full story as read-only context;
- one confirmed defect found by a blind detector;
- exact detector-selected sentence IDs and their current text.

You may change ONLY those supplied target sentence IDs.
You may leave some target sentences unchanged.
You may delete a target sentence by returning an empty replacement.
Do not change or rewrite any sentence outside the target list.

Rules:
- make the smallest correction that removes the confirmed defect;
- preserve characters, tone, events, physical rules and already-correct state;
- add no subplot, moral, new object, new character or unrelated explanation;
- for response_causality, hands/task load may delay a hand-dependent action but must not cause inability to hear or speak;
- for state_continuity, make later state agree with the already-established earlier state;
- for causal_logic, restore the causal rule already demonstrated by the story;
- for closure_integrity, remove/rewrite only the text that reopens an already-completed ending.

Return JSON only:
{
  "replacements": [
    {"span_id": "S001", "replacement_text": "replacement for this sentence only"}
  ],
  "repair_note": "one short sentence"
}
""".strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_gold(natural: dict[str, Any], source_id: str, family: str) -> dict[str, Any]:
    source_rows = [row for row in natural["cases"] if row["source_id"] == source_id]
    if len(source_rows) != 1:
        raise RuntimeError(f"natural_source_not_unique:{source_id}:{len(source_rows)}")
    findings = [
        row for row in source_rows[0]["findings"]
        if row["defect_family"] == family
    ]
    if len(findings) != 1:
        raise RuntimeError(f"natural_gold_not_unique:{source_id}:{family}:{len(findings)}")
    return findings[0]


def matched_finding(
    findings: list[dict[str, Any]],
    *,
    expected_family: str,
    gold_span_ids: list[str],
) -> dict[str, Any] | None:
    gold = set(gold_span_ids)
    for finding in findings:
        if (
            finding["family"] == expected_family
            and gold.intersection(finding["span_ids"])
        ):
            return finding
    return None


def selected_spans(story: str, span_ids: list[str]) -> list[dict[str, str]]:
    rows = segment_story(story)
    by_id = {row["id"]: row["text"] for row in rows}
    missing = [span for span in span_ids if span not in by_id]
    if missing:
        raise RuntimeError("detector_span_missing:" + ",".join(missing))
    return [{"span_id": span, "text": by_id[span]} for span in span_ids]


def apply_replacements(
    story: str,
    targets: list[dict[str, str]],
    replacements: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    allowed = {row["span_id"]: row["text"] for row in targets}
    seen: set[str] = set()
    patches: list[tuple[int, int, str, str]] = []

    if not isinstance(replacements, list) or not replacements:
        raise RuntimeError("repair_replacements_missing")

    for item in replacements:
        if not isinstance(item, dict):
            raise RuntimeError("repair_replacement_not_object")
        span_id = str(item.get("span_id") or "")
        if span_id not in allowed:
            raise RuntimeError(f"repair_span_outside_authority:{span_id}")
        if span_id in seen:
            raise RuntimeError(f"repair_span_duplicate:{span_id}")
        seen.add(span_id)
        old = allowed[span_id]
        if story.count(old) != 1:
            raise RuntimeError(f"repair_target_not_unique:{span_id}:{story.count(old)}")
        start = story.index(old)
        replacement = str(item.get("replacement_text") or "")
        patches.append((start, start + len(old), replacement, span_id))

    repaired = story
    for start, end, replacement, _span_id in sorted(patches, reverse=True):
        repaired = repaired[:start] + replacement + repaired[end:]

    return repaired, {
        "authorized_span_ids": sorted(allowed),
        "patched_span_ids": sorted(seen),
        "outside_authorized_spans_byte_preserved_by_deterministic_patcher": True,
        "patch_count": len(patches),
    }


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]

    fixture = load_json(FIXTURE)
    natural = load_json(NATURAL)
    source_pool = load_json(SOURCE_POOL)
    admission = load_json(CLEAN_ADMISSION)

    source_by_id = {row["source_id"]: row for row in source_pool["sources"]}
    admitted_clean = {
        row["source_id"]
        for row in admission["entries"]
        if row["admitted_as_clean_source"] is True
    }

    results: list[dict[str, Any]] = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, spec in enumerate(fixture["cases"]):
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
            detector_findings, detector_meta = call_detector(
                api_key=api_key,
                model=DETECTOR_MODEL,
                story_id=proof_id,
                story_family=source["family"],
                story_text=story,
                seed=2026150000 + index,
                request_class="editorial_audit",
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
                    model=POST_VERIFY_MODEL,
                    story_id=f"{proof_id}_verify",
                    story_family=source["family"],
                    story_text=story,
                    seed=2026160000 + index,
                    request_class="judge",
                )
                total_cost += meta_cost(verifier_meta)
                row["repair"] = {"skipped": True}
                row["post_verify"] = {
                    "model": POST_VERIFY_MODEL,
                    "findings": verifier_findings,
                    "meta": verifier_meta,
                }
                row["pass"] = not detector_findings and not verifier_findings
                if not row["pass"]:
                    row["failure_stage"] = "CLEAN_FALSE_POSITIVE"
                results.append(row)
                continue

            gold = find_gold(natural, spec["source_id"], spec["expected_family"])
            matched = matched_finding(
                detector_findings,
                expected_family=spec["expected_family"],
                gold_span_ids=gold["span_ids"],
            )
            row["gold_score_only"] = {
                "family": gold["defect_family"],
                "severity": gold["severity"],
                "span_ids": gold["span_ids"],
                "repair_scope": gold["repair_scope"],
            }
            row["detector"]["expected_defect_confirmed"] = matched is not None

            if matched is None:
                row["failure_stage"] = "DETECTION"
                results.append(row)
                continue

            targets = selected_spans(story, matched["span_ids"])
            repair_payload, repair_meta = structured_call(
                api_key=api_key,
                model=REPAIR_MODEL,
                system=REPAIR_SYSTEM,
                payload={
                    "story_id": proof_id,
                    "story_family": source["family"],
                    "full_story_read_only": story,
                    "confirmed_defect": matched,
                    "target_spans": targets,
                },
                seed=2026155000 + index,
                max_tokens=1800,
                request_class="editorial_audit",
            )
            total_cost += meta_cost(repair_meta)

            replacements = repair_payload.get("replacements")
            repaired_story, mechanical = apply_replacements(
                story,
                targets,
                replacements,
            )

            verifier_findings, verifier_meta = call_detector(
                api_key=api_key,
                model=POST_VERIFY_MODEL,
                story_id=f"{proof_id}_repaired",
                story_family=source["family"],
                story_text=repaired_story,
                seed=2026160000 + index,
                request_class="judge",
            )
            total_cost += meta_cost(verifier_meta)

            row["repair"] = {
                "model": REPAIR_MODEL,
                "detector_selected_targets": targets,
                "replacements": replacements,
                "repair_note": repair_payload.get("repair_note"),
                "mechanical_invariants": mechanical,
                "meta": repair_meta,
            }
            row["repaired_story"] = repaired_story
            row["post_verify"] = {
                "model": POST_VERIFY_MODEL,
                "findings": verifier_findings,
                "meta": verifier_meta,
            }
            row["pass"] = (
                mechanical["outside_authorized_spans_byte_preserved_by_deterministic_patcher"]
                and len(verifier_findings) == 0
            )
            if not row["pass"]:
                row["failure_stage"] = "POST_REPAIR_VERIFY"

        except Exception as exc:
            row["failure_stage"] = "RUNTIME"
            row["error"] = f"{type(exc).__name__}: {exc}"

        results.append(row)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "schema_version": "story-defect-natural-e2e-repair-proof-result.v1",
            "status": "IN_PROGRESS",
            "completed": len(results),
            "results": results,
            "total_cost_usd": round(total_cost, 6),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    passes = sum(bool(row.get("pass")) for row in results)
    output = {
        "schema_version": "story-defect-natural-e2e-repair-proof-result.v1",
        "status": "PASS" if passes == len(results) == 5 else "FAIL",
        "models": {
            "detector": DETECTOR_MODEL,
            "repair": REPAIR_MODEL,
            "post_repair_verifier": POST_VERIFY_MODEL,
        },
        "summary": {
            "cases": len(results),
            "passes": passes,
            "failures": len(results) - passes,
            "all_five_pass": passes == 5,
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "summary": output["summary"],
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
        "case_results": [
            {
                "proof_id": row["proof_id"],
                "pass": row.get("pass"),
                "failure_stage": row.get("failure_stage"),
            }
            for row in results
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
