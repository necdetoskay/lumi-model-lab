from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.spineforge_v5 as sf
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v3_contract import SpineCreativeDraftV1
from src.spineforge_v3_human_approval import build_spineforge_v3_approval

PACK=Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
RAW_FIXTURE=Path("data/specifications/story_lab/spineforge_v5_replay_fixture.json")


def _raw()->dict:
    return copy.deepcopy(json.loads(RAW_FIXTURE.read_text())["creative_raw_payload"])


def _hard_keep()->dict:
    return {
        "schema":"spineforge-hardening-plan.v1",
        "decision":"KEEP",
        "assessment_summary":"No structural blocker.",
        "preserved_creative_strengths":["Impossible-road hook","Evidence-under-wonder engine"],
        "blocking_problems":[],
        "patches":[],
        "replan_feedback":[],
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
            "name":name,"score":4,"blocking_failure":False,"reason":"meets threshold"
        } for name in names],
        "decision":"ACCEPT",
        "blocking_reasons":[],
        "decision_reason":"Product-ready.",
    }


def _body()->dict:
    return {
        "usage":{
            "prompt_tokens":100,
            "completion_tokens":50,
            "total_tokens":150,
            "cost":0.001,
        }
    }


def test_actual_v2_attempt1_raw_replays_under_v5_without_inference()->None:
    raw=_raw()
    raw_support=[
        list(x["supporting_beat_keys"])
        for x in raw["episode_spine"]["reversal"]["evidence"]
    ]
    normalized,repairs=sf._normalize_creative_raw(raw)
    draft=SpineCreativeDraftV1.model_validate(normalized)
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    sf._validate_spine_authority(draft=draft,pack=pack)
    kinds={x["kind"] for x in repairs}
    assert "stamp_application_owned_model_identity" in kinds
    assert "derive_logistics_location_sequence" in kinds
    assert "remove_self_or_future_reversal_support" not in kinds
    assert "remove_future_reversal_support" not in kinds
    assert draft.creative_model==sf.AION_MODEL
    assert draft.episode_spine.logistics_plan.location_sequence==[
        "ashen_gate","greyfen","vellum_hall"
    ]
    normalized_support=[
        list(x.supporting_beat_keys)
        for x in draft.episode_spine.reversal.evidence
    ]
    assert normalized_support==raw_support


def test_v5_future_reversal_evidence_is_rejected_and_becomes_revision_data(monkeypatch,tmp_path:Path)->None:
    bad=_raw()
    bad["episode_spine"]["reversal"]["evidence"][0]["supporting_beat_keys"]=[
        "payoff_return_and_report"
    ]
    calls=[]
    def fake(**kwargs):
        calls.append(kwargs)
        return bad,_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)

    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="creative_contract_rejected"
    assert len(calls)==1
    candidate=result["revision_feedback_candidate"]
    assert candidate["schema"]=="spineforge-revision-feedback.v3"
    assert candidate["source_status"]=="creative_contract_rejected"
    assert candidate["next_attempt"]==2
    assert candidate["context_fingerprint"]==result["context_fingerprint"]
    assert candidate["validation_errors"]
    assert result["human_review"]["writer_authorized"] is False


def test_v5_revision_candidate_reenters_aion_then_reaches_human_stop(monkeypatch,tmp_path:Path)->None:
    bad=_raw()
    bad["episode_spine"]["reversal"]["evidence"][0]["supporting_beat_keys"]=[
        "payoff_return_and_report"
    ]
    first_calls=[]
    def first_fake(**kwargs):
        first_calls.append(kwargs)
        return bad,_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",first_fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    first=sf.run(context_pack_path=PACK,out_path=tmp_path/"first.json",api_key="x")
    assert first["status"]=="creative_contract_rejected"

    feedback_path=tmp_path/"feedback.json"
    feedback_path.write_text(json.dumps(first["revision_feedback_candidate"]))

    captured=[]
    seq=[_raw(),_hard_keep(),_gate_accept()]
    def second_fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",second_fake)
    second=sf.run(
        context_pack_path=PACK,
        out_path=tmp_path/"second.json",
        revision_feedback_path=feedback_path,
        api_key="x",
    )
    assert second["attempt_index"]==2
    assert second["status"]=="awaiting_human_review"
    assert second["human_review"]["writer_authorized"] is False
    assert len(captured)==3
    revision=json.loads(captured[0]["user_prompt"])["revision_context"]
    assert revision["source_status"]=="creative_contract_rejected"
    assert revision["next_attempt"]==2
    assert revision["context_fingerprint"]==second["context_fingerprint"]


def test_v5_all_models_receive_same_context_pack(monkeypatch,tmp_path:Path)->None:
    captured=[]
    seq=[_raw(),_hard_keep(),_gate_accept()]
    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="awaiting_human_review"
    payloads=[json.loads(x["user_prompt"]) for x in captured]
    packs=[x["spine_context_pack"] for x in payloads]
    assert {x["context_fingerprint"] for x in packs}=={result["context_fingerprint"]}
    assert {x["context_pack_id"] for x in packs}=={result["context_pack_id"]}


