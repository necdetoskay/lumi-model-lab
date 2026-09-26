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


def evaluate_narrative_load_promotion_gate(
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate evidence readiness without making the human promotion decision."""
    profile = profile or load_candidate_profile()
    evidence = profile.get("promotion_evidence") or {}
    integration = evidence.get("architect_integration") or {}
    known_risk = evidence.get("known_risk") or {}
    terminal = evidence.get("terminal_closure_guard") or {}
    absolute_tiebreak = integration.get("emotional_absolute_tiebreak") or {}
    change_policy = profile.get("change_policy") or {}
    gate = change_policy.get("promotion_gate") or {}
    integration_policy = profile.get("integration_policy") or {}

    blockers: list[str] = []

    if gate.get("require_architect_integration_qualified"):
        if not integration_policy.get("architect_integration_qualified"):
            blockers.append("architect_integration_not_qualified")

    if gate.get("require_no_mandatory_extra_planner_hop"):
        if integration.get("extra_mandatory_planner_hop") is not False:
            blockers.append("mandatory_extra_planner_hop_present")

    latest_summary = integration.get("latest_resolved_summary") or {}
    if gate.get("require_zero_latest_baseline_wins"):
        if int(latest_summary.get("baseline_wins", 0)) != 0:
            blockers.append("latest_baseline_consensus_loss")

    guarded_fantastical = evidence.get("guarded_fantastical_consensus") or {}
    required_guarded_baseline_wins = gate.get("require_guarded_fantastical_baseline_wins")
    if required_guarded_baseline_wins is not None:
        if int(guarded_fantastical.get("baseline_wins", -1)) != int(
            required_guarded_baseline_wins
        ):
            blockers.append("guarded_fantastical_baseline_loss")

    if gate.get("require_targeted_known_risk_validation_complete"):
        if not known_risk.get("targeted_guard_validation_completed"):
            blockers.append("targeted_known_risk_validation_incomplete")
        if not known_risk.get("terminal_closure_tail_risk_validation_completed"):
            blockers.append("terminal_closure_tail_risk_validation_incomplete")

    terminal_consensus = terminal.get("consensus") or {}
    if gate.get("require_terminal_closure_guard_order_swapped"):
        if terminal_consensus.get("order_swapped") is not True:
            blockers.append("terminal_closure_guard_not_order_swapped")

    required_serious_defects = gate.get(
        "require_terminal_closure_guard_serious_defects"
    )
    if required_serious_defects is not None:
        if int(terminal.get("serious_defects_guarded_candidate", -1)) != int(
            required_serious_defects
        ):
            blockers.append("terminal_closure_guard_serious_defect")

    if gate.get("require_emotional_absolute_tiebreak_pass"):
        if absolute_tiebreak.get("strict_resolution_pass") is not True:
            blockers.append("emotional_absolute_tiebreak_not_passed")

    if gate.get("require_emotional_absolute_tiebreak_position_independent"):
        if absolute_tiebreak.get("position_independent") is not True:
            blockers.append("emotional_absolute_tiebreak_not_position_independent")

    required_absolute_serious_defects = gate.get(
        "require_emotional_absolute_tiebreak_serious_defects"
    )
    if required_absolute_serious_defects is not None:
        candidate_defects = (
            int((absolute_tiebreak.get("candidate_seed_1") or {}).get("serious_defect_count", -1))
            + int((absolute_tiebreak.get("candidate_seed_2") or {}).get("serious_defect_count", -1))
        )
        if candidate_defects != int(required_absolute_serious_defects):
            blockers.append("emotional_absolute_tiebreak_serious_defect")

    family_resolution = integration.get("latest_family_resolution") or {}
    required_families = list(gate.get("required_family_resolutions") or [])
    missing_families = [family for family in required_families if family not in family_resolution]
    if missing_families:
        blockers.extend(f"family_resolution_missing:{family}" for family in missing_families)

    unresolved_families = [
        family
        for family in required_families
        if str(family_resolution.get(family) or "").startswith("inconclusive")
    ]
    max_unresolved = int(gate.get("max_unresolved_families_for_production", 0))

    evidence_pass = not blockers
    if not evidence_pass:
        state = "BLOCKED_EVIDENCE"
    elif len(unresolved_families) > max_unresolved:
        state = "HOLD_MULTI_SEED_REGRESSION"
    elif change_policy.get("production_promotion_requires_explicit_decision"):
        state = "AWAIT_EXPLICIT_PROMOTION_DECISION"
    else:
        state = "TECHNICALLY_READY"

    return {
        "state": state,
        "evidence_pass": evidence_pass,
        "production_gate_pass": (
            evidence_pass
            and len(unresolved_families) <= max_unresolved
            and not change_policy.get("production_promotion_requires_explicit_decision")
        ),
        "requires_explicit_promotion_decision": bool(
            change_policy.get("production_promotion_requires_explicit_decision")
        ),
        "blockers": blockers,
        "unresolved_families": unresolved_families,
        "max_unresolved_families_for_production": max_unresolved,
        "required_families": required_families,
        "qualified_scope": {
            "exact_age": profile.get("exact_age"),
            "reading_mode": profile.get("reading_mode"),
            "nominal_target_words": profile.get("nominal_target_words"),
        },
    }
