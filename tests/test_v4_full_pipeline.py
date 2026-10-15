"""No-network V4 guard and full-line routing tests; never call paid provider."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.v4_paid_guard import V4ProviderLedger,V4PaidStop
from src.v4_full_pipeline import run
from src.story_stage_common import write_json
from experiments.v4_one_case_full_run import validate

ROOT=Path("data/specifications/story_lab")
CASE=ROOT/"four_genre_v3_inputs/closed_platform_case_manifest_v4.json"
F2=ROOT/"age18_forbidden_cartographer_f2_approved_for_aion_20261015.json"


def test_paid_guard_prevents_model_output_token_limit_before_post(tmp_path):
    ledger=V4ProviderLedger(evidence_dir=tmp_path/"evidence")
    called=[]
    ledger.original_post=lambda url,**kwargs:called.append(1)
    with pytest.raises(V4PaidStop,match="EXPLICIT_OUTPUT_TOKEN_CEILING"):
        ledger.post("https://openrouter.ai/api/v1/chat/completions",
                    json={"model":"anthropic/claude-sonnet-5.5","max_tokens":12000})
    assert called==[] and ledger.posts==0


def test_paid_guard_observes_cost_before_downstream_parser(tmp_path):
    ledger=V4ProviderLedger(evidence_dir=tmp_path/"evidence")
    class Response:
        ok=True;status_code=200
        def json(self):return {"id":"gen-offline","choices":[{"message":{"content":"{}"}}],
                               "usage":{"cost":0.091516,"prompt_tokens":100,"completion_tokens":200}}
    ledger.original_post=lambda *_args,**_kwargs: Response()
    response=ledger.post("https://openrouter.ai/api/v1/chat/completions",
        json={"model":"anthropic/claude-sonnet-5.5","messages":[]})
    assert response.ok
    assert ledger.spent==Decimal("0.091516")
    assert ledger.posts==1
    assert ledger.summary()["provider_confirmed_cost_usd"]=="0.091516"


def test_v4_full_pipeline_offline_synthetic_routing_only(tmp_path,monkeypatch):
    f2=json.loads(F2.read_text(encoding="utf-8"))
    spine_result={
        "status":"v4_gate_accept_model_reviewed","v4_version":"V4",
        "gate":f2["gate"],"episode_spine":f2["episode_spine"],
        "approved_premise":f2["approved_premise"],
        "projection":f2["projection"],
        "usage_rollup":f2["source_usage_rollup"],
    }
    monkeypatch.setattr("src.v4_full_pipeline.verify_frozen_lane",
        lambda _profile:{"verified_files":52,"runtime_revision":"AGE18-V4-DERIVED-LOGISTICS-v1"})
    order=[]
    story="The Platform That Arrived Empty\nMara brought the log."
    turkish="Boş Gelen Peron\nMara kayıt defterini getirdi."
    def mock_dispatch(*,trigger_path,out_dir):
        source=json.loads(trigger_path.read_text())
        name=source["stage"]
        order.append(name)
        results={
            "SPINE":spine_result,
            "WRITER":{"status":"writer_generated","story":story,
                      "deterministic_checks":{"non_empty":True,"title_present":True}},
            "AUTHORITY_GATE":{"status":"clean","story":story,
                      "next_stage":"TRANSLATION","pipeline_usage_rollup":{"calls":[]}},
            "TRANSLATION":{"status":"semantic_guard_clean","next_stage":"FIDELITY",
                      "accepted_english_master":story,"turkish_delivery":turkish},
            "FIDELITY":{"status":"clean","next_stage":"FINALIZE",
                      "publication_ready":True,"accepted_english_master":story,
                      "turkish_delivery":turkish},
            "FINALIZE":{"status":"publication_ready","publication_ready":True,
                      "english_word_count":7,"turkish_word_count":6,
                      "product_path_cost_usd":0},
        }
        result=copy.deepcopy(results[name])
        write_json(out_dir/"result.json",result)
        return {"result_status":result["status"]}
    out=run(case_manifest=CASE,out_dir=tmp_path/"output",
            paid_authorized=True,stage_dispatch=mock_dispatch)
    assert out["status"]=="EN_TR_STORY_COMPLETE_UNPUBLISHED"
    assert order==["SPINE","WRITER","AUTHORITY_GATE","TRANSLATION","FIDELITY","FINALIZE"]
    assert out["world_state_commits"]==0
    assert out["human_approval_fabricated"] is False
    assert (tmp_path/"output"/"summary.json").is_file()


def test_v4_grant_never_reuses_v3_once_claim():
    grant={
        "schema":"lumi.v4.one-case-full-en-tr-once.v1",
        "authorized":True,"stage":"FULL_EN_TR",
        "case_id":"age18.closed-platform.mystery.stress-01",
        "case_manifest":"data/specifications/story_lab/four_genre_v3_inputs/closed_platform_case_manifest_v4.json",
        "runtime_revision":"AGE18-V4-DERIVED-LOGISTICS-v1",
        "observed_spend_stop_usd":"2.00","maximum_provider_posts":12,
        "client_output_token_limit":None,
        "human_review_fabrication":False,"no_manual_repairs":True,
        "no_world_commit":True,"no_publication":True,
        "reference":"user approved 2026-10-15: build V4 then replay Mara story through complete EN-TR line",
        "grant_id":"V4FULLMARA2026101501","approved_code_sha":"a"*40,
    }
    validate(grant)
    grant["schema"]="lumi.v3-four-spine-uncapped-paid-once.v1"
    with pytest.raises(V4PaidStop):
        validate(grant)
