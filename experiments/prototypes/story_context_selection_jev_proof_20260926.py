from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.openrouter_jev import call_openrouter_jev, choice_question, choice_value

FIXTURE = Path("experiments/fixtures/story_context_selection_proof_20260926.json")
OUT = Path("runs/story-context-selection-proof/result.json")

CHOICES = {
    "REQUIRED_GENERATIVE": (
        "This fact is necessary input for planning this StoryIntent and should be included "
        "as positive story-planning material. Omitting it would likely make the plan unable "
        "to satisfy the intent or preserve an essential active fact."
    ),
    "REQUIRED_GUARD": (
        "This fact must be included mainly as a constraint/boundary so the planner does not "
        "violate canon, knowledge, state, world, or safety. It need not appear in the plot."
    ),
    "RELEVANT_GENERATIVE": (
        "This fact is materially useful story-planning material for this intent and is worth "
        "including in a minimal context packet, but the plan could still exist without it."
    ),
    "RELEVANT_GUARD": (
        "This fact is materially useful as a constraint/boundary for this intent and is worth "
        "including in a minimal context packet, but it is not strictly mandatory."
    ),
    "OPTIONAL": (
        "This fact may be loosely useful but is not important enough for the minimal context "
        "packet. Omit it unless a later planner explicitly requests more evidence."
    ),
    "IRRELEVANT": (
        "This fact has no material planning or guard value for this StoryIntent and should be "
        "omitted from the minimal context packet."
    ),
    "ESCALATE": (
        "The supplied evidence is insufficient or ambiguous; do not guess whether this fact "
        "belongs in the minimal context packet."
    ),
}

