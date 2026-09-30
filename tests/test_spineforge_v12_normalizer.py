from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v12 import _validate_episode_authority
from src.spineforge_v12_normalizer import (
    DERIVED_PATH,
    MechanicalNormalizationError,
    normalize_mechanical_fields,
)


RESULT = Path("experiments/results/spineforge-v11/36746646152/result.json")


def _evidence() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _diff_paths(before, after, prefix=""):
    if type(before) is not type(after):
        return [prefix or "<root>"]
    if isinstance(before, dict):
        out = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in before or key not in after:
                out.append(path)
            else:
                out.extend(_diff_paths(before[key], after[key], path))
        return out
    if isinstance(before, list):
        return [] if before == after else [prefix]
    return [] if before == after else [prefix]


def test_v11_attempt1_normalizes_only_derived_route_then_fully_validates():
    evidence = _evidence()
    raw = evidence["architect_raw"]
    normalized, report = normalize_mechanical_fields(raw)

    assert report.changed is True
    assert len(report.changes) == 1
    assert report.changes[0].path == DERIVED_PATH
    assert report.changes[0].semantic_change is False
    assert report.changes[0].before == ["vellum_hall", "greyfen", "ashen_gate"]
    assert report.changes[0].after == [
        "vellum_hall", "greyfen", "ashen_gate", "greyfen"
    ]
    assert _diff_paths(raw, normalized) == [DERIVED_PATH]

    spine = EpisodeSpineV3.model_validate(normalized)
    pack = SpineContextPackV1.model_validate(evidence["context_pack"])
    _validate_episode_authority(spine=spine, pack=pack)


def test_normalizer_is_idempotent():
    raw = _evidence()["architect_raw"]
    once, first = normalize_mechanical_fields(raw)
    twice, second = normalize_mechanical_fields(once)
    assert first.changed is True
    assert second.changed is False
    assert twice == once


def test_normalizer_never_changes_semantic_story_fields():
    raw = _evidence()["architect_raw"]
    normalized, _ = normalize_mechanical_fields(raw)
    for key in [
        "beats", "reversal", "decision_point", "climax", "local_payoff",
        "saga_progression", "persistent_outcome_candidates", "writer_rules",
    ]:
        assert normalized[key] == raw[key]


def test_normalizer_does_not_hide_semantic_contract_failure():
    raw = copy.deepcopy(_evidence()["architect_raw"])
    raw["reversal"]["evidence"][0]["certainty"] = "CERTAIN"
    normalized, _ = normalize_mechanical_fields(raw)
    with pytest.raises(ValidationError) as exc:
        EpisodeSpineV3.model_validate(normalized)
    assert "certainty" in str(exc.value)


def test_normalizer_does_not_hide_authority_failure():
    evidence = _evidence()
    raw = copy.deepcopy(evidence["architect_raw"])
    raw["beats"][3]["location_ref"] = "hidden_unapproved_location"
    normalized, _ = normalize_mechanical_fields(raw)
    spine = EpisodeSpineV3.model_validate(normalized)
    pack = SpineContextPackV1.model_validate(evidence["context_pack"])
    with pytest.raises(RuntimeError) as exc:
        _validate_episode_authority(spine=spine, pack=pack)
    assert "outside approved premise" in str(exc.value)


def test_normalizer_refuses_to_invent_missing_structure():
    raw = copy.deepcopy(_evidence()["architect_raw"])
    del raw["beats"]
    with pytest.raises(MechanicalNormalizationError):
        normalize_mechanical_fields(raw)

    raw = copy.deepcopy(_evidence()["architect_raw"])
    del raw["logistics_plan"]
    with pytest.raises(MechanicalNormalizationError):
        normalize_mechanical_fields(raw)
