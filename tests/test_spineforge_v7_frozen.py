from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v7_case_manifest import load_spineforge_v7_case
from src.spineforge_v7_contract import StructuralBeatsV1, StructuralFrameV1, StructuralResolutionV1
from src.spineforge_v7_structured_call import (
    SONNET_STRICT_SCHEMA_MAX_BYTES,
    build_provider_transport_schema,
    schema_size_bytes,
)

PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v7_partitioned_strict_frozen.json")
CASE = Path("data/specifications/story_lab/spineforge_v7_age18_forbidden_cartographer_case_v1.json")
LEDGER = Path("data/specifications/story_lab/spineforge_v7_age18_forbidden_cartographer_cost_ledger_v1.json")
TRIGGER = Path("experiments/triggers/spineforge-v7.json")


def test_v7_frozen_runtime_hashes_verify() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v7"
    assert result["verified_files"] == 28


def test_v7_case_ready_zero_spend_and_no_paid_trigger() -> None:
    case = load_spineforge_v7_case(CASE)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert case.status == "READY_FOR_ATTEMPT_1"
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["v7_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not TRIGGER.exists()


def test_v7_frozen_profile_records_partitioned_strict_boundary() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    policy = profile["strict_transport_policy"]
    assert policy["sonnet_provider_strict_schema"] is True
    assert policy["luna_provider_strict_schema"] is True
    assert policy["provider_require_parameters"] is True
    assert policy["sonnet_transport_schema_budget_bytes"] == 4096
    assert profile["runtime"]["durable_checkpoint_after_every_completed_call"] is True
    assert profile["paid_boundary_policy"]["evidence_archive_does_not_push_branch"] is True


def test_v7_transport_schemas_remain_under_frozen_budget() -> None:
    sizes = {
        "structural_frame": schema_size_bytes(
            build_provider_transport_schema(StructuralFrameV1.model_json_schema(by_alias=True))
        ),
        "structural_beats": schema_size_bytes(
            build_provider_transport_schema(StructuralBeatsV1.model_json_schema(by_alias=True))
        ),
        "structural_resolution": schema_size_bytes(
            build_provider_transport_schema(StructuralResolutionV1.model_json_schema(by_alias=True))
        ),
    }
    assert sizes == {"structural_frame": 1431, "structural_beats": 856, "structural_resolution": 2891}
    assert max(sizes.values()) < SONNET_STRICT_SCHEMA_MAX_BYTES


def test_v1_through_v7_frozen_profiles_verify() -> None:
    profiles = [
        ("data/specifications/story_lab/spineforge_runtime_profile_v1_frozen.json", 25),
        ("data/specifications/story_lab/spineforge_runtime_profile_v2_context_frozen.json", 26),
        ("data/specifications/story_lab/spineforge_runtime_profile_v3_contract_recovery_frozen.json", 26),
        ("data/specifications/story_lab/spineforge_runtime_profile_v4_normalizer_integrity_frozen.json", 26),
        ("data/specifications/story_lab/spineforge_runtime_profile_v5_creative_blueprint_frozen.json", 24),
        ("data/specifications/story_lab/spineforge_runtime_profile_v6_blueprint_strict_frozen.json", 28),
        ("data/specifications/story_lab/spineforge_runtime_profile_v7_partitioned_strict_frozen.json", 28),
    ]
    for path, count in profiles:
        result = verify_spineforge_runtime(Path(path))
        assert result["verified"] is True
        assert result["verified_files"] == count


def test_v7_runtime_has_no_case_specific_recovery() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    forbidden = ["Leyra", "Ashen Gate", "Greyfen", "forbidden_cartographer"]
    for row in profile["runtime_freeze"]["files"]:
        path = Path(row["path"])
        if path.suffix.lower() not in {".py", ".md", ".yml", ".yaml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into frozen v7 runtime {path}"
