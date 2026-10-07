import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.spineforge_relay_v1_contracts import RequiredEventSpecV1, ScenePlanV1, canonical_sha256
from src.spineforge_relay_v1_compile import compile_scene_contract, SceneCompileError
from src.spineforge_relay_v1_events import PredicateEvidenceV1, evaluate_events
from src.spineforge_relay_v1_q5t import build_inputs, execute, prepare, request_for, freeze_scene

PROSE = " ".join(["The scene continues."] * 65)


def rows(contract, prose=PROSE):
    return [PredicateEvidenceV1(event_id=e.id, predicate_id=p.id, subject=p.subject,
        action=p.action, target=p.target, verdict="SUPPORTED", provenance="DIRECT_OBSERVATION",
        exact_text=prose, evidence_subject=p.subject, state_pointer=None, reason="Synthetic entailment for local plumbing only.")
        for e in contract.required_events for p in e.predicates]


def auth(pf):
    return {"preflight_sha256": canonical_sha256(pf), "paid_execution_authorized": True,
        "max_rewrites": 1, "automatic_retry": False, "state_application_on_accept": True,
        "user_instruction": "2026-10-07: fresh Q5T Sol/Sonnet qualification; max 1 rewrite; no retry; freeze only on PASS"}


def test_frozen_inputs_unchanged_but_contract_fingerprint_changes():
    from src.spineforge_relay_v1_q5 import build_inputs as legacy
    _, state, _, route, contract = build_inputs()
    _, old_state, _, old_route, old_contract = legacy()
    assert canonical_sha256(state) == canonical_sha256(old_state)
    assert canonical_sha256(route) == canonical_sha256(old_route)
    assert canonical_sha256(contract) != canonical_sha256(old_contract)


def test_ambiguous_destination_event_needs_no_separate_clue():
    _, state, _, _, contract = build_inputs()
    event = contract.required_events[2]
    assert event.required_observer == "Ekin"
    assert event.separate_physical_clue_required is False
    assert [(p.subject, p.action) for p in event.predicates] == [
        ("sea_dragon", "HEAD_TOWARD"), ("Duru", "INDICATE_DESTINATION"), ("Ekin", "ACKNOWLEDGE")]
    assert evaluate_events(contract=contract, state=state, prose=PROSE, evidence=rows(contract)) == []


@pytest.mark.parametrize("field,value,code", [
    ("verdict", "UNSUPPORTED", "EVENT_NOT_SATISFIED"),
    ("verdict", "AMBIGUOUS", "EVENT_NOT_SATISFIED"),
    ("subject", "someone_else", "EVENT_ATTRIBUTION"),
    ("target", "somewhere_else", "EVENT_ATTRIBUTION"),
    ("exact_text", "not actually in prose", "EVENT_UNGROUNDED"),
    ("exact_text", "", "EVENT_UNGROUNDED"),
    ("provenance", "INVENTED_CLUE", "EVENT_PROVENANCE"),
    ("provenance", "UNESTABLISHED_LORE", "EVENT_PROVENANCE"),
    ("provenance", "INVENTED_WORLD_RULE", "EVENT_PROVENANCE"),
    ("evidence_subject", "weed", "EVENT_FORBIDDEN_SUBJECT"),
    ("evidence_subject", "shell", "EVENT_FORBIDDEN_SUBJECT"),
    ("evidence_subject", "cave", "EVENT_FORBIDDEN_SUBJECT"),
    ("state_pointer", "/characters/Duru/knowledge/0", "EVENT_SOURCE_MISMATCH"),
])
def test_bad_evidence_fails_closed(field, value, code):
    _, state, _, _, contract = build_inputs()
    evidence = rows(contract)
    evidence[2] = evidence[2].model_copy(update={field: value})
    assert code in {f.code for f in evaluate_events(contract=contract, state=state, prose=PROSE, evidence=evidence)}


