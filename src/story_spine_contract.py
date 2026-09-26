from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_profile(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_spine(profile: dict[str, Any], planner_output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = profile["spine_policy"]
    support_policy = profile["supporting_thread_policy"]
    spine = planner_output.get("spine") or []

    if not isinstance(spine, list):
        return ["spine_not_list"]

    min_beats = int(policy["min_beats"])
    max_beats = int(policy["max_beats"])
    if len(spine) < min_beats or len(spine) > max_beats:
        errors.append(f"beat_count_out_of_range:{len(spine)}")

    allowed_density = set(policy["allowed_density"])
    allowed_functions = set(policy["allowed_functions"])
    functions: list[str] = []
    beat_texts: list[str] = []

    for index, beat in enumerate(spine):
        if not isinstance(beat, dict):
            errors.append(f"beat_not_object:{index}")
            continue

        density = beat.get("density")
        function = beat.get("function")
        text = str(beat.get("beat") or "").strip()

        if density not in allowed_density:
            errors.append(f"invalid_density:{index}:{density}")
        if function not in allowed_functions:
            errors.append(f"invalid_function:{index}:{function}")
        else:
            functions.append(function)
        if not text:
            errors.append(f"empty_beat:{index}")
        else:
            beat_texts.append(text.casefold())

    if policy.get("duplicate_beat_text_forbidden", False):
        if len(beat_texts) != len(set(beat_texts)):
            errors.append("duplicate_beat_text")

    for required in policy.get("required_functions") or []:
        if required not in functions:
            errors.append(f"missing_required_function:{required}")

    progression = set(policy.get("required_progression_any") or [])
    if progression and not progression.intersection(functions):
        errors.append("missing_progression_function")

    # Closure must be terminal. Payoff must occur before closure.
    if spine:
        if spine[-1].get("function") != "closure":
            errors.append("closure_not_terminal")
        payoff_positions = [
            i for i, beat in enumerate(spine)
            if isinstance(beat, dict) and beat.get("function") == "payoff"
        ]
        if payoff_positions and payoff_positions[-1] >= len(spine) - 1:
            errors.append("payoff_not_before_closure")

    support = planner_output.get("supporting_thread") or {}
    used = bool(support.get("used"))
    if used:
        if int(support_policy.get("max_threads", 1)) < 1:
            errors.append("supporting_thread_forbidden")
        if not str(support.get("description") or "").strip():
            errors.append("supporting_thread_description_missing")
        if not str(support.get("why_it_belongs") or "").strip():
            errors.append("supporting_thread_rationale_missing")

    return errors


def is_valid_spine(profile: dict[str, Any], planner_output: dict[str, Any]) -> bool:
    return not validate_spine(profile, planner_output)
