from __future__ import annotations

from typing import Any

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v5_contract import SpineForgeProductV5


def build_spineforge_v5_approval(
    *,
    evidence: dict[str, Any],
    current_context_pack: SpineContextPackV1,
    source_run_id: int,
    reviewer_note: str,
) -> dict[str, Any]:
    if evidence.get("status") != "awaiting_human_review":
        raise RuntimeError("SpineForge v5 product is not awaiting human review.")
    if evidence.get("context_pack_id") != current_context_pack.context_pack_id:
        raise RuntimeError("Current ContextPack id differs from Spine Product source.")
    if evidence.get("context_fingerprint") != current_context_pack.context_fingerprint:
        raise RuntimeError("Current ContextPack fingerprint differs from Spine Product source.")

    product = SpineForgeProductV5.model_validate(evidence["spine_product"])
    if product.context_fingerprint != current_context_pack.context_fingerprint:
        raise RuntimeError("Spine Product context fingerprint is stale.")
    if product.product_gate.decision != "ACCEPT":
        raise RuntimeError("Spine Product Gate must ACCEPT before human approval.")

    return {
        "schema_version": "spineforge-v5-human-approved.v1",
        "source_run_id": source_run_id,
        "context_pack_id": current_context_pack.context_pack_id,
        "context_fingerprint": current_context_pack.context_fingerprint,
        "spine_context_pack": current_context_pack.model_dump(mode="json", by_alias=True),
        "spine_product": product.model_dump(mode="json", by_alias=True),
        "episode_spine": product.compiled_spine.model_dump(mode="json", by_alias=True),
        "human_review": {
            "verdict": "APPROVE",
            "reviewer_note": reviewer_note,
            "story_writer_authorized": True,
        },
        "spineforge_usage_rollup": evidence["pipeline_usage_rollup"],
    }