@pytest.mark.parametrize("mutation", ["missing_observer", "duplicate", "unknown"])
def test_evidence_coverage(mutation):
    _, state, _, _, contract = build_inputs()
    evidence = rows(contract)
    if mutation == "missing_observer":
        evidence = [r for r in evidence if r.action != "ACKNOWLEDGE"]
    elif mutation == "duplicate":
        evidence.append(evidence[0])
    else:
        evidence[0] = evidence[0].model_copy(update={"event_id": "invented"})
    assert evaluate_events(contract=contract, state=state, prose=PROSE, evidence=evidence)


def test_strict_contract_rejects_natural_language_and_objective_fallback():
    _, state, plan, route, _ = build_inputs()
    payload = plan.model_dump(mode="json")
    payload["required_events"] = ["Duru shows evidence"]
    with pytest.raises(ValidationError):
        ScenePlanV1.model_validate(payload)
    payload["required_events"] = []
    with pytest.raises(SceneCompileError, match="mandatory"):
        compile_scene_contract(state, ScenePlanV1.model_validate(payload), route)


@pytest.mark.parametrize("change", ["overlap", "observer", "result", "duplicate", "mode"])
def test_event_contract_invariants(change):
    _, state, plan, route, _ = build_inputs()
    payload = plan.model_dump(mode="json")
    event = payload["required_events"][2]
    if change == "overlap": event["forbidden_provenance"].append("DIRECT_OBSERVATION")
    if change == "observer": event["required_observer"] = "other"
    if change == "result": event["resulting_state"] = {"/world/invented": True}
    if change == "duplicate": payload["required_events"].append(deepcopy(event))
    if change == "mode": event["evidence_mode"] = "ESTABLISHED_KNOWLEDGE"
    with pytest.raises(ValidationError):
        compile_scene_contract(state, ScenePlanV1.model_validate(payload), route)


def test_generic_event_with_unrelated_characters_has_same_semantics():
    _, state, plan, route, _ = build_inputs()
    payload = plan.model_dump(mode="json")
    event = payload["required_events"][2]
    event.update(id="OTHER-E1", actor="Mira", target="station", required_observer="Jon")
    event["predicates"] = [dict(id="P1", subject="Mira", action="INDICATE_DESTINATION", target="station"),
                           dict(id="P2", subject="Jon", action="ACKNOWLEDGE", target="train_heading_to_station")]
    payload["required_events"] = [event]
    c = compile_scene_contract(state, ScenePlanV1.model_validate(payload), route)
    assert not evaluate_events(contract=c, state=state, prose=PROSE, evidence=rows(c))


