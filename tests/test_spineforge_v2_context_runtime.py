from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.spineforge_v2 as sf
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_context_revision import build_context_bound_revision_feedback
from src.spineforge_v2_human_approval import build_spineforge_v2_approval

PACK=Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
OLD_SOURCE=Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f1_recovery_source_36656865491.json"
)


def _valid_spine()->dict:
    raw=json.loads(OLD_SOURCE.read_text())["architect_raw_payload"]
    raw["logistics_plan"]["location_sequence"]=[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    return raw


def _signature()->dict:
    return {
        "dramatic_engine":"An impossible mapped road pits curiosity against professional truth.",
        "protagonist_desire":"Earn independent map authority.",
        "protagonist_pressure":"A closing field window and a community waiting on her words.",
        "central_wonder_or_intrigue":"A road the legal map denies seems to answer her instruments.",
        "signature_scene_promises":["The impossible compass turn.","A dusk decision at the gate."],
        "roleplay_opportunities":["Survey the gate.","Defend a field claim.","Choose whether to test or report."],
        "emotional_turns":["Wonder becomes suspicion.","Professional pride becomes responsibility."],
        "world_specific_story_uses":["Living legal maps.","Wardstones answer measured lines."],
        "freshness_claim":"Fantasy cartography drives the conflict rather than decorating it.",
        "why_reader_wants_next_beat":"Each observation changes what can responsibly be claimed.",
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
        "assessment_summary":"Climax needs creative redesign.",
        "preserved_creative_strengths":["Impossible-road hook","Cartographic magic"],
        "blocking_problems":["Climax is too procedural."],
        "patches":[],
        "replan_feedback":["Create a more dramatizable climax while preserving authority."],
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


def test_all_three_models_receive_same_context_pack_fingerprint(monkeypatch,tmp_path:Path) -> None:
    captured=[]
    seq=[_creative(),_hard_keep(),_gate_accept()]

    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured)-1],_body(),{},[]

    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)

    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    assert result["status"]=="awaiting_human_review"
    assert len(captured)==3

    payloads=[json.loads(x["user_prompt"]) for x in captured]
    packs=[x["spine_context_pack"] for x in payloads]
    fingerprints={x["context_fingerprint"] for x in packs}
    ids={x["context_pack_id"] for x in packs}
    assert len(fingerprints)==1
    assert len(ids)==1
    assert next(iter(fingerprints))==result["context_fingerprint"]

    # No model receives the raw source file graph outside the application-owned pack.
    assert "premise_context" not in payloads[0]
    assert "approved_premise" not in payloads[0]
    assert "premise_context" not in payloads[1]
    assert "approved_premise" not in payloads[2]


def test_sonnet_replan_is_context_bound(monkeypatch,tmp_path:Path) -> None:
    seq=[_creative(),_hard_replan()]
    calls=[]
    def fake(**kwargs):
        calls.append(kwargs)
        return seq[len(calls)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    result=sf.run(context_pack_path=PACK,out_path=tmp_path/"r.json",api_key="x")
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    feedback=build_context_bound_revision_feedback(result,context_pack=pack)
    assert feedback.context_fingerprint==pack.context_fingerprint
    assert feedback.feedback.next_attempt==2


def test_stale_revision_feedback_is_rejected_before_inference(monkeypatch,tmp_path:Path) -> None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    source={
        "status":"creative_replan_required",
        "attempt_index":1,
        "context_pack_id":pack.context_pack_id,
        "context_fingerprint":pack.context_fingerprint,
        "creative_draft":_creative(),
        "hardening_plan":_hard_replan(),
    }
    feedback=build_context_bound_revision_feedback(source,context_pack=pack)
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


def test_human_approval_refuses_stale_context(monkeypatch,tmp_path:Path) -> None:
    captured=[]
    seq=[_creative(),_hard_keep(),_gate_accept()]
    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured)-1],_body(),{},[]
    monkeypatch.setattr(sf,"call_structured_json_with_retry",fake)
    monkeypatch.setattr(sf,"require_qualification_runtime_profile",lambda model:None)
    evidence=sf.run(context_pack_path=PACK,out_path=tmp_path/"result.json",api_key="x")
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())

    approved=build_spineforge_v2_approval(
        evidence=evidence,
        current_context_pack=pack,
        source_run_id=123,
        reviewer_note="approved",
    )
    assert approved["context_fingerprint"]==pack.context_fingerprint
    assert approved["human_review"]["story_writer_authorized"] is True

    stale_raw=pack.model_dump(mode="json",by_alias=True)
    stale_raw["context_fingerprint"]="f"*64
    stale=SpineContextPackV1.model_validate(stale_raw)
    with pytest.raises(RuntimeError,match="fingerprint differs"):
        build_spineforge_v2_approval(
            evidence=evidence,
            current_context_pack=stale,
            source_run_id=123,
            reviewer_note="approved",
        )
