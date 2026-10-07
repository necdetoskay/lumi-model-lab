import json
from pathlib import Path

import pytest

from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_events import evaluate_events
from src.spineforge_relay_v1_q5t import StructuredGuardV1
from src.spineforge_relay_v1_q7c import build_chain, prepare, authorization_for, execute, request_for
from src.spineforge_relay_v1_events import PredicateEvidenceV1


PROSE = " ".join(["The scene continues."] * 85)


def evidence(contract):
    return [PredicateEvidenceV1(event_id=e.id, predicate_id=p.id, subject=p.subject, action=p.action,
        target=p.target, verdict="SUPPORTED", provenance="DIRECT_OBSERVATION", exact_text=PROSE,
        evidence_subject=p.subject, state_pointer=None, reason="Synthetic plumbing test; not entailment proof.")
        for e in contract.required_events for p in e.predicates]


def fake(decisions, calls, fail_at=None):
    def call(**kwargs):
        payload=json.loads(kwargs["user_prompt"])
        assert payload["story_state"]["revision"] == 5
        assert payload["previous_accepted_scene"]["artifact"]["scene_id"] == "SC05"
        assert payload["previous_accepted_scene"]["state_after"] == payload["story_state"]
        calls.append(kwargs["model"])
        if len(calls)==fail_at: raise TimeoutError("uncertain dispatch")
        stage="guard" if "candidate_prose" in payload else "writer"
        _,request=request_for(stage,payload)
        text=PROSE
        if stage=="guard":
            rows=evidence(build_chain()[4][0][1])
            if decisions.pop(0)=="REWRITE":
                next(r for r in rows if r.action=="EXIT_VIA").verdict="UNSUPPORTED"
            text=StructuredGuardV1(event_evidence=rows,residual={"decision":"PASS","findings":[],"summary":"Synthetic test"}).model_dump_json()
        return text,{"choices":[{"finish_reason":"stop"}],"usage":{"prompt_tokens":100,"completion_tokens":100,"total_tokens":200,"cost":0.001}},request
    return call


def test_q7c_binds_revision_five_and_required_safe_egress():
    fixture,intent,route,state,rows,final=build_chain()
    plan,contract,_=rows[0]
    assert state.revision==5 and state.next_spine_beat=="SC06"
    assert len(rows)==1 and contract.scene_id=="SC06"
    assert canonical_sha256(fixture["previous_accepted_scene"]["state_after"])==canonical_sha256(state)
    actions={(p.action,p.target) for e in contract.required_events for p in e.predicates}
    assert ("EXIT_VIA","open_upper_room_door") in actions
    assert ("TRAVERSE","established_coastal_path_to_harbor") in actions
    assert final.revision==6 and final.next_spine_beat is None
    assert final.objects["compass"].location=="lost_at_sea"


@pytest.mark.parametrize("defect",["missing_exit","uncertain_exit","flooded_exit"])
def test_q7b_egress_defect_cannot_satisfy_new_contract(defect):
    _,_,_,state,rows,_=build_chain();c=rows[0][1];ev=evidence(c)
    if defect=="missing_exit": ev=[r for r in ev if r.action!="EXIT_VIA"]
    if defect=="uncertain_exit": next(r for r in ev if r.action=="EXIT_VIA").verdict="AMBIGUOUS"
    if defect=="flooded_exit": next(r for r in ev if r.action=="EXIT_VIA").evidence_subject="flooded_lower_room"
    assert evaluate_events(contract=c,state=state,prose=PROSE,evidence=ev)


@pytest.mark.parametrize("decisions,count,accepted",[(["PASS"],2,True),(["REWRITE","PASS"],4,True),(["REWRITE","REWRITE"],4,False)])
def test_q7c_bounded_run_does_not_rewrite_old_run(tmp_path,decisions,count,accepted):
    pf=prepare();calls=[];out=tmp_path/"run"
    result=execute(api_key="fake",preflight=pf,authorization=authorization_for(pf),output=out,call_fn=fake(decisions,calls))
    assert len(calls)==count
    assert result["status"]==("ACCEPT" if accepted else "REJECT_NON_CONVERGENT")
    assert result["state_advanced_to_revision"]==(6 if accepted else 5)
    assert (out/"SC06-accepted.json").exists() is accepted
    with pytest.raises(FileExistsError):
        execute(api_key="fake",preflight=pf,authorization=authorization_for(pf),output=tmp_path/"another",call_fn=fake([],calls))
    assert len(calls)==count


@pytest.mark.parametrize("fail_at",[1,2,3,4])
def test_q7c_uncertain_dispatch_never_retries(tmp_path,fail_at):
    pf=prepare();calls=[]
    result=execute(api_key="fake",preflight=pf,authorization=authorization_for(pf),output=tmp_path/"run",call_fn=fake(["REWRITE","PASS"],calls,fail_at))
    assert len(calls)==fail_at
    assert result["status"]=="REJECT_NON_CONVERGENT"
    assert result["state_advanced_to_revision"]==5


def test_q7c_preflight_or_authorization_drift_never_dispatches(tmp_path):
    pf=prepare();auth=authorization_for(pf);auth["max_calls"]=5
    with pytest.raises(RuntimeError,match="authorization mismatch"):
        execute(api_key="fake",preflight=pf,authorization=auth,output=tmp_path/"run",call_fn=lambda **k:pytest.fail("must not dispatch"))
    pf["start_state_sha256"]="0"*64
    with pytest.raises(RuntimeError,match="preflight drift"):
        execute(api_key="fake",preflight=pf,authorization=authorization_for(pf),output=tmp_path/"run",call_fn=lambda **k:pytest.fail("must not dispatch"))