def fake_provider(decisions, calls, fail_at=None):
    def call(**kwargs):
        calls.append(kwargs["model"])
        if fail_at == len(calls): raise TimeoutError("uncertain dispatch")
        payload = json.loads(kwargs["user_prompt"])
        stage = "guard" if "candidate_prose" in payload else "writer"
        _, request = request_for(stage, payload)
        text = PROSE
        if stage == "guard":
            _, _, _, _, c = build_inputs()
            evidence = rows(c)
            if decisions.pop(0) == "REWRITE": evidence[2].verdict = "UNSUPPORTED"
            text = json.dumps({"event_evidence": [r.model_dump(mode="json") for r in evidence],
                "residual": {"schema_name": "spineforge-relay.semantic-guard.v1", "decision": "PASS", "findings": [], "summary": "Synthetic plumbing test."}})
        return text, {"choices": [{"finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200, "cost": 0.001}}, request
    return call


@pytest.mark.parametrize("decisions,count,accepted", [(["PASS"],2,True), (["REWRITE","PASS"],4,True), (["REWRITE","REWRITE"],4,False)])
def test_bounded_run_and_deterministic_freeze(tmp_path, decisions, count, accepted):
    pf=prepare(); calls=[]; out=tmp_path/"run"
    result=execute(api_key="fake", preflight=pf, authorization=auth(pf), output=out, call_fn=fake_provider(decisions,calls))
    assert len(calls) == count
    assert result["state_advanced"] is accepted
    assert result["status"] == ("ACCEPT" if accepted else "REJECT_NON_CONVERGENT")
    assert (out/"accepted-scene.json").exists() is accepted
    if accepted:
        bundle=json.loads((out/"accepted-scene.json").read_text())
        assert bundle["state_after"]["revision"] == 1
        assert bundle["state_after"]["next_spine_beat"] == "SC02"
        assert bundle["state_after"]["objects"]["compass"]["location"] == "mother_dragon"
    before=(out/"result.json").read_bytes()
    with pytest.raises(FileExistsError):
        execute(api_key="fake", preflight=pf, authorization=auth(pf), output=out, call_fn=fake_provider([],calls))
    assert len(calls)==count and before==(out/"result.json").read_bytes()
    with pytest.raises(FileExistsError):
        execute(api_key="fake", preflight=pf, authorization=auth(pf), output=tmp_path/"another-run", call_fn=fake_provider([],calls))
    assert len(calls) == count


@pytest.mark.parametrize("fail_at", [1,2,3,4])
def test_uncertain_call_stops_without_retry_or_state(tmp_path, fail_at):
    pf=prepare(); calls=[]
    result=execute(api_key="fake", preflight=pf, authorization=auth(pf), output=tmp_path/"run",
                   call_fn=fake_provider(["REWRITE","PASS"],calls,fail_at))
    assert len(calls)==fail_at
    assert result["status"]=="REJECT_NON_CONVERGENT"
    assert result["state_advanced"] is False
    assert result["usage_complete"] is False


def test_preflight_drift_never_dispatches(tmp_path):
    pf=prepare(); pf["max_rewrites"]=2
    with pytest.raises(RuntimeError, match="drift"):
        execute(api_key="fake", preflight=pf, authorization=auth(pf), output=tmp_path/"run", call_fn=lambda **k: pytest.fail("must not dispatch"))


def test_historical_q5sf_still_rejected():
    result=json.loads(Path("evidence/spineforge-relay/SFR-V1-Q5SF-PAID-20261007/result.json").read_text(encoding="utf-8"))
    assert result["decision"] == "REJECT_NON_CONVERGENT"


def test_zero_cost_workflow_has_no_paid_job():
    text=Path(".github/workflows/spineforge-relay-v1-zero-cost.yml").read_text()
    assert "OPENROUTER_API_KEY" not in text
    assert "execute_once" not in text


def test_q5t_transport_has_no_fallback_and_sufficient_guard_budget():
    inputs, *_ = build_inputs()
    for stage in ("writer", "guard"):
        _, request = request_for(stage, inputs)
        assert request["provider"]["allow_fallbacks"] is False
        assert request["provider"]["require_parameters"] is True
    assert request["max_tokens"] == 5000


def test_established_knowledge_must_belong_to_correct_character():
    _, state, plan, route, _ = build_inputs()
    payload = plan.model_dump(mode="json")
    event = payload["required_events"][2]
    event["evidence_mode"] = "ESTABLISHED_KNOWLEDGE"
    event["allowed_provenance"] = ["STORY_STATE_KNOWLEDGE"]
    event["required_observer"] = None
    event["predicates"] = [event["predicates"][1]]
    payload["required_events"] = [event]
    c = compile_scene_contract(state, ScenePlanV1.model_validate(payload), route)
    evidence = rows(c)
    evidence[0].provenance = "STORY_STATE_KNOWLEDGE"
    evidence[0].state_pointer = "/characters/Duru/knowledge/0"
    evidence[0].evidence_subject = "lighthouse_location"
    assert not evaluate_events(contract=c, state=state, prose=PROSE, evidence=evidence)
    evidence[0].state_pointer = "/characters/Ekin/knowledge/0"
    assert evaluate_events(contract=c, state=state, prose=PROSE, evidence=evidence)
