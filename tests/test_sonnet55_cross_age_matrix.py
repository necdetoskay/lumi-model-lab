from __future__ import annotations

import json
from pathlib import Path

from src.capability_cube import (
    default_reading_mode_for_age_tier,
    narrative_age_tier_for_range,
    standard_target_words_for_age_tier,
)
from src.reader_profile_v2 import ReaderDevelopmentProfileV2


MATRIX = Path(
    "data/specifications/story_lab/sonnet55_cross_age_qualification_matrix_v1.json"
)
AGE12 = Path("data/specifications/reader_profiles/age12_adventure_v2.json")


def test_cross_age_matrix_matches_canonical_capability_cube() -> None:
    matrix = json.loads(MATRIX.read_text())
    assert matrix["status"] == "C0_PAID_BLOCKED"
    assert matrix["paid_boundary"]["authorized"] is False

    for case in matrix["cases"]:
        age = int(case["exact_age"])
        tier = narrative_age_tier_for_range(age, age)
        assert case["narrative_age_tier"] == tier
        assert case["reading_mode"] == default_reading_mode_for_age_tier(tier)
        assert (
            case["qualification_standard_target_words"]
            == standard_target_words_for_age_tier(tier)
        )


def test_age12_control_profile_is_valid_and_immutable_control() -> None:
    profile = ReaderDevelopmentProfileV2.model_validate_json(AGE12.read_text())
    matrix = json.loads(MATRIX.read_text())
    control = next(row for row in matrix["cases"] if row["exact_age"] == 12)

    assert profile.exact_age == 12
    assert control["status"] == "BASELINE_GREEN"
    assert control["reader_profile"] == str(AGE12)
    assert control["product_standard_words_min"] == profile.standard_session.target_words_min
    assert control["product_standard_words_max"] == profile.standard_session.target_words_max


def test_unqualified_ages_cannot_have_paid_authority_yet() -> None:
    matrix = json.loads(MATRIX.read_text())
    pending = [row for row in matrix["cases"] if row["exact_age"] != 12]

    assert {row["exact_age"] for row in pending} == {18, 25, 40, 60}
    for row in pending:
        assert row["reader_profile"] is None
        assert row["product_standard_words_min"] is None
        assert row["product_standard_words_max"] is None
        assert row["status"] == "BLOCKED_READER_PROFILE_AND_PRODUCT_BUDGET"
