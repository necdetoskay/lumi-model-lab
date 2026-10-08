"""Actual Q7E evidence replay and corrupt-record checks; zero provider calls."""
import json
import shutil
from pathlib import Path
import pytest
from src.spineforge_relay_v1_q7e_evidence import verify_q7e

ROOT = Path("evidence/spineforge-relay/SFR-V1-Q7E-PLAN-COVERAGE-20261007-local")


def test_recorded_plan_coverage_chain_replays_without_rewrite():
    result = verify_q7e(ROOT)
    assert result["status"] == "OFFLINE_REPLAY_PASS"
    assert result["provider_calls"] == 4 and result["rewrite_count"] == 0
    assert result["final_revision"] == 6 and result["next_spine_beat"] is None
    assert result["cost_usd"] == 0.15638


@pytest.mark.parametrize("defect", ["removed_goal", "provider_cost", "predecessor", "request_quote"])
def test_corrupt_goal_evidence_is_rejected(tmp_path, defect):
    copied = tmp_path/"recorded"
    shutil.copytree(ROOT, copied)
    if defect == "removed_goal":
        path = copied/"SC05-coverage-contract.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["obligations"].pop()
    elif defect == "provider_cost":
        path = copied/"SC05-1-writer-response.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["usage"]["cost"] += 0.01
    elif defect == "predecessor":
        path = copied/"SC06-1-writer-request.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        inner = json.loads(payload["messages"][1]["content"])
        inner["previous_accepted_scene"]["artifact"]["prose"] = "unbound"
        payload["messages"][1]["content"] = json.dumps(inner)
    else:
        path = copied/"SC05-1-guard-text.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        inner = json.loads(payload["text"])
        next(r for r in inner["event_evidence"] if r["action"] == "ASK_FOR_HELP")["exact_text"] = "invented request"
        payload["text"] = json.dumps(inner)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="evidence mismatch"):
        verify_q7e(copied)
