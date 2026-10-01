from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v10_1_case_manifest import load_spineforge_v10_1_case


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v10_1_beat_set_parity_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v10_1_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v10_1_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v10-1.json")


def test_v10_1_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v10.1"
    assert result["verified_files"] == 30


def test_v10_1_frozen_profile_records_beat_set_and_owner_guards() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    beat = profile["beat_set_policy"]
    owner = profile["failure_owner_policy"]
    assert beat["final_required_phases_at_beats_boundary"] is True
    assert set(beat["required_phases"]) == {
        "HOOK", "COMPLICATION", "REVERSAL", "DECISION", "CLIMAX", "PAYOFF"
    }
    assert beat["failure_before_resolution_if_missing"] is True
    assert owner["earliest_owning_partition"] is True
    assert owner["unclassified_owner_stops_without_revision_retry"] is True


def test_v10_1_case_zero_spend_and_without_paid_trigger() -> None:
    case = load_spineforge_v10_1_case(CASE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case.status in {"ZERO_COST_QUALIFICATION", "READY_FOR_ATTEMPT_1"}
    assert ledger["v10_1_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
