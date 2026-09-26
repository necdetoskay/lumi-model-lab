from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import parse_cost, parse_usage
from src.story_defect_corpus import assign_source_splits, load_source_pool
from src.story_defect_detection import segment_story, validate_defect_finding

OUT = Path("runs/story-defect-clean-audit-pilot/result.json")

PILOT_SOURCE_IDS = [
    "src_cohort_a_01",
    "src_cohort_a_02",
    "src_cohort_a_03",
    "src_cohort_a_04",
    "src_cohort_a_05",
]

AUDITORS = [
    {
        "id": "sonnet5",
        "model": "anthropic/claude-sonnet-5",
        "request_class": "editorial_audit",
        "temperature": 0.0,
        "max_tokens": 3500,
    },
    {
        "id": "haiku45",
        "model": "anthropic/claude-haiku-4.5",
        "request_class": "judge",
        "temperature": 0.0,
        "max_tokens": 2500,
    },
]

SYSTEM = r"""
You are an independent publication-defect auditor for a Turkish read-aloud story for an exact-age-4 child.

Your task is NOT literary scoring and NOT rewriting. Find only concrete semantic defects in these exact families:

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
- physical_feasibility: an action, body movement, object interaction, reach, force, motion or physical affordance is impossible or unsupported by the established story conditions.
- causal_logic: an important effect, inference, solution or outcome does not follow from established causes/rules/evidence.
- state_continuity: an object, completed action or committed state silently resets, relocates, disappears, reappears or contradicts itself without a transition.
- epistemic_order: a character uses information before they could have observed, learned, inferred or been told it.
- spatial_consistency: a character/object occupies incompatible locations or traverses space without support.
- temporal_consistency: event order or duration contradicts the story timeline.
- response_causality: inability/delay in responding is incorrectly converted into inability to perceive, e.g. busy hands imply inability to hear.
- closure_integrity: after terminal closure the story reopens the main action, adds a second payoff, or appends a new action/prop tail.
- canon_integrity: prose contradicts or invents an authoritative durable fact supplied in constraints.

Important:
- Do not report style preferences, word-count deviation, ordinary imagination, metaphor, harmless simplification, dialogue taste or optional polish.
- Do not invent hidden physical constraints. A child is not "too short/weak" unless the text establishes that.
- Do not treat a delayed reply as failed hearing unless the prose explicitly makes that causal claim.
- A finding must cite exact sentence IDs from the supplied story.
- severity=serious only when the defect materially breaks story logic/coherence for publication.
- severity=critical only for a fundamental contradiction that invalidates the central solution/canon.
- If evidence is ambiguous, do not manufacture a defect; set uncertain=true only when there is a concrete suspicious span that genuinely needs adjudication.
- Do not rewrite any sentence.

Return JSON only:
{
  "verdict": "NO_BLOCKING_DEFECT_FOUND|BLOCKING_DEFECT_FOUND|NEEDS_ADJUDICATION",
  "defects": [
    {
      "family": "physical_feasibility|causal_logic|state_continuity|epistemic_order|spatial_consistency|temporal_consistency|response_causality|closure_integrity|canon_integrity",
      "severity": "minor|moderate|serious|critical",
      "span_ids": ["S001"],
      "reason": "concise evidence-based reason",
      "repair_scope": "NO_REPAIR|LOCAL_REPAIR|STRUCTURAL_REPAIR|REPLAN",
      "uncertain": false
    }
  ],
  "summary": "one concise sentence"
}
""".strip()


def validate_audit(payload: dict[str, Any], valid_span_ids: set[str]) -> list[str]:
    errors: list[str] = []
    verdict = payload.get("verdict")
    if verdict not in {
        "NO_BLOCKING_DEFECT_FOUND",
        "BLOCKING_DEFECT_FOUND",
        "NEEDS_ADJUDICATION",
    }:
        errors.append("verdict_invalid")
    defects = payload.get("defects")
    if not isinstance(defects, list):
        return errors + ["defects_missing"]
    for index, finding in enumerate(defects):
        if not isinstance(finding, dict):
            errors.append(f"defect_{index}_not_object")
            continue
        finding_errors = validate_defect_finding(finding)
        errors.extend(f"defect_{index}:{error}" for error in finding_errors)
        for span_id in finding.get("span_ids") or []:
            if span_id not in valid_span_ids:
                errors.append(f"defect_{index}:unknown_span:{span_id}")
        if not isinstance(finding.get("uncertain"), bool):
            errors.append(f"defect_{index}:uncertain_invalid")
    return errors


