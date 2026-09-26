from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_defect_natural_e2e_repair_proof_20260926 import (
    ADJUDICATOR_MODEL,
    VERIFY_MODEL,
    call_checklist_detector,
    meta_cost,
)
from src.story_defect_detection import segment_story

FIXTURE = Path("experiments/fixtures/story_defect_natural_v11_candidate_pool.v0.1.json")
OUT = Path("runs/story-defect-natural-v11-candidate-adjudication/result.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a["family"] == b["family"]
        and bool(set(a["span_ids"]).intersection(b["span_ids"]))
    )


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = load_json(FIXTURE)

    started = time.perf_counter()
    total_cost = 0.0
    results: list[dict[str, Any]] = []

    for index, candidate in enumerate(fixture["candidates"]):
        story = candidate["story"]
        story_id = candidate["candidate_id"]

        luna_findings, luna_meta = call_checklist_detector(
            api_key=api_key,
            model=ADJUDICATOR_MODEL,
            story_id=f"{story_id}_luna_blind",
            story_family=candidate["family"],
            story_text=story,
            seed=2026180000 + index * 100,
        )
        total_cost += meta_cost(luna_meta)

        haiku_findings, haiku_meta = call_checklist_detector(
            api_key=api_key,
            model=VERIFY_MODEL,
            story_id=f"{story_id}_haiku_blind",
            story_family=candidate["family"],
            story_text=story,
            seed=2026180001 + index * 100,
        )
        total_cost += meta_cost(haiku_meta)

        agreements: list[dict[str, Any]] = []
        for luna in luna_findings:
            for haiku in haiku_findings:
                if not overlaps(luna, haiku):
                    continue
                agreements.append({
                    "family": luna["family"],
                    "luna": luna,
                    "haiku": haiku,
                    "span_union": sorted(
                        set(luna["span_ids"]) | set(haiku["span_ids"])
                    ),
                    "span_intersection": sorted(
                        set(luna["span_ids"]) & set(haiku["span_ids"])
                    ),
                    "repair_scope_match": (
                        luna["repair_scope"] == haiku["repair_scope"]
                    ),
                })

        consensus_families = sorted({row["family"] for row in agreements})
        scope_stable = all(row["repair_scope_match"] for row in agreements)
        admitted = (
            len(consensus_families) == 1
            and len(agreements) >= 1
            and scope_stable
        )

        selected = None
        if admitted:
            family = consensus_families[0]
            matching = [row for row in agreements if row["family"] == family]
            selected = {
                "family": family,
                "severity": "critical"
                if any(
                    finding["severity"] == "critical"
                    for row in matching
                    for finding in [row["luna"], row["haiku"]]
                )
                else "serious",
                "repair_scope": matching[0]["luna"]["repair_scope"],
                "span_ids": sorted(
                    {
                        span
                        for row in matching
                        for span in row["span_union"]
                    }
                ),
                "agreement_count": len(matching),
            }

        results.append({
            "candidate_id": story_id,
            "family": candidate["family"],
            "provenance": candidate["provenance"],
            "segments": segment_story(story),
            "luna": {
                "model": ADJUDICATOR_MODEL,
                "findings": luna_findings,
                "meta": luna_meta,
            },
            "haiku": {
                "model": VERIFY_MODEL,
                "findings": haiku_findings,
                "meta": haiku_meta,
            },
            "agreements": agreements,
            "consensus_families": consensus_families,
            "scope_stable": scope_stable,
            "admitted": admitted,
            "selected_gold": selected,
        })

    admitted_count = sum(1 for row in results if row["admitted"])
    output = {
        "schema_version": "story-defect-natural-v11-candidate-adjudication-result.v1",
        "status": "PASS" if admitted_count == len(results) == 2 else "FAIL",
        "models": {
            "gold_adjudicator_a": ADJUDICATOR_MODEL,
            "gold_adjudicator_b": VERIFY_MODEL,
            "sonnet_used_for_gold": False,
        },
        "summary": {
            "candidates": len(results),
            "admitted": admitted_count,
            "rejected": len(results) - admitted_count,
            "two_replacements_ready": admitted_count == 2,
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "summary": output["summary"],
        "total_cost_usd": output["total_cost_usd"],
        "candidates": [
            {
                "candidate_id": row["candidate_id"],
                "admitted": row["admitted"],
                "selected_gold": row["selected_gold"],
            }
            for row in results
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
