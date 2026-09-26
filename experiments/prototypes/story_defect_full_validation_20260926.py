from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_defect_paid_validator_pilot_20260926 import (
    SYSTEM,
    score_case,
    validate_payload,
)
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import segment_story
from src.story_defect_synthetic_corpus import load_synthetic_corpus

OUT = Path("runs/story-defect-full-validation/result.json")
PRIMARY = {"id":"sonnet5","model":"anthropic/claude-sonnet-5","request_class":"editorial_audit","max_tokens":2200}
SECONDARY = {"id":"haiku45","model":"anthropic/claude-haiku-4.5","request_class":"judge","max_tokens":1800}


def run_validator(api_key: str, case: dict[str, Any], model: dict[str, Any], seed: int) -> dict[str, Any]:
    segments = segment_story(case["text"])
    parsed, meta = structured_call(
        api_key=api_key,
        model=model["model"],
        system=SYSTEM,
        payload={
            "case_id": case["case_id"],
            "story_family": case["family"],
            "story_segments": segments,
        },
        seed=seed,
        max_tokens=model["max_tokens"],
        request_class=model["request_class"],
    )
    findings = validate_payload(parsed, {row["id"] for row in segments})
    score = score_case(case, findings)
    cost = float(((meta.get("cost") or {}).get("usd")) or 0.0)
    return {"model":model["model"],"findings":findings,**score,"cost_usd":cost,"meta":meta}


def same_finding(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a["family"] == b["family"] and bool(set(a["span_ids"]).intersection(b["span_ids"]))


def confirmed_secondary_defects(primary: dict[str, Any], secondary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if secondary is None:
        return []
    confirmed = []
    for p in primary["second_blocking_findings"]:
        if any(same_finding(p, s) for s in secondary["second_blocking_findings"]):
            confirmed.append(p)
    return confirmed


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    corpus = load_synthetic_corpus()
    results = []
    total_cost = 0.0
    secondary_calls = 0
    started = time.perf_counter()

    for index, case in enumerate(corpus["cases"]):
        primary = run_validator(key, case, PRIMARY, 2026099000 + index)
        total_cost += primary["cost_usd"]
        needs_secondary = (
            not primary["intended_defect_confirmed"]
            or bool(primary["second_blocking_findings"])
            or bool(primary["overlap_family_disagreements"])
        )
        secondary = None
        if needs_secondary:
            secondary_calls += 1
            secondary = run_validator(key, case, SECONDARY, 2026101000 + index)
            total_cost += secondary["cost_usd"]

        intended_confirmed = primary["intended_defect_confirmed"] or bool(
            secondary and secondary["intended_defect_confirmed"]
        )
        confirmed_second = confirmed_secondary_defects(primary, secondary)
        persistent_family_ambiguity = bool(
            primary["overlap_family_disagreements"]
            and secondary
            and secondary["overlap_family_disagreements"]
        )

        if not intended_confirmed:
            status = "QUARANTINED_INTENDED_DEFECT_NOT_CONFIRMED"
        elif confirmed_second:
            status = "QUARANTINED_SECOND_BLOCKING_DEFECT_CONFIRMED"
        elif persistent_family_ambiguity:
            status = "QUARANTINED_FAMILY_AMBIGUITY"
        else:
            status = "INDEPENDENTLY_VALIDATED"

        results.append({
            "case_id":case["case_id"],
            "source_id":case["source_id"],
            "recipe_id":case["mutation"]["recipe_id"],
            "dataset_split":case["dataset_split"],
            "expected":{
                "family":case["gold"]["family"],
                "severity":case["gold"]["severity"],
                "span_ids":case["gold"]["span_ids"],
                "repair_scope":case["gold"]["repair_scope"],
            },
            "primary":primary,
            "secondary":secondary,
            "adjudication_used":needs_secondary,
            "intended_defect_confirmed":intended_confirmed,
            "confirmed_second_blocking_findings":confirmed_second,
            "persistent_family_ambiguity":persistent_family_ambiguity,
            "validation_status":status,
        })

    counts: dict[str,int] = {}
    for row in results:
        counts[row["validation_status"]] = counts.get(row["validation_status"],0)+1
    output={
        "schema_version":"story-defect-full-validation.v1",
        "status":"COMPLETE",
        "corpus_schema":corpus["schema_version"],
        "primary_validator":PRIMARY,
        "secondary_validator":SECONDARY,
        "policy":{
            "blind_validation":True,
            "secondary_only_on_primary_disagreement_or_extra_defect":True,
            "single_validator_second_defect_cannot_veto_gold":True,
            "confirmed_second_defect_requires_cross_validator_family_and_span_agreement":True,
        },
        "summary":{
            "case_count":len(results),
            "secondary_calls":secondary_calls,
            "status_counts":counts,
            "validated_count":counts.get("INDEPENDENTLY_VALIDATED",0),
            "quarantined_count":len(results)-counts.get("INDEPENDENTLY_VALIDATED",0),
        },
        "total_cost_usd":round(total_cost,6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
        "results":results,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "summary":output["summary"],
        "total_cost_usd":output["total_cost_usd"],
        "elapsed_seconds":output["elapsed_seconds"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
