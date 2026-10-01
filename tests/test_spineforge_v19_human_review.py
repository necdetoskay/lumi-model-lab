from pathlib import Path

import pytest

from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19_human_review import (
    build_human_approval,
    build_human_review_decision,
    render_human_preview,
    spine_hash,
)


PACK = Path(
    "data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json"
)


def _spine(pack: SpineContextPackV1) -> dict:
    locations = list(pack.approved_premise["location_refs"])
    return {
        "schema": "narrative-spine.v1",
        "title": "The Returning Road",
        "episode_concept": {
            "story_promise": "Leyra tests the returning forbidden route.",
            "story_family": "FANTASY_MYSTERY",
            "tone": "exploratory tension",
            "target_reader_effect": "agency and intrigue",
        },
        "protagonist": {
            "role": "forbidden cartographer",
            "immediate_goal": "verify the route while evidence exists",
            "pressure": "the route may disappear before dusk",
        },
        "central_question": "What changed enough for the road to return?",
        "stakes": "Leyra risks access, evidence, and credibility.",
        "world_specific_elements": [
            {"context_ref": locations[0], "narrative_use": "field evidence"},
            {"context_ref": locations[1], "narrative_use": "boundary test"},
        ],
        "beats": [
            {
                "key": "measure_marks",
                "location_ref": locations[0],
                "character_action": "Leyra measures the returned track.",
                "external_change": "A buried marker becomes visible.",
                "new_information": "The marker predates the current chart.",
                "consequence": "She has evidence but not an explanation.",
                "escalation": "The route begins changing.",
            },
            {
                "key": "test_boundary",
                "location_ref": locations[1],
                "character_action": "Leyra tests the boundary.",
                "external_change": "The boundary responds to alignment.",
                "new_information": "The route and boundary are linked.",
                "consequence": "A deeper test could cost her safe return.",
                "escalation": "Access becomes conditional.",
            },
            {
                "key": "compare_paths",
                "location_ref": locations[0],
                "character_action": "Leyra compares two evidence paths.",
                "external_change": "One visible trace starts fading.",
                "new_information": "She can preserve proof or pursue deeper observation, not both.",
                "consequence": "She must choose what uncertainty to carry home.",
                "escalation": "The evidence window closes.",
            },
        ],
        "decision": {
            "required": True,
            "pressure": "Only one observation can be finished before the trace fades.",
            "options": [
                {
                    "option": "preserve boundary proof",
                    "immediate_cost": "give up the deeper route",
                    "possible_consequence": "strong evidence but smaller discovery",
                },
                {
                    "option": "pursue the deeper route",
                    "immediate_cost": "return with weaker proof",
                    "possible_consequence": "greater discovery but credibility risk",
                },
            ],
        },
        "climax": "Leyra commits to one evidence strategy before the route closes.",
        "local_payoff": "She earns one bounded finding and a sharper next question.",
        "unresolved_hooks": ["Why did the route return now?"],
        "reveal_limits": ["Do not answer causes absent from the reveal-safe ContextPack."],
        "persistent_outcome_candidates": [{
            "type": "KNOWLEDGE",
            "description": "A bounded finding about route/boundary behavior.",
            "commit_condition": "the Writer depicts the observation successfully",
        }],
        "writer_rules": ["Keep candidate outcomes uncommitted until delivered in prose."],
    }


def test_preview_and_approval_are_bound_to_exact_spine_and_context():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    gate = SpineProductGateV19.model_validate({
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "Ready.",
    })
    preview = render_human_preview(spine=spine, pack=pack, gate=gate)
    assert spine_hash(spine) in preview
    assert pack.context_fingerprint in preview

    approval = build_human_approval(
        spine=spine,
        gate=gate,
        source_context_pack_id=pack.context_pack_id,
        source_context_fingerprint=pack.context_fingerprint,
        current_context_pack=pack,
        reviewer_note="Approved after reading the same hashed preview.",
    )
    assert approval["spine_hash"] == spine_hash(spine)
    assert approval["human_review"]["story_writer_authorized"] is True


def test_stale_context_fingerprint_blocks_human_approval():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    gate = SpineProductGateV19.model_validate({
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "Ready.",
    })
    with pytest.raises(RuntimeError):
        build_human_approval(
            spine=spine,
            gate=gate,
            source_context_pack_id=pack.context_pack_id,
            source_context_fingerprint="stale",
            current_context_pack=pack,
            reviewer_note="Should not approve stale product.",
        )


def _gate(decision: str) -> SpineProductGateV19:
    return SpineProductGateV19.model_validate({
        "schema": "spineforge-v19-product-gate.v1",
        "decision": decision,
        "blocking_findings": [] if decision == "ACCEPT" else [{
            "dimension": "DECISION_QUALITY",
            "severity": "MAJOR",
            "repairability": "LOCAL",
            "target_path": "narrative_spine.beats[1]",
            "reason": "A local repair is required.",
            "evidence": "The selected branch is not concrete.",
        }],
        "summary": "Human boundary test.",
    })


def test_human_revise_keeps_spine_open_but_blocks_writer():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    review = build_human_review_decision(
        spine=spine,
        gate=_gate("REPAIR"),
        source_context_pack_id=pack.context_pack_id,
        source_context_fingerprint=pack.context_fingerprint,
        current_context_pack=pack,
        verdict="REVISE",
        reason_code="LOCAL_EXECUTION_DEFECT",
        reviewer_note="Repair the selected branch before Writer.",
    )
    assert review["human_review"]["status"] == "HUMAN_REVISION_REQUIRED"
    assert review["human_review"]["required_action"] == "TARGETED_REPAIR_REQUIRES_EXPLICIT_AUTHORIZATION"
    assert review["human_review"]["story_writer_authorized"] is False
    assert review["human_review"]["spine_closed"] is False


def test_human_reject_closes_spine_and_requires_replan_even_when_gate_only_requested_repair():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    review = build_human_review_decision(
        spine=spine,
        gate=_gate("REPAIR"),
        source_context_pack_id=pack.context_pack_id,
        source_context_fingerprint=pack.context_fingerprint,
        current_context_pack=pack,
        verdict="REJECT",
        reason_code="PREMISE_QUALITY",
        reviewer_note="The premise is too technical and not compelling enough for the intended reader.",
    )
    assert review["human_review"]["status"] == "HUMAN_REJECTED_PREMISE"
    assert review["human_review"]["required_action"] == "REPLAN_REQUIRES_EXPLICIT_AUTHORIZATION"
    assert review["human_review"]["story_writer_authorized"] is False
    assert review["human_review"]["spine_closed"] is True


def test_human_cannot_approve_when_product_gate_is_not_accept():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    with pytest.raises(RuntimeError):
        build_human_review_decision(
            spine=spine,
            gate=_gate("REPAIR"),
            source_context_pack_id=pack.context_pack_id,
            source_context_fingerprint=pack.context_fingerprint,
            current_context_pack=pack,
            verdict="APPROVE",
            reason_code="SHOULD_FAIL",
            reviewer_note="A non-accepted gate must never authorize Writer.",
        )


def test_stale_context_blocks_reject_and_revise_too():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    for verdict in ("REVISE", "REJECT"):
        with pytest.raises(RuntimeError):
            build_human_review_decision(
                spine=spine,
                gate=_gate("REPAIR"),
                source_context_pack_id=pack.context_pack_id,
                source_context_fingerprint="stale",
                current_context_pack=pack,
                verdict=verdict,
                reason_code="STALE_TEST",
                reviewer_note="Stale review decisions must not bind to current state.",
            )
