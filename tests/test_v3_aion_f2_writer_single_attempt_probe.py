"""F2 Aion Mini Writer approval / one-provider-call proof, zero live HTTP."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import v3_aion_f2_writer_single_attempt_probe as f2
from src.v3_single_attempt_guard import SafetyStop

WRITER="aion-labs/aion-3.5-mini"
SYNTHETIC_STORY=" ".join([
    "Leyra studied the sealed map before Dessa logged the final reading carefully."
] * 160)


def make_grant(tmp_path):
    grant={
        "schema":"lumi.v3-aion-f2-writer-paid-grant.v1",
        "authorized":True,
        "stage":"WRITER",
        "case_id":f2.CASE_ID,
        "model":WRITER,
        "source_spine_run_id":f2.SOURCE_SPINE_RUN_ID,
        "frozen_runtime_sha":f2.FROZEN_V3_SHA,
        "approved_spine_sha256":f2.APPROVED_SHA256,
        "max_total_usd":"0.10",
        "guard_commit_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        "grant_id":"OFFLINE-AION-F2-WRITER-20261015",
        "human_paid_authorization_reference":"OFFLINE_TEST_ONLY",
    }
    target=tmp_path/"grant.json"
    target.write_text(json.dumps(grant))
    return target


def isolate_checkout(monkeypatch):
    """Only fake uncommitted status and diff until CI pins exact reviewed SHA."""
    old=subprocess.check_output
    def fake_output(args,**kwargs):
        if args[:2]==["git","status"]:
            return ""
        if args[:2]==["git","diff"]:
            return "src/v3_single_attempt_aion_writer_guard.py\n"
        return old(args,**kwargs)
    monkeypatch.setattr(f2.subprocess,"check_output",fake_output)
    monkeypatch.setenv("OPENROUTER_API_KEY","SYNTHETIC_OFFLINE_NO_NETWORK")


class Response:
    ok=True
    status_code=200
    headers={}
    def __init__(self,status=200,cost=0.031,completion=SYNTHETIC_STORY):
        self.ok=status==200
        self.status_code=status
        self.cost=cost
        self.completion=completion

    def json(self):
        if not self.ok:
            return {"error":{"message":"FAKE_RATE_LIMIT"}}
        return {
            "id":"gen-offline-f2-one-writer",
            "choices":[{"message":{"content":self.completion},
                        "finish_reason":"stop"}],
            "usage":{"prompt_tokens":2500,"completion_tokens":2200,
                     "total_tokens":4700,"cost":self.cost},
        }

    @property
    def text(self):
        return '{"error":"FAKE_RATE_LIMIT"}'


def test_f2_writer_strictly_uses_aion_and_f2_context():
    v=f2.validate_source()
    assert v["verified_files"]==43
    from src.episode_writer_v2_generate import build_writer_input
    approved=json.loads(f2.APPROVED.read_text())
    assert approved["qualification_provenance"]["source_archived_sha256"]==f2.SOURCE_F2_SHA256
    assert approved["human_review"]["verdict"]=="APPROVE"
    context=build_writer_input(approved,authority_packet_version="v2")
    assert context["source_spine_run_id"]==38700326961
    assert context["hard_rules"]["writer_must_choose_exactly_one_decision_branch"]
    assert "Dessa" in context["human_review"]["note"]


@pytest.mark.parametrize("changed,expected",[
    ({"stage":"SPINE"},"F2_WRITER_GRANT_SCOPE_MISMATCH"),
    ({"model":"anthropic/claude-sonnet-5.5"},"F2_WRITER_GRANT_SCOPE_MISMATCH"),
    ({"source_spine_run_id":36612862926},"F2_WRITER_GRANT_SCOPE_MISMATCH"),
    ({"max_total_usd":"0.11"},"F2_WRITER_GRANT_SCOPE_MISMATCH"),
    ({"approved_spine_sha256":"0"*64},"F2_WRITER_GRANT_SCOPE_MISMATCH"),
])
def test_grant_scope_refuses_without_claim(tmp_path,changed,expected):
    p=make_grant(tmp_path)
    raw=json.loads(p.read_text())
    raw.update(changed)
    p.write_text(json.dumps(raw))
    with pytest.raises(SafetyStop,match=expected):
        f2.run(grant_file=p,evidence_dir=tmp_path/"evidence",claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_writer_paid_approval_reference_required(tmp_path):
    p=make_grant(tmp_path)
    raw=json.loads(p.read_text())
    raw["human_paid_authorization_reference"]=""
    p.write_text(json.dumps(raw))
    with pytest.raises(SafetyStop,match="F2_WRITER_EXPLICIT_AUTHORIZATION_MISSING"):
        f2.run(grant_file=p,evidence_dir=tmp_path/"evidence",claim_dir=tmp_path/"claims")


def test_success_one_post_then_grant_replay_blocked(tmp_path,monkeypatch):
    isolate_checkout(monkeypatch)
    p=make_grant(tmp_path)
    calls=[]
    def fake_post(url,**kwargs):
        assert kwargs["json"]["model"]==WRITER
        assert kwargs["json"]["messages"][0]["role"]=="system"
        assert kwargs["json"]["messages"][1]["role"]=="user"
        payload=json.loads(kwargs["json"]["messages"][1]["content"])
        assert payload["source_spine_run_id"]==38700326961
        assert payload["hard_rules"]["one_writer_call_only"] is True
        calls.append(WRITER)
        return Response()
    with patch("requests.post",side_effect=fake_post):
        result=f2.run(grant_file=p,evidence_dir=tmp_path/"first",claim_dir=tmp_path/"claims")
        assert result["status"]=="writer_generated"
        assert result["writer_model"]==WRITER
        assert result["next_stage_authorized"] is False
        with pytest.raises(SafetyStop,match="F2_WRITER_GRANT_ALREADY_CONSUMED"):
            f2.run(grant_file=p,evidence_dir=tmp_path/"second",claim_dir=tmp_path/"claims")
    assert calls==[WRITER]
    assert not (tmp_path/"second").exists()
    assert (tmp_path/"first"/"story-en.txt").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1
    evidence=[json.loads(x.read_text()) for x in (tmp_path/"first").glob("[0-9][0-9][0-9]-*.json")]
    assert any(x["kind"]=="STAGE_FINISHED" and x["post_count"]==1 for x in evidence)


@pytest.mark.parametrize("http_status",[429,500,503])
def test_provider_errors_stop_after_one_post(tmp_path,monkeypatch,http_status):
    isolate_checkout(monkeypatch)
    p=make_grant(tmp_path)
    calls=[]
    def fake_post(url,**kwargs):
        calls.append(WRITER)
        return Response(status=http_status)
    with patch("requests.post",side_effect=fake_post):
        with pytest.raises(Exception):
            f2.run(grant_file=p,evidence_dir=tmp_path/"fail",claim_dir=tmp_path/"claims")
    assert calls==[WRITER]
    assert not (tmp_path/"fail"/"story-en.txt").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1


def test_cost_over_cap_stops_before_story_output(tmp_path,monkeypatch):
    isolate_checkout(monkeypatch)
    p=make_grant(tmp_path)
    calls=[]
    def fake_post(url,**kwargs):
        calls.append(WRITER)
        return Response(cost=0.12)
    with patch("requests.post",side_effect=fake_post):
        with pytest.raises(SafetyStop,match="CUMULATIVE_COST_CEILING_REACHED"):
            f2.run(grant_file=p,evidence_dir=tmp_path/"fail",claim_dir=tmp_path/"claims")
    assert calls==[WRITER]
    assert not (tmp_path/"fail"/"story-en.txt").exists()
