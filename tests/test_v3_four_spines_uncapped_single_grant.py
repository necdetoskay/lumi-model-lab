"""Fail-closed offline qualification for the new no-output-token-cap V3 Spine runner."""
import json
import subprocess
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest

from experiments import v3_four_spines_uncapped_single_grant as lane
from src.v3_single_attempt_guard import SafetyStop


def _grant(sha="a"*40):
    return {
        "schema":lane.GRANT_SCHEMA,
        "authorized":True,"stage":"SPINE_ONLY",
        "models":list(lane.SPINE_MODELS),
        "frozen_v3_sha":lane.FROZEN_V3_SHA,
        "runtime_revision":"AGE18-V3-UNCAPPED-v1",
        "case_order":list(lane.ORDER),
        "total_ceiling_usd":"2.00","per_case_ceiling_usd":"0.50",
        "maximum_provider_posts":8,"no_auto_retry":True,
        "writer_authorized":False,"human_spine_approval":False,
        "reference":"user 2026-10-15 continue four Spine trials on uncapped V3 under prior 2 USD envelope",
        "grant_id":"V3UNCAPPED4SPINES20261015001",
        "approved_run_commit_sha":sha,
    }


def test_new_revision_grant_is_accepted():
    lane._paid_grant(_grant())


@pytest.mark.parametrize("field,value",[
    ("runtime_revision","AGE18-FROZEN-v1"),
    ("stage","WRITER"),("no_auto_retry",False),
    ("total_ceiling_usd","3.00"),("per_case_ceiling_usd","0.75"),
    ("writer_authorized",True),("human_spine_approval",True),
    ("authorized",False),("maximum_provider_posts",9),
    ("grant_id","too"),
])
def test_invalid_auth_fails_before_post(field,value):
    g=_grant();g[field]=value
    with pytest.raises(SafetyStop):
        lane._paid_grant(g)


def test_once_claim_consumed_even_if_crash(tmp_path):
    g=_grant(); lane._claim_once(tmp_path/"claims",g)
    with pytest.raises(FileExistsError):
        lane._claim_once(tmp_path/"claims",g)


def test_frozen_43_file_revision_valid():
    from src.frozen_lane_verify import verify_frozen_lane
    r=verify_frozen_lane(lane.PROFILE)
    assert r["runtime_revision"]=="AGE18-V3-UNCAPPED-v1" and r["verified_files"]==43


def test_error_accounts_provider_spend_and_no_next_case(tmp_path,monkeypatch):
    grant_path=tmp_path/"grant.json"
    grant_path.write_text(json.dumps(_grant()))
    case=lane.ROOT/"closed_platform_case_manifest_v1.json"
    monkeypatch.setattr(lane,"_check_source",lambda g:[("closed_platform",case),("orbit_rescue",case)])
    monkeypatch.setenv("OPENROUTER_API_KEY","OFFLINE-FAKE-DO-NOT-POST")
    calls=[]
    class MockGuard:
        def __init__(self,evidence_dir,max_cost_usd):
            self.spent=Decimal("0.141996")
            self.calls=1
        @contextmanager
        def installed(self):
            yield self
    def fake_stage(*,trigger_path,out_dir):
        calls.append(str(out_dir))
        raise ValueError("STRUCTURED_JSON_RESPONSE_TRUNCATED")
    monkeypatch.setattr(lane,"SingleAttemptSpineGuard",MockGuard)
    monkeypatch.setattr(lane,"frozen_stage_run",fake_stage)
    dest=tmp_path/"evidence"
    with pytest.raises(ValueError,match="TRUNCATED"):
        lane.run(grant_path=grant_path,claim_dir=tmp_path/"claims",evidence_dir=dest)
    assert len(calls)==1
    receipt=json.loads((dest/"closed_platform"/"cost-receipt.json").read_text())
    assert receipt["aggregate_cost_usd"]=="0.141996"
    assert receipt["model_posts"]==1
    assert receipt["writer_dispatched"] is False
    stop=json.loads((dest/"stopped.json").read_text())
    assert stop["aggregate_confirmed_usd"]=="0.141996"


def test_old_claim_schema_not_accepted():
    g=_grant(); g["schema"]="lumi.v3-four-spine-paid-once.v1"
    with pytest.raises(SafetyStop):
        lane._paid_grant(g)
