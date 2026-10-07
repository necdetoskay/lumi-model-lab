import pytest
import json
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_events import PredicateEvidenceV1
from src.spineforge_relay_v1_q7d_inputs import build_chain, prepare, request_for
from src.spineforge_relay_v1_spatial import (
    SpatialTopologyV1, SpatialStateV1, SpatialOperationV1,
    compile_spatial_contract, evaluate_spatial,
)


def bound(index=2):
    fixture, _, _, _, rows, _ = build_chain()
    _, scene, state = rows[index]
    spatial = fixture["spatial_plans"][index]
    contract = compile_spatial_contract(scene=scene, state=state,
        topology=SpatialTopologyV1.model_validate(fixture["topology"]),
        operations=[SpatialOperationV1.model_validate(o) for o in spatial["operations"]],
        expected_exit=SpatialStateV1.model_validate(spatial["expected_exit"]))
    evidence = [PredicateEvidenceV1(event_id=o.event_id, predicate_id=o.predicate_id,
        subject=o.subject, action=o.kind, target=o.target, verdict="SUPPORTED", provenance="DIRECT_OBSERVATION",
        exact_text=f"Unique action {i}.", evidence_subject=o.target, state_pointer=None, reason="Test extraction")
        for i, o in enumerate(contract.operations)]
    prose = " ".join(r.exact_text for r in evidence)
    return contract, scene, state, evidence, prose


def test_fresh_chain_keeps_original_scene_and_migrates_only_metadata():
    fixture, _, _, start, rows, final = build_chain()
    original = fixture["previous_accepted_scene"]["state_after"]
    payload = start.model_dump(mode="json")
    payload["world"].pop("spatial")
    assert payload == original
    assert start.revision == 1 and final.revision == 6 and final.next_spine_beat is None
    assert [p.scene_id for p, _, _ in rows] == ["SC02", "SC03", "SC04", "SC05", "SC06"]
    assert rows[2][2].world["spatial"]["access_constraints"][0]["active"] is True
    assert final.world["spatial"]["positions"]["Ekin"] == "harbor"


def test_grounded_ordered_evidence_passes():
    c, scene, state, evidence, prose = bound()
    assert evaluate_spatial(contract=c, scene=scene, state=state, prose=prose, evidence=evidence) == []


@pytest.mark.parametrize("mutation", ["reverse", "missing", "duplicate", "unsupported", "knowledge", "misattribute", "repeated_quote", "overlap"])
def test_spatial_evidence_corruption_fails_closed(mutation):
    c, scene, state, evidence, prose = bound()
    if mutation == "reverse": prose = " ".join(r.exact_text for r in reversed(evidence))
    if mutation == "missing": evidence.pop(0)
    if mutation == "duplicate": evidence.append(evidence[0])
    if mutation == "unsupported": evidence[0].verdict = "UNSUPPORTED"
    if mutation == "knowledge": evidence[0].provenance = "STORY_STATE_KNOWLEDGE"
    if mutation == "misattribute": evidence[0].subject = "Duru"
    if mutation == "repeated_quote": prose += " " + evidence[0].exact_text
    if mutation == "overlap": evidence[1].exact_text = evidence[0].exact_text
    assert evaluate_spatial(contract=c, scene=scene, state=state, prose=prose, evidence=evidence)


@pytest.mark.parametrize("mutation", ["state", "contract", "exit", "operations"])
def test_spatial_binding_corruption_rejected(mutation):
    c, scene, state, evidence, prose = bound()
    if mutation == "state": state.world["spatial"]["positions"]["Ekin"] = "harbor"
    if mutation == "contract": c.scene_contract_sha256 = "0"*64
    if mutation == "exit": c.exit.positions["Ekin"] = "harbor"
    if mutation == "operations": c.operations[0].predicate_id = "unknown"
    assert evaluate_spatial(contract=c, scene=scene, state=state, prose=prose, evidence=evidence)


def test_writer_and_guard_share_exact_spatial_input():
    c, scene, state, _, _ = bound()
    payload = {"spatial_contract": c.model_dump(mode="json"), "scene_contract": scene.model_dump(mode="json")}
    for stage in ("writer", "guard"):
        kwargs, request = request_for(stage, payload)
        assert "spatial_contract" in kwargs["user_prompt"]
        assert "spatial_contract" in request["messages"][1]["content"]
        assert "RELEASE" in kwargs["system_prompt"]
        assert request["provider"]["allow_fallbacks"] is False


def test_preflight_binds_fresh_contracts_and_total_budget():
    pf = prepare()
    assert pf["max_calls"] == 20 and pf["max_total_cost_usd"] == 0.60
    assert len(set(pf["contract_sha256"])) == 5
    assert pf["migration"]["source_state_sha256"] != pf["start_state_sha256"]
    assert len(pf["files"]) == len({p["path"] for p in pf["files"]})


@pytest.mark.parametrize("mode", ["accept", "reject", "timeout"])
def test_executor_freezes_only_after_all_spatial_checks_and_never_retries(tmp_path, mode):
    from src.spineforge_relay_v1_q7d import execute
    from src.spineforge_relay_v1_q7d_inputs import authorization_for
    from src.spineforge_relay_v1_q5t import StructuredGuardV1
    calls = []
    def call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        stage = "guard" if "candidate_prose" in payload else "writer"
        _, request = request_for(stage, payload)
        calls.append(stage)
        if mode == "timeout":
            raise TimeoutError("Uncertain dispatch")
        scene = payload["scene_contract"]
        rows = []
        anchors = []
        for event in scene["required_events"]:
            for predicate in event["predicates"]:
                anchor = f"{event['id']} {predicate['id']} visible action."
                anchors.append(anchor)
                rows.append(PredicateEvidenceV1(event_id=event["id"], predicate_id=predicate["id"],
                    subject=predicate["subject"], action=predicate["action"], target=predicate["target"],
                    verdict="SUPPORTED", provenance="DIRECT_OBSERVATION", exact_text=anchor,
                    evidence_subject=predicate["target"], state_pointer=None,
                    reason="Synthetic plumbing check, no semantic qualification"))
        if mode == "reject":
            rows[-1].verdict = "UNSUPPORTED"
        prose = " ".join(anchors) + " " + " ".join(["quiet"]*200)
        text = prose if stage == "writer" else StructuredGuardV1(event_evidence=rows,
            residual={"decision": "PASS", "findings": [], "summary": "Synthetic plumbing"}).model_dump_json()
        return text, {"choices": [{"finish_reason": "stop"}], "usage": {
            "prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200, "cost": 0.001}}, request
    pf = prepare()
    result = execute(api_key="fake", preflight=pf, authorization=authorization_for(pf), output=tmp_path/"run", call_fn=call)
    assert len(calls) == {"accept": 10, "reject": 4, "timeout": 1}[mode]
    assert result["status"] == ("ACCEPT" if mode == "accept" else "REJECT_NON_CONVERGENT")
    assert result["state_advanced_to_revision"] == (6 if mode == "accept" else 1)
    with pytest.raises(FileExistsError):
        execute(api_key="fake", preflight=pf, authorization=authorization_for(pf), output=tmp_path/"other", call_fn=call)
