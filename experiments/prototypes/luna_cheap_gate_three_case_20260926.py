from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

FIXTURE = Path("experiments/fixtures/luna_cheap_gate_three_case_20260926.json")
OUT = Path("runs/luna-cheap-gate-three-case/result.json")
MODEL = "openai/gpt-5.6-luna"

SYSTEM = r"""
You are a strict, low-cost publication-blocker gate for children's stories.
The story may be Turkish or English and is intended for an exact-age-4 read-aloud audience.

Evaluate EVERY canonical semantic defect family separately:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Report ONLY serious or critical semantic defects. Ignore grammar, style, length, repetition, optional polish, narrator-mindread, mild didactic phrasing, and taste unless they cause a serious story failure.

Important:
- Do not invent hidden physical, spatial, temporal, knowledge, or canon constraints.
- Ordinary fantasy/personification is not a defect when internally coherent.
- response_causality: busy hands or task load must not be treated as physical inability to hear or answer. If unexplained silence materially drives misunderstanding, flag it unless the story explicitly establishes a voluntary choice to postpone answering.
- state_continuity: flag committed object/action states that contradict or reset without a transition.
- closure_integrity: flag only material reopening/breakage of an otherwise terminal ending.
- Do not rewrite the story.

For every family return exactly one evaluation.

Return JSON only:
{
  "evaluations":[
    {
      "family":"physical_feasibility",
      "present":false,
      "severity":null,
      "repair_scope":null,
      "span_ids":[],
      "reason":"brief evidence-based reason"
    }
  ]
}
""".strip()

VALID_SCOPES = {"LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN", None}

def meta_cost(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    cost = meta.get("cost")
    if isinstance(cost, dict) and isinstance(cost.get("usd"), (int, float)):
        return float(cost["usd"])
    if isinstance(cost, (int, float)):
        return float(cost)
    return 0.0

def normalize(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    rows = payload.get("evaluations")
    if not isinstance(rows, list):
        raise RuntimeError("evaluations_missing")
    seen = set()
    findings = []
    for row in rows:
        family = str(row.get("family") or "")
        if family not in DEFECT_FAMILIES or family in seen:
            raise RuntimeError(f"family_invalid_or_duplicate:{family}")
        seen.add(family)
        present = row.get("present")
        if not isinstance(present, bool):
            raise RuntimeError(f"present_invalid:{family}")
        if not present:
            continue
        severity = str(row.get("severity") or "")
        if severity not in {"serious", "critical"}:
            raise RuntimeError(f"severity_invalid:{family}:{severity}")
        spans = [str(x) for x in (row.get("span_ids") or [])]
        if not spans or not set(spans).issubset(valid_ids):
            raise RuntimeError(f"span_invalid:{family}:{spans}")
        scope = row.get("repair_scope")
        if scope in {"LOCAL", "STRUCTURAL"}:
            scope = {"LOCAL":"LOCAL_REPAIR","STRUCTURAL":"STRUCTURAL_REPAIR"}[scope]
        if scope not in {"LOCAL_REPAIR","STRUCTURAL_REPAIR","REPLAN"}:
            raise RuntimeError(f"scope_invalid:{family}:{scope}")
        findings.append({
            "family": family,
            "severity": severity,
            "repair_scope": scope,
            "span_ids": spans,
            "reason": str(row.get("reason") or "").strip(),
        })
    if seen != set(DEFECT_FAMILIES):
        raise RuntimeError(f"families_missing:{sorted(set(DEFECT_FAMILIES)-seen)}")
    return findings

def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    results = []
    total_cost = 0.0
    started = time.perf_counter()

    for i, case in enumerate(fixture["cases"]):
        segments = segment_story(case["story"])
        payload, meta = structured_call(
            api_key=api_key,
            model=MODEL,
            system=SYSTEM,
            payload={
                "case_id": case["case_id"],
                "language": case["language"],
                "story_family": case["family"],
                "exact_age": 4,
                "reading_mode": "READ_ALOUD",
                "audit_families": list(DEFECT_FAMILIES),
                "story_segments": segments,
            },
            seed=2026092620 + i,
            max_tokens=2600,
            request_class="editorial_audit",
        )
        total_cost += meta_cost(meta)
        findings = normalize(payload, {x["id"] for x in segments})

        row = {
            "case_id": case["case_id"],
            "kind": case["kind"],
            "findings": findings,
            "cost_usd": round(meta_cost(meta), 6),
            "pass": False,
        }

        if case["kind"] == "clean":
            row["pass"] = len(findings) == 0
            row["scoring"] = {"clean_zero_findings": row["pass"]}
        else:
            expected_spans = set(case["expected_span_ids"])
            matched = next(
                (
                    f for f in findings
                    if f["family"] == case["expected_family"]
                    and expected_spans.intersection(f["span_ids"])
                ),
                None,
            )
            row["scoring"] = {
                "expected_family": case["expected_family"],
                "expected_span_ids": case["expected_span_ids"],
                "family_and_span_overlap": matched is not None,
                "detected_scope": matched["repair_scope"] if matched else None,
                "expected_scope": case["expected_repair_scope"],
            }
            row["pass"] = matched is not None

        results.append(row)

    passes = sum(1 for r in results if r["pass"])
    output = {
        "schema_version": "luna-cheap-gate-three-case-result.v1",
        "model": MODEL,
        "status": "PASS" if passes == len(results) else "FAIL",
        "summary": {
            "cases": len(results),
            "passes": passes,
            "failures": len(results)-passes,
            "all_three_pass": passes == len(results),
        },
        "results": results,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter()-started, 3),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