def test_v5_stale_feedback_stops_before_inference(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    source={
        "status":"creative_contract_rejected",
        "attempt_index":1,
        "context_pack_id":pack.context_pack_id,
        "context_fingerprint":pack.context_fingerprint,
        "creative_raw_payload":_raw(),
        "failure":{"type":"ValidationError","message":"future reversal evidence"},
        "creative_parse_failures":[],
    }
    from src.spineforge_v3_context_revision import build_context_bound_revision_feedback_v3
    feedback=build_context_bound_revision_feedback_v3(source,context_pack=pack)
    raw=feedback.model_dump(mode="json",by_alias=True)
    raw["context_fingerprint"]="0"*64
    path=tmp_path/"stale.json"
    path.write_text(json.dumps(raw))

    calls=[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",lambda **kwargs:calls.append(kwargs))
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    with pytest.raises(RuntimeError,match="context_fingerprint is stale"):
        sf.run(
            context_pack_path=PACK,
            out_path=tmp_path/"out.json",
            revision_feedback_path=path,
            api_key="x",
        )
    assert calls==[]


def test_v5_human_approval_still_stops_writer_until_explicit_approval(monkeypatch,tmp_path:Path)->None:
    seq=[_raw(),_hard_keep(),_gate_accept()]
    calls=[]
    def fake(**kwargs):
        calls.append(kwargs)
        return seq[len(calls)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    evidence=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert evidence["human_review"]["writer_authorized"] is False

    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    approved=build_spineforge_v3_approval(
        evidence=evidence,
        current_context_pack=pack,
        source_run_id=123,
        reviewer_note="approved",
    )
    assert approved["human_review"]["story_writer_authorized"] is True
    assert approved["context_fingerprint"]==pack.context_fingerprint

def _paid_raw(key:str)->dict:
    payload=json.loads(RAW_FIXTURE.read_text())
    return copy.deepcopy(payload[key]["creative_raw_payload"])


def test_v5_real_attempt1_shape_is_repaired_but_structural_failure_remains()->None:
    raw=_paid_raw("v4_attempt_1")
    assert isinstance(raw["episode_spine"]["logistics_plan"]["movement_constraints"],str)
    normalized,repairs=sf._normalize_creative_raw(raw)
    assert normalized["episode_spine"]["logistics_plan"]["movement_constraints"]==[
        "Must stay on the exterior survey path."
    ]
    kinds={x["kind"] for x in repairs}
    assert "coerce_scalar_string_to_list" in kinds
    assert "COMPLICATION" not in {
        x["phase"] for x in normalized["episode_spine"]["beats"]
    }
    with pytest.raises(ValidationError,match="missing required phases: COMPLICATION"):
        SpineCreativeDraftV1.model_validate(normalized)


def test_v5_real_attempt2_missing_complication_remains_structural_failure()->None:
    raw=_paid_raw("v4_attempt_2")
    assert "COMPLICATION" not in {x["phase"] for x in raw["episode_spine"]["beats"]}
    normalized,repairs=sf._normalize_creative_raw(raw)
    assert "COMPLICATION" not in {x["phase"] for x in normalized["episode_spine"]["beats"]}
    assert all(x["kind"]!="create_missing_phase" for x in repairs)
    with pytest.raises(ValidationError,match="missing required phases: COMPLICATION"):
        SpineCreativeDraftV1.model_validate(normalized)


def test_v5_real_attempt3_decision_noop_is_safe_normalized_and_contract_valid()->None:
    raw=_paid_raw("v4_attempt_3")
    decision=next(x for x in raw["episode_spine"]["beats"] if x["phase"]=="DECISION")
    assert "new_information" not in decision
    normalized,repairs=sf._normalize_creative_raw(raw)
    normalized_decision=next(
        x for x in normalized["episode_spine"]["beats"] if x["phase"]=="DECISION"
    )
    assert normalized_decision["new_information"]==""
    draft=SpineCreativeDraftV1.model_validate(normalized)
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    sf._validate_spine_authority(draft=draft,pack=pack)
    kinds={x["kind"] for x in repairs}
    assert "fill_decision_noop_new_information" in kinds


def test_v5_never_fills_missing_new_information_on_non_decision()->None:
    raw=_paid_raw("v4_attempt_3")
    hook=next(x for x in raw["episode_spine"]["beats"] if x["phase"]=="HOOK")
    hook.pop("new_information",None)
    normalized,repairs=sf._normalize_creative_raw(raw)
    normalized_hook=next(
        x for x in normalized["episode_spine"]["beats"] if x["phase"]=="HOOK"
    )
    assert "new_information" not in normalized_hook
    assert not any(
        x["kind"]=="fill_decision_noop_new_information"
        and ".new_information" in x["field"]
        and "beats[0]" in x["field"]
        for x in repairs
    )
    with pytest.raises(ValidationError):
        SpineCreativeDraftV1.model_validate(normalized)

