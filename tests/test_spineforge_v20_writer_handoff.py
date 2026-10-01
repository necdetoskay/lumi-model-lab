from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v20_writer_handoff import build_writer_handoff


APPROVAL = Path("evidence/spineforge-v20-human-review/36910614976-approved.json")
REPAIR = Path("evidence/spineforge-v20-paid-repair/36910614976/age12-island-v20-repair1-result.json")
PACK = Path("data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json")


def _load():
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    repair = json.loads(REPAIR.read_text(encoding="utf-8"))
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    return approval, repair, pack


def test_human_approval_is_bound_to_exact_repaired_spine_and_writer_ready():
    approval, repair, pack = _load()
    handoff = build_writer_handoff(
        approval=approval,
        repair_result=repair,
        current_context_pack=pack,
    )
    assert handoff["status"] == "WRITER_READY"
    assert handoff["writer_model"] == "aion-labs/aion-3.5-mini"
    assert handoff["spine_hash"] == "f9c5bed93448d6c56787466ae583dfcee06d0f856641d9c3901136f142bffae6"
    assert handoff["context_fingerprint"] == "090ae8343daa2b24e95923ee9e9dc11356664baed9a79c4ff95fd0207b834233"
    assert handoff["target_words_min"] == 1600
    assert handoff["target_words_max"] == 2500
    assert handoff["paid_writer_execution_authorized"] is False
    assert handoff["human_review"]["story_writer_authorized"] is True


def test_writer_handoff_blocks_stale_spine_hash():
    approval, repair, pack = _load()
    stale = deepcopy(approval)
    stale["spine_hash"] = "0" * 64
    with pytest.raises(RuntimeError, match="Spine hash"):
        build_writer_handoff(
            approval=stale,
            repair_result=repair,
            current_context_pack=pack,
        )


def test_writer_handoff_blocks_non_accept_gate():
    approval, repair, pack = _load()
    bad = deepcopy(repair)
    bad["product_gate"]["decision"] = "REPAIR"
    bad["product_gate"]["blocking_findings"] = [{"synthetic": True}]
    with pytest.raises(RuntimeError, match="clean ACCEPT"):
        build_writer_handoff(
            approval=approval,
            repair_result=bad,
            current_context_pack=pack,
        )


def test_writer_handoff_blocks_stale_context():
    approval, repair, pack = _load()
    raw = pack.model_dump(mode="json", by_alias=True)
    raw["context_fingerprint"] = "stale"
    stale_pack = SpineContextPackV1.model_validate(raw)
    with pytest.raises(RuntimeError, match="stale"):
        build_writer_handoff(
            approval=approval,
            repair_result=repair,
            current_context_pack=stale_pack,
        )
