"""Paid-stage safety controls; ALL provider replies synthesized, zero spend."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import v3_f2_autonomous_quality_probe as probe
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.v3_single_attempt_guard import SafetyStop


def grant(tmp_path):
    obj={
        "schema":"lumi.v3-f2-autonomous-quality-grant.v1",
        "authorized":True,
        "stage":"ENGLISH_QUALITY",
        "case_id":probe.CASE_ID,
        "writer_run_id":probe.WRITER_RUN,
        "spine_run_id":probe.SPINE_RUN,
        "story_sha256":probe.STORY_SHA,
        "approved_spine_sha256":probe.APPROVED_SHA,
        "frozen_runtime_sha":probe.FROZEN_V3_SHA,
        "models":["openai/gpt-5.6-luna","openai/gpt-5.6-sol","openai/gpt-5.6-luna"],
        "human_paid_authorization_reference":"SYNTHETIC_NO_PROVIDER_CALLS",
        "max_total_usd":"0.08",
        "grant_id":"QUALITY-F2-LOCAL-ONLY-20261015",
        "guard_commit_sha":subprocess.check_output(
            ["git","rev-parse","HEAD"],text=True,
        ).strip(),
    }
    path=tmp_path/"grant.json"
    path.write_text(json.dumps(obj))
    return path


def patch_git_for_uncommitted_test(monkeypatch):
    previous=subprocess.check_output
    def checked(args,**kwargs):
        if args[:2]==["git","status"]:
            return ""
        if args[:2]==["git","diff"]:
            return "src/v3_unattended_story_quality.py\n"
        return previous(args,**kwargs)
    monkeypatch.setattr(probe.subprocess,"check_output",checked)
    monkeypatch.setenv("OPENROUTER_API_KEY","OFFLINE_SYNTHETIC_NOT_SENT")
    monkeypatch.setenv("LUMI_QUALITY_GLOBAL_CLAIM_VERIFIED","YES")


def clean_audit(story, flag):
    seg=next((s for s in segment_story(story)
              if "Three timed readings." in s["text"]),None)
    return {"evaluations":[{
        "family":family,
        "present":flag and family=="state_continuity",
        "severity":"serious" if flag and family=="state_continuity" else None,
        "repair_scope":"local" if flag and family=="state_continuity" else None,
        "span_ids":[seg["id"]] if flag and family=="state_continuity" else [],
        "exact_quote":"Three timed readings." if flag and family=="state_continuity" else None,
        "reason":"Contradiction" if flag and family=="state_continuity" else "none",
    } for family in DEFECT_FAMILIES]}


class Response:
    ok=True
    status_code=200
    headers={}
    def __init__(self,model,value,n):
        self.model=model
        self.value=value
        self.n=n
    def json(self):
        return {
            "id":"gen-offline-f2-quality-"+str(self.n),
            "choices":[{"message":{"content":json.dumps(self.value)},
                        "finish_reason":"stop"}],
            "usage":{"cost":0.008,"prompt_tokens":1900,
                     "completion_tokens":900,"total_tokens":2800},
        }


@pytest.mark.parametrize("alter,error",[
    ({"stage":"WRITER"},"QUALITY_GRANT_SCOPE_MISMATCH"),
    ({"models":["openai/gpt-5.6-luna"]},"QUALITY_GRANT_SCOPE_MISMATCH"),
    ({"story_sha256":"f"*64},"QUALITY_GRANT_SCOPE_MISMATCH"),
    ({"max_total_usd":"0.21"},"QUALITY_CEILING_INVALID"),
    ({"guard_commit_sha":"a"*40},"QUALITY_GUARD_COMMIT_MISMATCH"),
    ({"human_paid_authorization_reference":""},"SEPARATE_PAID_QUALITY_AUTHORIZATION_REQUIRED"),
])
def test_wrong_grant_fails_before_claim(tmp_path,alter,error):
    file=grant(tmp_path)
    obj=json.loads(file.read_text())
    obj.update(alter)
    file.write_text(json.dumps(obj))
    with pytest.raises(SafetyStop,match=error):
        probe.run(grant_file=file,evidence_dir=tmp_path/"ev",
                  claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_global_run_claim_mandatory(tmp_path,monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY","OFFLINE")
    monkeypatch.delenv("LUMI_QUALITY_GLOBAL_CLAIM_VERIFIED",raising=False)
    file=grant(tmp_path)
    with pytest.raises(SafetyStop):
        probe.run(grant_file=file,evidence_dir=tmp_path/"ev",
                  claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_exact_writer_artifact_sha_is_pinned():
    story,writer,approved,frozen=probe.verify_source()
    assert len(story.split())==2767
    assert writer["status"]=="writer_generated_deterministic_check_failed"
    assert frozen["verified_files"]==43


def test_full_runner_model_autorepair_one_use(tmp_path,monkeypatch):
    patch_git_for_uncommitted_test(monkeypatch)
    file=grant(tmp_path)
    story=probe.STORY.read_text()
    responses=[
        clean_audit(story,True),
        {"repairs":[{"old":"Three timed readings.",
                     "new":"Four timed readings.",
                     "why":"Narrative has four observations"}]},
        clean_audit(story.replace("Three timed readings.","Four timed readings."),False),
    ]
    calls=[]
    def fake_post(url,**kwargs):
        n=len(calls)
        calls.append(kwargs["json"]["model"])
        return Response(calls[-1],responses[n],n+1)
    with patch("requests.post",side_effect=fake_post):
        out=probe.run(grant_file=file,evidence_dir=tmp_path/"first",
                      claim_dir=tmp_path/"claims")
        with pytest.raises(SafetyStop,match="QUALITY_GRANT_ALREADY_USED"):
            probe.run(grant_file=file,evidence_dir=tmp_path/"second",
                      claim_dir=tmp_path/"claims")
    assert calls==["openai/gpt-5.6-luna","openai/gpt-5.6-sol","openai/gpt-5.6-luna"]
    assert out["model_calls"]==3
    assert out["status"]=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
    assert out["length_warning"] is True
    assert out["length_blocking"] is False
    assert out["observed_cost_usd"]=="0.024"
    assert (tmp_path/"first"/"english-quality-accepted.txt").exists()
    assert "Three timed readings." in probe.STORY.read_text()
    assert "Four timed readings." in (tmp_path/"first"/"english-quality-accepted.txt").read_text()
    assert len(list((tmp_path/"first").glob("model-*.json")))==3
    assert not (tmp_path/"second").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1


def test_audit_clean_does_not_generate_sol_call(tmp_path,monkeypatch):
    patch_git_for_uncommitted_test(monkeypatch)
    file=grant(tmp_path)
    calls=[]
    def fake_post(url,**kwargs):
        calls.append(kwargs["json"]["model"])
        return Response(calls[-1],clean_audit(probe.STORY.read_text(),False),1)
    with patch("requests.post",side_effect=fake_post):
        out=probe.run(grant_file=file,evidence_dir=tmp_path/"first",
                      claim_dir=tmp_path/"claims")
    assert calls==["openai/gpt-5.6-luna"]
    assert out["model_calls"]==1
    assert out["length_warning"]


def test_api_error_stops_without_auto_retry_or_story_acceptance(tmp_path,monkeypatch):
    patch_git_for_uncommitted_test(monkeypatch)
    file=grant(tmp_path)
    seen=[]
    class FakeHTTPFailure:
        ok=False
        status_code=503
        headers={}
        text='{"error":"offline"}'
        def json(self):
            return {"error":"offline"}
    def error(url,**kwargs):
        seen.append(kwargs["json"]["model"])
        return FakeHTTPFailure()
    with patch("requests.post",side_effect=error):
        with pytest.raises(Exception):
            probe.run(grant_file=file,evidence_dir=tmp_path/"first",
                      claim_dir=tmp_path/"claims")
    assert seen==["openai/gpt-5.6-luna"]
    assert not (tmp_path/"first"/"english-quality-accepted.txt").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1
