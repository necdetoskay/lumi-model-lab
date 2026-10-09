import json
import shutil
from pathlib import Path
import pytest
from scripts.spineforge_production_plan_failure_audit import verify_plan_failure

ROOT = Path("evidence/spineforge-relay/SFR-V1-Q15-COMPACT-ROBOT-20261009")
AUTH = Path("evidence/spineforge-relay/SFR-V1-Q15-COMPACT-PREFLIGHT-20261009/closed-authority.json")


def test_q15_is_two_complete_invalid_plans_without_scene_or_state_change():
    proof = verify_plan_failure(ROOT, AUTH)
    assert proof["cost_usd"] == "0.1550770" and proof["total_tokens"] == 26539
    assert proof["no_third_attempt"] and not proof["story_generated"]


@pytest.mark.parametrize("target", ["decision", "structural", "response", "source", "third", "settlement"])
def test_q15_cannot_be_repaired_or_reclassified(tmp_path, target):
    root = tmp_path/"run";shutil.copytree(ROOT,root)
    auth = tmp_path/"authority.json";shutil.copyfile(AUTH,auth)
    if target == "source": (root/"frozen-sources/src/spineforge_production_compact.py").write_text("changed")
    elif target == "third": (root/"plan-3-planner-request.json").write_text("{}")
    else:
        path = auth if target == "settlement" else root/{"decision":"result.json", "structural":"plan-2-structural.json", "response":"plan-2-planner-response.json"}[target]
        data=json.loads(path.read_text(encoding="utf8"))
        if target == "decision": data["status"]="ACCEPT"
        elif target == "structural": data["message"]="changed"
        elif target == "response": data["usage"]["cost"]=0
        else: data["reservations"]["whole-chain"]["actual_calls"]=1
        path.write_text(json.dumps(data),encoding="utf8")
    with pytest.raises(RuntimeError,match="Saved plan failure mismatch"):
        verify_plan_failure(root,auth)
