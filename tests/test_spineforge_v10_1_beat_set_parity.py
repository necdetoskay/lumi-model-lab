from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.spineforge_v10 as sf
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v5_contract import SpineCreativeBlueprintV2
from src.spineforge_v10_contract import (
    REQUIRED_EPISODE_PHASES_V10,
    StructuralBeatsV10,
    StructuralFrameV10,
)


PAID_RESULT = Path("experiments/results/spineforge-v10/36810208041/result.json")
PACK = Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")


def _paid_result() -> dict:
    return json.loads(PAID_RESULT.read_text(encoding="utf-8"))


def test_v10_1_exact_v10_paid_beats_fail_before_resolution_on_missing_reversal() -> None:
    raw = _paid_result()["structural_beats"]
    with pytest.raises(ValidationError, match="REVERSAL"):
        StructuralBeatsV10.model_validate(raw)


def test_v10_1_required_phase_set_matches_final_episode_spine_invariant() -> None:
    assert REQUIRED_EPISODE_PHASES_V10 == {
        "HOOK", "COMPLICATION", "REVERSAL", "DECISION", "CLIMAX", "PAYOFF"
    }


def test_v10_1_missing_phase_assembly_error_maps_to_structural_beats_owner() -> None:
    exc = ValueError("Episode Spine missing required phases: REVERSAL")
    assert sf._assembly_failure_owner(exc) == "STRUCTURAL_BEATS"


def test_v10_1_resolution_semantic_error_maps_to_structural_resolution_owner() -> None:
    exc = ValueError("reversal evidence must reference beats established at or before reversal")
    assert sf._assembly_failure_owner(exc) == "STRUCTURAL_RESOLUTION"


def test_v10_1_unknown_assembly_error_does_not_guess_owner() -> None:
    exc = ValueError("unexpected future invariant")
    assert sf._assembly_failure_owner(exc) is None


def test_v10_1_beats_retry_preserves_blueprint_and_frame_only() -> None:
    result = _paid_result()
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    blueprint = SpineCreativeBlueprintV2.model_validate(result["creative_blueprint"])
    frame = StructuralFrameV10.model_validate(result["structural_frame"])
    feedback = sf._revision(
        pack=pack,
        attempt=1,
        source_status="structural_beats_contract_rejected",
        retry_stage="STRUCTURAL_BEATS",
        must_change=["Structural Beats missing final EpisodeSpine required phases: REVERSAL"],
        blueprint=blueprint,
        frame=frame,
    )
    assert feedback.retry_stage == "STRUCTURAL_BEATS"
    assert feedback.preserved_blueprint is not None
    assert feedback.preserved_frame is not None
    assert feedback.preserved_beats is None
