from __future__ import annotations

import hashlib
from typing import Any, Literal

from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19
from src.spine_context_pack_v1 import SpineContextPackV1, canonical_json


HumanReviewVerdict = Literal["APPROVE", "REVISE", "REJECT"]


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


def _assert_current_context(
    *,
    source_context_pack_id: str,
    source_context_fingerprint: str,
    current_context_pack: SpineContextPackV1,
) -> None:
    if source_context_pack_id != current_context_pack.context_pack_id:
        raise RuntimeError("Current ContextPack id differs from Spine source.")
    if source_context_fingerprint != current_context_pack.context_fingerprint:
        raise RuntimeError("Current ContextPack fingerprint differs from Spine source.")


def build_human_review_decision(
    *,
    spine: NarrativeSpineV1,
    gate: SpineProductGateV19,
    source_context_pack_id: str,
    source_context_fingerprint: str,
    current_context_pack: SpineContextPackV1,
    verdict: HumanReviewVerdict,
    reason_code: str,
    reviewer_note: str,
) -> dict[str, Any]:
    _assert_current_context(
        source_context_pack_id=source_context_pack_id,
        source_context_fingerprint=source_context_fingerprint,
        current_context_pack=current_context_pack,
    )

    reason_code = reason_code.strip()
    reviewer_note = reviewer_note.strip()
    if not reason_code:
        raise ValueError("Human review reason_code must not be empty.")
    if not reviewer_note:
        raise ValueError("Human review reviewer_note must not be empty.")

    if verdict == "APPROVE" and gate.decision != "ACCEPT":
        raise RuntimeError("Spine Product Gate must ACCEPT before human approval.")

    artifact_hash = spine_hash(spine)
    review_id = hashlib.sha256(
        (
            f"{source_context_fingerprint}:{artifact_hash}:{gate.decision}:"
            f"{verdict}:{reason_code}:{reviewer_note}"
        ).encode("utf-8")
    ).hexdigest()

    if verdict == "APPROVE":
        status = "WRITER_READY"
        required_action = "WRITER"
        story_writer_authorized = True
        spine_closed = False
    elif verdict == "REVISE":
        status = "HUMAN_REVISION_REQUIRED"
        required_action = "TARGETED_REPAIR_REQUIRES_EXPLICIT_AUTHORIZATION"
        story_writer_authorized = False
        spine_closed = False
    else:
        status = "HUMAN_REJECTED_PREMISE"
        required_action = "REPLAN_REQUIRES_EXPLICIT_AUTHORIZATION"
        story_writer_authorized = False
        spine_closed = True

    return {
        "schema": "spineforge-v19-human-review.v2",
        "review_id": review_id,
        "context_pack_id": source_context_pack_id,
        "context_fingerprint": source_context_fingerprint,
        "spine_hash": artifact_hash,
        "gate_decision": gate.decision,
        "human_review": {
            "verdict": verdict,
            "reason_code": reason_code,
            "reviewer_note": reviewer_note,
            "status": status,
            "required_action": required_action,
            "story_writer_authorized": story_writer_authorized,
            "spine_closed": spine_closed,
        },
    }


def build_human_approval(
    *,
    spine: NarrativeSpineV1,
    gate: SpineProductGateV19,
    source_context_pack_id: str,
    source_context_fingerprint: str,
    current_context_pack: SpineContextPackV1,
    reviewer_note: str,
) -> dict[str, Any]:
    decision = build_human_review_decision(
        spine=spine,
        gate=gate,
        source_context_pack_id=source_context_pack_id,
        source_context_fingerprint=source_context_fingerprint,
        current_context_pack=current_context_pack,
        verdict="APPROVE",
        reason_code="HUMAN_APPROVED",
        reviewer_note=reviewer_note,
    )
    return {
        "schema": "spineforge-v19-human-approved.v1",
        "approval_id": decision["review_id"],
        "context_pack_id": decision["context_pack_id"],
        "context_fingerprint": decision["context_fingerprint"],
        "spine_hash": decision["spine_hash"],
        "human_review": {
            "verdict": "APPROVE",
            "reviewer_note": reviewer_note.strip(),
            "story_writer_authorized": True,
        },
    }
