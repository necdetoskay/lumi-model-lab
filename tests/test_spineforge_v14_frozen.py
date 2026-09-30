from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v14_targeted_semantic_repair_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v14_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v14_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v14.json")


def test_v14_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-TARGETED-REPAIR-FROZEN-v14"
    assert result["verified_files"] == 27


def test_v14_frozen_profile_is_repair_only():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    assert profile["runtime_id"] == "spineforge.contextpack.v14.repair"
    assert runtime["repair_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["reaudit_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["max_calls_per_attempt"] == 2
    assert runtime["architect_recall"] is False
    assert runtime["automatic_repair_loop_enabled"] is False
    assert runtime["writer_authorized"] is False
    assert runtime["source_evidence"] == (
        "experiments/results/spineforge-v12/36752663853/result.json"
    )


def test_v14_zero_spend_and_no_paid_trigger_after_freeze():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case["status"] in {"ZERO_COST_QUALIFICATION", "READY_FOR_ATTEMPT_1"}
    assert ledger["v14_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()


def test_v14_freeze_locks_source_evidence_and_case():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    paths = {row["path"] for row in profile["runtime_freeze"]["files"]}
    assert "experiments/results/spineforge-v12/36752663853/result.json" in paths
    assert "data/specifications/story_lab/spineforge_v14_age18_forbidden_cartographer_case_v1.json" in paths
    assert "prompts/spineforge_targeted_semantic_repair_v14.md" in paths
    assert "prompts/spineforge_single_owner_auditor_v11.md" in paths
