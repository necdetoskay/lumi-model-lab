from __future__ import annotations

import json
from pathlib import Path

from src.cross_age_spine_safe_normalize import normalize_logistics_location_sequence
from src.episode_spine_v2_contract import EpisodeSpineV2


SOURCE = Path(
    "data/specifications/story_lab/"
    "sonnet55_cross_age_age18_c1_recovery_source_36608347735.json"
)


def test_age18_c1_decorated_location_refs_normalize_without_semantic_rewrite() -> None:
    source = json.loads(SOURCE.read_text())
    raw = source["architect_raw_payload"]
    normalized, repairs = normalize_logistics_location_sequence(raw)

    assert len(repairs) == 3
    assert normalized["logistics_plan"]["location_sequence"] == [
        "meridian_harbor",
        "beacon_ridge",
        "meridian_harbor",
    ]

    # Only logistics sequence decoration changes.
    before = json.loads(json.dumps(raw))
    before["logistics_plan"]["location_sequence"] = normalized["logistics_plan"]["location_sequence"]
    assert before == normalized

    EpisodeSpineV2.model_validate(normalized)


def test_unknown_location_decoration_is_not_rewritten() -> None:
    raw = {
        "beats": [
            {"location_ref": "a"},
            {"location_ref": "b"},
        ],
        "logistics_plan": {
            "location_sequence": ["a", "unknown (x)"],
        },
    }
    normalized, repairs = normalize_logistics_location_sequence(raw)
    assert normalized is raw
    assert repairs == []
