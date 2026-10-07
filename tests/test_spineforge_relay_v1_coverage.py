import json
import pytest
from src.spineforge_relay_v1_coverage import (
    PlanObligationV1, PredicateOrderV1, compile_plan_coverage, evaluate_plan_coverage,
)
from src.spineforge_relay_v1_events import PredicateEvidenceV1
from src.spineforge_relay_v1_q7e_inputs import build_chain, prepare, request_for, authorization_for


def bound():
    fixture, _, _, _, rows, _ = build_chain()
    plan, scene, _ = rows[0]
    raw = fixture["coverage_plans"][0]
    coverage = compile_plan_coverage(plan=plan, scene=scene,
        obligations=[PlanObligationV1.model_validate(o) for o in raw["obligations"]],
        ordered_dependencies=[PredicateOrderV1.model_validate(o) for o in raw["ordered_dependencies"]])
    events = sorted(scene.required_events, key=lambda e: e.id != "SC05-HELP")
    evidence = [PredicateEvidenceV1(event_id=e.id, predicate_id=p.id, subject=p.subject, action=p.action,
        target=p.target, verdict="SUPPORTED", provenance="DIRECT_OBSERVATION",
        exact_text=f"{e.id} {p.id} visible action.", evidence_subject=p.target, state_pointer=None,
        reason="Synthetic plumbing, not semantic entailment") for e in events for p in e.predicates]
    prose = " ".join(r.exact_text for r in evidence)
    return coverage, plan, scene, evidence, prose


def test_all_original_goal_fields_are_bound_without_inference():
    c, plan, scene, ev, prose = bound()
    assert {o.source_field for o in c.obligations} == {"narrative_purpose", "objective", "turn"}
    assert evaluate_plan_coverage(coverage=c, plan=plan, scene=scene, prose=prose, evidence=ev) == []


@pytest.mark.parametrize("defect", ["missing_goal", "duplicate_goal", "stale_text", "wrong_actor", "unknown_predicate", "duplicate_predicate", "stale_plan", "stale_contract", "cycle"])
def test_invalid_coverage_bindings_fail_closed(defect):
    c, plan, scene, _, _ = bound()
    if defect == "missing_goal": c.obligations.pop()
    if defect == "duplicate_goal": c.obligations[0].source_field = "turn"
    if defect == "stale_text": c.obligations[0].source_text = "invented goal"
    if defect == "wrong_actor": c.obligations[0].required_predicates[0].subject = "Duru"
    if defect == "unknown_predicate": c.obligations[0].required_predicates[0].predicate_id = "missing"
    if defect == "duplicate_predicate": c.obligations[0].required_predicates.append(c.obligations[0].required_predicates[0])
    if defect == "stale_plan": plan.turn = "different turn"
    if defect == "stale_contract": scene.scene_id = "different scene"
    if defect == "cycle":
        d = c.ordered_dependencies[0]
        c.ordered_dependencies.append(PredicateOrderV1(before=d.after, after=d.before))
    with pytest.raises(ValueError):
        compile_plan_coverage(plan=plan, scene=scene, obligations=c.obligations, ordered_dependencies=c.ordered_dependencies)


@pytest.mark.parametrize("defect", ["offered_help", "ambiguous_request", "duplicate_request", "wrong_actor", "ungrounded", "after_assistance", "shared_quote", "fingerprint"])
def test_help_offer_cannot_substitute_for_a_grounded_prior_request(defect):
    c, plan, scene, ev, prose = bound()
    ask = next(r for r in ev if r.action == "ASK_FOR_HELP")
    if defect == "offered_help": ev.remove(ask)
    if defect == "ambiguous_request": ask.verdict = "AMBIGUOUS"
    if defect == "duplicate_request": ev.append(ask)
    if defect == "wrong_actor": ask.subject = "Duru"
    if defect == "ungrounded": ask.exact_text = "never spoken"
    if defect == "after_assistance": prose = " ".join(r.exact_text for r in ev if r is not ask)+" "+ask.exact_text
    if defect == "shared_quote": next(r for r in ev if r.event_id == "SC05-HELP" and r.predicate_id == "P2").exact_text = ask.exact_text
    if defect == "fingerprint": c.scene_contract_sha256 = "0"*64
    assert evaluate_plan_coverage(coverage=c, plan=plan, scene=scene, prose=prose, evidence=ev)


def test_fresh_chain_preserves_spatial_source_and_remaining_budget():
    fixture, _, _, start, rows, final = build_chain()
    assert start.model_dump(mode="json") == fixture["previous_accepted_scene"]["state_after"]
    assert start.revision == 4 and final.revision == 6
    assert [p.scene_id for p, _, _ in rows] == ["SC05", "SC06"]
    pf = prepare()
    assert pf["max_calls"] == 8 and pf["combined_max_calls"] == 18
    assert round(pf["prior_spend_usd"]+pf["max_total_cost_usd"], 6) == 0.60


def test_writer_and_guard_receive_same_goal_contract():
    c, _, _, _, _ = bound()
    payload = {"plan_coverage_contract": c.model_dump(mode="json")}
    for stage in ("writer", "guard"):
        kwargs, request = request_for(stage, payload)
        assert json.loads(kwargs["user_prompt"])["plan_coverage_contract"] == payload["plan_coverage_contract"]
        assert "ASK_FOR_HELP" in kwargs["system_prompt"]
        assert request["provider"]["allow_fallbacks"] is False


@pytest.mark.parametrize("mode", ["accept", "reject", "timeout"])
def test_bounded_fresh_executor_keeps_previous_run_immutable(tmp_path, mode):
    from src.spineforge_relay_v1_q7e import execute
    from src.spineforge_relay_v1_q5t import StructuredGuardV1
    calls = []
    def call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        stage = "guard" if "candidate_prose" in payload else "writer"
        _, request = request_for(stage, payload)
        calls.append(stage)
        if mode == "timeout": raise TimeoutError("Uncertain dispatch")
        events = sorted(payload["scene_contract"]["required_events"], key=lambda e: e["id"] != "SC05-HELP")
        rows = []
        for e in events:
            for p in e["predicates"]:
                rows.append(PredicateEvidenceV1(event_id=e["id"],predicate_id=p["id"],subject=p["subject"],action=p["action"],target=p["target"],verdict="SUPPORTED",provenance="DIRECT_OBSERVATION",exact_text=f"{e['id']} {p['id']} visible action.",evidence_subject=p["target"],state_pointer=None,reason="Synthetic test"))
        prose = " ".join(r.exact_text for r in rows)+" "+" ".join(["quiet"]*200)
        if mode == "reject": next(r for r in rows if r.action == "ASK_FOR_HELP").verdict = "UNSUPPORTED"
        text = prose if stage == "writer" else StructuredGuardV1(event_evidence=rows,residual={"decision":"PASS","findings":[],"summary":"Synthetic"}).model_dump_json()
        return text,{"choices":[{"finish_reason":"stop"}],"usage":{"prompt_tokens":100,"completion_tokens":100,"total_tokens":200,"cost":0.001}},request
    pf = prepare()
    result = execute(api_key="fake",preflight=pf,authorization=authorization_for(pf),output=tmp_path/"run",call_fn=call)
    assert len(calls) == {"accept":4,"reject":4,"timeout":1}[mode]
    assert result["status"] == ("ACCEPT" if mode == "accept" else "REJECT_NON_CONVERGENT")
    assert result["state_advanced_to_revision"] == (6 if mode == "accept" else 4)
    with pytest.raises(FileExistsError):
        execute(api_key="fake",preflight=pf,authorization=authorization_for(pf),output=tmp_path/"second",call_fn=call)
