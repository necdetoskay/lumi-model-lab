from __future__ import annotations

import copy
import json
from pathlib import Path

from src.spine_context_pack_v1 import write_spine_context_pack
from src.spineforge_v13 import run


RESULT = Path("experiments/results/spineforge-v12/36752663853/result.json")
SOURCE = Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")


def test_v13_exact_v12_outputs_become_typed_repair_without_new_inference(tmp_path: Path):
    evidence = json.loads(RESULT.read_text(encoding="utf-8"))
    architect_raw = copy.deepcopy(evidence["architect_raw"])
    audit_raw = copy.deepcopy(evidence["audit_raw"])
    pack_path = tmp_path / "pack.json"
    write_spine_context_pack(source_path=SOURCE, out_path=pack_path)

    outputs = [architect_raw, audit_raw]
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        raw = outputs[len(calls) - 1]
        body = {
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "cost": 0.007,
            }
        }
        request = {"response_format": {"type": "json_object"}}
        return raw, body, request, []

    result = run(
        context_pack_path=pack_path,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert len(calls) == 2
    assert result["status"] == "repair_required"
    assert result["audit"]["decision"] == "REPAIR"
    assert len(result["audit"]["blocking_defects"]) == 6
    assert len(result["repair_candidate"]["targets"]) == 5
    assert result["audit_contract_normalization"]["changed"] is True
    assert result["automatic_repair_enabled"] is False
    assert result["writer_authorized"] is False
