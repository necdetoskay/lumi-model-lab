from __future__ import annotations

import json
from pathlib import Path

from src.story_authority_packet_v2 import build_story_authority_packet_v2

APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")


def packet():
    return build_story_authority_packet_v2(json.loads(APPROVED.read_text()))


def test_v2_contains_positive_character_and_premise_authority() -> None:
    p=packet()
    assert p["schema_version"]=="story-authority-packet.v2"
    assert p["character_authority"]["exact_age"]==18
    assert "junior licensed cartographer" in p["character_authority"]["current_role"]
    joined=" ".join(p["premise_authorized_facts"]).lower()
    assert "certification-grade field check" in joined
    assert "pilot confidence" in joined
    assert "cargo timing" in joined


def test_v2_contains_explicit_spine_event_permissions() -> None:
    p=packet()
    by_key={x["key"]:x for x in p["spine_authorized_events"]}
    assert "pilot's signal query" in by_key["stakeholder_pressure"]["character_action"]
    assert "historical alignment mark" in by_key["historical_mark_check"]["character_action"]
    assert "other beacons are being cross-checked" in by_key["forward_tag"]["external_event"]
    assert "reviewer" in by_key["harbor_close"]["external_event"].lower()


def test_v2_keeps_strict_unresolved_and_record_state_rules() -> None:
    p=packet()
    assert p["record_state_rules"]["raw_observations_are_distinct_from_formal_reviewed_entry"] is True
    assert p["record_state_rules"]["chosen_branch_controls_formal_entry_state"] is True
    assert "setup-independence" in p["must_remain_unresolved"]["inference_ceiling"]
    assert "other beacons" in p["must_remain_unresolved"]["unresolved_after_reversal"]


def test_v2_allows_only_transient_instantiation_not_new_history() -> None:
    pol=packet()["operational_instantiation_policy"]
    assert pol["allow_transient_role_participants"] is True
    assert pol["allow_non_decisive_numeric_instantiation_when_consistent_with_constraints"] is True
    assert "new durable history not authorized" in pol["still_forbid"]
