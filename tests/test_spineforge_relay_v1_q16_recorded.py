import json
import shutil
from pathlib import Path
import pytest
from scripts.spineforge_production_plan_failure_audit import verify_plan_failure

ROOT=Path("evidence/spineforge-relay/SFR-V1-Q16-COMPACT-V2-ROBOT-20261009")
AUTH=Path("evidence/spineforge-relay/SFR-V1-Q16-COMPACT-V2-PREFLIGHT-20261009/closed-authority.json")


def test_q16_is_bounded_rejection_not_a_generated_story():
    p=verify_plan_failure(ROOT,AUTH)
    assert p["cost_usd"]=="0.1744970" and p["total_tokens"]==28820
    assert p["no_third_attempt"] and not p["story_generated"] and not p["state_advanced"]


@pytest.mark.parametrize("target",["decision","structural","response","source","third","settlement"])
def test_q16_evidence_cannot_be_reclassified(tmp_path,target):
    root=tmp_path/"run";shutil.copytree(ROOT,root)
    auth=tmp_path/"authority.json";shutil.copyfile(AUTH,auth)
    if target=="source": (root/"frozen-sources/src/spineforge_production_compact_v2.py").write_text("changed")
    elif target=="third": (root/"plan-3-planner-request.json").write_text("{}")
    else:
        path=auth if target=="settlement" else root/{"decision":"result.json","structural":"plan-2-structural.json","response":"plan-2-planner-response.json"}[target]
        data=json.loads(path.read_text(encoding="utf8"))
        if target=="decision": data["status"]="ACCEPT"
        elif target=="structural": data["message"]="changed"
        elif target=="response": data["usage"]["cost"]=0
        else: data["reservations"]["whole-chain"]["actual_calls"]=1
        path.write_text(json.dumps(data),encoding="utf8")
    with pytest.raises(RuntimeError,match="Saved plan failure mismatch"):
        verify_plan_failure(root,auth)
