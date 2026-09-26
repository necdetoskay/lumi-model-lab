from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.openrouter_jev import call_openrouter_jev, noul_probability, noul_question

FIXTURE = Path("experiments/fixtures/story_context_selection_proof_20260926.json")
OUT = Path("runs/story-context-selection-hybrid-proof/result.json")

SELECT_THRESHOLD = 0.45
REVIEW_THRESHOLD = 0.30


def make_questions(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for fact in candidates:
        fid = fact["id"]
        out[fid] = noul_question(
            (
                f"Should soft candidate fact '{fid}' be included as additional context for the "
                "Story Planner? Direct StoryIntent references and hard guards are already supplied "
                "deterministically. Select only genuinely useful enrichment; do not duplicate the "
                "deterministic core and do not invent a story solution."
            ),
            true_criteria=(
                "TRUE when this remaining fact materially helps the planner create a coherent, "
                "intent-relevant spine beyond the already supplied deterministic core."
            ),
            false_criteria=(
                "FALSE when the fact is redundant, incidental, historical noise, unrelated, or "
                "safe to omit from the minimal planner context."
            ),
        )
    return out


def bucket(p: float) -> str:
    if p >= SELECT_THRESHOLD:
        return "SELECT"
    if p >= REVIEW_THRESHOLD:
        return "REVIEW"
    return "OMIT"


def deterministic_core(
    fixture: dict[str, Any], intent: dict[str, Any]
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    candidate_map = {x["id"]: x for x in fixture["candidates"]}
    refs = intent["story_intent"]["references"]
    required_ids = set(refs["required_fact_ids"])
    guard_ids = set(refs["hard_guard_fact_ids"])
    direct_ids = required_ids | guard_ids

    missing = sorted(direct_ids - set(candidate_map))
    if missing:
        raise RuntimeError(f"missing_direct_reference_facts:{missing}")

    core = list(fixture["always_required"])
    core.extend(candidate_map[fid] for fid in sorted(direct_ids))
    return core, direct_ids, guard_ids


def run_once(
    api_key: str,
    fixture: dict[str, Any],
    intent: dict[str, Any],
) -> dict[str, Any]:
    candidate_map = {x["id"]: x for x in fixture["candidates"]}
    core, direct_ids, guard_ids = deterministic_core(fixture, intent)
    soft_candidates = [
        fact for fact in fixture["candidates"] if fact["id"] not in direct_ids
    ]

    state = {
        "task": "minimal_story_context_soft_enrichment",
        "active_world_id": fixture["active_world_id"],
        "story_intent": intent["story_intent"],
        "deterministic_core": core,
        "soft_candidates": {x["id"]: x for x in soft_candidates},
        "policy": {
            "direct_references_are_already_in_core": True,
            "hard_guards_are_already_in_core": True,
            "forbidden_facts_are_removed_before_jev": True,
            "goal": "minimal useful enrichment only",
            "select_threshold": SELECT_THRESHOLD,
            "review_threshold": REVIEW_THRESHOLD,
        },
    }

    body = call_openrouter_jev(
        api_key=api_key,
        state=state,
        questions=make_questions(soft_candidates),
        timeout_seconds=60.0,
    )

    decisions = {}
    for fact in soft_candidates:
        fid = fact["id"]
        p = noul_probability(body["answers"][fid])
        decisions[fid] = {"probability": p, "bucket": bucket(p)}

    selected_ids = sorted(fid for fid,row in decisions.items() if row["bucket"]=="SELECT")
    review_ids = sorted(fid for fid,row in decisions.items() if row["bucket"]=="REVIEW")
    final_packet = {
        "deterministic_core": core,
        "jev_selected_enrichment": [candidate_map[fid] for fid in selected_ids],
    }
    return {
        "deterministic_core_ids": sorted(
            [x["id"] for x in fixture["always_required"]] + list(direct_ids)
        ),
        "hard_guard_ids": sorted(guard_ids),
        "decisions": decisions,
        "selected_enrichment_ids": selected_ids,
        "review_enrichment_ids": review_ids,
        "final_packet": final_packet,
        "raw_usage": body.get("usage"),
        "raw_model": body.get("model"),
    }


def expected_soft(intent_id: str) -> dict[str, Any]:
    if intent_id == "intent.problem_solving_truck":
        return {
            "must_select_any": ["location.cardboard", "location.wood_block"],
            "must_not_select": [
                "relationship.emre",
                "saga.kindness_closed",
                "knowledge.garden_gate",
                "inventory.blue_hat",
                "location.chalk_box",
            ],
        }
    if intent_id == "intent.friendship_chalk":
        return {
            "must_select_any": [],
            "must_not_select": [
                "relationship.emre",
                "knowledge.garden_gate",
                "location.cardboard",
                "location.wood_block",
                "inventory.umbrella",
            ],
        }
    if intent_id == "intent.garden_gate_mystery":
        return {
            "must_select_any": ["saga.explorer"],
            "must_not_select": [
                "relationship.emre",
                "location.cardboard",
                "location.wood_block",
                "location.chalk_box",
                "inventory.blue_chalk",
                "inventory.yellow_chalk",
            ],
        }
    raise RuntimeError(f"unknown_intent:{intent_id}")


def score(
    fixture: dict[str, Any],
    intent: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    refs = intent["story_intent"]["references"]
    expected_direct = set(refs["required_fact_ids"]) | set(refs["hard_guard_fact_ids"])
    core_ids = set(run["deterministic_core_ids"])
    selected = set(run["selected_enrichment_ids"])
    forbidden_ids = {x["id"] for x in fixture["forbidden"]}
    exp = expected_soft(intent["id"])

    missing_direct = sorted(expected_direct - core_ids)
    wrong_selected = sorted(set(exp["must_not_select"]) & selected)
    forbidden_leak = sorted(forbidden_ids & (core_ids | selected))
    required_soft_hits = sorted(set(exp["must_select_any"]) & selected)

    soft_requirement_ok = (
        True if not exp["must_select_any"] else len(required_soft_hits) >= 1
    )

    return {
        "missing_deterministic_direct_refs": missing_direct,
        "selected_forbidden_or_noise": wrong_selected,
        "forbidden_leak": forbidden_leak,
        "required_soft_hits": required_soft_hits,
        "pass": (
            not missing_direct
            and not wrong_selected
            and not forbidden_leak
            and soft_requirement_ok
        ),
    }


def main():
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    started = time.perf_counter()
    results = []

    for intent in fixture["intents"]:
        a = run_once(api_key, fixture, intent)
        b = run_once(api_key, fixture, intent)
        sa = score(fixture, intent, a)
        sb = score(fixture, intent, b)

        common_ids = sorted(set(a["decisions"]) & set(b["decisions"]))
        bucket_changes = sorted(
            fid for fid in common_ids
            if a["decisions"][fid]["bucket"] != b["decisions"][fid]["bucket"]
        )
        max_drift = max(
            (
                abs(
                    a["decisions"][fid]["probability"]
                    - b["decisions"][fid]["probability"]
                )
                for fid in common_ids
            ),
            default=0.0,
        )
        same_selected = a["selected_enrichment_ids"] == b["selected_enrichment_ids"]

        results.append({
            "intent_id": intent["id"],
            "story_intent": intent["story_intent"],
            "run_1": a,
            "run_2": b,
            "run_1_score": sa,
            "run_2_score": sb,
            "repeat_stability": {
                "same_selected_enrichment": same_selected,
                "bucket_changes": bucket_changes,
                "max_probability_drift": round(max_drift, 6),
            },
            "pass": sa["pass"] and sb["pass"] and same_selected,
        })

    packets = {
        row["intent_id"]: tuple(
            row["run_1"]["deterministic_core_ids"]
            + row["run_1"]["selected_enrichment_ids"]
        )
        for row in results
    }
    differentiated = len(set(packets.values())) == len(packets)
    qualification_pass = all(x["pass"] for x in results) and differentiated

    result = {
        "schema_version": "story-context-selection-hybrid-proof-result.v1",
        "profile": "LSF-A4-W500-context-builder-v0.1",
        "jev_model": "typesafe/jev-1.13",
        "architecture": {
            "deterministic_core": [
                "always_required",
                "StoryIntent direct fact references",
                "hard guards",
            ],
            "jev_scope": "soft enrichment only",
            "select_threshold": SELECT_THRESHOLD,
            "review_threshold": REVIEW_THRESHOLD,
            "review_sent_to_planner": False,
            "forbidden_sent_to_jev": False,
        },
        "summary": {
            "intent_count": len(results),
            "passes": sum(1 for x in results if x["pass"]),
            "failures": sum(1 for x in results if not x["pass"]),
            "packets_differentiated": differentiated,
            "qualification_pass": qualification_pass,
        },
        "results": results,
        "elapsed_seconds": round(time.perf_counter()-started, 3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({
        "summary": result["summary"],
        "intents": [
            {
                "intent_id": x["intent_id"],
                "core": x["run_1"]["deterministic_core_ids"],
                "selected_enrichment": x["run_1"]["selected_enrichment_ids"],
                "review": x["run_1"]["review_enrichment_ids"],
                "run_1_score": x["run_1_score"],
                "run_2_score": x["run_2_score"],
                "repeat_stability": x["repeat_stability"],
                "pass": x["pass"],
            }
            for x in results
        ],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
