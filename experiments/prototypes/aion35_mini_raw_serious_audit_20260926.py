from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

FIXTURE = Path("experiments/fixtures/aion35_mini_raw_story_for_serious_audit_20260926.json")
OUT = Path("runs/aion35-mini-raw-serious-audit/result.json")

DETECTOR_MODEL = "anthropic/claude-sonnet-5"
VERIFY_MODEL = "anthropic/claude-haiku-4.5"
ADJUDICATOR_MODEL = "openai/gpt-5.6-luna"

REPAIR_SCOPES = {"LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"}
SCOPE_ALIASES = {"LOCAL": "LOCAL_REPAIR", "STRUCTURAL": "STRUCTURAL_REPAIR"}

DETECTOR_SYSTEM = r"""
You are a strict publication-defect auditor for one finished English read-aloud story for an exact-age-4 child.

Audit the story blindly. You are not told whether it came from a benchmark, a clean control, or a candidate production writer.

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

For every family return exactly one evaluation with present=true or present=false.

If present=true:
- severity must be serious or critical;
- choose the MINIMUM safe repair scope:
  - LOCAL_REPAIR: a small number of exact supplied sentences can be changed while the rest stays untouched.
  - STRUCTURAL_REPAIR: coordinated changes across a wider story region are required, while the premise/plan can remain.
  - REPLAN: the underlying plan or causal architecture is too broken for bounded editing.
- cite the smallest exact supplied sentence-ID span that proves the defect.

If present=false:
- severity=null, repair_scope=null, span_ids=[];
- briefly explain why the family is not publication-blocking.

Rules:
- Report ONLY serious or critical semantic defects.
- Do NOT report grammar, style, word count, repetition, optional polish, narrator-mindread, mild didactic phrasing, or taste unless it creates a serious semantic/story failure.
- Do not invent hidden physical, spatial, temporal, knowledge, or canon constraints.
- Ordinary childlike personification/metaphor is not a physical defect.
- closure_integrity is serious only when a terminal ending is materially reopened or the promised central payoff is missing in a way that breaks the story.
- canon_integrity is serious only for a durable authoritative fact that is invented, contradicted, or changed.
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

CHECKLIST_SYSTEM = r"""
You are a second independent publication-defect auditor for a finished English read-aloud story for an exact-age-4 child.

Do not assume the first auditor was correct. Evaluate EVERY canonical family separately:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Return only serious/critical semantic defects. Ignore grammar, style, word count, repetition, optional polish, narrator-mindread, mild didactic phrasing, or taste unless it creates a serious story failure.
Do not invent hidden constraints.
Do not rewrite.

For every family return exactly one assessment.

