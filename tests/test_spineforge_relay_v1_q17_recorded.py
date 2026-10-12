import json
import shutil
from pathlib import Path
import pytest
from scripts.spineforge_production_review_failure_audit import verify_review_failure

ROOT=Path("evidence/spineforge-relay/SFR-V1-Q17-COMPACT-V3-ROBOT-20261009")
AUTH=Path("evidence/spineforge-relay/SFR-V1-Q17-COMPACT-V3-PREFLIGHT-20261009/closed-authority.json")

def test_q17_stopped_after_structural_pass_and_invalid_review():
    p=verify_review_failure(ROOT,AUTH)
    assert p["cost_usd"]=="0.149573" and p["total_tokens"]==41761
    assert p["invalid_source_pointers"]==6 and p["plan_rewrite_dispatches"]==0
    assert not p["story_generated"] and not p["state_advanced"]

@pytest.mark.parametrize("target",["decision","structural","response","source","repair","settlement"])
def test_q17_cannot_be_resumed_or_reclassified(tmp_path,target):
    root=tmp_path/"run";shutil.copytree(ROOT,root)
    auth=tmp_path/"authority.json";shutil.copyfile(AUTH,auth)
    if target=="source": (root/"frozen-sources/src/spineforge_production_pipeline.py").write_text("changed")
    elif target=="repair": (root/"plan-2-planner-request.json").write_text("{}")
    else:
        path=auth if target=="settlement" else root/{"decision":"result.json","structural":"plan-1-structural.json","response":"plan-1-plan_guard-response.json"}[target]
        data=json.loads(path.read_text(encoding="utf8"))
        if target=="decision": data["status"]="ACCEPT"
        elif target=="structural": data["status"]="REJECTED_DESIGN"
        elif target=="response": data["usage"]["cost"]=0
        else: data["reservations"]["whole-chain"]["actual_calls"]=1
        path.write_text(json.dumps(data),encoding="utf8")
    with pytest.raises(RuntimeError,match="Saved review failure mismatch"):
        verify_review_failure(root,auth)
