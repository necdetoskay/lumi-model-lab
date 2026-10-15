"""Single-fresh-Luna recheck tests using exact archived real Luna/Sol input."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import v3_f2_quality_luna_recheck_probe as resume
from src.story_defect_detection import DEFECT_FAMILIES
from src.v3_single_attempt_guard import SafetyStop
from src.v3_unattended_story_quality import QualityStop


def grant(tmp_path):
    doc={
        "schema":"lumi.v3-f2-final-luna-recheck-grant.v1",
        "authorized":True,
        "stage":"ENGLISH_QUALITY_RECHECK",
        "case_id":resume.base.CASE_ID,
        "source_writer_run_id":resume.base.WRITER_RUN,
        "source_quality_run_id":resume.SOURCE_QUALITY_RUN,
        "original_story_sha256":resume.base.STORY_SHA,
        "archived_luna_sha256":resume.LUNA_SHA,
        "archived_sol_sha256":resume.SOL_SHA,
        "model":"openai/gpt-5.6-luna",
        "frozen_runtime_sha":resume.FROZEN_V3_SHA,
        "max_total_usd":"0.02",
        "grant_id":"OFFLINE-RECHECK-ONCE-20261015",
        "guard_commit_sha":subprocess.check_output(
            ["git","rev-parse","HEAD"],text=True
        ).strip(),
        "human_paid_authorization_reference":"OFFLINE_TEST_ONLY_NO_REAL_BILLING",
    }
    target=tmp_path/"grant.json"
    target.write_text(json.dumps(doc))
    return target


def clean_git(monkeypatch):
    old=subprocess.check_output
    def fake(args,**kwargs):
        if args[:2]==["git","status"]:
            return ""
        if args[:2]==["git","diff"]:
            return "src/v3_unattended_story_quality.py\n"
        return old(args,**kwargs)
    monkeypatch.setattr(resume.subprocess,"check_output",fake)
    monkeypatch.setenv("LUMI_RECHECK_GLOBAL_CLAIM_VERIFIED","YES")
    monkeypatch.setenv("OPENROUTER_API_KEY","SYNTHETIC_OFFLINE_ONLY")


def zero_finding_reply():
    return {"evaluations":[{
        "family":family,
        "present":False,"severity":None,"repair_scope":None,
        "span_ids":[],"exact_quote":None,"reason":"SYNTHETIC_CLEAN_RESULT",
    } for family in DEFECT_FAMILIES]}


class Response:
    ok=True
    status_code=200
    headers={}
    def __init__(self,payload):self.payload=payload
    def json(self):
        return {
            "id":"gen-offline-final-luna-f2",
            "choices":[{"message":{"content":json.dumps(self.payload)},
                        "finish_reason":"stop"}],
            "usage":{"prompt_tokens":2200,"completion_tokens":800,
                      "total_tokens":3000,"cost":0.009},
        }


def test_prior_real_evidence_reconstructs_only_model_authored_candidate():
    candidate,writer,approved,packet,cost,verified=resume.verify_recorded_model_evidence()
    original=resume.base.STORY.read_text()
    assert candidate!=original
    assert len(candidate.split())==2767
    assert cost==__import__("decimal").Decimal("0.0844978")
    assert verified["verified_files"]==43
    patch=json.loads(resume.SOL_FILE.read_text())["model_json"]["repairs"][0]
    assert candidate==original.replace(patch["old"],patch["new"],1)
    assert hashlib.sha256(original.encode()).hexdigest()==resume.base.STORY_SHA


@pytest.mark.parametrize("updates,error",[
    ({"stage":"WRITER"},"RECHECK_GRANT_SCOPE_MISMATCH"),
    ({"model":"openai/gpt-5.6-sol"},"RECHECK_GRANT_SCOPE_MISMATCH"),
    ({"source_quality_run_id":0},"RECHECK_GRANT_SCOPE_MISMATCH"),
    ({"archived_sol_sha256":"0"*64},"RECHECK_GRANT_SCOPE_MISMATCH"),
    ({"max_total_usd":"0.31"},"RECHECK_CEILING_INVALID"),
    ({"human_paid_authorization_reference":""},"SEPARATE_LUNA_RECHECK_APPROVAL_REQUIRED"),
])
def test_wrong_grant_never_spends_or_consumes_claim(tmp_path,updates,error):
    file=grant(tmp_path)
    d=json.loads(file.read_text());d.update(updates);file.write_text(json.dumps(d))
    with pytest.raises(SafetyStop,match=error):
        resume.run(grant_file=file,evidence_dir=tmp_path/"ev",claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_fresh_global_claim_mandatory(tmp_path,monkeypatch):
    monkeypatch.delenv("LUMI_RECHECK_GLOBAL_CLAIM_VERIFIED",raising=False)
    with pytest.raises(SafetyStop):
        resume.run(grant_file=grant(tmp_path),
                   evidence_dir=tmp_path/"evidence",claim_dir=tmp_path/"claims")
    assert not (tmp_path/"claims").exists()


def test_recheck_only_one_new_luna_call_and_reuse_blocked(tmp_path,monkeypatch):
    clean_git(monkeypatch)
    file=grant(tmp_path)
    calls=[]
    def mock_post(url,**kwargs):
        calls.append(kwargs["json"]["model"])
        return Response(zero_finding_reply())
    with patch("requests.post",side_effect=mock_post):
        out=resume.run(grant_file=file,
                       evidence_dir=tmp_path/"first",claim_dir=tmp_path/"claims")
        with pytest.raises(SafetyStop,match="RECHECK_GRANT_ALREADY_CONSUMED"):
            resume.run(grant_file=file,
                       evidence_dir=tmp_path/"second",claim_dir=tmp_path/"claims")
    assert calls==["openai/gpt-5.6-luna"]
    assert out["status"]=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
    assert out["length_warning"] is True
    assert out["model_authored_local_edits"]==1
    assert out["live_recheck_calls"]==1
    assert out["new_recheck_cost_usd"]=="0.009"
    assert out["no_manual_story_edit"] is True
    assert out["translation_authorized"] is False
    assert out["world_state_commit_authorized"] is False
    assert (tmp_path/"first"/"english-quality-accepted.txt").is_file()
    assert (tmp_path/"first"/"model-03-post_repair_coherence_reaudit.json").is_file()
    assert not (tmp_path/"second").exists()
    assert "Three timed readings." in resume.base.STORY.read_text()


def test_luna_finds_another_problem_and_stops_with_no_accepted_file(tmp_path,monkeypatch):
    clean_git(monkeypatch)
    file=grant(tmp_path)
    candidate,_,_,_,_,_=resume.verify_recorded_model_evidence()
    from src.story_defect_detection import segment_story
    segment=next(s for s in segment_story(candidate) if "Four timed readings." in s["text"])
    bad=zero_finding_reply()
    row=next(x for x in bad["evaluations"] if x["family"]=="state_continuity")
    row.update({
        "present":True,"severity":"serious","repair_scope":"local",
        "span_ids":[segment["id"]],
        "exact_quote":"Four timed readings.",
        "reason":"SYNTHETIC_EXTRA_BLOCKING_ISSUE",
    })
    calls=[]
    def fake_post(url,**kwargs):
        calls.append(kwargs["json"]["model"])
        return Response(bad)
    with patch("requests.post",side_effect=fake_post):
        with pytest.raises(QualityStop,match="REAL_LUNA_RECHECK_FOUND_BLOCKING_DEFECT"):
            resume.run(grant_file=file,evidence_dir=tmp_path/"failure",
                       claim_dir=tmp_path/"claims")
    assert calls==["openai/gpt-5.6-luna"]
    assert not (tmp_path/"failure"/"english-quality-accepted.txt").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1