Return JSON only:
{
  "assessments": [
    {
      "family": "physical_feasibility",
      "defect_present": false,
      "severity": null,
      "repair_scope": null,
      "span_ids": [],
      "reason": "brief evidence-based reason"
    }
  ]
}
""".strip()


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


def normalize_primary(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    evaluations = payload.get("evaluations")
    if not isinstance(evaluations, list):
        raise RuntimeError("evaluations_missing")
    seen = set()
    findings = []
    for row in evaluations:
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
        findings.append({
            "family": family,
            "severity": severity,
            "repair_scope": normalize_scope(row.get("repair_scope")),
            "span_ids": spans,
            "reason": str(row.get("reason") or "").strip(),
        })
    if seen != set(DEFECT_FAMILIES):
        raise RuntimeError(f"families_missing:{sorted(set(DEFECT_FAMILIES)-seen)}")
    return findings


def normalize_checklist(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    assessments = payload.get("assessments")
    if not isinstance(assessments, list):
        raise RuntimeError("assessments_missing")
    seen = set()
    findings = []
    for row in assessments:
        family = str(row.get("family") or "")
        if family not in DEFECT_FAMILIES or family in seen:
            raise RuntimeError(f"checklist_family_invalid_or_duplicate:{family}")
        seen.add(family)
        present = row.get("defect_present")
        if not isinstance(present, bool):
            raise RuntimeError(f"checklist_present_invalid:{family}")
        if not present:
            continue
        severity = str(row.get("severity") or "")
        if severity in {"minor", "moderate"}:
            continue
        if severity not in {"serious", "critical"}:
            raise RuntimeError(f"checklist_severity_invalid:{family}:{severity}")
        spans = [str(x) for x in (row.get("span_ids") or [])]
        if not spans or not set(spans).issubset(valid_ids):
            raise RuntimeError(f"checklist_span_invalid:{family}:{spans}")
        findings.append({
            "family": family,
            "severity": severity,
            "repair_scope": normalize_scope(row.get("repair_scope")),
            "span_ids": spans,
            "reason": str(row.get("reason") or "").strip(),
        })
    if seen != set(DEFECT_FAMILIES):
        raise RuntimeError(f"checklist_families_missing:{sorted(set(DEFECT_FAMILIES)-seen)}")
    return findings


def primary_call(api_key: str, model: str, segments: list[dict[str, Any]], seed: int):
    payload, meta = structured_call(
        api_key=api_key,
        model=model,
        system=DETECTOR_SYSTEM,
        payload={
            "story_id": "AION35_MINI_RAW",
            "story_family": "curiosity_discovery",
            "language": "en",
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "audit_families": list(DEFECT_FAMILIES),
            "story_segments": segments,
        },
        seed=seed,
        max_tokens=2600,
        request_class="editorial_audit",
    )
    return normalize_primary(payload, {x["id"] for x in segments}), meta


def checklist_call(api_key: str, model: str, segments: list[dict[str, Any]], seed: int, request_class: str):
    payload, meta = structured_call(
        api_key=api_key,
        model=model,
        system=CHECKLIST_SYSTEM,
        payload={
            "story_id": "AION35_MINI_RAW",
            "story_family": "curiosity_discovery",
            "language": "en",
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "story_segments": segments,
        },
        seed=seed,
        max_tokens=3600,
        request_class=request_class,
    )
    return normalize_checklist(payload, {x["id"] for x in segments}), meta


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    story = fixture["story"]
    segments = segment_story(story)
    started = time.perf_counter()
    total_cost = 0.0

    primary_findings, primary_meta = primary_call(api_key, DETECTOR_MODEL, segments, 2026092611)
    total_cost += meta_cost(primary_meta)

    checklist_findings = []
    checklist_meta = None
    selected_findings = primary_findings
    selected_round = "blind_primary"
    if not primary_findings:
        checklist_findings, checklist_meta = checklist_call(
            api_key, DETECTOR_MODEL, segments, 2026092612, "editorial_audit"
        )
        total_cost += meta_cost(checklist_meta)
        selected_findings = checklist_findings
        selected_round = "blind_family_by_family_zero_confirmation" if checklist_findings else "confirmed_zero"

    verifier_findings, verifier_meta = primary_call(api_key, VERIFY_MODEL, segments, 2026092613)
    total_cost += meta_cost(verifier_meta)

    adjudicator_findings, adjudicator_meta = checklist_call(
        api_key, ADJUDICATOR_MODEL, segments, 2026092614, "editorial_audit"
    )
    total_cost += meta_cost(adjudicator_meta)

    repair_required = bool(selected_findings or verifier_findings)
    qualification_clean = not repair_required

    result = {
        "schema_version": "aion35-mini-raw-serious-audit-result.v1",
        "source": fixture,
        "models": {
            "primary_detector": DETECTOR_MODEL,
            "zero_confirmation": DETECTOR_MODEL,
            "independent_verifier": VERIFY_MODEL,
            "diagnostic_adjudicator": ADJUDICATOR_MODEL,
        },
        "primary_detector": {
            "findings": primary_findings,
            "meta": primary_meta,
        },
        "zero_confirmation": {
            "ran": not bool(primary_findings),
            "findings": checklist_findings,
            "meta": checklist_meta,
            "selected_round": selected_round,
        },
        "selected_detector_findings": selected_findings,
        "independent_verifier": {
            "findings": verifier_findings,
            "meta": verifier_meta,
        },
        "diagnostic_adjudicator": {
            "findings": adjudicator_findings,
            "meta": adjudicator_meta,
            "qualification_effect": "DIAGNOSTIC_ONLY",
        },
        "decision": {
            "qualification_clean": qualification_clean,
            "repair_required_for_publication_blockers": repair_required,
            "publication_blocking_findings": selected_findings + verifier_findings,
            "minor_or_moderate_polish_not_evaluated_as_blocking": True,
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "primary_findings": primary_findings,
        "selected_round": selected_round,
        "selected_detector_findings": selected_findings,
        "verifier_findings": verifier_findings,
        "diagnostic_adjudicator_findings": adjudicator_findings,
        "qualification_clean": qualification_clean,
        "repair_required_for_publication_blockers": repair_required,
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
