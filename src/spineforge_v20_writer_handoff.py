from __future__ import annotations

from typing import Any

from src.narrative_spine_v1_contract import NarrativeSpineV1
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19_human_review import spine_hash


WRITER_MODEL = "aion-labs/aion-3.5-mini"


def build_writer_handoff(
    *,
    approval: dict[str, Any],
    repair_result: dict[str, Any],
    current_context_pack: SpineContextPackV1,
) -> dict[str, Any]:
    if approval.get("schema") != "spineforge-v20-human-approved.v1":
        raise RuntimeError("v20 human approval artifact schema mismatch.")
    if approval.get("gate_decision") != "ACCEPT":
        raise RuntimeError("Writer handoff requires ACCEPT gate.")
    if not approval.get("writer_handoff_ready"):
        raise RuntimeError("Human approval is not Writer-ready.")
    human = approval.get("human_review") or {}
    if human.get("verdict") != "APPROVE":
        raise RuntimeError("Human APPROVE verdict is required.")
    if human.get("story_writer_authorized") is not True:
        raise RuntimeError("Human approval did not authorize Writer handoff.")

    if repair_result.get("status") != "awaiting_human_review":
        raise RuntimeError("Repair result is not a human-reviewable accepted product.")
    gate = repair_result.get("product_gate") or {}
    if gate.get("decision") != "ACCEPT" or gate.get("blocking_findings"):
        raise RuntimeError("Writer handoff requires a clean ACCEPT product gate.")

    spine = NarrativeSpineV1.model_validate(repair_result["repaired_spine"])
    actual_spine_hash = spine_hash(spine)
    if actual_spine_hash != approval.get("spine_hash"):
        raise RuntimeError("Approved Spine hash differs from repaired Spine.")
    if approval.get("context_pack_id") != current_context_pack.context_pack_id:
        raise RuntimeError("Approved ContextPack id is stale.")
    if approval.get("context_fingerprint") != current_context_pack.context_fingerprint:
        raise RuntimeError("Approved ContextPack fingerprint is stale.")
    if repair_result.get("context_fingerprint") != current_context_pack.context_fingerprint:
        raise RuntimeError("Repair result ContextPack fingerprint is stale.")

    reader = current_context_pack.reader_profile
    session = current_context_pack.session_target
    exact_age = int(reader["exact_age"])
    target_min = int(session["target_words_min"])
    target_max = int(session["target_words_max"])
    if exact_age != 12:
        raise RuntimeError("v20 age12 Writer handoff exact_age mismatch.")
    if target_min != 1600 or target_max != 2500:
        raise RuntimeError("v20 Writer handoff word authority mismatch.")

    return {
        "schema": "spineforge-v20-writer-handoff.v1",
        "status": "WRITER_READY",
        "writer_model": WRITER_MODEL,
        "approval_id": approval["approval_id"],
        "context_pack_id": current_context_pack.context_pack_id,
        "context_fingerprint": current_context_pack.context_fingerprint,
        "spine_hash": actual_spine_hash,
        "exact_age": exact_age,
        "target_words_min": target_min,
        "target_words_max": target_max,
        "preferred_words_min": 2000,
        "preferred_words_max": 2200,
        "human_review": human,
        "paid_writer_execution_authorized": False,
        "writer_input": {
            "task": "write_one_finished_episode_from_human_approved_narrative_spine",
            "reader_profile": reader,
            "session_target": session,
            "spine_context_pack": current_context_pack.model_dump(mode="json", by_alias=True),
            "approved_narrative_spine": spine.model_dump(mode="json", by_alias=True),
            "hard_rules": {
                "one_writer_call_only": True,
                "editor_call_forbidden": True,
                "judge_call_forbidden": True,
                "repair_call_forbidden": True,
                "translation_call_forbidden": True,
                "follow_selected_spine_path_only": True,
                "saga_unknowns_must_remain_unresolved": True,
                "database_state_commit_forbidden": True,
            },
        },
    }
