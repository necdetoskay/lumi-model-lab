from __future__ import annotations

import json
from pathlib import Path

from src.episode_postprocess_v2 import _validate_source
from src.story_canon_authority_qualification import _gold_segment_map
from src.story_authority_packet import build_story_authority_packet

SOURCE=Path("data/specifications/story_lab/age18_cross_age_c2_postprocess_source_36612862926.json")
APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
GOLD=Path("data/specifications/story_lab/age18_cross_age_c2_confirmed_authority_gold.json")
PACKET=Path("data/specifications/story_lab/age18_cross_age_c2_authority_packet_v1.json")


def test_age18_c3_inputs_are_strict_and_gold_anchors_exist() -> None:
    source=json.loads(SOURCE.read_text())
    approved=json.loads(APPROVED.read_text())
    gold=json.loads(GOLD.read_text())
    _validate_source(source,approved)
    mapping=_gold_segment_map(source["english_story"],gold["targets"])
    assert set(mapping)=={
        "premature_formal_record_commit",
        "setup_instrument_exclusion_overclaim",
        "raw_notes_blank_page_contradiction",
    }
    assert all(mapping.values())
    assert source["deterministic_checks"]["word_count"]==2172
    assert source["source_pipeline_usage_rollup"]["totals"]["cost_usd"]==0.12550455


def test_age18_pinned_authority_packet_matches_builder() -> None:
    approved=json.loads(APPROVED.read_text())
    packet=json.loads(PACKET.read_text())
    assert packet==build_story_authority_packet(approved)
    assert packet["record_state_rules"]["raw_observations_are_distinct_from_formal_reviewed_entry"] is True
    assert "setup-independence" in packet["must_remain_unresolved"]["inference_ceiling"]
