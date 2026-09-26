from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.story_defect_synthetic_corpus import load_synthetic_corpus

OUT = Path("runs/story-defect-paid-validator-pilot/result.json")
MODEL = "anthropic/claude-sonnet-5"
REQUEST_CLASS = "editorial_audit"

SYSTEM = r"""
You are an independent publication-defect verifier for one finished Turkish children's story.
Reader: exact age 4, adult read-aloud.

You are BLIND to any benchmark mutation or expected answer. Audit the current story on its own.

Report ONLY serious or critical semantic defects in these exact families:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Definitions:
physical_feasibility = impossible/unsupported physical action, reach, force, motion, object interaction or affordance.
causal_logic = a material effect/inference/solution does not follow from established causes/rules/evidence.
state_continuity = committed object/action/state resets, relocates, reappears, disappears or contradicts itself without transition.
epistemic_order = a character uses information before they could know it.
spatial_consistency = incompatible location or unsupported movement.
temporal_consistency = contradictory/impossible timing or event order.
response_causality = inability/delay to respond is incorrectly converted into inability to perceive.
closure_integrity = after terminal closure the story reopens the main action/solution/payoff.
canon_integrity = an authoritative durable fact is contradicted or invented.

Rules:
- Zero findings is allowed.
- Do NOT report grammar/style/word-count/repetition/polish.
- Do NOT call fantasy itself a defect when the story consistently establishes the fantasy rule.
- Do NOT invent hidden constraints such as height, strength, distance, or knowledge unless the story establishes them.
- serious = should block publication until corrected.
- critical = central logic/canon/physical rule is fundamentally broken.
- Cite sentence IDs exactly as supplied.
- If two or more spans are required to establish one defect, include all relevant IDs.
- Do not rewrite.

Return JSON only:
{
  "findings": [
    {
      "family": "physical_feasibility|causal_logic|state_continuity|epistemic_order|spatial_consistency|temporal_consistency|response_causality|closure_integrity|canon_integrity",
      "severity": "serious|critical",
      "span_ids": ["S001"],
      "reason": "brief evidence-based reason"
    }
  ]
}
""".strip()


def select_pilot_cases(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    by_recipe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in corpus["cases"]:
        by_recipe[case["mutation"]["recipe_id"]].append(case)

    recipe_ids = sorted(by_recipe)
    selected = []
    for index, recipe_id in enumerate(recipe_ids):
        rows = by_recipe[recipe_id]
        selected.append(rows[index % len(rows)])
    if len(selected) != 15:
        raise RuntimeError(f"pilot_recipe_count_mismatch:{len(selected)}")
    return selected


def validate_payload(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("findings_missing")
    normalized = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise RuntimeError(f"finding_{index}_not_object")
        family = finding.get("family")
        severity = finding.get("severity")
        severity_missing = severity is None
        if severity_missing:
            severity = "serious"
        span_ids = finding.get("span_ids")
        reason = str(finding.get("reason") or "").strip()
        reason_missing = not bool(reason)
        if reason_missing:
            reason = "[validator omitted reason]"
        if family not in DEFECT_FAMILIES:
            raise RuntimeError(f"finding_{index}_family_invalid:{family}")
        if severity not in {"serious", "critical"}:
            raise RuntimeError(f"finding_{index}_severity_invalid:{severity}")
        if not isinstance(span_ids, list) or not span_ids:
            raise RuntimeError(f"finding_{index}_spans_missing")
        if not set(span_ids).issubset(valid_ids):
            raise RuntimeError(f"finding_{index}_spans_invalid:{span_ids}")
        normalized.append({
            "family": family,
            "severity": severity,
            "span_ids": span_ids,
            "reason": reason,
            "reason_missing": reason_missing,
            "severity_missing": severity_missing,
        })
    return normalized


def score_case(case: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    expected_family = case["gold"]["family"]
    expected_spans = set(case["gold"]["span_ids"])

    matching = [
        f for f in findings
        if f["family"] == expected_family
        and expected_spans.intersection(f["span_ids"])
    ]
    overlapping_other_family = [
        f for f in findings
        if f["family"] != expected_family
        and expected_spans.intersection(f["span_ids"])
    ]
    second_blocking = [
        f for f in findings
        if not expected_spans.intersection(f["span_ids"])
    ]

    return {
        "intended_defect_confirmed": bool(matching),
        "matching_findings": matching,
        "overlap_family_disagreements": overlapping_other_family,
        "second_blocking_findings": second_blocking,
        "accept_gold": bool(matching) and not second_blocking,
    }


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    corpus = load_synthetic_corpus()
    cases = select_pilot_cases(corpus)

    results = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, case in enumerate(cases):
        segments = segment_story(case["text"])
        valid_ids = {row["id"] for row in segments}
        parsed, meta = structured_call(
            api_key=key,
            model=MODEL,
            system=SYSTEM,
            payload={
                "case_id": case["case_id"],
                "story_family": case["family"],
                "story_segments": segments,
            },
            seed=2026097000 + index,
            max_tokens=2200,
            request_class=REQUEST_CLASS,
        )
        findings = validate_payload(parsed, valid_ids)
        score = score_case(case, findings)
        cost = float(((meta.get("cost") or {}).get("usd")) or 0.0)
        total_cost += cost
        results.append({
            "case_id": case["case_id"],
            "recipe_id": case["mutation"]["recipe_id"],
            "source_id": case["source_id"],
            "dataset_split": case["dataset_split"],
            "expected": {
                "family": case["gold"]["family"],
                "severity": case["gold"]["severity"],
                "span_ids": case["gold"]["span_ids"],
                "repair_scope": case["gold"]["repair_scope"],
            },
            "validator_findings": findings,
            **score,
            "cost_usd": cost,
            "meta": meta,
        })

    confirmed = sum(1 for row in results if row["intended_defect_confirmed"])
    accepted = sum(1 for row in results if row["accept_gold"])
    second = sum(1 for row in results if row["second_blocking_findings"])
    family_disagreements = sum(1 for row in results if row["overlap_family_disagreements"])
    output = {
        "schema_version": "story-defect-paid-validator-pilot.v1",
        "status": "PAID_VALIDATOR_PILOT",
        "validator": {"model": MODEL, "request_class": REQUEST_CLASS},
        "blind_validation": True,
        "pilot_policy": "one case per frozen corrupt recipe; validator does not receive intended family/span",
        "summary": {
            "case_count": len(results),
            "intended_defect_confirmed": confirmed,
            "accepted_gold": accepted,
            "cases_with_second_blocking_defect": second,
            "cases_with_overlap_family_disagreement": family_disagreements,
            "confirmation_rate": confirmed / len(results),
            "gold_acceptance_rate": accepted / len(results),
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "summary": output["summary"],
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
