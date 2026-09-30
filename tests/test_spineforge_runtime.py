from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.spineforge_v1 as sf
from src.spineforge_human_approval import build_writer_approved_artifact

SOURCE=Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f1_recovery_source_36656865491.json"
)


def _valid_spine()->dict:
    raw=json.loads(SOURCE.read_text())["architect_raw_payload"]
    raw["logistics_plan"]["location_sequence"]=[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    return raw


def _signature()->dict:
    return {
        "dramatic_engine":"An impossible mapped road puts curiosity against professional truth.",
        "protagonist_desire":"Earn independent authority.",
        "protagonist_pressure":"A closing survey window and waiting community.",
        "central_wonder_or_intrigue":"A sealed gate answers to a road maps deny.",
        "signature_scene_promises":["Impossible compass turn","Dusk choice at the gate"],
        "roleplay_opportunities":["Survey the gate","Defend evidence","Answer the warden"],
        "emotional_turns":["Wonder to doubt","Pride to responsibility"],
        "world_specific_story_uses":["Living maps","Wardstones answer measured lines"],
        "freshness_claim":"Cartographic magic drives the plot.",
        "why_reader_wants_next_beat":"Every observation changes what can be claimed.",
    }


def _creative()->dict:
    return {
        "schema":"spineforge-creative-draft.v1",
        "creative_model":"aion-labs/aion-3.5-mini",
        "creative_signature":_signature(),
        "episode_spine":_valid_spine(),
        "self_check_notes":[],
    }


def _hard_keep()->dict:
    return {
        "schema":"spineforge-hardening-plan.v1",
        "decision":"KEEP",
        "assessment_summary":"No structural blocker.",
        "preserved_creative_strengths":["Impossible-road hook","Cartographic magic"],
        "blocking_problems":[],
        "patches":[],
        "replan_feedback":[],
    }


def _hard_replan()->dict:
    return {
        "schema":"spineforge-hardening-plan.v1",
        "decision":"REPLAN",
        "assessment_summary":"Creative climax is too procedural.",
        "preserved_creative_strengths":["Impossible-road hook","Cartographic magic"],
        "blocking_problems":["Climax lacks dramatizable confrontation."],
        "patches":[],
        "replan_feedback":["Creative Architect should redesign climax while preserving the hook."],
    }


def _gate_accept()->dict:
    names=[
        "STORY_DESIRE","ROLEPLAY_POTENTIAL","SCENE_POTENTIAL",
        "CHARACTER_DRIVENNESS","WORLD_SPECIFICITY","WONDER_OR_INTRIGUE",
        "AGE_MATURITY","CAUSAL_COHERENCE","ESCALATION","REVERSAL_QUALITY",
        "AGENCY","BRANCH_EXECUTABILITY","CLIMAX_PAYOFF","LOCAL_SATISFACTION",
        "SAGA_ALIGNMENT","WRITER_EXECUTABILITY","FRESHNESS",
    ]
    return {
        "schema":"spineforge-product-gate.v1",
        "dimensions":[{
            "name":name,"score":4,"blocking_failure":False,"reason":"good"
        } for name in names],
        "decision":"ACCEPT",
        "blocking_reasons":[],
        "decision_reason":"Ready for human review.",
    }


def _body(cost:float=0.001)->dict:
    return {
        "usage":{
            "prompt_tokens":100,
            "completion_tokens":50,
            "total_tokens":150,
            "cost":cost,
        }
    }


def _call_stub(sequence:list[dict]):
    calls=[]
    def fake(**kwargs):
        calls.append(kwargs["model"])
        payload=sequence[len(calls)-1]
        return payload,_body(),{},[]
    return calls,fake


def _paths():
    root=Path("data/specifications")
    return dict(
        saga_path=root/"saga_lab/age18_forbidden_cartographer_saga_v1.json",
        reader_path=root/"reader_profiles/age18_adventure_v2.json",
        fixture_path=root/"saga_lab/age18_forbidden_cartographer_fixture_v1.json",
        state_path=root/"story_lab/age18_forbidden_cartographer_initial_state_v1.json",
        premise_path=root/"story_lab/age18_forbidden_cartographer_controlled_premise_v1.json",
    )


def test_full_spineforge_stops_at_human_review_after_three_single_calls(monkeypatch,tmp_path):
    calls,fake=_call_stub([_creative(),_hard_keep(),_gate_accept()])
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(**_paths(),out_path=tmp_path/"result.json",api_key="x")
    assert calls==[sf.AION_MODEL,sf.SONNET_MODEL,sf.LUNA_MODEL]
    assert result["status"]=="awaiting_human_review"
    assert result["human_review"]["writer_authorized"] is False
    assert result["spine_product"]["product_gate"]["decision"]=="ACCEPT"


def test_invalid_creative_contract_spends_only_aion_call(monkeypatch,tmp_path):
    bad=_creative()
    bad["episode_spine"]["title"]=None
    calls,fake=_call_stub([bad])
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(**_paths(),out_path=tmp_path/"result.json",api_key="x")
    assert calls==[sf.AION_MODEL]
    assert result["status"]=="creative_contract_rejected"


def test_sonnet_replan_stops_before_luna(monkeypatch,tmp_path):
    calls,fake=_call_stub([_creative(),_hard_replan()])
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(**_paths(),out_path=tmp_path/"result.json",api_key="x")
    assert calls==[sf.AION_MODEL,sf.SONNET_MODEL]
    assert result["status"]=="creative_replan_required"


def test_every_model_call_disables_parse_retry(monkeypatch,tmp_path):
    captured=[]
    seq=[_creative(),_hard_keep(),_gate_accept()]
    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    sf.run(**_paths(),out_path=tmp_path/"result.json",api_key="x")
    assert [x["max_parse_attempts"] for x in captured]==[1,1,1]


def test_human_approval_adapter_is_writer_compatible(monkeypatch,tmp_path):
    calls,fake=_call_stub([_creative(),_hard_keep(),_gate_accept()])
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    evidence=sf.run(**_paths(),out_path=tmp_path/"result.json",api_key="x")
    approved=build_writer_approved_artifact(
        spineforge_evidence=evidence,
        source_run_id=123,
        reviewer_note="Human approved.",
    )
    assert approved["schema_version"]=="episode-spine-v2-human-approved.v1"
    assert approved["human_review"]["verdict"]=="APPROVE"
    assert approved["human_review"]["episode_writer_authorized"] is True
    assert approved["gate"]["decision"]=="ACCEPT"


def test_revision_feedback_is_data_driven_and_reenters_aion(monkeypatch,tmp_path):
    from src.spineforge_revision import build_revision_feedback

    calls,fake=_call_stub([_creative(),_hard_replan()])
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    first=sf.run(**_paths(),out_path=tmp_path/"first.json",api_key="x")
    feedback=build_revision_feedback(
        first,
        authority_freezes=[
            "Do not cross the sealed boundary.",
            "Do not reveal the hidden cause.",
        ],
    )
    feedback_path=tmp_path/"feedback.json"
    feedback_path.write_text(json.dumps(feedback.model_dump(mode="json",by_alias=True)))

    captured=[]
    seq=[_creative(),_hard_keep(),_gate_accept()]
    def revised(**kwargs):
        captured.append(kwargs)
        return seq[len(captured)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",revised)
    second=sf.run(
        **_paths(),
        out_path=tmp_path/"second.json",
        revision_feedback_path=feedback_path,
        api_key="x",
    )
    assert second["attempt_index"]==2
    aion_payload=json.loads(captured[0]["user_prompt"])
    assert aion_payload["revision_context"]["next_attempt"]==2
    assert aion_payload["revision_context"]["creative_feedback"]
    assert second["status"]=="awaiting_human_review"


def test_attempt_limit_stops_before_paid_call(monkeypatch,tmp_path):
    from src.spineforge_revision import SpineForgeRevisionFeedbackV1

    spine=_valid_spine()
    feedback={
        "schema":"spineforge-revision-feedback.v1",
        "source_attempt":3,
        "next_attempt":4,
        "source_status":"product_replan_required",
        "must_preserve":["a","b"],
        "must_change":["x"],
        "creative_feedback":["x"],
        "structural_feedback":[],
        "previous_creative_signature":_signature(),
        "previous_spine":spine,
        "authority_freezes":["z"],
    }
    path=tmp_path/"feedback.json"
    path.write_text(json.dumps(feedback))
    calls=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",lambda **kwargs:calls.append(kwargs))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    with pytest.raises(RuntimeError,match="attempt limit exceeded"):
        sf.run(
            **_paths(),out_path=tmp_path/"out.json",
            revision_feedback_path=path,max_attempts=3,api_key="x",
        )
    assert calls==[]
