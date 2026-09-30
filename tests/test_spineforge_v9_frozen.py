from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v7_contract import StructuralFrameV1
from src.spineforge_v9_case_manifest import load_spineforge_v9_case
from src.spineforge_v9_structured_call import (
    SONNET_STRICT_SCHEMA_MAX_BYTES,
    build_provider_transport_schema,
    schema_size_bytes,
    validate_required_properties,
)


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v9_path_aware_schema_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v9_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v9_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v9.json")


def test_v9_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v9"
    assert result["verified_files"] == 29


def test_v9_frozen_profile_records_path_aware_guard() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    policy = profile["strict_transport_policy"]
    assert policy["path_aware_schema_sanitizer"] is True
    assert policy["required_subset_properties_preflight"] is True
    assert policy["provider_strict_schema"] is True
    assert policy["strict_parse_retry"] == 0


def test_v9_frozen_frame_transport_contains_required_title_property() -> None:
    schema = build_provider_transport_schema(
        StructuralFrameV1.model_json_schema(by_alias=True)
    )
    validate_required_properties(schema)
    assert "title" in schema["required"]
    assert "title" in schema["properties"]
    assert schema["properties"]["title"] == {"type": "string"}
    assert schema_size_bytes(schema) < SONNET_STRICT_SCHEMA_MAX_BYTES


def test_v9_case_zero_spend_without_paid_trigger_before_authorization() -> None:
    case = load_spineforge_v9_case(CASE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case.status in {"ZERO_COST_QUALIFICATION", "READY_FOR_ATTEMPT_1"}
    assert ledger["v9_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()
