"""Safety regression for paid four Spine attempts; no provider network."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from experiments import v3_four_spines_single_grant as mod


def grant():
    return {
        "schema":mod.GRANT_SCHEMA,
        "authorized":True,
        "stage":"SPINE_ONLY",
        "models":list(mod.SPINE_MODELS),
        "frozen_v3_sha":mod.FROZEN_V3_SHA,
        "case_order":list(mod.ORDER),
        "total_ceiling_usd":"2.00",
        "per_case_ceiling_usd":"0.50",
        "maximum_provider_posts":8,
        "no_auto_retry":True,
        "writer_authorized":False,
        "human_spine_approval":False,
        "reference":"user explicit approval 2026-10-15: four Spine attempts, total 2 USD",
        "grant_id":"V3FOURSPINE-20261015-001",
        "approved_run_commit_sha":"a"*40,
    }


def test_exact_owner_grant_accepted_offline():
    mod._paid_grant(grant())


@pytest.mark.parametrize("field,value",[
    ("total_ceiling_usd","3.00"),
    ("per_case_ceiling_usd","0.75"),
    ("maximum_provider_posts",9),
    ("no_auto_retry",False),
    ("writer_authorized",True),
    ("human_spine_approval",True),
    ("stage","WRITER"),
    ("approved_run_commit_sha","unknown"),
    ("authorized",False),
    ("reference","synthetic unit test authorizes payments"),
])
def test_invalid_grants_block_before_model(field,value):
    g=grant();g[field]=value
    with pytest.raises(mod.SafetyStop):
        mod._paid_grant(g)


def test_case_order_and_model_swap_block():
    a=grant()
    a["case_order"][0],a["case_order"][1]=a["case_order"][1],a["case_order"][0]
    with pytest.raises(mod.SafetyStop):
        mod._paid_grant(a)
    b=grant();b["models"]=["anthropic/claude-sonnet-5.5","other-model"]
    with pytest.raises(mod.SafetyStop):
        mod._paid_grant(b)


def test_missing_key_blocks_even_with_structurally_valid_grant(tmp_path,monkeypatch):
    g=grant();p=tmp_path/"grant.json";p.write_text(json.dumps(g))
    monkeypatch.delenv("OPENROUTER_API_KEY",raising=False)
    # Stub source check, to prove zero network happens before missing API key stop.
    with patch.object(mod,"_check_source",return_value=[]),patch.object(mod,"SingleAttemptSpineGuard") as guard:
        with pytest.raises(mod.SafetyStop,match="PROVIDER_KEY_MISSING"):
            mod.run(grant_path=p,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"evidence")
        guard.assert_not_called()
    assert not (tmp_path/"claims").exists()


def test_once_claim_refuses_replay_any_output_path(tmp_path):
    g=grant()
    d=tmp_path/"claims"
    mod._claim_once(d,g)
    with pytest.raises(FileExistsError):
        mod._claim_once(d,g)
    assert len(list(d.glob("*.json")))==1


def test_no_side_effect_for_invalid_authorization(tmp_path,monkeypatch):
    g=grant();g["authorized"]=False
    p=tmp_path/"grant.json";p.write_text(json.dumps(g))
    with patch.object(mod,"_check_source") as source:
        with pytest.raises(mod.SafetyStop,match="MISSING_EXPLICIT_BATCH_AUTHORIZATION"):
            mod.run(grant_path=p,claim_dir=tmp_path/"claims",evidence_dir=tmp_path/"evidence")
    source.assert_not_called()


def test_four_real_manifest_targets_have_distinct_spines_and_no_preapproval():
    matrix=json.loads(mod.MATRIX.read_text())
    assert len(matrix["cases"])==4
    identities=set()
    for c in matrix["cases"]:
        slug=c["case_id"].split(".")[1].replace("-","_")
        path=mod.ROOT/f"{slug}_case_manifest_v1.json"
        m=json.loads(path.read_text())
        assert m["human_spine_approval"] is False
        assert m["paid_spine_authorized"] is False
        assert m["inputs"]["spine"]==c["input_files"]["saga_spine"]
        identities.add(m["inputs"]["spine"])
    assert len(identities)==4
