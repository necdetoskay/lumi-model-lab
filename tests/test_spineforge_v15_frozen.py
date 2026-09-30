from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v15_convergence_repair_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v15_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v15_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v15.json")


def test_v15_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONVERGENCE-REPAIR-FROZEN-v15"
    assert result["verified_files"] == 27


def test_v15_frozen_profile_locks_convergence_only_scope():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    repair = profile["repair_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v15.repair"
    assert runtime["source_evidence"] == "experiments/results/spineforge-v14/36755567557/result.json"
    assert runtime["repair_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["reaudit_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["max_calls_per_attempt"] == 2
    assert runtime["architect_recall"] is False
    assert runtime["automatic_repair_loop_enabled"] is False
    assert runtime["writer_authorized"] is False

    assert repair["erased_road_geometry_forbidden"] is True
    assert repair["maren_arrival_staging_required"] is True
    assert repair["replicate_outcome_contingent_required"] is True
    assert repair["divergent_branch_climax_and_tag_required"] is True
    assert repair["targeted_not_regenerative"] is True


def test_v15_ready_case_zero_spend_and_no_trigger():
    case = json.loads(CASE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    assert case["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v15_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
