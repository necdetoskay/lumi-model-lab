from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import (
    structured_call,
)
from src.story_defect_corpus import assign_source_splits, load_source_pool
from src.story_defect_detection import DEFECT_FAMILIES, segment_story


AUDITORS = [
    {
        "id": "sonnet5",
        "model": "anthropic/claude-sonnet-5",
        "request_class": "editorial_audit",
        "max_tokens": 2800,
        "seed_base": 2026096100,
    },
    {
        "id": "haiku45",
        "model": "anthropic/claude-haiku-4.5",
        "request_class": "judge",
        "max_tokens": 2500,
        "seed_base": 2026096200,
    },
]

SYSTEM = r"""
You are an independent publication-risk auditor for one finished Turkish children's story.

Reader contract:
- exact age 4
- adult read-aloud
- nominal 500 words is a SOFT target
- do not reward or punish length by itself

Your task is NOT literary scoring and NOT rewriting.
Look only for material defects in these families:

- physical_feasibility: impossible or unsupported physical action/affordance
- causal_logic: an important effect, inference, solution, or outcome does not follow from established causes/rules/evidence
- state_continuity: an object/completed action/committed state resets, moves, reappears, disappears, or contradicts itself without transition
- epistemic_order: a character uses information before they could know it
- spatial_consistency: incompatible location or unsupported movement
- temporal_consistency: contradictory or impossible timing/order
- response_causality: inability/delay to respond is incorrectly turned into inability to perceive
- closure_integrity: after terminal closure the story reopens action, adds a second payoff, or appends a weakening prop/action
- canon_integrity: authoritative durable facts are invented or contradicted

Rules:
- Do not invent a defect quota. Zero findings is valid.
- Do not report style preferences, word-count deviation, repetition, or minor wording unless they create one of the listed material defect families.
- serious = should block publication until corrected.
- critical = core story/canon/physical logic is materially broken and unsafe to publish as-is.
- moderate/minor may be recorded for audit context but do NOT make the source fail clean-source admission.
- quote must be an exact short quote copied from the supplied story.
- If a defect needs two spans to prove, include both exact quotes.
- You are auditing the current story only. Do not infer experiment identity or compare to another story.
- Never rewrite the story.

Return JSON only:
{
  "findings": [
    {
      "family": "physical_feasibility|causal_logic|state_continuity|epistemic_order|spatial_consistency|temporal_consistency|response_causality|closure_integrity|canon_integrity",
      "severity": "minor|moderate|serious|critical",
      "quotes": ["exact quote"],
      "reason": "brief evidence-based reason"
    }
  ],
  "clean_for_serious_critical": true,
  "summary": "one or two short sentences"
}
""".strip()


def quote_to_span_ids(story: str, quote: str) -> list[str]:
    quote = quote.strip()
    if not quote:
        return []
    segments = segment_story(story)
    direct = [row["id"] for row in segments if quote in row["text"] or row["text"] in quote]
    if direct:
        return direct
    story_index = story.find(quote)
    if story_index < 0:
        return []
    result = []
    cursor = 0
    for row in segments:
        pos = story.find(row["text"], cursor)
        if pos < 0:
            continue
        end = pos + len(row["text"])
        if max(pos, story_index) < min(end, story_index + len(quote)):
            result.append(row["id"])
        cursor = end
    return result


