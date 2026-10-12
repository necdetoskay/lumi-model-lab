import json
import shutil
from pathlib import Path

import pytest

from src.spineforge_relay_v1_evidence import verify_chain
from src.spineforge_relay_v1_runner import build_chain
from src.spineforge_relay_v1_q6d import request_for

ROOT = Path("evidence/spineforge-relay/SFR-V1-Q8B-REPEATABILITY-20261007")


def replay(root, name="q8-greenhouse-notebook"):
    fixture = Path("tests/fixtures/spineforge_relay_v1/" + name.replace("-", "_") + ".json")
    _, _, route, start, rows, final = build_chain(fixture)
    return verify_chain(root=root, start=start, rows=rows, route=route, expected_final=final, request_factory=request_for)


@pytest.mark.parametrize("name", ["q8-greenhouse-notebook", "q8-hill-kite"])
def test_real_q8b_saved_calls_replay_without_inference(name):
    result = replay(ROOT / name, name)
    assert result["status"] == "OFFLINE_REPLAY_PASS"
    assert result["provider_calls"] == 4
    assert result["rewrite_count"] == 0
    assert result["final_revision"] == 2
    assert result["next_spine_beat"] is None


@pytest.mark.parametrize("corruption", ["state", "prose", "tokens", "fingerprint", "bundle", "validation", "aggregate_cost"])
def test_saved_evidence_corruption_fails_closed(tmp_path, corruption):
    root = tmp_path / "story"
    shutil.copytree(ROOT / "q8-greenhouse-notebook", root)
    paths = {
        "state": "A1-1-writer-request.json", "prose": "A1-1-writer-text.json",
        "tokens": "A1-1-writer-ledger.json", "fingerprint": "A1-1-writer-ledger.json",
        "bundle": "A1-accepted.json", "validation": "A1-1-validation.json",
        "aggregate_cost": "result.json",
    }
    path = root / paths[corruption]
    value = json.loads(path.read_text(encoding="utf-8"))
    if corruption == "state":
        payload = json.loads(value["messages"][1]["content"])
        payload["story_state"]["revision"] += 1
        value["messages"][1]["content"] = json.dumps(payload)
    if corruption == "prose": value["text"] += " An invented ending."
    if corruption == "tokens": value["input_tokens"] += 1
    if corruption == "fingerprint": value["request_sha256"] = "0" * 64
    if corruption == "bundle": value["state_after"]["revision"] += 1
    if corruption == "validation": value["semantic_guard_used"] = False
    if corruption == "aggregate_cost": value["known_cost_usd"] = 0
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="evidence mismatch"):
        replay(root)


def test_q7b_mechanical_acceptance_does_not_override_editorial_rejection():
    from src.spineforge_relay_v1_q7b import build_chain as q7b_chain
    root = Path("evidence/spineforge-relay/SFR-V1-Q7B-REVIEW-20261007")
    _, _, route, start, rows, final = q7b_chain()
    mechanical = verify_chain(root=root, start=start, rows=rows, route=route, expected_final=final, request_factory=request_for)
    review = json.loads((root / "review.json").read_text(encoding="utf-8"))
    assert mechanical["status"] == "OFFLINE_REPLAY_PASS"
    assert review["qualification_status"] == "REJECT_EGRESS_ROUTE_CONTINUITY_GAP"
    prose = json.loads((root / "SC06-accepted.json").read_text(encoding="utf-8"))["artifact"]["prose"]
    assert review["blocking_findings"][0]["exact_text"] in prose
