from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from experiments.prototypes.story_defect_paid_validation_batch_20260926 import (
    ADJUDICATOR_MODEL,
    PRIMARY_MODEL,
    call_validator,
    extra_confirmed,
    inspect_findings,
)

CORPUS = Path("experiments/fixtures/story_defect_response_supplement.tr-age4.v2.json")
OUT = Path("runs/story-defect-response-supplement-v2-validation/result.json")


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    results = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, case in enumerate(payload["cases"]):
        primary_findings, primary_meta, primary_cost = call_validator(
            key=key,
            model=PRIMARY_MODEL,
            request_class="editorial_audit",
            max_tokens=2200,
            seed=2026120000 + index,
            case=case,
        )
        total_cost += primary_cost
        p = inspect_findings(case, primary_findings)

        needs_adjudication = (
            not p["intended"] or bool(p["overlap_other"]) or bool(p["second"])
        )
        adjudicator_findings = []
        adjudicator_meta = None
        adjudicator_cost = 0.0
        a = {"intended": [], "overlap_other": [], "second": []}
        adjudicator_error = None

        if needs_adjudication:
            try:
                adjudicator_findings, adjudicator_meta, adjudicator_cost = call_validator(
                    key=key,
                    model=ADJUDICATOR_MODEL,
                    request_class="judge",
                    max_tokens=1800,
                    seed=2026125000 + index,
                    case=case,
                )
                total_cost += adjudicator_cost
                a = inspect_findings(case, adjudicator_findings)
            except Exception as exc:
                adjudicator_error = f"{type(exc).__name__}: {exc}"

        intended_confirmed = bool(p["intended"]) or bool(a["intended"])
        primary_alt = {f["family"] for f in p["overlap_other"]}
        secondary_alt = {f["family"] for f in a["overlap_other"]}
        taxonomy_unresolved = bool(primary_alt.intersection(secondary_alt))
        confirmed_extra = (
            extra_confirmed(p["second"], a["second"])
            if needs_adjudication and adjudicator_error is None
            else []
        )

        status = (
            "VALIDATED_GOLD"
            if intended_confirmed and not taxonomy_unresolved and not confirmed_extra
            else "NEEDS_MANUAL_ADJUDICATION"
        )

        results.append({
            "case_id": case["case_id"],
            "source_id": case["source_id"],
            "dataset_split": case["dataset_split"],
            "expected": case["gold"],
            "primary": {
                "model": PRIMARY_MODEL,
                "findings": primary_findings,
                "cost_usd": primary_cost,
                "meta": primary_meta,
            },
            "adjudication": None if not needs_adjudication else {
                "model": ADJUDICATOR_MODEL,
                "findings": adjudicator_findings,
                "error": adjudicator_error,
                "cost_usd": adjudicator_cost,
                "meta": adjudicator_meta,
            },
            "final": {
                "status": status,
                "intended_confirmed": intended_confirmed,
                "taxonomy_unresolved": taxonomy_unresolved,
                "confirmed_extra_blocking_findings": confirmed_extra,
            },
        })

    validated = sum(1 for row in results if row["final"]["status"] == "VALIDATED_GOLD")
    output = {
        "schema_version": "story-defect-response-supplement-validation.v2",
        "status": "COMPLETE",
        "case_count": len(results),
        "summary": {
            "validated_gold": validated,
            "needs_manual_adjudication": len(results) - validated,
            "validation_rate": validated / len(results),
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
