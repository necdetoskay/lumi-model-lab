from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v7_contract import SpineForgeProductV7


def build_spineforge_v7_approval(
    *,
    evidence: dict[str, Any],
    current_context_pack: SpineContextPackV1,
    source_run_id: int,
    reviewer_note: str,
) -> dict[str, Any]:
    if evidence.get("status") != "awaiting_human_review":
        raise RuntimeError("SpineForge v7 product is not awaiting human review.")
    if evidence.get("context_pack_id") != current_context_pack.context_pack_id:
        raise RuntimeError("Current ContextPack id differs from Spine Product source.")
    if evidence.get("context_fingerprint") != current_context_pack.context_fingerprint:
        raise RuntimeError("Current ContextPack fingerprint differs from Spine Product source.")
    product = SpineForgeProductV7.model_validate(evidence["spine_product"])
    if product.context_fingerprint != current_context_pack.context_fingerprint:
        raise RuntimeError("Spine Product context fingerprint is stale.")
    if product.product_gate.decision != "ACCEPT":
        raise RuntimeError("Spine Product Gate must ACCEPT before human approval.")
    return {
        "schema_version": "spineforge-v7-human-approved.v1",
        "source_run_id": source_run_id,
        "context_pack_id": current_context_pack.context_pack_id,
        "context_fingerprint": current_context_pack.context_fingerprint,
        "spine_context_pack": current_context_pack.model_dump(mode="json", by_alias=True),
        "spine_product": product.model_dump(mode="json", by_alias=True),
        "episode_spine": product.structural_assembly.episode_spine.model_dump(
            mode="json", by_alias=True
        ),
        "human_review": {
            "verdict": "APPROVE",
            "reviewer_note": reviewer_note,
            "story_writer_authorized": True,
        },
        "spineforge_usage_rollup": evidence["pipeline_usage_rollup"],
    }


def write_spineforge_v7_approval(
    *,
    evidence_path: Path,
    context_pack_path: Path,
    out_path: Path,
    source_run_id: int,
    reviewer_note: str,
) -> dict[str, Any]:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    pack = SpineContextPackV1.model_validate_json(
        context_pack_path.read_text(encoding="utf-8")
    )
    approved = build_spineforge_v7_approval(
        evidence=evidence,
        current_context_pack=pack,
        source_run_id=source_run_id,
        reviewer_note=reviewer_note,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(approved, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return approved
