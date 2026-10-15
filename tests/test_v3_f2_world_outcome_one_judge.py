"""Zero-provider tests for one Luna world-outcome evidence gate."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from experiments import v3_f2_world_outcome_one_judge as runner
from src.v3_single_attempt_guard import SafetyStop
from experiments.v3_f2_world_outcome_evidence_gate import OutcomeStop
from tests.test_v3_f2_world_outcome_evidence_gate import fake_model_response


def grant(tmp_path):
    payload={
        "schema":"lumi.v3-f2-world-outcome-judge-grant.v1",
        "authorized":True,
        "stage":"WORLD_OUTCOME_EVIDENCE_ONLY",
        "case_id":runner.CASE_ID,
        "english_story_sha256":runner.EXPECTED_EN,
        "turkish_story_sha256":runner.EXPECTED_TR,
        "model":runner.MODEL,
        "frozen_runtime_sha":runner.FROZEN_V3_SHA,
        "source_delivery_commit":runner.PARENT_SHA,
        "max_total_usd":"0.02",
        "guard_commit_sha":subprocess.check_output(
            ["git","rev-parse","HEAD"],text=True).strip(),
        "grant_id":"OFFLINE-WORLD-JUDGE-20261015-ONCE",
        "human_paid_authorization_reference":"OFFLINE_TEST_NO_PAYMENT",
    }
    path=tmp_path/"grant.json"
    path.write_text(json.dumps(payload))
    return path


def offline_git(monkeypatch):
    prior=subprocess.check_output
    def checked(args,**kwargs):
        if args[:2]==["git","status"]:return ""
        if args[:2]==["git","diff"]:return "experiments/v3_f2_world_outcome_one_judge.py\n"
        return prior(args,**kwargs)
    monkeypatch.setattr(runner.subprocess,"check_output",checked)
    monkeypatch.setenv("LUMI_WORLD_JUDGE_GLOBAL_CLAIM_VERIFIED","YES")
    monkeypatch.setenv("OPENROUTER_API_KEY","SYNTHETIC_NO_NETWORK")


class Response:
    ok=True
    status_code=200
    headers={}
    def __init__(self,payload,cost=0.009):
        self.payload=payload
        self.cost=cost
    def json(self):
        return {
            "id":"gen-synthetic-f2-world-outcome",
            "choices":[{"message":{"content":json.dumps(self.payload)},"finish_reason":"stop"}],
            "usage":{"cost":self.cost,"prompt_tokens":7400,
                     "completion_tokens":1200,"total_tokens":8600},
        }


def test_frozen_staged_chain_is_verified_before_any_call():
    source=runner.input_packet()
    assert source["source_story_sha256"]==runner.EXPECTED_EN
    assert len(source["persistent_outcome_candidates"])==5
    assert len(source["approved_branch_options"])==2
    assert source["published"] is False
    assert source["world_state_committed"] is False


@pytest.mark.parametrize("updates,stop",[
    ({"model":"openai/gpt-5.6-sol"},"WORLD_JUDGE_GRANT_SCOPE_INVALID"),
    ({"stage":"WORLD_STATE_COMMIT"},"WORLD_JUDGE_GRANT_SCOPE_INVALID"),
    ({"english_story_sha256":"0"*64},"WORLD_JUDGE_GRANT_SCOPE_INVALID"),
    ({"source_delivery_commit":"0"*40},"WORLD_JUDGE_GRANT_SCOPE_INVALID"),
    ({"human_paid_authorization_reference":""},"WORLD_JUDGE_SEPARATE_PAID_GRANT_REQUIRED"),
    ({"max_total_usd":"0.04"},"WORLD_JUDGE_CEILING_INVALID"),
    ({"guard_commit_sha":"a"*40},"WORLD_JUDGE_GUARD_SHA_MISMATCH"),
])
def test_wrong_grant_never_spends_or_claims(tmp_path,updates,stop):
    g=grant(tmp_path)
    doc=json.loads(g.read_text());doc.update(updates)
    g.write_text(json.dumps(doc))
    with pytest.raises(SafetyStop,match=stop):
        runner.run(grant_file=g,evidence_dir=tmp_path/"out",claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_absent_global_claim_blocks_run(tmp_path,monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY","OFFLINE")
    monkeypatch.delenv("LUMI_WORLD_JUDGE_GLOBAL_CLAIM_VERIFIED",raising=False)
    with pytest.raises(SafetyStop):
        runner.run(grant_file=grant(tmp_path),
                   evidence_dir=tmp_path/"out",claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_mocked_single_luna_model_response_yields_only_uncommitted_proposal(tmp_path,monkeypatch):
    offline_git(monkeypatch)
    seen=[]
    def fake_post(url,**kwargs):
        seen.append(kwargs["json"]["model"])
        return Response(fake_model_response())
    g=grant(tmp_path)
    with patch("requests.post",side_effect=fake_post):
        answer=runner.run(grant_file=g,evidence_dir=tmp_path/"out",
                          claim_dir=tmp_path/"claims")
        with pytest.raises(SafetyStop,match="WORLD_JUDGE_GRANT_REPLAY_BLOCKED"):
            runner.run(grant_file=g,evidence_dir=tmp_path/"second",
                       claim_dir=tmp_path/"claims")
    assert seen==[runner.MODEL]
    assert answer["status"]=="MODEL_WORLD_OUTCOME_REVIEW_STAGED_NOT_COMMITTED"
    assert answer["provider_posts"]==1
    assert answer["reported_new_cost_usd"]=="0.009"
    assert answer["candidate_count"]==5
    assert answer["earned_candidate_count"]==1
    assert answer["publication_authorized"] is False
    assert answer["world_state_committed"] is False
    assert not (tmp_path/"second").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1
    out=json.loads((tmp_path/"out"/"world-outcome-proposal.json").read_text())
    assert out["applied_operations"]==[]
    assert out["world_state_transaction"] is None


def test_fabricated_quote_stops_but_archives_real_model_response(tmp_path,monkeypatch):
    offline_git(monkeypatch)
    fake=fake_model_response()
    fake["branch_evidence_quotes"][0]="Never spoken fabricated line by Dessa."
    seen=[]
    def fake_post(url,**kwargs):
        seen.append(kwargs["json"]["model"])
        return Response(fake)
    with patch("requests.post",side_effect=fake_post):
        with pytest.raises(OutcomeStop,match="WORLD_JUDGE_BRANCH_QUOTE_FABRICATED"):
            runner.run(grant_file=grant(tmp_path),evidence_dir=tmp_path/"out",
                       claim_dir=tmp_path/"claims")
    assert seen==[runner.MODEL]
    assert (tmp_path/"out"/"judge-model-response.json").exists()
    assert not (tmp_path/"out"/"world-outcome-proposal.json").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1


def test_provider_error_stops_after_one_post(tmp_path,monkeypatch):
    offline_git(monkeypatch)
    seen=[]
    class Error:
        ok=False;status_code=503;headers={}
        text='{"error":"synthetic"}'
        def json(self):return {"error":"synthetic"}
    def fake_post(url,**kwargs):
        seen.append(kwargs["json"]["model"]);return Error()
    with patch("requests.post",side_effect=fake_post):
        with pytest.raises(Exception):
            runner.run(grant_file=grant(tmp_path),evidence_dir=tmp_path/"out",
                       claim_dir=tmp_path/"claims")
    assert seen==[runner.MODEL]
    assert not (tmp_path/"out"/"world-outcome-proposal.json").exists()


def test_above_planning_ceiling_stops_before_acceptance(tmp_path,monkeypatch):
    offline_git(monkeypatch)
    calls=[]
    def fake_post(url,**kwargs):
        calls.append(kwargs["json"]["model"])
        return Response(fake_model_response(),cost=0.04)
    with patch("requests.post",side_effect=fake_post):
        with pytest.raises(SafetyStop,match="CUMULATIVE_COST_CEILING_REACHED"):
            runner.run(grant_file=grant(tmp_path),evidence_dir=tmp_path/"out",
                       claim_dir=tmp_path/"claims")
    assert calls==[runner.MODEL]
    assert not (tmp_path/"out"/"world-outcome-proposal.json").exists()