def blocking_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        finding
        for finding in payload.get("defects") or []
        if finding.get("severity") in {"serious", "critical"}
    ]


def classify_source(audits: list[dict[str, Any]]) -> str:
    if any(audit["validation_errors"] for audit in audits):
        return "AUDIT_INVALID"
    if any(
        audit["payload"].get("verdict") == "NEEDS_ADJUDICATION"
        or any(f.get("uncertain") for f in audit["payload"].get("defects") or [])
        for audit in audits
    ):
        return "NEEDS_ADJUDICATION"

    blocking = [blocking_findings(audit["payload"]) for audit in audits]
    if all(not findings for findings in blocking):
        return "DUAL_AUDIT_NO_BLOCKING_DEFECT_FOUND"
    if all(findings for findings in blocking):
        return "BLOCKING_DEFECT_CONFIRMED"
    return "NEEDS_ADJUDICATION"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ids", nargs="*", default=PILOT_SOURCE_IDS)
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    pool = load_source_pool()
    rows = {row["source_id"]: row for row in assign_source_splits(pool)}
    missing = [source_id for source_id in args.source_ids if source_id not in rows]
    if missing:
        raise RuntimeError("Unknown source IDs: " + ", ".join(missing))

    results: list[dict[str, Any]] = []
    total_cost = 0.0
    total_latency = 0.0

    for source_index, source_id in enumerate(args.source_ids):
        source = rows[source_id]
        segments = segment_story(source["story"])
        span_ids = {row["id"] for row in segments}
        user_prompt = json.dumps(
            {
                "source_id": source_id,
                "family": source["family"],
                "exact_age": source["exact_age"],
                "reading_mode": source["reading_mode"],
                "authoritative_constraints": {
                    "premise": source.get("premise"),
                    "provenance": source["provenance"],
                },
                "story_segments": segments,
            },
            ensure_ascii=False,
            indent=2,
        )

        audits: list[dict[str, Any]] = []
        for auditor_index, auditor in enumerate(AUDITORS):
            started = time.perf_counter()
            payload, body, request, parse_failures = call_structured_json_with_retry(
                api_key=api_key,
                model=auditor["model"],
                system_prompt=SYSTEM,
                user_prompt=user_prompt,
                temperature=auditor["temperature"],
                max_tokens=auditor["max_tokens"],
                seed=202609260 + source_index * 10 + auditor_index,
                request_class=auditor["request_class"],
            )
            latency = time.perf_counter() - started
            cost = float(parse_cost(body).usd or 0.0)
            total_cost += cost
            total_latency += latency
            validation_errors = validate_audit(payload, span_ids)
            audits.append(
                {
                    "auditor_id": auditor["id"],
                    "model": auditor["model"],
                    "request_class": auditor["request_class"],
                    "payload": payload,
                    "validation_errors": validation_errors,
                    "parse_failures": parse_failures,
                    "usage": parse_usage(body).model_dump(mode="json"),
                    "cost_usd": cost,
                    "latency_seconds": round(latency, 3),
                    "request_effective": {
                        "temperature": request.get("temperature"),
                        "max_tokens": request.get("max_tokens"),
                        "reasoning": request.get("reasoning"),
                        "response_format": request.get("response_format"),
                    },
                }
            )

        results.append(
            {
                "source_id": source_id,
                "scenario_group": source["scenario_group"],
                "family": source["family"],
                "dataset_split": source["dataset_split"],
                "story_sha256": source["story_sha256"],
                "audits": audits,
                "source_classification": classify_source(audits),
            }
        )

    summary: dict[str, int] = {}
    for row in results:
        key = row["source_classification"]
        summary[key] = summary.get(key, 0) + 1

    output = {
        "schema_version": "story-defect-clean-source-audit-pilot.v1",
        "status": "PILOT_EVIDENCE",
        "policy": {
            "single_auditor_clean_pass_is_insufficient": True,
            "no_threshold_selection_from_held_out": True,
            "source_story_not_mutated": True,
            "blocking_severities": ["serious", "critical"],
        },
        "auditors": AUDITORS,
        "source_ids": args.source_ids,
        "summary": summary,
        "cases": results,
        "total_cost_usd": round(total_cost, 9),
        "total_model_latency_seconds": round(total_latency, 3),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "summary": summary,
        "total_cost_usd": output["total_cost_usd"],
        "total_model_latency_seconds": output["total_model_latency_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
