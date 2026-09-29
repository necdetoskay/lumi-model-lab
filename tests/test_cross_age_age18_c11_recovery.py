from __future__ import annotations

import json
from pathlib import Path

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.sonnet55_spine_safe_normalize import normalize_reversal_support_refs

SOURCE = Path(
    "data/specifications/story_lab/"
    "sonnet55_cross_age_age18_c11_recovery_source_36610913523.json"
)


def test_age18_c11_self_reference_is_safely_removed() -> None:
    source = json.loads(SOURCE.read_text())
    raw = source["architect_raw_payload"]
    normalized, repairs = normalize_reversal_support_refs(raw)

    assert len(repairs) == 1
    assert repairs[0]["removed_refs"] == ["reversal_recognition"]
    assert repairs[0]["kept_refs"] == ["five_reading_series"]

    before = raw["reversal"]["evidence"][3]
    after = normalized["reversal"]["evidence"][3]
    assert before["claim"] == after["claim"]
    assert before["certainty"] == after["certainty"]

    spine = EpisodeSpineV2.model_validate(normalized)
    assert spine.exact_age == 18
    assert spine.episode_role == "MAIN_SAGA_ENTRY"
    assert spine.target_words_min == 1600
    assert spine.target_words_max == 2500
    assert spine.logistics_plan.location_sequence == [
        "meridian_harbor",
        "beacon_ridge",
        "meridian_harbor",
    ]


def test_c11_fixed_previous_branch_conflicts() -> None:
    source = json.loads(SOURCE.read_text())
    normalized, _ = normalize_reversal_support_refs(source["architect_raw_payload"])
    spine = EpisodeSpineV2.model_validate(normalized)

    assert "UNPLANNED" in " ".join(spine.writer_rules).upper()
    assert "Fresh_setup_repeat:" in spine.local_payoff
    assert "Provisional_record:" in spine.local_payoff
    assert "no reviewed formal record" in spine.local_payoff