SELECTED_PREFIXES = ("REQUIRED_", "RELEVANT_")


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_questions(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    questions = {}
    for fact in candidates:
        fid = fact["id"]
        questions[fid] = choice_question(
            (
                f"Decide whether candidate fact '{fid}' belongs in the MINIMAL Story Context "
                "Packet for the supplied StoryIntent. Judge only relevance/guard necessity. "
                "Do not invent a story solution. Prefer omission when the fact is not materially "
                "useful. Use ESCALATE rather than guessing when evidence is genuinely insufficient."
            ),
            CHOICES,
        )
    return questions


def run_once(
    *,
    api_key: str,
    fixture: dict[str, Any],
    intent: dict[str, Any],
) -> dict[str, Any]:
    candidates = fixture["candidates"]
    candidate_map = {x["id"]: x for x in candidates}
    state = {
        "task": "minimal_story_context_selection",
        "profile": fixture["profile"],
        "active_world_id": fixture["active_world_id"],
        "story_intent": intent["story_intent"],
        "always_required": fixture["always_required"],
        "candidate_facts": candidate_map,
        "policy": {
            "always_required_are_forced_by_code": True,
            "forbidden_facts_are_removed_before_this_request": True,
            "selected_choices": list(SELECTED_PREFIXES),
            "goal": "smallest sufficient context packet; do not design the story itself",
        },
    }
    body = call_openrouter_jev(
        api_key=api_key,
        state=state,
        questions=build_questions(candidates),
        timeout_seconds=60.0,
    )
    decisions = {}
    for fid in candidate_map:
        value, confidence = choice_value(body["answers"][fid])
        if value not in CHOICES:
            raise RuntimeError(f"unknown_choice:{fid}:{value}")
        decisions[fid] = {"choice": value, "confidence": confidence}

    selected = sorted(
        fid for fid, row in decisions.items()
        if row["choice"].startswith(SELECTED_PREFIXES)
    )
    guards = sorted(
        fid for fid, row in decisions.items()
        if row["choice"].endswith("_GUARD")
        and row["choice"].startswith(SELECTED_PREFIXES)
    )
    generative = sorted(
        fid for fid, row in decisions.items()
        if row["choice"].endswith("_GENERATIVE")
        and row["choice"].startswith(SELECTED_PREFIXES)
    )
    escalated = sorted(fid for fid, row in decisions.items() if row["choice"] == "ESCALATE")

    final_packet = {
        "always_required": fixture["always_required"],
        "selected_candidates": [candidate_map[fid] for fid in selected],
    }

    return {
        "decisions": decisions,
        "selected_candidate_ids": selected,
        "guard_candidate_ids": guards,
        "generative_candidate_ids": generative,
        "escalated_candidate_ids": escalated,
        "final_packet": final_packet,
        "final_packet_hash": stable_hash(final_packet),
        "raw_usage": body.get("usage"),
        "raw_model": body.get("model"),
    }


def score(intent: dict[str, Any], run: dict[str, Any], forbidden_ids: set[str]) -> dict[str, Any]:
    gold = intent["gold"]
    selected = set(run["selected_candidate_ids"])
    guards = set(run["guard_candidate_ids"])

    missing_must = sorted(set(gold["must_select"]) - selected)
    leaked_must_not = sorted(set(gold["must_not_select"]) & selected)
    missing_guards = sorted(set(gold["guard_expected"]) - guards)
    useful_hits = sorted(set(gold["useful_select_any"]) & selected)
    forbidden_leak = sorted(forbidden_ids & selected)

    return {
        "missing_must_select": missing_must,
        "selected_must_not_select": leaked_must_not,
        "missing_expected_guards": missing_guards,
        "useful_select_hits": useful_hits,
        "forbidden_leak": forbidden_leak,
        "pass": (
            not missing_must
            and not leaked_must_not
            and not missing_guards
            and not forbidden_leak
            and len(useful_hits) >= 1
            and not run["escalated_candidate_ids"]
        ),
    }


def main():
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    forbidden_ids = {x["id"] for x in fixture["forbidden"]}
    candidate_ids = {x["id"] for x in fixture["candidates"]}
    if forbidden_ids & candidate_ids:
        raise RuntimeError("forbidden_candidate_overlap")

    started = time.perf_counter()
    results = []

    for intent in fixture["intents"]:
        first = run_once(api_key=api_key, fixture=fixture, intent=intent)
        second = run_once(api_key=api_key, fixture=fixture, intent=intent)

        first_score = score(intent, first, forbidden_ids)
        second_score = score(intent, second, forbidden_ids)

        same_selected = first["selected_candidate_ids"] == second["selected_candidate_ids"]
        same_roles = (
            first["guard_candidate_ids"] == second["guard_candidate_ids"]
            and first["generative_candidate_ids"] == second["generative_candidate_ids"]
        )
        same_all_choices = all(
            first["decisions"][fid]["choice"] == second["decisions"][fid]["choice"]
            for fid in candidate_ids
        )

        results.append({
            "intent_id": intent["id"],
            "story_intent": intent["story_intent"],
            "gold": intent["gold"],
            "run_1": first,
            "run_2": second,
            "run_1_score": first_score,
            "run_2_score": second_score,
            "repeat_stability": {
                "same_selected_set": same_selected,
                "same_selected_roles": same_roles,
                "same_all_candidate_choices": same_all_choices,
            },
            "pass": (
                first_score["pass"]
                and second_score["pass"]
                and same_selected
                and same_roles
            ),
        })

    selected_sets = {
        row["intent_id"]: tuple(row["run_1"]["selected_candidate_ids"])
        for row in results
    }
    differentiated = len(set(selected_sets.values())) == len(selected_sets)
    all_pass = all(row["pass"] for row in results) and differentiated

    result = {
        "schema_version": "story-context-selection-proof-result.v1",
        "profile": fixture["profile"],
        "jev_model": "typesafe/jev-1.13",
        "deterministic_policy": {
            "always_required_count": len(fixture["always_required"]),
            "candidate_count": len(fixture["candidates"]),
            "forbidden_count": len(fixture["forbidden"]),
            "forbidden_sent_to_jev": False,
            "selected_choice_prefixes": list(SELECTED_PREFIXES),
        },
        "summary": {
            "intent_count": len(results),
            "passes": sum(1 for x in results if x["pass"]),
            "failures": sum(1 for x in results if not x["pass"]),
            "all_intents_pass": all(x["pass"] for x in results),
            "intent_packets_differentiated": differentiated,
            "qualification_pass": all_pass,
        },
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    concise = {
        "summary": result["summary"],
        "intents": [
            {
                "intent_id": x["intent_id"],
                "selected": x["run_1"]["selected_candidate_ids"],
                "guards": x["run_1"]["guard_candidate_ids"],
                "generative": x["run_1"]["generative_candidate_ids"],
                "run_1_score": x["run_1_score"],
                "run_2_score": x["run_2_score"],
                "repeat_stability": x["repeat_stability"],
                "pass": x["pass"],
            }
            for x in results
        ],
        "elapsed_seconds": result["elapsed_seconds"],
    }
    print(json.dumps(concise, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
