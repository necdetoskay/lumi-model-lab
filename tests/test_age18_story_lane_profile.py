from __future__ import annotations

import json
from pathlib import Path

LANE=Path("data/specifications/story_lab/age18_story_lane_profile_v1.json")
FINAL=Path("data/specifications/story_lab/age18_cross_age_final_delivery_v1.json")


def test_age18_lane_is_single_case_qualified_not_universal() -> None:
    lane=json.loads(LANE.read_text())
    assert lane["status"]=="SINGLE_CASE_QUALIFIED"
    assert lane["scope"]["exact_age"]==18
    assert lane["scope"]["narrative_family"]=="ADVENTURE"
    assert lane["hard_rules"]["do_not_reuse_for_other_exact_ages_without_qualification"] is True
    assert lane["hard_rules"]["do_not_claim_all_age18_narrative_families_are_qualified"] is True
    assert lane["promotion_requirements"]["minimum_additional_independent_age18_cases"]==3


def test_lane_metrics_match_final_evidence() -> None:
    lane=json.loads(LANE.read_text())
    final=json.loads(FINAL.read_text())
    ev=lane["qualification_evidence"]
    assert final["publication_ready"] is True
    assert ev["product_path_api_calls"]==final["api_calls"]==6
    assert ev["product_path_tokens"]==final["product_path_tokens"]==84747
    assert ev["product_path_cost_usd"]==final["product_path_cost_usd"]==0.17766185
    assert ev["product_path_latency_seconds"]==final["product_path_latency_seconds"]==426.802


def test_lane_uses_deterministic_hard_guards_and_conditional_sol() -> None:
    lane=json.loads(LANE.read_text())
    stages={row["stage"]:row for row in lane["pipeline"]}
    assert stages["HARD_AUTHORITY_GUARDS"]["model_call"] is False
    assert stages["TRANSLATION_SEMANTIC_GUARDS"]["model_call"] is False
    assert stages["BOUNDED_REPAIR_IF_REQUIRED"]["policy"]=="confirmed-local-defects-only"
    assert stages["FIDELITY_GRAY_AREA"]["policy"]=="semantic-gray-area-only"


def test_lane_separates_product_cost_from_research_spend() -> None:
    lane=json.loads(LANE.read_text())
    spend=lane["qualification_spend"]
    assert spend["accepted_product_path_api_calls"]==6
    assert spend["accepted_product_path_tokens"]==84747
    assert spend["accepted_product_path_cost_usd"]==0.17766185
    assert spend["all_paid_attempts_api_calls"]==10
    assert spend["all_paid_attempts_tokens"]==142255
    assert spend["all_paid_attempts_cost_usd"]==0.27549495
    assert spend["debug_and_qualification_overhead_cost_usd"]==0.09783310
    assert spend["debug_and_qualification_overhead_tokens"]==57508
