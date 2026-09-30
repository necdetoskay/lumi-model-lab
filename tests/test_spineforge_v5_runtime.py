from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.spineforge_v5 as sf
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v4 import _normalize_creative_raw
from src.spineforge_v5_contract import SpineForgeRevisionFeedbackV5
from src.spineforge_v5_human_approval import build_spineforge_v5_approval

PACK = Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
V4_FIXTURE = Path("data/specifications/story_lab/spineforge_v4_replay_fixture.json")
V4_ATTEMPT3 = Path("data/specifications/story_lab/spineforge_v5_replay_v4_attempt3_raw.json")


def _body() -> dict:
    return {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }
    }


def _intent_raw() -> dict:
    raw=json.loads(V4_FIXTURE.read_text(encoding="utf-8"))["creative_raw_payload"]
    return raw


def _valid_spine() -> dict:
    raw=_intent_raw()
    normalized,_=_normalize_creative_raw(raw)
    return normalized["episode_spine"]


def _compile(spine:dict|None=None) -> dict:
    return {
        "schema":"spineforge-structural-compilation.v1",
        "decision":"COMPILE",
        "assessment_summary":"Creative core preserved; strict structure compiled.",
        "preserved_creative_strengths":["impossible-road hook","evidence-under-wonder"],
        "compiled_spine":spine or _valid_spine(),
        "replan_feedback":[],
    }


def _replan() -> dict:
    return {
        "schema":"spineforge-structural-compilation.v1",
        "decision":"REPLAN",
        "assessment_summary":"Creative proposal needs a material branch rethink.",
        "preserved_creative_strengths":["impossible-road hook","evidence-under-wonder"],
        "compiled_spine":None,
        "replan_feedback":["Rebuild the choice so both branches are executable without crossing authority."],
    }


def _gate(decision:str="ACCEPT",target:str|None=None) -> dict:
    names=[
        "STORY_DESIRE","ROLEPLAY_POTENTIAL","SCENE_POTENTIAL",
        "CHARACTER_DRIVENNESS","WORLD_SPECIFICITY","WONDER_OR_INTRIGUE",
        "AGE_MATURITY","CAUSAL_COHERENCE","ESCALATION","REVERSAL_QUALITY",
        "AGENCY","BRANCH_EXECUTABILITY","CLIMAX_PAYOFF","LOCAL_SATISFACTION",
        "SAGA_ALIGNMENT","WRITER_EXECUTABILITY","FRESHNESS",
    ]
    return {
        "schema":"spineforge-product-gate.v5",
        "dimensions":[{
            "name":name,
            "score":4,
            "blocking_failure":False,
            "reason":"meets protected threshold",
        } for name in names],
        "decision":decision,
        "replan_target":target,
        "blocking_reasons":([] if decision=="ACCEPT" else ["Compiled branch consequence is not executable."]),
        "decision_reason":("Product-ready." if decision=="ACCEPT" else "Needs bounded replan."),
    }


def _fake_structured(raw:dict,captured:list[dict]):
    def fake(**kwargs):
        captured.append(kwargs)
        return raw,_body(),{},[]
    return fake


def _fake_direct(sequence:list[dict],captured:list[dict]):
    def fake(**kwargs):
        captured.append(kwargs)
        value=sequence[len(captured)-1]
        request={
            "response_format":kwargs.get("response_format"),
            "provider":{"require_parameters":kwargs.get("require_parameters")},
        }
        return json.dumps(value),_body(),request
    return fake


def test_v5_happy_path_reaches_human_stop_with_three_stages(monkeypatch,tmp_path:Path)->None:
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(_intent_raw(),aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(),_gate()],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)

    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")

    assert result["status"]=="awaiting_human_review"
    assert result["human_review"]["writer_authorized"] is False
    assert len(aion)==1
    assert len(direct)==2
    assert result["spine_product"]["schema"]=="spineforge-product.v5"
    assert result["spine_product"]["compiled_spine"]["schema"]=="episode-spine.v2"
    assert result["context_fingerprint"]==result["spine_product"]["context_fingerprint"]


def test_v5_sonnet_and_luna_use_strict_json_schema_and_require_parameters(monkeypatch,tmp_path:Path)->None:
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(_intent_raw(),aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(),_gate()],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)

    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="awaiting_human_review"
    assert [x["model"] for x in direct]==[sf.SONNET_MODEL,sf.LUNA_MODEL]
    for call in direct:
        fmt=call["response_format"]
        assert fmt["type"]=="json_schema"
        assert fmt["json_schema"]["strict"] is True
        assert call["require_parameters"] is True


