"""Saved live evidence replay and corruption checks; no provider calls."""
import json
import shutil
from pathlib import Path
import pytest
from src.spineforge_relay_v1_q7d_evidence import verify_q7d

ROOT = Path("evidence/spineforge-relay/SFR-V1-Q7D-SPATIAL-20261007")


def test_recorded_spatial_chain_replays_to_terminal_state():
    result = verify_q7d(ROOT)
    assert result["status"] == "OFFLINE_REPLAY_PASS"
    assert result["provider_calls"] == 10 and result["rewrite_count"] == 0
    assert result["final_revision"] == 6 and result["next_spine_beat"] is None
    assert result["cost_usd"] == 0.320349


@pytest.mark.parametrize("defect", ["removed_transition", "provider_cost", "predecessor", "anchor"])
def test_corrupt_spatial_evidence_is_rejected(tmp_path, defect):
    copied = tmp_path/"recorded"
    shutil.copytree(ROOT, copied)
    if defect == "removed_transition":
        path = copied/"SC04-spatial-contract.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["operations"].pop(0)
    elif defect == "provider_cost":
        path = copied/"SC02-1-writer-response.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["usage"]["cost"] += 0.01
    elif defect == "predecessor":
        path = copied/"SC03-1-writer-request.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        inner = json.loads(payload["messages"][1]["content"])
        inner["previous_accepted_scene"]["artifact"]["prose"] = "unbound"
        payload["messages"][1]["content"] = json.dumps(inner)
    else:
        path = copied/"SC04-1-guard-text.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        inner = json.loads(payload["text"])
        inner["event_evidence"][-1]["exact_text"] = "invented quote"
        payload["text"] = json.dumps(inner)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="evidence mismatch"):
        verify_q7d(copied)
