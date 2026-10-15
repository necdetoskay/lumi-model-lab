"""No production integration: G2 mapping, in-memory atomicity and rollback."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest
from experiments import v3_f2_g2_state_commit_preview as g

HOUSE="11111111-1111-4111-8111-111111111111"
PROFILE="22222222-2222-4222-8222-222222222222"
WORLD="33333333-3333-4333-8333-333333333333"
NODE="44444444-4444-4444-8444-444444444444"
NODE2="55555555-5555-4555-8555-555555555555"
EDGE="66666666-6666-4666-8666-666666666666"
CONTRACT="77777777-7777-4777-8777-777777777777"


def demo():
    scope={"householdId":HOUSE,"profileId":PROFILE,"worldInstanceId":WORLD}
    return {
        "marker":g.FIXTURE_MARKER,
        "scope":scope,
        "revision":9,
        "nodes":{
            NODE:{"scope":copy.deepcopy(scope),"status":"inactive","label":"synthetic"},
            NODE2:{"scope":copy.deepcopy(scope),"status":"blocked","label":"synthetic"},
        },
        "edges":{
            EDGE:{"scope":copy.deepcopy(scope),"availability":"blocked",
                  "label":"synthetic"},
        },
        "ledger":{},
    }


def sample_quote():
    return g.preview()["narrative_outcome_mappings"][0]["exact_evidence_quote"]


def op_node(node_id=NODE,status="active"):
    return {"kind":"NODE_STATE_SET","nodeId":node_id,
            "status":status,"statePayload":{},
            "evidenceQuote":sample_quote()}


def op_edge(edge_id=EDGE,status="restricted"):
    return {"kind":"EDGE_STATE_SET","edgeId":edge_id,
            "availability":status,"conditionPayload":{},
            "validFromTick":None,"expectedUntilTick":None,
            "evidenceQuote":sample_quote()}


def test_actual_g2_mapping_stops_without_real_id_and_baseline():
    preview=g.preview()
    assert preview["model_earned_count"]==5
    assert len(preview["narrative_outcome_mappings"])==5
    assert len(preview["missing_authoritative_bindings"])==len(
        g.G2_SCOPE_KEYS+g.G2_FROZEN_HEAD_KEYS)
    assert preview["g2_mapping_status"]=="BLOCKED_PENDING_AUTHORITATIVE_BINDINGS"
    assert preview["source_g2_commit"]==g.PROJECT_LUMI_SHA
    assert preview["g2_commit_request"] is None
    assert preview["g2_commit_executable"] is False
    assert preview["world_node_edge_mutations"]==[]
    assert preview["character_state_delta"] is None
    assert preview["production_g2_accepted_story_artifact_verified"] is False
    assert preview["live_database_connected"] is False
    assert preview["live_transaction_attempted"] is False
    assert preview["world_state_committed"] is False


def test_every_g2_candidate_refuses_invented_scope_and_target():
    result=g.preview()
    statuses=result["narrative_outcome_mappings"]
    assert {r["candidate_id"] for r in statuses}=={
        "f2-outcome-01","f2-outcome-02","f2-outcome-03",
        "f2-outcome-04","f2-outcome-05"}
    assert all(r["ready_to_commit"] is False and r["g2_executable_mutation"] is None
               and r["g2_fact_key"] is None and r["g2_delta"] is None
               and r["applied"] is False for r in statuses)
    assert statuses[1]["proposed_g2_class"]=="FOLLOW_UP_ACCESS_ELIGIBILITY_ONLY"
    assert statuses[1]["reason_blocked"]=="NOT_A_GRANTED_ROUTE_OR_EDGE_ACCESS_CHANGE"
    assert statuses[2]["reason_blocked"]=="NO_G2_REPUTATION_WORLD_MUTATION_KIND"
    assert all(4<=len(r["exact_evidence_quote"])<=280 for r in statuses)
    text=g.ENGLISH.read_text()
    assert all(r["exact_evidence_quote"] in text for r in statuses)


def test_production_binding_with_synthetic_guesses_still_not_commit_ready():
    bundle={k:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" for k in g.G2_SCOPE_KEYS}
    bundle.update({k:"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb" for k in
                   ("worldBeforeRevisionId","universeRevisionId","characterBeforeSnapshotId")})
    bundle.update({k:"c"*64 for k in
                   ("worldBeforeFingerprint","universeFingerprint","characterBeforeFingerprint")})
    bundle.update(characterBeforeRevisionNo=1,characterBeforeHeadVersion=1)
    result=g.preview(bundle)
    assert result["missing_authoritative_bindings"]==[]
    assert result["production_g2_accepted_story_artifact_verified"] is False
    assert result["g2_commit_executable"] is False
    assert result["g2_commit_request"] is None


def test_byte_exact_preflight_is_deterministic_and_writes_only_new_path(tmp_path):
    a=g.write_preview(tmp_path/"first")
    b=g.write_preview(tmp_path/"second")
    assert a==b
    assert (tmp_path/"first"/"g2-mapping-preview.json").read_bytes()==(
        tmp_path/"second"/"g2-mapping-preview.json").read_bytes()
    with pytest.raises(g.G2PreviewStop,match="G2_DRY_RUN_OUTPUT_ALREADY_EXISTS"):
        g.write_preview(tmp_path/"first")


def test_two_synthetic_mutations_atomic_and_compensation_restores_every_byte():
    before=demo()
    original=copy.deepcopy(before)
    ops=[op_node(),op_edge()]
    simulation=g.simulate_fixture_atomic_commit(
        before,contract_id=CONTRACT,expected_revision=9,ops=ops)
    assert before==original
    assert simulation["status"]=="SYNTHETIC_COMMIT_SIMULATED"
    assert simulation["after"]["revision"]==10
    assert simulation["after"]["nodes"][NODE]["status"]=="active"
    assert simulation["after"]["edges"][EDGE]["availability"]=="restricted"
    assert simulation["live_db_writes"]==0
    compensation=g.simulate_fixture_compensation(
        simulation["after"],simulation["rollback"])
    assert compensation["status"]=="SYNTHETIC_COMPENSATION_SIMULATED"
    assert compensation["restored"]==original
    assert g.fingerprint(compensation["restored"])==g.fingerprint(before)
    assert compensation["live_db_writes"]==0


def test_retry_same_contract_same_mutations_is_synthetic_idempotent():
    original=demo()
    ops=[op_node()]
    first=g.simulate_fixture_atomic_commit(
        original,contract_id=CONTRACT,expected_revision=9,ops=ops)
    retry=g.simulate_fixture_atomic_commit(
        first["after"],contract_id=CONTRACT,expected_revision=9,ops=ops)
    assert retry["status"]=="IDEMPOTENT_SYNTHETIC_REPLAY"
    assert retry["after"]==first["after"]
    assert retry["applied_operations"]==[]
    assert retry["live_db_writes"]==0


def test_same_contract_different_payload_blocked():
    first=g.simulate_fixture_atomic_commit(
        demo(),contract_id=CONTRACT,expected_revision=9,ops=[op_node()])
    with pytest.raises(g.G2PreviewStop,match="G2_FIXTURE_REPLAY_CONFLICT"):
        g.simulate_fixture_atomic_commit(
            first["after"],contract_id=CONTRACT,expected_revision=10,
            ops=[op_node(status="destroyed")])


def test_stale_head_blocks_whole_batch_and_leaves_input_unchanged():
    state=demo();before=copy.deepcopy(state)
    with pytest.raises(g.G2PreviewStop,match="G2_FIXTURE_STALE_REVISION"):
        g.simulate_fixture_atomic_commit(
            state,contract_id=CONTRACT,expected_revision=8,
            ops=[op_node(),op_edge()])
    assert state==before


def test_unknown_target_second_operation_never_partially_writes():
    state=demo();before=copy.deepcopy(state)
    with pytest.raises(g.G2PreviewStop,match="G2_OPERATION_TARGET_NOT_FOUND"):
        g.simulate_fixture_atomic_commit(
            state,contract_id=CONTRACT,expected_revision=9,
            ops=[op_node(),op_edge(edge_id=NODE2)])
    assert state==before


def test_cross_profile_target_blocks_whole_batch():
    state=demo()
    state["nodes"][NODE2]["scope"]["profileId"]="ffffffff-ffff-4fff-8fff-ffffffffffff"
    before=copy.deepcopy(state)
    with pytest.raises(g.G2PreviewStop,match="G2_OPERATION_CROSS_SCOPE_DENIED"):
        g.simulate_fixture_atomic_commit(
            state,contract_id=CONTRACT,expected_revision=9,
            ops=[op_edge(),op_node(node_id=NODE2)])
    assert state==before


def test_duplicate_mutation_and_wrong_kind_fail_closed():
    state=demo()
    with pytest.raises(g.G2PreviewStop,match="G2_FIXTURE_DUPLICATE_MUTATION"):
        g.simulate_fixture_atomic_commit(
            state,contract_id=CONTRACT,expected_revision=9,
            ops=[op_node(),op_node(status="blocked")])
    with pytest.raises(g.G2PreviewStop,match="G2_OPERATION_KIND_UNSUPPORTED"):
        g.simulate_fixture_atomic_commit(
            state,contract_id=CONTRACT,expected_revision=9,
            ops=[{"kind":"RELATIONSHIP_WRITE","id":NODE}])
    assert state["revision"]==9


def test_unsupported_open_passage_is_not_automatically_issued_by_preview():
    preview=g.preview()
    assert preview["world_node_edge_mutations"]==[]
    assert all(x["g2_executable_mutation"] is None
               for x in preview["narrative_outcome_mappings"])
    assert "open" in g.G2_MUTATION_STATUSES["EDGE_STATE_SET"]
    # The protocol supports edges, but no model verdict grants an edge ID
    # or passes the production StoryContract scope gate.
    assert preview["g2_commit_executable"] is False


def test_stale_post_state_denies_rollback_without_changing_snapshot():
    first=g.simulate_fixture_atomic_commit(
        demo(),contract_id=CONTRACT,expected_revision=9,ops=[op_node()])
    corrupted=copy.deepcopy(first["after"])
    corrupted["nodes"][NODE]["status"]="destroyed"
    original=copy.deepcopy(corrupted)
    with pytest.raises(g.G2PreviewStop,match="G2_FIXTURE_ROLLBACK_STALE_POST_STATE"):
        g.simulate_fixture_compensation(corrupted,first["rollback"])
    assert corrupted==original


def test_original_real_story_and_model_artifacts_remain_untouched(tmp_path):
    target=g.MODEL_PROPOSAL
    english=g.ENGLISH
    before_a,before_b=target.read_bytes(),english.read_bytes()
    g.write_preview(tmp_path/"dry")
    assert target.read_bytes()==before_a
    assert english.read_bytes()==before_b
    assert g.sha(target)==g.PROPOSAL_SHA
