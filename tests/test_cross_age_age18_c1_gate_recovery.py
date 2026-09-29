from __future__ import annotations

import json
from pathlib import Path

from src.cross_age_age18_c1_gate_recovery import validate_normalized_candidate
from src.cross_age_spine_safe_normalize import normalize_logistics_location_sequence


SOURCE = Path(
    "data/specifications/story_lab/"
    "sonnet55_cross_age_age18_c1_recovery_source_36608347735.json"
)


def test_age18_recovered_candidate_is_strictly_valid() -> None:
    source = json.loads(SOURCE.read_text())
    normalized, repairs = normalize_logistics_location_sequence(
        source["architect_raw_payload"]
    )
    assert len(repairs) == 3
    spine = validate_normalized_candidate(source, normalized)
    assert spine.exact_age == 18
    assert spine.session == "STANDARD"
    assert spine.target_words_min == 1600
    assert spine.target_words_max == 2500
    assert spine.episode_role == "MAIN_SAGA_ENTRY"
    assert spine.saga_progression.intended_milestone_keys == [
        "first_discrepancy_logged"
    ]
    assert spine.saga_progression.commit_only_if_earned is True
