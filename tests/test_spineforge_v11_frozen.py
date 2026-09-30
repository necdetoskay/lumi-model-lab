from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v11_case_manifest import load_spineforge_v11_case


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v11_single_owner_sonnet_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v11_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v11_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v11.json")


def test_v11_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-SINGLE-OWNER-FROZEN-v11"
    assert result["verified_files"] == 22


def test_v11_frozen_profile_records_single_owner_roleplay_policy() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    quality = profile["story_quality_policy"]
    transport = profile["transport_policy"]
    assert runtime["spine_architect_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["spine_auditor_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["max_calls_per_attempt"] == 2
    assert runtime["automatic_repair_enabled"] is False
    assert quality["roleplay_first"] is True
    assert quality["active_protagonist_required"] is True
    assert quality["sceneable_beats_required"] is True
    assert transport["provider_strict_json_schema"] is False
    assert transport["json_object_transport"] is True
    assert transport["local_episode_spine_validation"] is True


def test_v11_zero_spend_and_no_paid_trigger_before_authorization() -> None:
    case = load_spineforge_v11_case(CASE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case.status in {"ZERO_COST_QUALIFICATION", "READY_FOR_ATTEMPT_1"}
    assert ledger["v11_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()


def test_v11_paid_workflow_requires_explicit_trigger_path() -> None:
    workflow = Path(".github/workflows/spineforge-v11.yml").read_text(encoding="utf-8")
    assert "experiments/triggers/spineforge-v11.json" in workflow
    assert "workflow_dispatch" not in workflow
