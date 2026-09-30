from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.spineforge_contract import SpineForgeProductV1


def build_writer_approved_artifact(
    *,
    spineforge_evidence:dict[str,Any],
    source_run_id:int,
    reviewer_note:str,
)->dict[str,Any]:
    if spineforge_evidence.get("status")!="awaiting_human_review":
        raise RuntimeError("SpineForge product is not awaiting human review.")
    product_raw=spineforge_evidence.get("spine_product")
    if not isinstance(product_raw,dict):
        raise RuntimeError("SpineForge evidence is missing spine_product.")
    product=SpineForgeProductV1.model_validate(product_raw)
    if product.product_gate.decision!="ACCEPT":
        raise RuntimeError("Spine Product Gate must ACCEPT before human approval.")

    return {
        "schema_version":"episode-spine-v2-human-approved.v1",
        "source_run_id":source_run_id,
        "approved_premise":spineforge_evidence["approved_premise"],
        "projection":spineforge_evidence["projection"],
        "episode_spine":product.hardened_spine.model_dump(mode="json",by_alias=True),
        "gate":product.product_gate.model_dump(mode="json",by_alias=True),
        "human_review":{
            "verdict":"APPROVE",
            "reviewer_note":reviewer_note,
            "episode_writer_authorized":True,
            "source_product":"SPINEFORGE_V1",
        },
        "source_usage_rollup":spineforge_evidence["pipeline_usage_rollup"],
        "spineforge_product":product.model_dump(mode="json",by_alias=True),
    }


def write_writer_approved_artifact(
    *,
    source_path:Path,
    out_path:Path,
    source_run_id:int,
    reviewer_note:str,
)->dict[str,Any]:
    source=json.loads(source_path.read_text(encoding="utf-8"))
    result=build_writer_approved_artifact(
        spineforge_evidence=source,
        source_run_id=source_run_id,
        reviewer_note=reviewer_note,
    )
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result
