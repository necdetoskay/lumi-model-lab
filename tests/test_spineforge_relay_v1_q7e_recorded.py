import json
import shutil
from pathlib import Path

import pytest

from src.spineforge_relay_v1_q7e_evidence import verify_q7e

ROOT = Path("evidence/spineforge-relay/SFR-V1-Q7E-PLAN-COVERAGE-20261007")


def test_recorded_q7e_replays_to_terminal_state_without_inference():
    result = verify_q7e(ROOT)
    assert result["status"] == "OFFLINE_REPLAY_PASS"
    assert result["accepted_scenes"] == ["SC05", "SC06"]
    assert result["final_revision"] == 6
    assert result["next_spine_beat"] is None
    assert result["provider_calls"] == 4
    assert result["rewrite_count"] == 0


@pytest.mark.parametrize("defect", ["cost", "coverage", "predecessor"])
def test_recorded_q7e_rejects_corrupted_evidence(tmp_path, defect):
    copied = tmp_path / "run"
    shutil.copytree(ROOT, copied)
    if defect == "cost":
        path = copied / "SC05-1-writer-ledger.json"
        data = json.loads(path.read_text())
        data["cost_usd"] += 0.01
    else:
        path = copied / "SC05-1-guard-request.json"
        data = json.loads(path.read_text())
        payload = json.loads(data["messages"][1]["content"])
        if defect == "coverage":
            payload["plan_coverage_contract"]["obligations"].pop()
        else:
            payload["previous_accepted_scene"]["artifact"]["prose"] += " Invented."
        data["messages"][1]["content"] = json.dumps(payload)
    path.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match="Saved Relay evidence mismatch"):
        verify_q7e(copied)
