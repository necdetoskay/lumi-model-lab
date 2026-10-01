from __future__ import annotations

import json
from pathlib import Path

from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v19_obligations import load_qualification_cases
from src.spineforge_v19_transport import schema_size_bytes


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v19_narrative_spine_frozen.json")
TRIGGER = Path("experiments/triggers/spineforge-v19.json")


def test_v19_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-NARRATIVE-SPINE-FROZEN-v19"
    assert result["verified_files"] == 23


def test_v19_freeze_locks_single_owner_topology_and_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    product = profile["product_contract"]
    paid = profile["paid_boundary_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v19.narrative-spine-single-owner"
    assert profile["runtime_freeze"]["runtime_source_commit"] == "41ab5c5a43b4465207fa76c29fdcb073399c1566"
    assert runtime["architect_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["product_gate_model"] == "openai/gpt-5.6-luna"
    assert runtime["max_model_calls_per_case"] == 2
    assert runtime["automatic_retry_enabled"] is False
    assert runtime["automatic_repair_enabled"] is False
    assert runtime["writer_authorized"] is False

    assert product["legacy_universal_phase_taxonomy_required"] is False
    assert product["architect_provider_strict_json_schema"] is False
    assert product["architect_schema_size_bytes"] == schema_size_bytes(
        NarrativeSpineV1.model_json_schema(by_alias=True)
    )
    assert product["gate_provider_strict_json_schema"] is True
    assert product["gate_schema_size_bytes"] == schema_size_bytes(
        SpineProductGateV19.model_json_schema(by_alias=True)
    )
    assert product["gate_schema_size_bytes"] < product["strict_schema_max_bytes"]

    assert paid["explicit_user_authorization_required_before_first_paid_case"] is True
    assert paid["no_automatic_paid_retry"] is True
    assert paid["no_writer_call_inside_spineforge"] is True
    assert paid["no_translation_call_inside_spineforge"] is True
    assert paid["no_state_commit_inside_spineforge"] is True
    assert not TRIGGER.exists()


def test_v19_freeze_has_six_frozen_context_bound_cases_and_zero_spend():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    cases = load_qualification_cases().cases
    state = profile["qualification_state"]

    assert len(cases) == 6
    assert all(case.context_fixture_status == "FROZEN" for case in cases)
    assert all(case.context_fixture_ref for case in cases)
    assert profile["qualification"]["all_context_fixtures_frozen"] is True
    assert profile["qualification"]["human_review_required"] is True

    assert state == {
        "paid_authorized": False,
        "paid_api_calls": 0,
        "confirmed_cost_usd": 0,
        "writer_authorized": False,
    }
