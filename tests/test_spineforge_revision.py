from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_revision import build_revision_feedback

SOURCE=Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f1_recovery_source_36656865491.json"
)


def _creative():
    source=json.loads(SOURCE.read_text())
    raw=source["architect_raw_payload"]
    raw["logistics_plan"]["location_sequence"]=[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    return {
        "schema":"spineforge-creative-draft.v1",
        "creative_model":"aion-labs/aion-3.5-mini",
        "creative_signature":{
            "dramatic_engine":"engine",
            "protagonist_desire":"desire",
            "protagonist_pressure":"pressure",
            "central_wonder_or_intrigue":"wonder",
            "signature_scene_promises":["a","b"],
            "roleplay_opportunities":["a","b","c"],
            "emotional_turns":["a","b"],
            "world_specific_story_uses":["a","b"],
            "freshness_claim":"fresh",
            "why_reader_wants_next_beat":"momentum",
        },
        "episode_spine":raw,
        "self_check_notes":[],
    }


def test_sonnet_replan_becomes_data_feedback_for_next_aion_attempt():
    source={
        "status":"creative_replan_required",
        "attempt_index":1,
        "creative_draft":_creative(),
        "hardening_plan":{
            "preserved_creative_strengths":["wonder","roleplay"],
            "blocking_problems":["branch logistics fail"],
            "replan_feedback":["redesign branch causal bridge"],
        },
    }
    feedback=build_revision_feedback(
        source,
        authority_freezes=["keep reveal ceiling"],
    )
    assert feedback.next_attempt==2
    assert feedback.must_preserve==["wonder","roleplay"]
    assert feedback.creative_feedback==["redesign branch causal bridge"]
    assert feedback.previous_spine.exact_age==18


def test_luna_replan_becomes_data_feedback_for_next_aion_attempt():
    source={
        "status":"product_replan_required",
        "attempt_index":2,
        "creative_draft":_creative(),
        "hardening_plan":{
            "preserved_creative_strengths":["world magic","character agency"],
        },
        "product_gate":{
            "blocking_reasons":["roleplay potential is too low","climax is procedural"],
        },
    }
    feedback=build_revision_feedback(
        source,
        authority_freezes=["keep premise"],
    )
    assert feedback.next_attempt==3
    assert "roleplay potential is too low" in feedback.must_change
