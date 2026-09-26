from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.story_defect_synthetic_corpus import load_synthetic_corpus

OUT = Path("runs/story-defect-paid-validator-adjudication/result.json")
MODEL = "anthropic/claude-haiku-4.5"
CASE_IDS = [
    "src_cohort_a_seed2_01__causal_effect_without_cause",
    "src_cohort_b_03__physical_solid_barrier_violation",
    "src_emotional_guard_01__response_perception_conflation",
    "src_cohort_a_02__temporal_order_contradiction",
]

SYSTEM = r"""
Blindly audit one Turkish age-4 read-aloud story for serious/critical semantic defects.
Do not infer benchmark intent. Report only concrete publication-blocking defects in:
physical_feasibility, causal_logic, state_continuity, epistemic_order,
spatial_consistency, temporal_consistency, response_causality,
closure_integrity, canon_integrity.

Do not report style, grammar, length, repetition, or optional polish.
Do not invent hidden constraints. Fantasy is not itself a defect if internally consistent.
A character may change their mind after receiving new information; that is not a state reset.
A solved mystery may continue into harmless play; that is not a closure defect unless the main unresolved problem is reopened.
Use exact supplied sentence IDs. Do not rewrite.

JSON only:
{"findings":[{"family":"...","severity":"serious|critical","span_ids":["S001"],"reason":"..."}]}
""".strip()


def validate(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("findings_missing")
    out = []
    for i, f in enumerate(findings):
        if f.get("family") not in DEFECT_FAMILIES:
            raise RuntimeError(f"family_invalid:{i}")
        if f.get("severity") not in {"serious", "critical"}:
            raise RuntimeError(f"severity_invalid:{i}")
        spans = f.get("span_ids")
        if not isinstance(spans, list) or not spans or not set(spans).issubset(valid_ids):
            raise RuntimeError(f"span_invalid:{i}:{spans}")
        reason = str(f.get("reason") or "").strip()
        if not reason:
            raise RuntimeError(f"reason_missing:{i}")
        out.append({"family":f["family"],"severity":f["severity"],"span_ids":spans,"reason":reason})
    return out


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    corpus = load_synthetic_corpus()
    by_id = {c["case_id"]: c for c in corpus["cases"]}

    rows = []
    total_cost = 0.0
    started = time.perf_counter()
    for index, case_id in enumerate(CASE_IDS):
        case = by_id[case_id]
        segments = segment_story(case["text"])
        parsed, meta = structured_call(
            api_key=key,
            model=MODEL,
            system=SYSTEM,
            payload={"case_id":case_id,"story_family":case["family"],"story_segments":segments},
            seed=2026098000+index,
            max_tokens=1800,
            request_class="judge",
        )
        findings = validate(parsed,{r["id"] for r in segments})
        expected_spans=set(case["gold"]["span_ids"])
        intended=[f for f in findings if f["family"]==case["gold"]["family"] and expected_spans.intersection(f["span_ids"])]
        overlap_other=[f for f in findings if f["family"]!=case["gold"]["family"] and expected_spans.intersection(f["span_ids"])]
        second=[f for f in findings if not expected_spans.intersection(f["span_ids"])]
        cost=float(((meta.get("cost") or {}).get("usd")) or 0.0)
        total_cost += cost
        rows.append({
            "case_id":case_id,
            "expected":{"family":case["gold"]["family"],"span_ids":case["gold"]["span_ids"]},
            "findings":findings,
            "intended_confirmed":bool(intended),
            "overlap_family_disagreements":overlap_other,
            "second_blocking_findings":second,
            "cost_usd":cost,
        })

    output={
      "schema_version":"story-defect-paid-validator-adjudication.v1",
      "validator":MODEL,
      "blind_validation":True,
      "total_cost_usd":round(total_cost,6),
      "elapsed_seconds":round(time.perf_counter()-started,3),
      "results":rows,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
      "total_cost_usd":output["total_cost_usd"],
      "results":[
        {
          "case_id":r["case_id"],
          "intended_confirmed":r["intended_confirmed"],
          "overlap_family_disagreement":bool(r["overlap_family_disagreements"]),
          "second_blocking_count":len(r["second_blocking_findings"])
        } for r in rows
      ]
    },ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
