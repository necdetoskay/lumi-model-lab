from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.spineforge_contract import (
    CreativeSignatureV1,
    SpineCreativeDraftV1,
    SpineHardeningPlanV1,
    SpineProductGateV1,
)
from src.spineforge_patch import apply_hardening_plan

SOURCE=Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f1_recovery_source_36656865491.json"
)


def _spine()->EpisodeSpineV2:
    raw=json.loads(SOURCE.read_text())["architect_raw_payload"]
    raw["logistics_plan"]["location_sequence"]=[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    return EpisodeSpineV2.model_validate(raw)


def test_creative_draft_wraps_strict_episode_spine() -> None:
    draft=SpineCreativeDraftV1(
        schema="spineforge-creative-draft.v1",
        creative_model="aion-labs/aion-3.5-mini",
        creative_signature=CreativeSignatureV1(
            dramatic_engine="A forbidden route responds to a mapmaker who must choose evidence over desire.",
            protagonist_desire="Earn independent map authority.",
            protagonist_pressure="A closing field window and a community waiting on her words.",
            central_wonder_or_intrigue="A road the legal map denies seems to answer her instruments.",
            signature_scene_promises=["The impossible compass turn.","A dusk decision at the gate."],
            roleplay_opportunities=["Argue with a warden.","Defend a field claim.","Choose whether to test or report."],
            emotional_turns=["Wonder becomes suspicion.","Professional pride becomes responsibility."],
            world_specific_story_uses=["Living legal maps.","Wardstones that answer to measured lines."],
            freshness_claim="Fantasy cartography drives the conflict rather than decorating it.",
            why_reader_wants_next_beat="Each measurement changes what Leyra can responsibly claim.",
        ),
        episode_spine=_spine(),
    )
    assert draft.episode_spine.exact_age==18


def test_hardener_may_patch_execution_but_not_creative_identity() -> None:
    spine=_spine()
    plan=SpineHardeningPlanV1(
        schema="spineforge-hardening-plan.v1",
        decision="PATCH",
        assessment_summary="Bound one overclaim.",
        preserved_creative_strengths=["Impossible road hook","Map-magic identity"],
        blocking_problems=["Reversal certainty exceeds evidence."],
        patches=[{
            "path":"/reversal/reinterpretation",
            "expected_old":spine.reversal.reinterpretation,
            "replacement":"The gate shows a variable bounded response that neither proves an open road nor establishes its cause.",
            "defect_class":"EVIDENCE_CEILING",
            "reason":"Preserve uncertainty.",
            "creative_impact":"LOW",
        }],
    )
    hardened,applied=apply_hardening_plan(spine,plan)
    assert len(applied)==1
    assert hardened.title==spine.title
    assert hardened.beats==spine.beats


def test_hardener_cannot_take_over_title_or_branch_option() -> None:
    spine=_spine()
    for path,old in [
        ("/title",spine.title),
        ("/decision_point/branches/0/option",spine.decision_point.branches[0].option),
    ]:
        plan=SpineHardeningPlanV1(
            schema="spineforge-hardening-plan.v1",
            decision="PATCH",
            assessment_summary="bad patch",
            preserved_creative_strengths=["a","b"],
            blocking_problems=["x"],
            patches=[{
                "path":path,
                "expected_old":old,
                "replacement":"replacement",
                "defect_class":"OTHER_STRUCTURAL",
                "reason":"not allowed",
                "creative_impact":"LOW",
            }],
        )
        with pytest.raises(RuntimeError,match="creative identity"):
            apply_hardening_plan(spine,plan)


def test_keep_and_replan_are_mutually_strict() -> None:
    with pytest.raises(Exception):
        SpineHardeningPlanV1(
            schema="spineforge-hardening-plan.v1",
            decision="KEEP",
            assessment_summary="x",
            preserved_creative_strengths=["a","b"],
            blocking_problems=["not allowed"],
        )


def test_product_gate_requires_creative_and_structural_thresholds() -> None:
    names=[
        "STORY_DESIRE","ROLEPLAY_POTENTIAL","SCENE_POTENTIAL",
        "CHARACTER_DRIVENNESS","WORLD_SPECIFICITY","WONDER_OR_INTRIGUE",
        "AGE_MATURITY","CAUSAL_COHERENCE","ESCALATION","REVERSAL_QUALITY",
        "AGENCY","BRANCH_EXECUTABILITY","CLIMAX_PAYOFF","LOCAL_SATISFACTION",
        "SAGA_ALIGNMENT","WRITER_EXECUTABILITY","FRESHNESS",
    ]
    gate=SpineProductGateV1(
        schema="spineforge-product-gate.v1",
        dimensions=[
            {
                "name":name,
                "score":4,
                "blocking_failure":False,
                "reason":"meets threshold",
            }
            for name in names
        ],
        decision="ACCEPT",
        blocking_reasons=[],
        decision_reason="Product-ready.",
    )
    assert gate.decision=="ACCEPT"
