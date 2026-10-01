from __future__ import annotations

import hashlib
from typing import Any

from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19
from src.spine_context_pack_v1 import SpineContextPackV1, canonical_json


def spine_hash(spine: NarrativeSpineV1) -> str:
    payload = spine.model_dump(mode="json", by_alias=True)
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def render_human_preview(
    *,
    spine: NarrativeSpineV1,
    pack: SpineContextPackV1,
    gate: SpineProductGateV19,
) -> str:
    lines = [
        f"# {spine.title}",
        "",
        f"- ContextPack: {pack.context_pack_id}",
        f"- Context fingerprint: {pack.context_fingerprint}",
        f"- Spine hash: {spine_hash(spine)}",
        f"- Gate: {gate.decision}",
        f"- Story family: {spine.episode_concept.story_family}",
        f"- Promise: {spine.episode_concept.story_promise}",
        f"- Target reader effect: {spine.episode_concept.target_reader_effect}",
        f"- Protagonist role: {spine.protagonist.role}",
        f"- Immediate goal: {spine.protagonist.immediate_goal}",
        f"- Pressure: {spine.protagonist.pressure}",
        f"- Central question: {spine.central_question}",
        f"- Stakes: {spine.stakes}",
        "",
        "## Story flow",
    ]
    for index, beat in enumerate(spine.beats, start=1):
        lines.append(
            f"{index}. [{beat.location_ref}] {beat.character_action} -> "
            f"{beat.external_change} -> learns {beat.new_information} -> "
            f"consequence: {beat.consequence}"
        )

    lines.extend(["", "## Choice"])
    if spine.decision.required:
        lines.append(f"Pressure: {spine.decision.pressure}")
        for option in spine.decision.options:
            lines.append(
                f"- {option.option} | immediate cost: {option.immediate_cost} | "
                f"possible consequence: {option.possible_consequence}"
            )
    else:
        lines.append("- No mandatory branch choice for this reader/story-family profile.")

    lines.extend([
        "",
        f"## Climax\n{spine.climax}",
        "",
        f"## Local payoff\n{spine.local_payoff}",
        "",
        "## Unresolved hooks",
    ])
    lines.extend(f"- {item}" for item in spine.unresolved_hooks)
    lines.extend(["", "## Possible persistent outcomes"])
    lines.extend(
        f"- {item.type}: {item.description} (commit only if {item.commit_condition})"
        for item in spine.persistent_outcome_candidates
    )
    lines.extend(["", "## Writer limits"])
    lines.extend(f"- {item}" for item in spine.writer_rules)
    return "\n".join(lines).strip() + "\n"


def build_human_approval(
    *,
    spine: NarrativeSpineV1,
    gate: SpineProductGateV19,
    source_context_pack_id: str,
    source_context_fingerprint: str,
    current_context_pack: SpineContextPackV1,
    reviewer_note: str,
) -> dict[str, Any]:
    if gate.decision != "ACCEPT":
        raise RuntimeError("Spine Product Gate must ACCEPT before human approval.")
    if source_context_pack_id != current_context_pack.context_pack_id:
        raise RuntimeError("Current ContextPack id differs from Spine source.")
    if source_context_fingerprint != current_context_pack.context_fingerprint:
        raise RuntimeError("Current ContextPack fingerprint differs from Spine source.")

    artifact_hash = spine_hash(spine)
    approval_id = hashlib.sha256(
        f"{source_context_fingerprint}:{artifact_hash}:APPROVE".encode("utf-8")
    ).hexdigest()
    return {
        "schema": "spineforge-v19-human-approved.v1",
        "approval_id": approval_id,
        "context_pack_id": source_context_pack_id,
        "context_fingerprint": source_context_fingerprint,
        "spine_hash": artifact_hash,
        "human_review": {
            "verdict": "APPROVE",
            "reviewer_note": reviewer_note,
            "story_writer_authorized": True,
        },
    }
