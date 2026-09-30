from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v10_case_manifest import load_spineforge_v10_case
from src.spineforge_v10_contract import StructuralResolutionV10


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v10_partition_contract_parity_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v10_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v10_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v10.json")


def test_v10_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v10"
    assert result["verified_files"] == 30


def test_v10_frozen_profile_records_partition_contract_parity() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    policy = profile["partition_contract_policy"]
    assert policy["semantic_parity_with_episode_spine"] is True
    assert policy["episode_role_literal_at_frame_boundary"] is True
    assert policy["reversal_certainty_literal_at_resolution_boundary"] is True
    assert policy["persistent_outcome_type_literal_at_resolution_boundary"] is True
    assert policy["decision_branch_key_pattern_at_resolution_boundary"] is True


def test_v10_resolution_schema_exposes_final_certainty_literal() -> None:
    schema = StructuralResolutionV10.model_json_schema(by_alias=True)
    certainty = schema["$defs"]["ReversalEvidenceDraftV10"]["properties"]["certainty"]
    assert certainty["enum"] == ["OBSERVED", "INFERRED", "HYPOTHESIS"]


def test_v10_case_zero_spend_without_paid_trigger() -> None:
    case = load_spineforge_v10_case(CASE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case.status in {"ZERO_COST_QUALIFICATION", "READY_FOR_ATTEMPT_1"}
    assert ledger["v10_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