def test_v4_attempt3_raw_crosses_v5_aion_boundary_and_reaches_sonnet(monkeypatch,tmp_path:Path)->None:
    archived=json.loads(V4_ATTEMPT3.read_text(encoding="utf-8"))["creative_raw_payload"]
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(archived,aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(),_gate()],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)

    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="awaiting_human_review"
    assert len(direct)==2
    assert direct[0]["model"]==sf.SONNET_MODEL
    assert result["creative_intent"]["episode_spine"]["beats"][6].get("new_information") is None


def test_structural_contract_failure_targets_sonnet_and_next_attempt_skips_aion(monkeypatch,tmp_path:Path)->None:
    bad=_valid_spine()
    bad["beats"][0].pop("new_information")
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(_intent_raw(),aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(bad)],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)

    first=sf.run(context_pack_path=PACK,out_path=tmp_path/"first.json",api_key="x")
    assert first["status"]=="structural_compile_rejected"
    feedback=SpineForgeRevisionFeedbackV5.model_validate(first["revision_feedback_candidate"])
    assert feedback.target_stage=="SONNET_STRUCTURAL"
    assert feedback.next_attempt==2

    feedback_path=tmp_path/"feedback.json"
    feedback_path.write_text(json.dumps(first["revision_feedback_candidate"]),encoding="utf-8")

    aion2=[]
    direct2=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",lambda **kwargs:aion2.append(kwargs))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(),_gate()],direct2))

    second=sf.run(
        context_pack_path=PACK,
        out_path=tmp_path/"second.json",
        revision_feedback_path=feedback_path,
        api_key="x",
    )
    assert second["attempt_index"]==2
    assert second["status"]=="awaiting_human_review"
    assert second["creative_intent_reused_from_revision"] is True
    assert aion2==[]
    assert [x["model"] for x in direct2]==[sf.SONNET_MODEL,sf.LUNA_MODEL]


def test_sonnet_replan_targets_aion(monkeypatch,tmp_path:Path)->None:
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(_intent_raw(),aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_replan()],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="structural_replan_required"
    assert result["revision_feedback_candidate"]["target_stage"]=="AION_CREATIVE"
    assert len(direct)==1


@pytest.mark.parametrize("target",["AION_CREATIVE","SONNET_STRUCTURAL"])
def test_luna_replan_routes_feedback_to_named_stage(monkeypatch,tmp_path:Path,target:str)->None:
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(_intent_raw(),aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(),_gate("REPLAN",target)],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="product_replan_required"
    assert result["revision_feedback_candidate"]["target_stage"]==target


def test_stale_v5_feedback_stops_before_inference(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    feedback={
        "schema":"spineforge-revision-feedback.v5",
        "context_pack_id":pack.context_pack_id,
        "context_fingerprint":"0"*64,
        "source_attempt":1,
        "next_attempt":2,
        "target_stage":"SONNET_STRUCTURAL",
        "source_status":"structural_compile_rejected",
        "must_preserve":["hook","wonder"],
        "must_change":["fix structure"],
        "creative_feedback":[],
        "structural_feedback":["fix structure"],
        "previous_creative_intent":{
            "schema":"spineforge-creative-intent.v1",
            "creative_model":sf.AION_MODEL,
            "creative_signature":_intent_raw()["creative_signature"],
            "episode_spine":_intent_raw()["episode_spine"],
            "self_check_notes":[],
        },
        "previous_compiled_spine":None,
        "validation_errors":["bad"],
        "authority_freezes":list(pack.hard_freezes),
    }
    path=tmp_path/"stale.json"
    path.write_text(json.dumps(feedback),encoding="utf-8")
    calls=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",lambda **kwargs:calls.append(kwargs))
    monkeypatch.setattr(sf,"call_openrouter",lambda **kwargs:calls.append(kwargs))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    with pytest.raises(RuntimeError,match="context_fingerprint is stale"):
        sf.run(context_pack_path=PACK,out_path=tmp_path/"out.json",revision_feedback_path=path,api_key="x")
    assert calls==[]


def test_human_approval_is_only_writer_authorization_boundary(monkeypatch,tmp_path:Path)->None:
    aion=[]
    direct=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",_fake_structured(_intent_raw(),aion))
    monkeypatch.setattr(sf,"call_openrouter",_fake_direct([_compile(),_gate()],direct))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    evidence=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert evidence["human_review"]["writer_authorized"] is False

    pack=SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    approved=build_spineforge_v5_approval(
        evidence=evidence,
        current_context_pack=pack,
        source_run_id=123,
        reviewer_note="approved",
    )
    assert approved["human_review"]["story_writer_authorized"] is True

    stale=pack.model_copy(update={"context_fingerprint":"0"*64})
    with pytest.raises(RuntimeError,match="fingerprint differs"):
        build_spineforge_v5_approval(
            evidence=evidence,
            current_context_pack=stale,
            source_run_id=123,
            reviewer_note="approved",
        )
