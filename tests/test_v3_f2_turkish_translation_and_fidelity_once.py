"""No-network proof for independent F2 Turkish translator + fidelity gate."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import v3_f2_turkish_translation_and_fidelity_once as tr
from src.v3_single_attempt_guard import SafetyStop


def grant(tmp_path):
    row={
        "schema":"lumi.v3-f2-english-to-turkish-grant.v1",
        "authorized":True,"stage":"TURKISH_TRANSLATION_FIDELITY",
        "case_id":tr.CASE_ID,"source_quality_run_id":tr.SOURCE_RUN,
        "source_english_sha256":tr.SOURCE_SHA,
        "approved_spine_sha256":tr.APPROVED_SHA,
        "frozen_runtime_sha":tr.FROZEN_V3_SHA,
        "models":list(tr.TRANSLATION_MODELS),
        "max_total_usd":"0.12","grant_id":"OFFLINE-F2-TURKISH-ONCE-20261015",
        "guard_commit_sha":subprocess.check_output(
            ["git","rev-parse","HEAD"],text=True).strip(),
        "human_paid_authorization_reference":"OFFLINE_SYNTHETIC_ONLY",
    }
    path=tmp_path/"grant.json";path.write_text(json.dumps(row))
    return path


def offline_checkout(monkeypatch):
    prior=subprocess.check_output
    def check(args,**kwargs):
        if args[:2]==["git","status"]: return ""
        if args[:2]==["git","diff"]: return "experiments/v3_f2_turkish_translation_and_fidelity_once.py\n"
        return prior(args,**kwargs)
    monkeypatch.setattr(tr.subprocess,"check_output",check)
    monkeypatch.setenv("OPENROUTER_API_KEY","OFFLINE_NO_NETWORK")
    monkeypatch.setenv("LUMI_F2_TR_GLOBAL_CLAIM_VERIFIED","YES")


def turkish_fixture():
    return (
        "# Haritanın Kabul Etmeyi Reddettiği Yol\n\n"
        "Leyra, Vellum Hall salonundaki pusulaya dikkatle baktı. "
        "Dessa ölçümleri yazdı, Ashen Gate kapısını açmadılar. "
        "Ilyan nedenin bilinmediğini söyledi. "
        "Greyfen halkı raporu aldı. "
        "Tam olarak ne olduğundan henüz emin değillerdi.\n"
    )


class Reply:
    ok=True
    status_code=200
    headers={}
    text=""
    def __init__(self,n,content,cost=0.011):
        self.n=n;self.content=content;self.cost=cost
    def json(self):
        return {
            "id":"gen-offline-f2-turkish-"+str(self.n),
            "choices":[{"message":{"content":self.content},"finish_reason":"stop"}],
            "usage":{"cost":self.cost,"prompt_tokens":1654,
                     "completion_tokens":2400,"total_tokens":4054},
        }


@pytest.mark.parametrize("alter,error",[
    ({"stage":"SPINE"},"TRANSLATION_GRANT_SCOPE_INVALID"),
    ({"source_quality_run_id":0},"TRANSLATION_GRANT_SCOPE_INVALID"),
    ({"source_english_sha256":"0"*64},"TRANSLATION_GRANT_SCOPE_INVALID"),
    ({"models":["openai/gpt-5.6-luna"]},"TRANSLATION_GRANT_SCOPE_INVALID"),
    ({"max_total_usd":"0.16"},"TRANSLATION_CEILING_INVALID"),
    ({"human_paid_authorization_reference":""},"TRANSLATION_SEPARATE_PAID_APPROVAL_REQUIRED"),
])
def test_invalid_grant_never_consumes_claim(tmp_path,alter,error):
    p=grant(tmp_path)
    row=json.loads(p.read_text());row.update(alter);p.write_text(json.dumps(row))
    with pytest.raises(SafetyStop,match=error):
        tr.run(grant_file=p,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"out")
    assert not (tmp_path/"claims").exists()


def test_source_files_and_original_frozen_profile_exact():
    assert tr.file_sha(tr.STORY)==tr.SOURCE_SHA
    assert tr.file_sha(tr.APPROVED)==tr.APPROVED_SHA
    assert tr.TRANSLATION_MODELS==("google/gemini-3.8-flash","openai/gpt-5.6-luna")
    from src.frozen_lane_verify import verify_frozen_lane
    assert verify_frozen_lane(tr.PROFILE)["verified_files"]==43


def test_global_run_bound_claim_required(tmp_path,monkeypatch):
    offline_checkout(monkeypatch)
    monkeypatch.delenv("LUMI_F2_TR_GLOBAL_CLAIM_VERIFIED")
    with pytest.raises(SafetyStop,match="TRANSLATION_RUN_BOUND_GLOBAL_CLAIM_MISSING"):
        tr.run(grant_file=grant(tmp_path),claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"out")
    assert not (tmp_path/"claims").exists()


def test_two_model_posts_translation_and_luna_fidelity_clean(tmp_path,monkeypatch):
    offline_checkout(monkeypatch)
    claims=[]
    responses=[
        turkish_fixture(),
        json.dumps({"fidelity_clean":True,"findings":[]},ensure_ascii=False),
    ]
    def fake_post(url,**kwargs):
        n=len(claims)
        claims.append(kwargs["json"]["model"])
        return Reply(n+1,responses[n])
    p=grant(tmp_path)
    with patch("requests.post",side_effect=fake_post):
        out=tr.run(grant_file=p,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"pass")
        with pytest.raises(SafetyStop,match="TRANSLATION_GRANT_ALREADY_USED"):
            tr.run(grant_file=p,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"again")
    assert claims==list(tr.TRANSLATION_MODELS)
    assert out["status"]=="AUTOMATED_TURKISH_FIDELITY_CLEAN"
    assert out["model_posts"]==2
    assert out["new_cost_usd"]=="0.022"
    assert out["human_text_edits"]==0
    assert out["publication_authorized"] is False
    assert (tmp_path/"pass"/"translation-tr.txt").exists()
    assert not (tmp_path/"again").exists()
    assert len(list((tmp_path/"claims").glob("*.json")))==1
    observations=[
        json.loads(f.read_text()) for f in (tmp_path/"pass").glob("[0-9][0-9][0-9]-*.json")
    ]
    assert len([x for x in observations if x["kind"]=="PROVIDER_OBSERVED"])==2


def test_luna_semantic_findings_block_turkish_acceptance(tmp_path,monkeypatch):
    offline_checkout(monkeypatch)
    posts=[]
    error={"fidelity_clean":False,"findings":[{
        "severity":"serious","class":"negation_shift",
        "source_quote":"not established","translation_quote":"kesinleşti",
        "why":"Synthetic omission of not",
    }]}
    def post(url,**kwargs):
        n=len(posts);posts.append(kwargs["json"]["model"])
        return Reply(n+1,turkish_fixture() if n==0 else json.dumps(error))
    with patch("requests.post",side_effect=post):
        with pytest.raises(SafetyStop,match="TURKISH_FIDELITY_FINDINGS_STOP"):
            tr.run(grant_file=grant(tmp_path),claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"reject")
    assert posts==list(tr.TRANSLATION_MODELS)
    assert not (tmp_path/"reject"/"qualification.json").exists()


def test_first_provider_error_stops_at_first_post(tmp_path,monkeypatch):
    offline_checkout(monkeypatch)
    seen=[]
    class Error:
        ok=False;status_code=503;text='{"error":"synthetic"}';headers={}
        def json(self):return {"error":"synthetic"}
    def post(url,**kwargs):
        seen.append(kwargs["json"]["model"])
        return Error()
    with patch("requests.post",side_effect=post):
        with pytest.raises(Exception):
            tr.run(grant_file=grant(tmp_path),claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"stop")
    assert seen==["google/gemini-3.8-flash"]
    assert not (tmp_path/"stop"/"translation-tr.txt").exists()


def test_overceiling_observed_cost_blocks_second_call(tmp_path,monkeypatch):
    offline_checkout(monkeypatch)
    seen=[]
    def post(url,**kwargs):
        seen.append(kwargs["json"]["model"])
        return Reply(1,turkish_fixture(),cost=0.17)
    with patch("requests.post",side_effect=post):
        with pytest.raises(SafetyStop,match="CUMULATIVE_COST_CEILING_REACHED"):
            tr.run(grant_file=grant(tmp_path),claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"stop")
    assert seen==["google/gemini-3.8-flash"]
    assert not (tmp_path/"stop"/"qualification.json").exists()
