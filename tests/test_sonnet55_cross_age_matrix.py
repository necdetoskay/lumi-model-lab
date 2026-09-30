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
    assert matrix["status"] == "C0_GREEN"
    assert matrix["paid_boundary"]["authorized"] is False
    assert matrix["paid_boundary"]["next_scope"] is None

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


def test_cross_age_reader_authorities_are_promoted_with_fixed_product_budget() -> None:
    matrix = json.loads(MATRIX.read_text())
    promoted = [row for row in matrix["cases"] if row["exact_age"] != 12]

    assert {row["exact_age"] for row in promoted} == {18, 25, 40, 60}
    for row in promoted:
        assert row["reader_profile"] is not None
        assert row["product_standard_words_min"] == 1600
        assert row["product_standard_words_max"] == 2500
        if row["exact_age"] == 18:
            assert row["status"] == "PUBLICATION_READY"
            assert row["latest_gate_decision"] == "ACCEPT"
            assert row["latest_run_id"] == 36612862926
            assert row["writer_run_id"] == 36612862926
            assert row["writer_word_count"] == 2172
            assert row["confirmed_preaudit_root_count"] == 3
            assert row["c3_run_id"] == 36614762650
            assert row["c3_matched_root_count"] == 1
            assert row["c3_target_root_count"] == 3
            assert row["c31_run_id"] == 36616784331
            assert row["c31_matched_root_count"] == 2
            assert row["c31_target_root_count"] == 3
            assert row["c32_deterministic_root_recall"] == 1.0
            assert row["c32_deterministic_unmapped_findings"] == 0
            assert row["c32_clean_control_age12_findings"] == 0
            assert row["c4_run_id"] == 36618878723
            assert row["c4_model_repairs"] == 3
            assert row["c41_deterministic_repairs"] == 2
            assert row["accepted_english_word_count"] == 2176
            assert row["post_repair_guard_findings"] == 0
            assert row["c5_run_id"] == 36620129124
            assert row["translation_cost_usd"] == 0.01754025
            assert row["translation_tokens"] == 7391
            assert row["turkish_word_count"] == 1814
            assert row["c6_run_id"] == 36654772221
            assert row["final_product_path_cost_usd"] == 0.17766185
            assert row["final_product_path_tokens"] == 84747
            assert row["final_product_path_latency_seconds"] == 426.802
            assert row["final_api_calls"] == 6
            assert row["final_turkish_word_count"] == 1817
        else:
            assert row["status"] == "READY_FOR_SEQUENTIAL_QUALIFICATION"


def test_promoted_profiles_validate_and_candidate_files_remain_as_history() -> None:
    matrix = json.loads(MATRIX.read_text())
    assert matrix["status"] == "C0_GREEN"

    for row in matrix["cases"]:
        if row["exact_age"] == 12:
            continue
        candidate_path = Path(row["candidate_profile"])
        candidate = ReaderDevelopmentProfileV2.model_validate_json(candidate_path.read_text())
        promoted = ReaderDevelopmentProfileV2.model_validate_json(Path(row["reader_profile"]).read_text())
        assert candidate.exact_age == promoted.exact_age == row["exact_age"]
        assert promoted.capability_bridge.narrative_age_tier == row["narrative_age_tier"]
        assert promoted.capability_bridge.reading_mode == row["reading_mode"]
        assert promoted.standard_session.target_words_min == 1600
        assert promoted.standard_session.target_words_max == 2500
