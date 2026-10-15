"""Standalone zero-provider Sol verdict after real Gemini/Luna findings."""
import json,subprocess
from pathlib import Path
from unittest.mock import patch
import pytest
from experiments import v3_f2_turkish_sol_adjudication_once as s
from src.v3_single_attempt_guard import SafetyStop

def grant(tmp_path):
    x={
        "schema":"lumi.v3-f2-tr-sol-adjudication-grant.v1",
        "authorized":True,
        "stage":"TR_FIDELITY_ADJUDICATION",
        "case_id":"age18.forbidden-cartographer.fantasy.frozen-01",
        "source_run_id":38713969969,
        "source_luna_sha256":s.EXPECTED[s.LUNA],
        "source_turkish_sha256":s.EXPECTED[s.TURKISH],
        "model":s.MODEL,
        "frozen_runtime_sha":s.FROZEN_V3_SHA,
        "guard_commit_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        "max_total_usd":"0.10",
        "grant_id":"OFFLINE-TR-SOL-ONCE-20261015",
        "human_paid_authorization_reference":"OFFLINE_TEST_ONLY",
    }
    p=tmp_path/"grant.json";p.write_text(json.dumps(x));return p

def setup(monkeypatch):
    old=subprocess.check_output
    def fake(args,**kw):
        if args[:2]==["git","diff"]:
            return "experiments/v3_f2_turkish_sol_adjudication_once.py\n"
        if args[:2]==["git","status"]:return ""
        return old(args,**kw)
    monkeypatch.setattr(s.subprocess,"check_output",fake)
    monkeypatch.setenv("LUMI_TR_SOL_GLOBAL_CLAIM_VERIFIED","YES")
    monkeypatch.setenv("OPENROUTER_API_KEY","SYNTHETIC_OFFLINE")

def adjudication(confirms):
    return {
        "evaluations":[
            {"finding_index":i,"decision":"CONFIRM" if i in confirms else "REJECT",
             "reason":"SYNTHETIC_QUALIFICATION"}
            for i in range(3)
        ],
        "confirmed_finding_indices":list(confirms),
    }

class Response:
    ok=True;status_code=200;headers={}
    def __init__(self,value):self.value=value
    def json(self):
        return {
            "id":"gen-offline-turkish-adjudication",
            "choices":[{"message":{"content":json.dumps(self.value)},"finish_reason":"stop"}],
            "usage":{"cost":0.013,"prompt_tokens":4000,"completion_tokens":600,
                     "total_tokens":4600},
        }

def test_archived_findings_exactly_three_and_profile_unchanged():
    frozen,luna,gemini=s.verify_sources()
    assert frozen["verified_files"]==43
    assert len(luna["fidelity_findings"])==3
    assert gemini["translation_model"]=="google/gemini-3.8-flash"
    assert s.MODEL=="openai/gpt-5.6-sol"

@pytest.mark.parametrize("wrong,error",[
    ({"model":"openai/gpt-5.6-luna"},"SOL_GRANT_SCOPE_MISMATCH"),
    ({"source_luna_sha256":"0"*64},"SOL_GRANT_SCOPE_MISMATCH"),
    ({"max_total_usd":"0.30"},"SOL_BUDGET_INVALID"),
    ({"human_paid_authorization_reference":""},"SOL_SEPARATE_PERMISSION_REQUIRED"),
    ({"stage":"WRITER"},"SOL_GRANT_SCOPE_MISMATCH"),
])
def test_tampered_grant_never_spends(tmp_path,wrong,error):
    p=grant(tmp_path)
    d=json.loads(p.read_text());d.update(wrong);p.write_text(json.dumps(d))
    with pytest.raises(SafetyStop,match=error):
        s.run(grant_file=p,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"out")
    assert not (tmp_path/"claims").exists()

def test_one_sol_model_call_all_false_positives_accepts_raw_turkish(tmp_path,monkeypatch):
    setup(monkeypatch)
    called=[]
    def mockpost(url,**kw):
        called.append(kw["json"]["model"])
        return Response(adjudication([]))
    g=grant(tmp_path)
    with patch("requests.post",side_effect=mockpost):
        out=s.run(grant_file=g,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"pass")
        with pytest.raises(SafetyStop,match="SOL_GRANT_ALREADY_CONSUMED"):
            s.run(grant_file=g,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"again")
    assert called==[s.MODEL]
    assert out["status"]=="AUTOMATED_TURKISH_FIDELITY_ACCEPTED"
    assert out["confirmed_findings"]==0
    assert out["model_posts"]==1
    assert out["manual_text_edits"]==0
    assert (tmp_path/"pass"/"turkish-quality-accepted.txt").read_text()==s.TURKISH.read_text()
    assert not (tmp_path/"again").exists()

def test_one_sol_confirms_defect_stops_before_repair(tmp_path,monkeypatch):
    setup(monkeypatch)
    called=[]
    def mockpost(url,**kw):
        called.append(kw["json"]["model"])
        return Response(adjudication([0]))
    with patch("requests.post",side_effect=mockpost):
        out=s.run(grant_file=grant(tmp_path),claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"out")
    assert called==[s.MODEL]
    assert out["status"]=="CONFIRMED_FINDINGS_AWAIT_MODEL_REPAIR"
    assert out["confirmed_findings"]==1
    assert not (tmp_path/"out"/"turkish-quality-accepted.txt").exists()

def test_sol_http_failure_stops_after_one_post(tmp_path,monkeypatch):
    setup(monkeypatch)
    called=[]
    class Fail:
        ok=False;status_code=503;headers={};text='{"error":"offline"}'
        def json(self):return {"error":"offline"}
    def post(url,**kw):
        called.append(kw["json"]["model"]);return Fail()
    with patch("requests.post",side_effect=post):
        with pytest.raises(Exception):
            s.run(grant_file=grant(tmp_path),claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"failed")
    assert called==[s.MODEL]
    assert not (tmp_path/"failed"/"turkish-quality-accepted.txt").exists()
