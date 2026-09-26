from __future__ import annotations

from typing import Any


ALLOWED_DENSITY = {"brief", "develop", "anchor"}
ALLOWED_FUNCTIONS = {
    "setup",
    "signal",
    "hypothesis",
    "test",
    "complication",
    "observation",
    "decision",
    "social_shift",
    "payoff",
    "closure",
}


def validate_narrative_load_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spine = plan.get("spine")

    if not isinstance(spine, list):
        return ["spine_missing"]

    if not 8 <= len(spine) <= 12:
        errors.append("spine_size_out_of_range")

    for index, beat in enumerate(spine):
        if not isinstance(beat, dict):
            errors.append(f"beat_{index}_invalid")
            continue
        if beat.get("density") not in ALLOWED_DENSITY:
            errors.append(f"beat_{index}_density_invalid")
        if beat.get("function") not in ALLOWED_FUNCTIONS:
            errors.append(f"beat_{index}_function_invalid")
        text = beat.get("beat")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"beat_{index}_text_missing")

    thread = plan.get("supporting_thread") or {}
    used = bool(thread.get("used"))

    if used:
        if not str(thread.get("description") or "").strip():
            errors.append("supporting_thread_description_missing")
        if not str(thread.get("why_it_belongs") or "").strip():
            errors.append("supporting_thread_belonging_rationale_missing")

    return errors


def candidate_requires_supporting_thread(plan: dict[str, Any]) -> bool:
    """Supporting thread is deliberately optional; never infer it from beat count."""
    return False


def can_advance_to_writer(plan: dict[str, Any]) -> bool:
    return not validate_narrative_load_plan(plan)
