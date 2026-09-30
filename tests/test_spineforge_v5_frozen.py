from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v5_case_manifest import load_spineforge_v5_case
from src.spineforge_v5_stage import run as run_stage

PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v5_creative_blueprint_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v5_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v5_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v5.json")


def test_v5_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v5"
    assert result["verified_files"] == 24


def test_v5_case_is_ready_but_paid_trigger_does_not_exist() -> None:
    case = load_spineforge_v5_case(CASE)
    ledger = json.loads(LEDGER.read_text())
    assert case.status == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v5_actual_spend"]["api_calls"] == 0
    assert ledger["v5_actual_spend"]["total_tokens"] == 0
    assert ledger["v5_actual_spend"]["cost_usd"] == 0
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()


def test_v5_runtime_profile_freezes_blueprint_ownership_boundary() -> None:
    profile = json.loads(PROFILE.read_text())
    assert profile["runtime"]["creative_product_schema"] == "spineforge-creative-blueprint.v2"
    assert profile["runtime"]["structural_product_schema"] == "spineforge-structural-assembly.v1"
    assert profile["runtime"]["strict_episode_spine_schema"] == "episode-spine.v2"
    assert profile["runtime"]["creative_architect_model"] == "aion-labs/aion-3.5-mini"
    assert profile["runtime"]["structural_compiler_model"] == "anthropic/claude-sonnet-5.5"
    assert profile["runtime"]["product_gate_model"] == "openai/gpt-5.6-luna"
    assert profile["paid_boundary_policy"]["no_writer_call_inside_spineforge"] is True


def test_v5_stage_rejects_unapproved_trigger_before_runtime(tmp_path: Path) -> None:
    trigger = tmp_path / "trigger.json"
    trigger.write_text(json.dumps({
        "schema_version": "spineforge-v5-trigger.v1",
        "scope": "SPINEFORGE_V5_ATTEMPT",
        "paid_authorized": False,
        "case_manifest": str(CASE),
        "attempt_index": 1,
    }))
    with pytest.raises(RuntimeError, match="not explicitly authorized"):
        run_stage(trigger_path=trigger, out_dir=tmp_path / "out")
