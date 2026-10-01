from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_obligations import load_qualification_cases


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json")


def test_v20_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-STORY-FIRST-FROZEN-v20.2"
    assert result["verified_files"] == 25


def test_v20_freeze_locks_story_first_topology_and_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    product = profile["product_contract"]
    paid = profile["paid_boundary_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v20.story-first-single-owner"
    assert profile["runtime_freeze"]["runtime_source_commit"] == "1f2eec63413ab15f00dcf57768e6583d8aee824b"
    assert runtime["architect_model"] == "anthropic/claude-sonnet-5.5"
    assert runtime["product_gate_model"] == "openai/gpt-5.6-luna"
    assert runtime["max_model_calls_per_case"] == 2
    assert runtime["automatic_retry_enabled"] is False
    assert runtime["automatic_repair_enabled"] is False
    assert runtime["writer_authorized"] is False

    assert product["story_first"] is True
    assert product["procedural_adventure_reject_signal"] is True
    assert product["post_decision_single_path_required"] is True

    assert paid["explicit_user_authorization_required_before_paid_case"] is True
    assert paid["no_automatic_paid_retry"] is True
    assert paid["repair_requires_separate_explicit_authorization"] is True
    assert paid["replan_requires_separate_explicit_authorization"] is True
    assert paid["no_writer_call_inside_spineforge"] is True


def test_v20_freeze_has_one_frozen_age12_island_case_and_zero_spend():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    case_set = load_qualification_cases()
    assert len(case_set.cases) == 1
    case = case_set.cases[0]
    assert case.context_fixture_status == "FROZEN"
    assert case.case_id == "spineforge.v20.age12.adventure-exploration.island.01"
    assert case.obligations.exact_age == 12
    assert case.obligations.story_family == "ADVENTURE_EXPLORATION"

    q = profile["qualification"]
    assert q["context_fingerprint"] == "090ae8343daa2b24e95923ee9e9dc11356664baed9a79c4ff95fd0207b834233"
    assert q["target_words_min"] == 1600
    assert q["target_words_max"] == 2500

    state = profile["qualification_state"]
    assert state["paid_authorized"] is False
    assert state["paid_api_calls"] == 2
    assert state["confirmed_cost_usd"] == 0.06831485
    assert state["writer_authorized"] is False


def test_v20_2_freeze_locks_local_repair_source_scope_and_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    repair = profile["repair_state"]
    paid = profile["paid_boundary_policy"]

    assert repair["source_run_id"] == 36908095596
    assert repair["source_spine_hash"] == "4ae3ef5af8316234999a7fc432feeab5e4169e4b440de5bab08cb86f15f74d9b"
    assert repair["source_gate_decision"] == "REPAIR"
    assert repair["finding_count"] == 1
    assert repair["repairability"] == "LOCAL"
    assert repair["paid_repair_authorized"] is False
    assert repair["automatic_repair_enabled"] is False
    assert repair["writer_authorized"] is False

    assert paid["repair_diff_guard_required"] is True
    assert paid["repair_regate_required"] is True
    assert paid["repair_authorization_marker"] == "PAID-V20-AGE12-ISLAND-REPAIR1"
