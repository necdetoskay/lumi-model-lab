import json
import shutil
from pathlib import Path
import pytest
from scripts.spineforge_production_truncation_audit import verify_truncation

ROOT = Path("evidence/spineforge-relay/SFR-V1-Q14-GENERIC-ROBOT-20261009")
AUTH = Path("evidence/spineforge-relay/SFR-V1-Q14-GENERIC-PREFLIGHT-20261009/closed-authority.json")


def test_q14_truncation_is_settled_rejection_without_story():
    proof = verify_truncation(ROOT, AUTH)
    assert proof["cost_usd"] == "0.1362735"
    assert proof["total_tokens"] == 18510 and proof["output_tokens"] == 12000
    assert proof["reservation_status"] == "SETTLED"
    assert not proof["story_generated"] and not proof["state_advanced"]


@pytest.mark.parametrize("target", ["decision", "finish", "usage", "text", "source", "authority"])
def test_q14_cannot_be_reclassified_or_patched(tmp_path, target):
    root = tmp_path / "run"
    shutil.copytree(ROOT, root)
    authority = tmp_path / "authority.json"
    shutil.copyfile(AUTH, authority)
    if target == "source":
        (root / "frozen-sources/src/spineforge_production_pipeline.py").write_text("changed")
    else:
        path = authority if target == "authority" else root / {"decision": "result.json", "finish": "plan-1-planner-response.json", "usage": "plan-1-planner-response.json", "text": "plan-1-planner-text.json"}[target]
        value = json.loads(path.read_text(encoding="utf8"))
        if target == "decision": value["status"] = "ACCEPT"
        elif target == "finish": value["choices"][0]["finish_reason"] = "stop"
        elif target == "usage": value["usage"]["cost"] = 0
        elif target == "text": value["text"] = "{}"
        else: value["reservations"]["whole-chain"]["actual_cost_usd"] = "0"
        path.write_text(json.dumps(value), encoding="utf8")
    with pytest.raises(RuntimeError, match="Saved truncation evidence mismatch"):
        verify_truncation(root, authority)
