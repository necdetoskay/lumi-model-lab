from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes import story_v5_length_pressure_family_pairwise_20260926 as fam
from experiments.prototypes.story_defect_natural_e2e_repair_proof_20260926 import (
    ADJUDICATOR_MODEL,
    VERIFY_MODEL,
    call_checklist_detector,
    meta_cost,
)
from src.story_defect_detection import segment_story

OUT = Path("runs/story-defect-natural-v11-replacement-hunt/result.json")
TARGET_WORDS = 700
MIN_WORDS = 375
MAX_WORDS = 625
MAX_STORIES = 4
REQUIRED_ADMITTED = 2
FAMILIES = [
    "emotional_development",
    "everyday_fantastical_discovery",
    "friendship_social_problem",
    "nature_environment",
]
SEED_BASE = 2026190000


def overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["family"] == right["family"]
        and bool(set(left["span_ids"]).intersection(right["span_ids"]))
    )


def independent_gold(
    *,
    api_key: str,
    story_id: str,
    story_family: str,
    story_text: str,
    seed: int,
) -> tuple[dict[str, Any], float]:
    luna_findings, luna_meta = call_checklist_detector(
        api_key=api_key,
        model=ADJUDICATOR_MODEL,
        story_id=f"{story_id}_luna_blind",
        story_family=story_family,
        story_text=story_text,
        seed=seed,
    )
    haiku_findings, haiku_meta = call_checklist_detector(
        api_key=api_key,
        model=VERIFY_MODEL,
        story_id=f"{story_id}_haiku_blind",
        story_family=story_family,
        story_text=story_text,
        seed=seed + 1,
    )
    cost = meta_cost(luna_meta) + meta_cost(haiku_meta)

    agreements: list[dict[str, Any]] = []
    for luna in luna_findings:
        for haiku in haiku_findings:
            if not overlap(luna, haiku):
                continue
            agreements.append({
                "family": luna["family"],
                "luna": luna,
                "haiku": haiku,
                "repair_scope_match": luna["repair_scope"] == haiku["repair_scope"],
                "span_intersection": sorted(
                    set(luna["span_ids"]).intersection(haiku["span_ids"])
                ),
                "span_union": sorted(
                    set(luna["span_ids"]).union(haiku["span_ids"])
                ),
            })

    families = sorted({row["family"] for row in agreements})
    admitted = (
        len(families) == 1
        and len(agreements) >= 1
        and all(row["repair_scope_match"] for row in agreements)
    )

    selected_gold = None
    if admitted:
        family = families[0]
        rows = [row for row in agreements if row["family"] == family]
        selected_gold = {
            "family": family,
            "severity": "critical"
            if any(
                finding["severity"] == "critical"
                for row in rows
                for finding in (row["luna"], row["haiku"])
            )
            else "serious",
            "repair_scope": rows[0]["luna"]["repair_scope"],
            "span_ids": sorted(
                {
                    span
                    for row in rows
                    for span in row["span_union"]
                }
            ),
            "span_intersection": sorted(
                {
                    span
                    for row in rows
                    for span in row["span_intersection"]
                }
            ),
        }

    return {
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
        "consensus_families": families,
        "admitted": admitted,
        "selected_gold": selected_gold,
    }, cost


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]

    fixtures = {
        row["family"]: row
        for row in fam.FIXTURES
        if row["family"] in FAMILIES
    }
    missing = sorted(set(FAMILIES) - set(fixtures))
    if missing:
        raise RuntimeError(f"missing_story_fixtures:{missing}")

    started = time.perf_counter()
    total_cost = 0.0
    attempts: list[dict[str, Any]] = []
    admitted: list[dict[str, Any]] = []

    story_index = 0
    round_index = 0
    while story_index < MAX_STORIES and len(admitted) < REQUIRED_ADMITTED:
        for family_index, family in enumerate(FAMILIES):
            if story_index >= MAX_STORIES or len(admitted) >= REQUIRED_ADMITTED:
                break

            fixture = fixtures[family]
            seed = SEED_BASE + round_index * 1000 + family_index * 100
            generated = fam.generate(
                api_key,
                fixture,
                TARGET_WORDS,
                seed,
            )
            total_cost += float(generated.get("cost_usd") or 0.0)

            story_id = f"V11_HUNT_{story_index + 1:02d}_{family}"
            row: dict[str, Any] = {
                "story_id": story_id,
                "story_family": family,
                "seed": seed,
                "writer_model": fam.base.WRITER_MODEL,
                "target_words": TARGET_WORDS,
                "word_count": generated["word_count"],
                "story": generated["story"],
                "writer_meta": {
                    "cost_usd": generated["cost_usd"],
                    "elapsed_seconds": generated["elapsed_seconds"],
                    "usage": generated["usage"],
                },
                "admitted": False,
            }

            if not MIN_WORDS <= generated["word_count"] <= MAX_WORDS:
                row["rejection_reason"] = "WORD_RANGE"
                attempts.append(row)
                story_index += 1
                continue

            gold, gold_cost = independent_gold(
                api_key=api_key,
                story_id=story_id,
                story_family=family,
                story_text=generated["story"],
                seed=seed + 10,
            )
            total_cost += gold_cost
            row["independent_gold"] = gold
            row["segments"] = segment_story(generated["story"])
            row["admitted"] = bool(gold["admitted"])
            if row["admitted"]:
                admitted.append({
                    "story_id": story_id,
                    "story_family": family,
                    "seed": seed,
                    "writer_model": fam.base.WRITER_MODEL,
                    "word_count": generated["word_count"],
                    "story": generated["story"],
                    "selected_gold": gold["selected_gold"],
                })
            else:
                row["rejection_reason"] = "NO_STABLE_BLOCKING_GOLD"

            attempts.append(row)
            story_index += 1

        round_index += 1

    output = {
        "schema_version": "story-defect-natural-v11-replacement-hunt-result.v1",
        "status": "PASS" if len(admitted) == REQUIRED_ADMITTED else "FAIL",
        "policy": {
            "no_defect_injection": True,
            "writer_model": fam.base.WRITER_MODEL,
            "gold_models": [ADJUDICATOR_MODEL, VERIFY_MODEL],
            "sonnet_detector_not_used_for_gold_selection": True,
            "max_stories": MAX_STORIES,
            "early_stop_after_admitted": REQUIRED_ADMITTED,
            "word_range": [MIN_WORDS, MAX_WORDS],
        },
        "summary": {
            "stories_generated": story_index,
            "admitted": len(admitted),
            "required": REQUIRED_ADMITTED,
            "replacement_pair_ready": len(admitted) == REQUIRED_ADMITTED,
        },
        "admitted": admitted,
        "attempts": attempts,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "summary": output["summary"],
        "admitted": [
            {
                "story_id": row["story_id"],
                "story_family": row["story_family"],
                "selected_gold": row["selected_gold"],
            }
            for row in admitted
        ],
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
