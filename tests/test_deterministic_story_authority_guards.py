from __future__ import annotations

import json
from pathlib import Path

from src.deterministic_story_authority_guards import run_deterministic_authority_guards
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_canon_authority_qualification import _gold_segment_map, _score

SOURCE=Path("data/specifications/story_lab/age18_cross_age_c2_postprocess_source_36612862926.json")
APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
GOLD=Path("data/specifications/story_lab/age18_cross_age_c2_confirmed_authority_gold.json")


def authority():
    return build_story_authority_packet_v2(json.loads(APPROVED.read_text()))


def test_age18_story_hits_all_three_confirmed_roots_without_model() -> None:
    source=json.loads(SOURCE.read_text())
    gold=json.loads(GOLD.read_text())
    findings=run_deterministic_authority_guards(source["english_story"],authority())
    mapping=_gold_segment_map(source["english_story"],gold["targets"])
    score=_score(findings,gold["targets"],mapping)
    assert score["recall"]==1.0
    assert set(score["matched_targets"])=={
        "premature_formal_record_commit",
        "setup_instrument_exclusion_overclaim",
        "raw_notes_blank_page_contradiction",
    }


def test_future_intention_to_file_is_not_premature_commit() -> None:
    story=(
        "She wrote five readings into her field notes. "
        "She would file a provisional record after the reviewer checked it. "
        "The reviewer signed the entry. "
        "The provisional record was filed."
    )
    findings=run_deterministic_authority_guards(story,authority())
    assert not [x for x in findings if x["guard_id"]=="formal_record_ordering"]


def test_reviewed_formal_absence_does_not_erase_raw_notes() -> None:
    story=(
        "She logged five readings in her field notebook. "
        "There was no reviewed formal record before the window closed."
    )
    findings=run_deterministic_authority_guards(story,authority())
    assert not [x for x in findings if x["guard_id"]=="raw_observation_erasure"]


def test_blank_page_after_raw_measurements_is_blocked() -> None:
    story=(
        "She logged five readings in her field notebook. "
        "If she left now, the next surveyor would start from a blank page."
    )
    findings=run_deterministic_authority_guards(story,authority())
    rows=[x for x in findings if x["guard_id"]=="raw_observation_erasure"]
    assert len(rows)==1


def test_uncertain_setup_language_is_allowed() -> None:
    story=(
        "The pattern survived the series, but setup drift and instrument error "
        "could still explain it."
    )
    findings=run_deterministic_authority_guards(story,authority())
    assert not [x for x in findings if x["guard_id"]=="unresolved_setup_overclaim"]


def test_definitive_setup_exclusion_is_blocked() -> None:
    story="Whatever happened, it was not a single bad setup."
    findings=run_deterministic_authority_guards(story,authority())
    rows=[x for x in findings if x["guard_id"]=="unresolved_setup_overclaim"]
    assert len(rows)==1


def test_wrong_character_thought_is_not_caught_by_hard_guard() -> None:
    story=(
        "For a second she thought movement meant cause. "
        "Then she corrected herself: three variables had changed together."
    )
    findings=run_deterministic_authority_guards(story,authority())
    assert not [x for x in findings if x["guard_id"]=="unresolved_cause_overclaim"]


def test_no_documented_series_after_logged_readings_is_blocked() -> None:
    story=(
        "She logged five readings with timestamps and tide heights. "
        "If she left now, there would be no documented series for the next surveyor."
    )
    findings=run_deterministic_authority_guards(story,authority())
    rows=[x for x in findings if x["guard_id"]=="raw_observation_erasure"]
    assert len(rows)==1


def test_unlikely_setup_error_language_is_blocked_when_setup_remains_unresolved() -> None:
    story=(
        "Offset is unlikely to be simple instrument or setup error given the ordered decline; "
        "however, this is not yet proven."
    )
    findings=run_deterministic_authority_guards(story,authority())
    rows=[x for x in findings if x["guard_id"]=="unresolved_setup_overclaim"]
    assert len(rows)==1


def test_fixed_offset_reinterpretation_without_setup_exclusion_is_allowed() -> None:
    story=(
        "The changing series is less consistent with a single fixed offset, "
        "but setup drift and instrument error remain possible."
    )
    findings=run_deterministic_authority_guards(story,authority())
    assert not [x for x in findings if x["guard_id"]=="unresolved_setup_overclaim"]
