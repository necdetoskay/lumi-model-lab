from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.openrouter_jev import call_openrouter_jev, noul_probability, noul_question

FIXTURE = Path("experiments/fixtures/story_context_selection_proof_20260926.json")
OUT = Path("runs/story-context-selection-probability-proof/result.json")

SELECT_THRESHOLD = 0.80
REVIEW_THRESHOLD = 0.40


def questions(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for fact in candidates:
        fid = fact["id"]
        result[fid] = noul_question(
            (
                f"For candidate fact '{fid}', decide whether this fact is materially necessary "
                "or useful enough to include in the MINIMAL Story Context Packet for the supplied "
                "StoryIntent. Judge context relevance only; do not invent the story solution."
            ),
            true_criteria=(
                "TRUE when omitting this fact could materially weaken, misdirect, or constrain "
                "correct planning for this StoryIntent, including when it is useful generative "
                "material or an important semantic boundary."
            ),
            false_criteria=(
                "FALSE when the fact is redundant, merely decorative, only loosely related, "
                "historical noise, or safe to omit from a minimal context packet."
            ),
        )
    return result


def bucket(p: float) -> str:
    if p >= SELECT_THRESHOLD:
        return "SELECT"
    if p >= REVIEW_THRESHOLD:
        return "REVIEW"
    return "OMIT"


def run_once(api_key: str, fixture: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    candidate_map = {x["id"]: x for x in fixture["candidates"]}
    state = {
        "task": "minimal_story_context_binary_relevance",
        "active_world_id": fixture["active_world_id"],
        "story_intent": intent["story_intent"],
        "always_required": fixture["always_required"],
        "candidate_facts": candidate_map,
        "policy": {
            "hard_invariants_are_owned_by_deterministic_code": True,
            "forbidden_facts_are_removed_before_jev": True,
            "select_threshold": SELECT_THRESHOLD,
            "review_threshold": REVIEW_THRESHOLD,
            "goal": "minimal sufficient context, not maximum context",
        },
    }
    body = call_openrouter_jev(
        api_key=api_key,
        state=state,
        questions=questions(fixture["candidates"]),
        timeout_seconds=60.0,
    )
    rows = {}
    for fid in candidate_map:
        p = noul_probability(body["answers"][fid])
        rows[fid] = {"probability": p, "bucket": bucket(p)}

    return {
        "decisions": rows,
        "selected_candidate_ids": sorted(fid for fid,row in rows.items() if row["bucket"]=="SELECT"),
        "review_candidate_ids": sorted(fid for fid,row in rows.items() if row["bucket"]=="REVIEW"),
        "omitted_candidate_ids": sorted(fid for fid,row in rows.items() if row["bucket"]=="OMIT"),
        "raw_usage": body.get("usage"),
        "raw_model": body.get("model"),
    }


def score(intent: dict[str, Any], run: dict[str, Any], forbidden_ids: set[str]) -> dict[str, Any]:
    gold = intent["gold"]
    selected = set(run["selected_candidate_ids"])
    review = set(run["review_candidate_ids"])
    included_or_review = selected | review

    missing_must = sorted(set(gold["must_select"]) - selected)
    dangerous_omit = sorted(set(gold["must_select"]) - included_or_review)
    wrong_select = sorted(set(gold["must_not_select"]) & selected)
    forbidden_leak = sorted(forbidden_ids & included_or_review)

    return {
        "missing_must_select": missing_must,
        "dangerous_omit": dangerous_omit,
        "selected_must_not_select": wrong_select,
        "forbidden_leak": forbidden_leak,
        "pass": not missing_must and not wrong_select and not forbidden_leak,
    }


def main():
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    forbidden_ids = {x["id"] for x in fixture["forbidden"]}
    started = time.perf_counter()
    results = []

    for intent in fixture["intents"]:
        a = run_once(api_key, fixture, intent)
        b = run_once(api_key, fixture, intent)
        sa = score(intent, a, forbidden_ids)
        sb = score(intent, b, forbidden_ids)

        candidate_ids = [x["id"] for x in fixture["candidates"]]
        drifts = {
            fid: round(abs(a["decisions"][fid]["probability"] - b["decisions"][fid]["probability"]), 6)
            for fid in candidate_ids
        }
        max_drift = max(drifts.values()) if drifts else 0.0
        bucket_changes = sorted(
            fid for fid in candidate_ids
            if a["decisions"][fid]["bucket"] != b["decisions"][fid]["bucket"]
        )

        same_selected = a["selected_candidate_ids"] == b["selected_candidate_ids"]
        stable = same_selected and not bucket_changes

        results.append({
            "intent_id": intent["id"],
            "story_intent": intent["story_intent"],
            "gold": intent["gold"],
            "run_1": a,
            "run_2": b,
            "run_1_score": sa,
            "run_2_score": sb,
            "repeat_stability": {
                "same_selected_set": same_selected,
                "bucket_changes": bucket_changes,
                "max_probability_drift": max_drift,
            },
            "pass": sa["pass"] and sb["pass"] and stable,
        })

    first_selected_sets = {
        row["intent_id"]: tuple(row["run_1"]["selected_candidate_ids"])
        for row in results
    }
    differentiated = len(set(first_selected_sets.values())) == len(first_selected_sets)
    all_pass = all(row["pass"] for row in results) and differentiated

    result = {
        "schema_version": "story-context-selection-probability-proof-result.v1",
        "profile": "LSF-A4-W500-context-selector-probability-v0.1",
        "jev_model": "typesafe/jev-1.13",
        "thresholds": {
            "SELECT": f">={SELECT_THRESHOLD}",
            "REVIEW": f">={REVIEW_THRESHOLD} and <{SELECT_THRESHOLD}",
            "OMIT": f"<{REVIEW_THRESHOLD}",
        },
        "deterministic_policy": {
            "always_required_forced": True,
            "forbidden_removed_pre_jev": True,
            "hard_guards_not_delegated_to_jev": True,
        },
        "summary": {
            "intent_count": len(results),
            "passes": sum(1 for x in results if x["pass"]),
            "failures": sum(1 for x in results if not x["pass"]),
            "intent_packets_differentiated": differentiated,
            "qualification_pass": all_pass,
        },
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "summary": result["summary"],
        "intents": [
            {
                "intent_id": x["intent_id"],
                "selected": x["run_1"]["selected_candidate_ids"],
                "review": x["run_1"]["review_candidate_ids"],
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
