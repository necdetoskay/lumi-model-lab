from __future__ import annotations

import copy
from pathlib import Path

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19 import LUNA_MODEL, SONNET_MODEL, run
from src.spineforge_v19_obligations import load_qualification_cases


PACK = Path(
    "data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json"
)


def _spine(pack: SpineContextPackV1) -> dict:
    locations = list(pack.approved_premise["location_refs"])
    assert len(locations) >= 2
    return {
        "schema": "narrative-spine.v1",
        "title": "The Returning Road",
        "episode_concept": {
            "story_promise": "Leyra tests the returning forbidden route.",
            "story_family": "FANTASY_MYSTERY",
            "tone": "exploratory tension",
            "target_reader_effect": "agency, intrigue, and earned uncertainty",
        },
        "protagonist": {
            "role": "forbidden cartographer",
            "immediate_goal": "verify the route while evidence still exists",
            "pressure": "the route may disappear before dusk",
        },
        "central_question": "What changed enough for the road to return?",
        "stakes": "Leyra risks access, evidence, and credibility.",
        "world_specific_elements": [
            {"context_ref": locations[0], "narrative_use": "initial field evidence"},
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
                "character_action": "Leyra tests the boundary with a reversible marker.",
                "external_change": "The boundary responds to route alignment.",
                "new_information": "The route and boundary are linked.",
                "consequence": "A deeper test could cost her safe return.",
                "escalation": "Access becomes conditional.",
            },
            {
                "key": "compare_paths",
                "location_ref": locations[0],
                "character_action": "Leyra compares two possible evidence paths.",
                "external_change": "One visible trace starts fading.",
                "new_information": "She can preserve proof or pursue a deeper observation, not both.",
                "consequence": "She must choose what kind of uncertainty to carry home.",
                "escalation": "The evidence window closes.",
            },
        ],
        "decision": {
            "required": True,
            "pressure": "Only one observation can be finished before the trace fades.",
            "options": [
                {
                    "option": "preserve the boundary proof",
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


def _accept_gate() -> dict:
    return {
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "The product is ready for human review.",
    }


def _fake(outputs, calls):
    def call(**kwargs):
        calls.append(kwargs)
        raw = outputs[len(calls) - 1]
        body = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cost": 0.001,
            }
        }
        request = {"response_format": {"type": "json_object"}, "provider": {}}
        return raw, body, request, []
    return call


def test_v19_single_architect_then_luna_gate_then_stop():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = next(
        x for x in load_qualification_cases().cases
        if x.obligations.exact_age == 18
    )
    calls = []
    fake = _fake([_spine(pack), _accept_gate()], calls)

    result = run(
        context_pack=pack,
        obligations=case.obligations,
        api_key="zero-cost-test",
        architect_call_fn=fake,
        gate_call_fn=fake,
        architect_prompt="architect",
        gate_prompt="gate",
    )

    assert result["status"] == "awaiting_human_review"
    assert [call["model"] for call in calls] == [SONNET_MODEL, LUNA_MODEL]
    assert result["writer_authorized"] is False
    assert result["automatic_retry_enabled"] is False
    assert result["automatic_repair_enabled"] is False
    assert result["deterministic_validation"]["authority_valid"] is True
    assert result["pipeline_usage_rollup"]["totals"]["api_calls"] == 2


def test_v19_repair_does_not_execute_third_paid_call():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = next(
        x for x in load_qualification_cases().cases
        if x.obligations.exact_age == 18
    )
    repair_gate = {
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "REPAIR",
        "blocking_findings": [{
            "dimension": "CLIMAX_PAYOFF",
            "severity": "MAJOR",
            "repairability": "LOCAL",
            "target_path": "climax",
            "reason": "The climax action is not specific enough.",
            "evidence": "Current climax describes commitment but not the concrete act.",
        }],
        "summary": "One local patch is sufficient.",
    }
    calls = []
    fake = _fake([_spine(pack), repair_gate], calls)
    result = run(
        context_pack=pack,
        obligations=case.obligations,
        api_key="zero-cost-test",
        architect_call_fn=fake,
        gate_call_fn=fake,
        architect_prompt="architect",
        gate_prompt="gate",
    )
    assert result["status"] == "repair_required"
    assert len(calls) == 2
    assert result["repair_candidate"]["automatic_execution"] is False


def test_v19_authority_failure_stops_before_luna():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = next(
        x for x in load_qualification_cases().cases
        if x.obligations.exact_age == 18
    )
    broken = copy.deepcopy(_spine(pack))
    broken["beats"][0]["location_ref"] = "unauthorized_hidden_location"
    calls = []
    fake = _fake([broken], calls)
    result = run(
        context_pack=pack,
        obligations=case.obligations,
        api_key="zero-cost-test",
        architect_call_fn=fake,
        gate_call_fn=fake,
        architect_prompt="architect",
        gate_prompt="gate",
    )
    assert result["status"] == "architect_contract_or_authority_rejected"
    assert len(calls) == 1