def validate_audit(payload: dict[str, Any], story: str) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("audit_findings_missing")

    normalized = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise RuntimeError(f"audit_finding_{index}_not_object")
        family = finding.get("family")
        severity = finding.get("severity")
        quotes = finding.get("quotes")
        reason = str(finding.get("reason") or "").strip()
        if family not in DEFECT_FAMILIES:
            raise RuntimeError(f"audit_finding_{index}_family_invalid:{family}")
        if severity not in {"minor", "moderate", "serious", "critical"}:
            raise RuntimeError(f"audit_finding_{index}_severity_invalid:{severity}")
        if not isinstance(quotes, list) or not quotes:
            raise RuntimeError(f"audit_finding_{index}_quotes_missing")
        if not reason:
            raise RuntimeError(f"audit_finding_{index}_reason_missing")

        span_ids: list[str] = []
        for quote in quotes:
            quote = str(quote).strip()
            if not quote or quote not in story:
                raise RuntimeError(f"audit_finding_{index}_quote_not_exact")
            span_ids.extend(quote_to_span_ids(story, quote))
        if not span_ids:
            raise RuntimeError(f"audit_finding_{index}_span_mapping_failed")

        normalized.append(
            {
                "family": family,
                "severity": severity,
                "quotes": [str(q) for q in quotes],
                "span_ids": sorted(set(span_ids)),
                "reason": reason,
            }
        )

    blocking = [f for f in normalized if f["severity"] in {"serious", "critical"}]
    declared = payload.get("clean_for_serious_critical")
    if not isinstance(declared, bool):
        raise RuntimeError("audit_clean_flag_invalid")
    if declared != (len(blocking) == 0):
        raise RuntimeError("audit_clean_flag_disagrees_with_findings")
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--split", choices=["calibration", "held_out", "all"], default="calibration")
    args = parser.parse_args()

    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    rows = assign_source_splits(load_source_pool())
    if args.split != "all":
        rows = [row for row in rows if row["dataset_split"] == args.split]
    rows = rows[: args.limit] if args.limit > 0 else rows

    started = time.perf_counter()
    total_cost = 0.0
    results = []

    for source_index, row in enumerate(rows):
        audits = {}
        for auditor_index, auditor in enumerate(AUDITORS):
            parsed, meta = structured_call(
                api_key=key,
                model=auditor["model"],
                system=SYSTEM,
                payload={
                    "source_id": row["source_id"],
                    "family": row["family"],
                    "exact_age": row["exact_age"],
                    "reading_mode": row["reading_mode"],
                    "story_segments": segment_story(row["story"]),
                    "story": row["story"],
                },
                seed=auditor["seed_base"] + source_index * 10 + auditor_index,
                max_tokens=auditor["max_tokens"],
                request_class=auditor["request_class"],
            )
            findings = validate_audit(parsed, row["story"])
            cost = float(((meta.get("cost") or {}).get("usd")) or 0.0)
            total_cost += cost
            blocking = [f for f in findings if f["severity"] in {"serious", "critical"}]
            audits[auditor["id"]] = {
                "model": auditor["model"],
                "findings": findings,
                "blocking_count": len(blocking),
                "clean_for_serious_critical": len(blocking) == 0,
                "summary": parsed.get("summary"),
                "cost_usd": cost,
                "meta": meta,
            }

        admitted = all(a["clean_for_serious_critical"] for a in audits.values())
        results.append(
            {
                "source_id": row["source_id"],
                "scenario_group": row["scenario_group"],
                "family": row["family"],
                "dataset_split": row["dataset_split"],
                "story_sha256": row["story_sha256"],
                "admitted_as_clean_source": admitted,
                "admission_policy": "both_independent_auditors_have_zero_serious_or_critical_findings",
                "audits": audits,
                "provenance": row["provenance"],
            }
        )

    result = {
        "schema_version": "story-defect-clean-source-audit-result.v1",
        "auditors": [a["model"] for a in AUDITORS],
        "position_independent": True,
        "source_generation_calls": 0,
        "split": args.split,
        "source_count": len(results),
        "admitted_count": sum(1 for row in results if row["admitted_as_clean_source"]),
        "quarantined_count": sum(1 for row in results if not row["admitted_as_clean_source"]),
        "results": results,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-defect-clean-source-audit")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "source_count": result["source_count"],
                "admitted_count": result["admitted_count"],
                "quarantined_count": result["quarantined_count"],
                "total_cost_usd": result["total_cost_usd"],
                "elapsed_seconds": result["elapsed_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
