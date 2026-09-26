from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_defect_natural_e2e_repair_proof_20260926 import (
    ADJUDICATOR_MODEL,
    blind_detect_with_zero_confirmation,
    call_checklist_detector,
    meta_cost,
)

SOURCE_POOL = Path("experiments/fixtures/story_defect_source_pool.tr-age4.v1.json")
OUT = Path("runs/story-defect-natural-candidate-admission/result.json")

CANDIDATE_SOURCE_IDS = [
    "src_cohort_a_03",
    "src_emotional_guard_03",
    "src_cohort_b_05",
    "src_cohort_a_seed2_04",
    "src_cohort_a_seed2_05",
    "src_fantastical_guard_03",
]

TARGET_ACCEPTED = 2


def overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get("family") == right.get("family")
        and bool(set(left.get("span_ids") or []).intersection(right.get("span_ids") or []))
    )


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    pool = json.loads(SOURCE_POOL.read_text(encoding="utf-8"))
    by_id = {row["source_id"]: row for row in pool["sources"]}

    results: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, source_id in enumerate(CANDIDATE_SOURCE_IDS):
        source = by_id[source_id]
        sonnet_findings, sonnet_meta = blind_detect_with_zero_confirmation(
            api_key=api_key,
            story_id=f"candidate_{source_id}",
            story_family=source["family"],
            story_text=source["story"],
            seed=2026180000 + index,
        )
        total_cost += meta_cost(sonnet_meta)

        luna_findings, luna_meta = call_checklist_detector(
            api_key=api_key,
            model=ADJUDICATOR_MODEL,
            story_id=f"candidate_{source_id}_luna",
            story_family=source["family"],
            story_text=source["story"],
            seed=2026185000 + index,
        )
        total_cost += meta_cost(luna_meta)

        consensus = [
            finding
            for finding in sonnet_findings
            if any(overlap(finding, other) for other in luna_findings)
        ]

        row = {
            "source_id": source_id,
            "story_family": source["family"],
            "sonnet_findings": sonnet_findings,
            "sonnet_meta": sonnet_meta,
            "luna_findings": luna_findings,
            "luna_meta": luna_meta,
            "consensus_findings": consensus,
            "accepted": bool(consensus),
        }
        results.append(row)

        if consensus:
            accepted.append({
                "source_id": source_id,
                "story_family": source["family"],
                "findings": consensus,
            })

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({
            "status": "IN_PROGRESS",
            "target_accepted": TARGET_ACCEPTED,
            "accepted_count": len(accepted),
            "accepted": accepted,
            "results": results,
            "total_cost_usd": round(total_cost, 6),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if len(accepted) >= TARGET_ACCEPTED:
            break

    output = {
        "schema_version": "story-defect-natural-candidate-admission.v1",
        "status": "PASS" if len(accepted) >= TARGET_ACCEPTED else "FAIL",
        "target_accepted": TARGET_ACCEPTED,
        "accepted_count": len(accepted),
        "accepted": accepted,
        "tested_count": len(results),
        "results": results,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "accepted_count": output["accepted_count"],
        "tested_count": output["tested_count"],
        "accepted": output["accepted"],
        "total_cost_usd": output["total_cost_usd"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
