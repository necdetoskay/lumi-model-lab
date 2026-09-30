from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v8_evidence_summary import build_summary
from src.spineforge_v8_stage import run as run_stage


V7_PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v7_partitioned_strict_frozen.json")


def test_v8_summary_preserves_exact_failure_and_usage_without_raw_blueprint() -> None:
    result = {
        "status": "structural_frame_contract_rejected",
        "attempt_index": 1,
        "context_pack_id": "pack",
        "context_fingerprint": "f" * 64,
        "failure": {
            "stage": "spineforge_structural_frame",
            "type": "ValidationError",
            "message": "preserved_creative_strengths: List should have at least 2 items",
        },
        "pipeline_usage_rollup": {
            "totals": {
                "api_calls": 2,
                "input_tokens": 1000,
                "output_tokens": 500,
                "reasoning_tokens": 200,
                "cached_tokens": 100,
                "total_tokens": 1500,
                "cost_usd": 0.0123,
                "latency_seconds": 12.4,
            },
            "calls": [{"stage": "aion"}, {"stage": "frame"}],
        },
        "stage_evidence": {
            "spineforge_creative_architect": {"raw_payload": {"secret": "not-for-log"}},
            "spineforge_structural_frame": {"raw_payload": {"secret": "not-for-log"}},
        },
        "revision_feedback_candidate": {
            "source_status": "structural_frame_contract_rejected",
            "retry_stage": "STRUCTURAL_FRAME",
            "must_change": ["fix the exact validation defect"],
            "preserved_blueprint": {"story": "full blueprint must not be printed"},
            "preserved_frame": None,
            "preserved_beats": None,
        },
        "human_review": {"writer_authorized": False},
    }
    summary = build_summary(result)
    assert summary["failure"]["message"].startswith("preserved_creative_strengths")
    assert summary["usage"]["api_calls"] == 2
    assert summary["usage"]["cost_usd"] == 0.0123
    assert summary["revision_feedback"]["retry_stage"] == "STRUCTURAL_FRAME"
    assert summary["revision_feedback"]["preserved_blueprint_sha256"]
    rendered = json.dumps(summary)
    assert "full blueprint must not be printed" not in rendered
    assert "not-for-log" not in rendered
    assert summary["writer_authorized"] is False


def test_v8_unapproved_trigger_stops_before_case_load(tmp_path: Path) -> None:
    trigger = tmp_path / "trigger.json"
    trigger.write_text(json.dumps({
        "schema_version": "spineforge-v8-trigger.v1",
        "scope": "SPINEFORGE_V8_ATTEMPT",
        "paid_authorized": False,
        "case_manifest": "missing.json",
        "attempt_index": 1,
    }))
    with pytest.raises(RuntimeError, match="not explicitly authorized"):
        run_stage(trigger_path=trigger, out_dir=tmp_path / "out")


def test_v8_reuses_v7_generation_runtime_without_model_logic_fork() -> None:
    text = Path("src/spineforge_v8_stage.py").read_text(encoding="utf-8")
    assert "from src.spineforge_v7 import run as run_spineforge" in text
    for token in ("call_structured_json_once", "AION_MODEL", "SONNET_MODEL", "LUNA_MODEL"):
        assert token not in text


def test_v7_frozen_runtime_remains_verifiable() -> None:
    result = verify_spineforge_runtime(V7_PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v7"
    assert result["verified_files"] == 28
