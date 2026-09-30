from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v16_evidence_logic_repair_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v16_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v16_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v16.json")


def test_v16_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-EVIDENCE-LOGIC-REPAIR-FROZEN-v16"
    assert result["verified_files"] == 28


def test_v16_frozen_profile_locks_partial_repair_and_complete_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    repair = profile["repair_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v16.repair"
    assert runtime["source_evidence"] == "experiments/results/spineforge-v15/36757835721/result.json"
    assert runtime["repair_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["reaudit_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["max_calls_per_attempt"] == 2
    assert runtime["architect_recall"] is False
    assert runtime["automatic_repair_loop_enabled"] is False
    assert runtime["writer_authorized"] is False

    assert repair["partial_source_audit_repair_only"] is True
    assert repair["partial_source_audit_accept_forbidden"] is True
    assert repair["final_reaudit_all_18_dimensions_required"] is True
    assert repair["semantic_repair_by_application_forbidden"] is True


def test_v16_ready_zero_spend_and_untriggered_after_freeze():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    assert case["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v16_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
