from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.narrative_spine_v1_contract import NarrativeSpineV1
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19_obligations import ReaderStoryObligationsV1


FORBIDDEN_HIDDEN_MARKERS = (
    "hidden_truth",
    "hidden_statement",
    "reveal_steps",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NarrativeSpineValidationReportV19(StrictModel):
    schema_id: str = Field(default="spineforge-v19-validation.v1", alias="schema")
    context_pack_id: str
    context_fingerprint: str
    location_sequence: list[str]
    discovery_turns: int
    real_choice_count: int
    authority_valid: bool = True
    reveal_safe: bool = True
    obligations_valid: bool = True


def _authorized_context_refs(pack: SpineContextPackV1) -> set[str]:
    refs: set[str] = set()
    premise = pack.approved_premise
    refs.update(str(x) for x in premise.get("location_refs", []))

    for group in (pack.relationships, pack.inventory, pack.memories, pack.opportunities):
        for row in group:
            key = getattr(row, "key", None)
            if key:
                refs.add(str(key))

    saga = pack.saga
    for row in saga.get("eligible_milestones", []):
        if isinstance(row, dict) and row.get("key"):
            refs.add(str(row["key"]))
    for row in saga.get("public_long_term_questions", []):
        if isinstance(row, dict) and row.get("key"):
            refs.add(str(row["key"]))

    boundaries = pack.knowledge_boundaries
    for bucket in (
        "accessible_locations",
        "rumored_locations",
        "locked_or_limited_locations",
    ):
        for row in boundaries.get(bucket, []):
            if isinstance(row, dict) and row.get("key"):
                refs.add(str(row["key"]))
    return refs


def _full_access_locations(pack: SpineContextPackV1) -> set[str]:
    return {
        str(row["key"])
        for row in pack.knowledge_boundaries.get("accessible_locations", [])
        if isinstance(row, dict)
        and row.get("key")
        and row.get("premise_usage") == "FULL"
    }


def _derive_location_sequence(spine: NarrativeSpineV1) -> list[str]:
    out: list[str] = []
    for beat in spine.beats:
        if not out or out[-1] != beat.location_ref:
            out.append(beat.location_ref)
    return out


def validate_narrative_spine(
    *,
    spine: NarrativeSpineV1,
    pack: SpineContextPackV1,
    obligations: ReaderStoryObligationsV1,
) -> NarrativeSpineValidationReportV19:
    age = int(pack.reader_profile["exact_age"])
    if obligations.exact_age != age:
        raise RuntimeError(
            f"obligations exact_age {obligations.exact_age} does not match ContextPack {age}"
        )

    if spine.episode_concept.story_family != obligations.story_family:
        raise RuntimeError("spine story_family differs from qualification obligations")

    premise_locations = {str(x) for x in pack.approved_premise.get("location_refs", [])}
    used_locations = {beat.location_ref for beat in spine.beats}
    if used_locations - premise_locations:
        raise RuntimeError(
            "spine uses location outside approved premise: "
            + ", ".join(sorted(used_locations - premise_locations))
        )

    full_access = _full_access_locations(pack)
    if used_locations - full_access:
        raise RuntimeError(
            "spine uses location without FULL premise access: "
            + ", ".join(sorted(used_locations - full_access))
        )

    allowed_refs = _authorized_context_refs(pack)
    used_refs = {row.context_ref for row in spine.world_specific_elements}
    if used_refs - allowed_refs:
        raise RuntimeError(
            "spine uses unauthorized world/context refs: "
            + ", ".join(sorted(used_refs - allowed_refs))
        )

    serialized = json.dumps(
        spine.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    leaked = [marker for marker in FORBIDDEN_HIDDEN_MARKERS if marker in serialized]
    if leaked:
        raise RuntimeError(
            "spine contains forbidden hidden-Saga markers: " + ", ".join(leaked)
        )

    if obligations.decision_required and not spine.decision.required:
        raise RuntimeError("reader/story-family obligations require a real decision")

    discovery_turns = sum(1 for beat in spine.beats if beat.new_information.strip())
    if discovery_turns < obligations.minimum_discovery_turns:
        raise RuntimeError(
            f"spine has {discovery_turns} discovery turns; "
            f"{obligations.minimum_discovery_turns} required"
        )

    real_choice_count = len(spine.decision.options) if spine.decision.required else 0
    return NarrativeSpineValidationReportV19(
        context_pack_id=pack.context_pack_id,
        context_fingerprint=pack.context_fingerprint,
        location_sequence=_derive_location_sequence(spine),
        discovery_turns=discovery_turns,
        real_choice_count=real_choice_count,
    )
