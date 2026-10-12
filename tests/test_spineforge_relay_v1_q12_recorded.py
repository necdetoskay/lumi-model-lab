import json
import shutil
from pathlib import Path
import pytest
from scripts.spineforge_relay_story_replay import verify_story

ROOT=Path("evidence/spineforge-relay/SFR-V1-Q12-SOURCE-SPAN-MOSAIC-20261008")
FIXTURE=Path("tests/fixtures/spineforge_relay_v1/q12_span_mosaic_chain.json")

def test_recorded_q12_acceptance_and_closed_budget():
    proof=verify_story(ROOT,FIXTURE)
    assert proof["recorded_decision"]=="ACCEPT"
    assert proof["accepted_scenes"]==[f"S{i:02}" for i in range(1,7)]
    assert proof["final_revision"]==6 and proof["next_spine_beat"] is None
    assert proof["provider_calls"]==12 and proof["rewrite_count"]==0
    assert proof["cost_usd"]==.3322835 and proof["total_tokens"]==126873
    closed=json.loads(Path("evidence/spineforge-relay/SFR-V1-Q12-PREFLIGHT-20261008/closed-authority.json").read_text())
    assert closed["status"]=="CLOSED"
    assert closed["reservations"]["complete-story"]["actual_calls"]==12
    assert float(closed["reservations"]["complete-story"]["actual_cost_usd"])==proof["cost_usd"]

@pytest.mark.parametrize("target",["resolved_quote","source_table","state","cost"])
def test_recorded_q12_tampering_fails_replay(tmp_path,target):
    root=tmp_path/"records"
    shutil.copytree(ROOT,root)
    if target=="resolved_quote":
        path=root/"S04-1-resolved-guard.json"
        data=json.loads(path.read_text(encoding="utf8"))
        data["event_evidence"][0]["exact_text"]="fabricated quote"
    elif target=="source_table":
        path=root/"S04-1-guard-request.json"
        data=json.loads(path.read_text(encoding="utf8"))
        payload=json.loads(data["messages"][1]["content"])
        payload["source_span_table"]["spans"][0]["text"]="forged source"
        data["messages"][1]["content"]=json.dumps(payload)
    elif target=="state":
        path=root/"result.json"
        data=json.loads(path.read_text());data["state_advanced_to_revision"]=7
    else:
        path=root/"S04-1-guard-ledger.json"
        data=json.loads(path.read_text());data["cost_usd"]=0
    path.write_text(json.dumps(data),encoding="utf8")
    with pytest.raises(RuntimeError,match="Saved Relay evidence mismatch"):
        verify_story(root,FIXTURE)
