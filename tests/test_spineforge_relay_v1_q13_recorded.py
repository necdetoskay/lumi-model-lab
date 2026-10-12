import json
import shutil
from pathlib import Path
import pytest
from scripts.spineforge_production_failure_audit import verify_failure

ROOT=Path("evidence/spineforge-relay/SFR-V1-Q13-GENERIC-ROBOT-20261009")
AUTH=Path("evidence/spineforge-relay/SFR-V1-Q13-GENERIC-PREFLIGHT-20261009/closed-authority.json")
COMMIT="715a471eb300c72e1f44ea8035a3e848006c9621"


def test_recorded_q13_is_unknown_usage_failure_not_a_zero_cost_story():
    proof=verify_failure(ROOT,AUTH,COMMIT)
    assert proof["attempted_provider_dispatches"]==1 and proof["complete_provider_responses"]==0
    assert proof["actual_cost_usd"] is None and proof["usage_complete"] is False
    assert proof["authority_status"]=="CLOSED" and proof["reservation_status"]=="UNCERTAIN"
    assert proof["recorded_json_instruction_present"] is False
    assert proof["original_http_cause_known"] is False and proof["story_generated"] is False

@pytest.mark.parametrize("target",["decision","usage","request","source"])
def test_recorded_failure_cannot_be_reclassified_or_repaired(tmp_path,target):
    root=tmp_path/"run";shutil.copytree(ROOT,root)
    if target=="source":
        path=root/"frozen-sources/src/spineforge_production_pipeline.py"
        path.write_text("changed")
    else:
        path=root/("plan-1-planner-request.json" if target=="request" else "result.json")
        data=json.loads(path.read_text())
        if target=="decision":data["status"]="ACCEPT"
        elif target=="usage":data["usage_complete"]=True
        else:data["messages"][0]["content"] += " Return JSON."
        path.write_text(json.dumps(data))
    with pytest.raises(RuntimeError,match="Saved failure evidence mismatch"):
        verify_failure(root,AUTH,COMMIT)
