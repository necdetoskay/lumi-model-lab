from __future__ import annotations

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spine_context_pack_v1 import SpineContextPackV1


def _allowed_full_locations(pack: SpineContextPackV1) -> set[str]:
    return {
        str(row["key"])
        for row in pack.knowledge_boundaries["accessible_locations"]
        if row.get("premise_usage") == "FULL"
    }


def validate_compiled_spine_authority(
    *,
    spine: EpisodeSpineV3,
    pack: SpineContextPackV1,
) -> None:
    """
    v5-owned ContextPack authority validation for Sonnet's compiled spine.

    Structural contract validity belongs to EpisodeSpineV3/Pydantic.
    This layer checks application-owned canonical values and access boundaries.
    """
    premise = pack.approved_premise
    session = pack.session_target

    if spine.premise_key != premise["key"]:
        raise RuntimeError("Spine premise_key mismatch.")
    if spine.exact_age != int(pack.reader_profile["exact_age"]):
        raise RuntimeError("Spine exact_age mismatch.")
    if spine.session != session["name"]:
        raise RuntimeError("Spine session mismatch.")
    if (
        spine.target_words_min != int(session["target_words_min"])
        or spine.target_words_max != int(session["target_words_max"])
    ):
        raise RuntimeError("Spine word target mismatch.")

    allowed = set(premise["location_refs"])
    full = _allowed_full_locations(pack)
    if not allowed.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")

    used = {beat.location_ref for beat in spine.beats}
    if not used.issubset(allowed):
        raise RuntimeError("Spine uses location outside approved premise.")

    intended = set(pack.saga["intended_milestone_keys"])
    if set(spine.saga_progression.intended_milestone_keys) != intended:
        raise RuntimeError("Spine intended milestones differ from ContextPack authority.")
    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY",
        "MAIN_SAGA_PROGRESS",
        "MIXED",
    }:
        raise RuntimeError("Main Saga milestone requires Main Saga episode role.")
