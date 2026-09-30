from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v18_strict_audit_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v18_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v18_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v18.json")


def test_v18_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-STRICT-AUDIT-TRANSPORT-FROZEN-v18"
    assert result["verified_files"] == 24


def test_v18_frozen_profile_locks_small_strict_schema_and_single_call():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    transport = profile["transport_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v18.strict-audit"
    assert runtime["source_evidence"] == "experiments/results/spineforge-v16/36760550050/result.json"
    assert runtime["audit_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["max_calls_per_attempt"] == 1
    assert runtime["architect_recall"] is False
    assert runtime["repair_recall"] is False
    assert runtime["writer_authorized"] is False

    assert transport["provider_strict_json_schema"] is True
    assert transport["strict_schema_size_bytes"] == 2270
    assert transport["strict_schema_size_bytes"] < transport["strict_schema_max_bytes"]
    assert transport["all_18_dimension_keys_required"] is True
    assert transport["provider_require_parameters"] is True


def test_v18_ready_zero_spend_and_no_paid_trigger_after_freeze():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    assert case["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v18_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
