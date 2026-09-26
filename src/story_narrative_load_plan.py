from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PROFILE_PATH = Path(
    "configs/story_planner_profiles/tr_age4_narrative_load.v1.candidate.json"
)


def load_candidate_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_narrative_load_plan(
    plan: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    profile = profile or load_candidate_profile()
    policy = profile["spine"]
    support_policy = profile["supporting_thread"]

    spine = plan.get("spine")
    if not isinstance(spine, list):
        return ["spine_missing"]

    min_beats = int(policy["min_beats"])
    max_beats = int(policy["max_beats"])
    if not min_beats <= len(spine) <= max_beats:
        errors.append("spine_size_out_of_range")

    allowed_density = set(policy["allowed_density"])
    allowed_functions = set(policy["allowed_functions"])
    functions: list[str] = []
    normalized_texts: list[str] = []

    for index, beat in enumerate(spine):
        if not isinstance(beat, dict):
            errors.append(f"beat_{index}_invalid")
            continue

        density = beat.get("density")
        function = beat.get("function")
        text = beat.get("beat")

        if density not in allowed_density:
            errors.append(f"beat_{index}_density_invalid")
        if function not in allowed_functions:
            errors.append(f"beat_{index}_function_invalid")
        else:
            functions.append(str(function))

        if not isinstance(text, str) or not text.strip():
            errors.append(f"beat_{index}_text_missing")
        else:
            normalized_texts.append(text.strip().casefold())

    if policy.get("duplicate_beat_text_forbidden"):
        if len(normalized_texts) != len(set(normalized_texts)):
            errors.append("duplicate_beat_text")

    for required in policy.get("required_functions") or []:
        if required not in functions:
            errors.append(f"required_function_missing:{required}")

    progression = set(policy.get("required_progression_any") or [])
    if progression and not progression.intersection(functions):
        errors.append("progression_function_missing")

    if spine and policy.get("closure_must_be_terminal"):
        last = spine[-1] if isinstance(spine[-1], dict) else {}
        if last.get("function") != "closure":
            errors.append("closure_not_terminal")

    if policy.get("payoff_must_precede_closure"):
        payoff_positions = [
            index
            for index, beat in enumerate(spine)
            if isinstance(beat, dict) and beat.get("function") == "payoff"
        ]
        closure_positions = [
            index
            for index, beat in enumerate(spine)
            if isinstance(beat, dict) and beat.get("function") == "closure"
        ]
        if payoff_positions and closure_positions:
            if max(payoff_positions) >= min(closure_positions):
                errors.append("payoff_not_before_closure")

    thread = plan.get("supporting_thread") or {}
    used = bool(thread.get("used"))
    if used:
        if int(support_policy.get("max_count", 1)) < 1:
            errors.append("supporting_thread_forbidden")
        if not str(thread.get("description") or "").strip():
            errors.append("supporting_thread_description_missing")
        if not str(thread.get("why_it_belongs") or "").strip():
            errors.append("supporting_thread_belonging_rationale_missing")

    return errors


def candidate_requires_supporting_thread(plan: dict[str, Any]) -> bool:
    """Supporting thread is optional and must never be inferred from length/beat count."""
    return False


def can_advance_to_writer(
    plan: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> bool:
    return not validate_narrative_load_plan(plan, profile)
