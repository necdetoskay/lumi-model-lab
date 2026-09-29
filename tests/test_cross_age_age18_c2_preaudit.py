from __future__ import annotations

import json
from pathlib import Path

from src.story_authority_packet import build_story_authority_packet

APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
PACKET=Path("data/specifications/story_lab/age18_cross_age_c2_authority_packet_v1.json")
PREAUDIT=Path("data/specifications/story_lab/age18_cross_age_c2_human_preaudit.json")


def test_age18_authority_packet_preserves_record_and_inference_rules() -> None:
    approved=json.loads(APPROVED.read_text())
    pinned=json.loads(PACKET.read_text())
    assert build_story_authority_packet(approved)==pinned
    assert pinned["record_state_rules"]["raw_observations_are_distinct_from_formal_reviewed_entry"] is True
    assert pinned["record_state_rules"]["chosen_branch_controls_formal_entry_state"] is True
    ceiling=pinned["must_remain_unresolved"]["inference_ceiling"]
    assert "setup-independence" in ceiling
    assert "physical cause" in ceiling
    assert "recurrence" in ceiling


def test_age18_human_preaudit_has_three_confirmed_roots() -> None:
    pre=json.loads(PREAUDIT.read_text())
    assert pre["writer_run_id"]==36612862926
    assert pre["deterministic"]["word_count"]==2172
    assert pre["deterministic"]["branch_observed"]=="provisional_record"
    ids={row["id"] for row in pre["confirmed_audit_targets"]}
    assert ids=={
        "premature_formal_record_commit",
        "setup_instrument_exclusion_overclaim",
        "raw_notes_blank_page_contradiction",
    }
    assert pre["decision"]["paid_next_stage_authorized"] is False
