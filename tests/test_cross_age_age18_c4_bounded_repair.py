from __future__ import annotations

import json
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.story_authority_packet_v2 import build_story_authority_packet_v2

SOURCE=Path("data/specifications/story_lab/age18_cross_age_c2_postprocess_source_36612862926.json")
APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
GUARD=Path("data/specifications/story_lab/age18_cross_age_c32_deterministic_guard_evidence.json")


def test_c4_inputs_are_locked_to_three_confirmed_local_defects() -> None:
    source=json.loads(SOURCE.read_text())
    approved=json.loads(APPROVED.read_text())
    guard=json.loads(GUARD.read_text())
    _validate_source(source,approved)
    assert guard["status"]=="PASS"
    assert guard["age18"]["score"]["recall"]==1.0
    assert guard["age18"]["score"]["unmapped_finding_count"]==0
    findings=guard["age18"]["findings"]
    assert len(findings)==3
    assert all(row["repair_scope"]=="local" for row in findings)
    assert {row["guard_id"] for row in findings}=={
        "formal_record_ordering",
        "raw_observation_erasure",
        "unresolved_setup_overclaim",
    }


def test_c4_authority_packet_preserves_branch_and_inference_limits() -> None:
    approved=json.loads(APPROVED.read_text())
    packet=build_story_authority_packet_v2(approved)
    assert packet["record_state_rules"]["chosen_branch_controls_formal_entry_state"] is True
    assert "setup-independence" in packet["must_remain_unresolved"]["inference_ceiling"]
    assert "provisional_record" in packet["record_state_rules"]["branch_contracts"]
