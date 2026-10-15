"""V4.2 source-bound paid safety regression; no network or provider charges."""
from decimal import Decimal
from pathlib import Path
import pytest

from src.v4_2_paid_guard import V4PaidStop, V4ProviderLedger, MAX_PROVIDER_CALLS
from experiments.v4_2_one_case_full_run import validate, SCHEMA, MAX_POSTS

MODEL="anthropic/claude-sonnet-5.5"
URL="https://openrouter.ai/api/v1/chat/completions"


def _grant():
    return {
        "schema":SCHEMA,"authorized":True,"stage":"FULL_EN_TR",
        "case_id":"age18.closed-platform.mystery.stress-01",
        "case_manifest":"data/specifications/story_lab/four_genre_v3_inputs/closed_platform_case_manifest_v4_2.json",
        "runtime_revision":"AGE18-V4-ITERATIVE-QUALITY-REPAIR-v1",
        "observed_spend_stop_usd":"2.00",
        "maximum_provider_posts":24,
        "client_output_token_limit":None,
        "human_review_fabrication":False,
        "no_manual_repairs":True,
        "no_world_commit":True,
        "no_publication":True,
        "reference":"user 2026-10-15 continue: V4.2 full Mara story with three bounded English repair rounds, observed 2 USD stop",
        "grant_id":"V42MARAOFFLINEVALID01",
        "approved_code_sha":"a"*40,
    }


def test_v42_separate_grant_and_24_call_protection():
    assert MAX_PROVIDER_CALLS==MAX_POSTS==24
    validate(_grant())


@pytest.mark.parametrize("field,value",[
    ("schema","lumi.v4-1.one-case-full-en-tr-once.v1"),
    ("runtime_revision","AGE18-V4-SEMANTIC-REPLAN-REPAIR-v1"),
    ("case_manifest","closed_platform_case_manifest_v4_1.json"),
    ("maximum_provider_posts",25),
    ("observed_spend_stop_usd","4.00"),
    ("client_output_token_limit",12000),
    ("no_manual_repairs",False),
    ("no_world_commit",False),
    ("no_publication",False),
])
def test_stale_or_expanded_grant_rejected(field,value):
    data=_grant()
    data[field]=value
    with pytest.raises(V4PaidStop):
        validate(data)


@pytest.mark.parametrize("ceiling",["max_tokens","max_completion_tokens","max_output_tokens"])
def test_actual_provider_http_never_gets_client_token_ceiling(tmp_path,ceiling):
    g=V4ProviderLedger(evidence_dir=tmp_path/"guard")
    calls=[]
    g.original_post=lambda *args,**kwargs:calls.append(kwargs)
    with pytest.raises(V4PaidStop,match="OUTPUT_TOKEN_CEILING"):
        g.post(URL,json={"model":MODEL,ceiling:12000})
    assert not calls
    assert g.posts==0


def test_post_observes_charged_cost_before_json_validation(tmp_path):
    g=V4ProviderLedger(evidence_dir=tmp_path/"guard")
    class FakeResponse:
        ok=True
        status_code=200
        def json(self):
            return {"id":"gen-test","usage":{"cost":0.08125,"prompt_tokens":501,"completion_tokens":1800},
                    "choices":[{"message":{"content":"invalid-but-billed"}}]}
    g.original_post=lambda *args,**kwargs:FakeResponse()
    g.post(URL,json={"model":MODEL,"messages":[]})
    assert g.spent==Decimal("0.08125")
    assert g.posts==1
    assert (tmp_path/"guard"/"004-provider_observed.json").exists()


def test_observed_overspend_blocks_further_posts(tmp_path):
    g=V4ProviderLedger(evidence_dir=tmp_path/"guard",max_reported_usd=Decimal("0.02"))
    class FakeResponse:
        ok=True
        status_code=200
        def json(self):
            return {"id":"gen-test","usage":{"cost":0.03},"choices":[]}
    g.original_post=lambda *args,**kwargs:FakeResponse()
    with pytest.raises(V4PaidStop,match="SPEND_OBSERVED_OVER_PLANNING_LIMIT"):
        g.post(URL,json={"model":MODEL,"messages":[]})
    assert g.spent==Decimal("0.03") and g.posts==1
