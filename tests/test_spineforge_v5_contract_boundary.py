from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.spineforge_v5_contract import (
    SpineCreativeIntentV1,
    SpineStructuralCompilationV1,
    migrate_v4_raw_to_v5_intent,
)

FIXTURES = [
    Path("data/specifications/story_lab/spineforge_v5_replay_v4_attempt1_raw.json"),
    Path("data/specifications/story_lab/spineforge_v5_replay_v4_attempt2_raw.json"),
    Path("data/specifications/story_lab/spineforge_v5_replay_v4_attempt3_raw.json"),
]
VALID_SPINE_FIXTURE = Path("data/specifications/story_lab/spineforge_v4_replay_fixture.json")


def test_all_v4_paid_aion_payloads_cross_v5_creative_boundary_without_semantic_mutation() -> None:
    for path in FIXTURES:
        source = json.loads(path.read_text(encoding="utf-8"))
        raw = source["creative_raw_payload"]
        nested_before = json.loads(json.dumps(raw["episode_spine"]))
        migrated = migrate_v4_raw_to_v5_intent(raw)
        intent = SpineCreativeIntentV1.model_validate(migrated)
        assert intent.episode_spine == nested_before
        assert migrated["creative_model"] == "aion-labs/aion-3.5-mini"


def test_v5_creative_boundary_does_not_reject_v4_deep_contract_defects() -> None:
    for path in FIXTURES:
        source = json.loads(path.read_text(encoding="utf-8"))
        migrated = migrate_v4_raw_to_v5_intent(source["creative_raw_payload"])
        SpineCreativeIntentV1.model_validate(migrated)


def test_structural_compile_accepts_known_valid_episode_spine() -> None:
    raw = json.loads(VALID_SPINE_FIXTURE.read_text(encoding="utf-8"))
    compiled = raw["creative_raw_payload"]["episode_spine"]
    value = SpineStructuralCompilationV1.model_validate({
        "schema": "spineforge-structural-compilation.v1",
        "decision": "COMPILE",
        "assessment_summary": "Compiled without replacing the creative core.",
        "preserved_creative_strengths": ["impossible-road hook", "evidence-under-wonder"],
        "compiled_spine": compiled,
        "replan_feedback": [],
    })
    assert value.compiled_spine is not None


def test_structural_compile_still_rejects_missing_required_beat_field() -> None:
    raw = json.loads(VALID_SPINE_FIXTURE.read_text(encoding="utf-8"))
    compiled = json.loads(json.dumps(raw["creative_raw_payload"]["episode_spine"]))
    compiled["beats"][0].pop("new_information")
    with pytest.raises(ValidationError, match="new_information"):
        SpineStructuralCompilationV1.model_validate({
            "schema": "spineforge-structural-compilation.v1",
            "decision": "COMPILE",
            "assessment_summary": "bad",
            "preserved_creative_strengths": ["a", "b"],
            "compiled_spine": compiled,
            "replan_feedback": [],
        })


def test_replan_has_no_compiled_spine_and_requires_feedback() -> None:
    value = SpineStructuralCompilationV1.model_validate({
        "schema": "spineforge-structural-compilation.v1",
        "decision": "REPLAN",
        "assessment_summary": "Creative core cannot be preserved under authority.",
        "preserved_creative_strengths": ["hook", "roleplay"],
        "compiled_spine": None,
        "replan_feedback": ["Rebuild the branch logic without crossing the locked boundary."],
    })
    assert value.decision == "REPLAN"
