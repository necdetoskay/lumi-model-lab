from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v17_audit_only_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v17_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v17_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v17.json")


def test_v17_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-AUDIT-ONLY-RECOVERY-FROZEN-v17"
    assert result["verified_files"] == 25


def test_v17_frozen_profile_locks_one_call_audit_only_topology():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    audit = profile["audit_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v17.audit"
    assert runtime["source_evidence"] == "experiments/results/spineforge-v16/36760550050/result.json"
    assert runtime["audit_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["audit_max_tokens"] == 8000
    assert runtime["max_calls_per_attempt"] == 1
    assert runtime["repair_called"] is False
    assert runtime["architect_recall"] is False
    assert runtime["writer_authorized"] is False

    assert audit["all_18_dimensions_required"] is True
    assert audit["freshness_required"] is True
    assert audit["compact_output_required"] is True
    assert audit["structured_failure_usage_checkpoint_required"] is True
    assert audit["accept_requires_complete_typed_audit"] is True


def test_v17_ready_zero_spend_and_untriggered_after_freeze():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    assert case["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v17_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
