from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v8_case_manifest import load_spineforge_v8_case


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v8_durable_evidence_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v8_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v8_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v8.json")


def test_v8_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v8"
    assert result["verified_files"] == 29


def test_v8_freeze_reuses_v7_generation_topology_and_hardens_evidence_only() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert profile["runtime"]["generation_runtime"] == "src/spineforge_v7.py"
    assert profile["runtime"]["generation_topology_identical_to_v7"] is True
    policy = profile["evidence_policy"]
    assert policy["compact_actions_log_summary_required"] is True
    assert policy["full_repo_evidence_required"] is True
    assert policy["artifact_upload"] == "best_effort_only"
    assert policy["artifact_quota_may_not_destroy_primary_evidence"] is True


def test_v8_case_ready_zero_spend_and_without_paid_trigger() -> None:
    case = load_spineforge_v8_case(CASE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case.status == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v8_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
