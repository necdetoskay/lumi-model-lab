from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v12_deterministic_normalization_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v12_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v12_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v12.json")


def test_v12_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-DETERMINISTIC-NORMALIZATION-FROZEN-v12"
    assert result["verified_files"] == 23


def test_v12_frozen_profile_locks_single_normalization_path():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert profile["runtime_id"] == "spineforge.contextpack.v12"
    assert profile["runtime"]["spine_architect_model"] == "anthropic/claude-sonnet-5.5"
    assert profile["runtime"]["spine_auditor_model"] == "anthropic/claude-sonnet-5.5"
    assert profile["runtime"]["max_calls_per_attempt"] == 2
    policy = profile["mechanical_normalization_policy"]
    assert policy["allowed_paths"] == ["logistics_plan.location_sequence"]
    assert policy["semantic_change_forbidden"] is True
    assert policy["idempotence_required"] is True


def test_v12_still_zero_spend_and_untriggered_after_freeze():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case["status"] in {"ZERO_COST_QUALIFICATION", "READY_FOR_ATTEMPT_1"}
    assert ledger["v12_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
