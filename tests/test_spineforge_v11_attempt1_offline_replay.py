from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v11 import _validate_episode_authority


RESULT = Path("experiments/results/spineforge-v11/36746646152/result.json")


def _collapsed_beat_locations(raw: dict) -> list[str]:
    ordered: list[str] = []
    for beat in raw["beats"]:
        location = beat["location_ref"]
        if not ordered or ordered[-1] != location:
            ordered.append(location)
    return ordered


def test_attempt1_has_exactly_one_replayable_mechanical_contract_defect() -> None:
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    raw = evidence["architect_raw"]

    with pytest.raises(ValidationError) as exc:
        EpisodeSpineV3.model_validate(raw)
    message = str(exc.value)
    assert "logistics_plan.location_sequence must match" in message

    repaired = copy.deepcopy(raw)
    repaired["logistics_plan"]["location_sequence"] = _collapsed_beat_locations(repaired)

    spine = EpisodeSpineV3.model_validate(repaired)
    pack = SpineContextPackV1.model_validate(evidence["context_pack"])
    _validate_episode_authority(spine=spine, pack=pack)

    assert repaired["logistics_plan"]["location_sequence"] == [
        "vellum_hall",
        "greyfen",
        "ashen_gate",
        "greyfen",
    ]


def test_attempt1_spine_preserves_roleplay_first_story_shape_after_no_semantic_change() -> None:
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    repaired = copy.deepcopy(evidence["architect_raw"])
    repaired["logistics_plan"]["location_sequence"] = _collapsed_beat_locations(repaired)
    spine = EpisodeSpineV3.model_validate(repaired)

    # These are control invariants, not a replacement for the Sonnet red-team audit.
    assert 8 <= len(spine.beats) <= 12
    assert len(spine.decision_point.branches) >= 2
    assert {row.certainty for row in spine.reversal.evidence} >= {
        "OBSERVED",
        "INFERRED",
        "HYPOTHESIS",
    }
    assert sum(bool(beat.character_action.strip()) for beat in spine.beats) == len(spine.beats)
    actions = [beat.character_action.strip().lower() for beat in spine.beats]
    assert len(set(actions)) >= 6
    assert any(
        any(term in action for term in ("measure", "reading", "compare", "record", "check"))
        for action in actions
    )
    assert spine.saga_progression.commit_only_if_earned is True
    assert spine.decision_point.outcome_uncommitted is True
