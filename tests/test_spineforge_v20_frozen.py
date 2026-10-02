from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_obligations import load_qualification_cases


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json")


def test_v20_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-STORY-FIRST-FROZEN-v20.26"
    assert result["verified_files"] == 61


def test_v20_freeze_locks_story_first_topology_and_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    product = profile["product_contract"]
    paid = profile["paid_boundary_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v20.story-first-single-owner"
    assert profile["runtime_freeze"]["runtime_source_commit"] == "4ab89f69b"
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


def test_v20_freeze_has_one_frozen_age12_island_case_and_tracked_paid_state():
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
    assert state["paid_api_calls"] == 17
    assert state["confirmed_cost_usd"] == 0.5895394
    assert state["writer_product_authorized"] is True
    assert state["paid_writer_execution_authorized"] is False


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


def test_v20_4_freeze_locks_human_approval_and_bounded_writer_retry_without_paid_execution():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    review = profile["human_review_state"]
    writer = profile["writer_state"]
    paid = profile["paid_boundary_policy"]

    assert review["verdict"] == "APPROVE"
    assert review["approval_id"] == "63d4b9734dc4966cac672481dc8404d02679ceea9444554a8931842a21f0d112"
    assert review["spine_hash"] == "f9c5bed93448d6c56787466ae583dfcee06d0f856641d9c3901136f142bffae6"
    assert review["context_fingerprint"] == "090ae8343daa2b24e95923ee9e9dc11356664baed9a79c4ff95fd0207b834233"
    assert review["writer_handoff_ready"] is True

    assert writer["status"] == "WRITER_PRODUCT_FROZEN_AWAITING_STORY_AUDIT"
    assert writer["model"] == "aion-labs/aion-3.5-mini"
    assert writer["target_words_min"] == 1600
    assert writer["target_words_max"] == 2500
    assert writer["paid_writer_execution_authorized"] is False
    assert writer["automatic_retry_enabled"] is False
    assert writer["editor_authorized"] is False
    assert writer["judge_authorized"] is False
    assert writer["repair_authorized"] is False
    assert writer["translation_authorized"] is False
    assert writer["state_commit_authorized"] is False

    assert paid["writer_authorization_marker"] == "PAID-V20-AGE12-ISLAND-WRITER3"
    assert paid["writer_requires_exact_approval_id"] is True
    assert paid["writer_requires_exact_spine_hash"] is True
    assert paid["writer_requires_exact_context_fingerprint"] is True
    assert paid["writer_one_call_only"] is True
    assert paid["writer_downstream_calls_forbidden"] is True


def test_v20_5_writer_retry_freeze_records_failed_attempts_and_bounded_transport():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    writer = profile["writer_state"]
    paid = profile["paid_boundary_policy"]

    attempt = writer["attempt1"]
    assert attempt["run_id"] == 36955873689
    assert attempt["status"] == "writer_provider_failure"
    assert attempt["finish_reason"] == "length"
    assert attempt["output_tokens"] == 32768
    assert attempt["reasoning_tokens"] == 33220
    assert attempt["cost_usd"] == 0.052983
    assert attempt["story_text_returned"] is False
    assert attempt["automatic_retry_executed"] is False

    attempt2 = writer["attempt2"]
    assert attempt2["run_id"] == 36964320381
    assert attempt2["status"] == "writer_provider_failure"
    assert attempt2["http_status"] == 400
    assert attempt2["failure_reason"] == "reasoning_mandatory_endpoint_rejected_effort_none"
    assert attempt2["input_tokens"] == 0
    assert attempt2["output_tokens"] == 0
    assert attempt2["reasoning_tokens"] == 0
    assert attempt2["cost_usd"] == 0.0
    assert attempt2["story_text_returned"] is False
    assert attempt2["automatic_retry_executed"] is False

    attempt3 = writer["attempt3"]
    assert attempt3["run_id"] == 36965340665
    assert attempt3["status"] == "writer_generated"
    assert attempt3["word_count"] == 2324
    assert attempt3["length_pass"] is True
    assert attempt3["input_tokens"] == 10154
    assert attempt3["output_tokens"] == 3935
    assert attempt3["reasoning_tokens"] == 1020
    assert attempt3["cost_usd"] == 0.0126168
    assert attempt3["story_text_returned"] is True
    assert attempt3["automatic_retry_executed"] is False
    assert writer["human_story_review_required"] is False

    assert writer["next_attempt_index"] is None
    assert writer["request_class"] == "spineforge_v20_story_writer"
    assert writer["reasoning_effort"] == "low"
    assert writer["max_tokens"] == 7000
    assert writer["paid_writer_execution_authorized"] is False

    assert paid["writer1_marker_consumed"] is True
    assert paid["writer2_marker_consumed"] is True
    assert paid["writer3_marker_consumed"] is True
    assert paid["writer_retry_requires_explicit_authorization"] is True
    assert paid["writer_request_class"] == "spineforge_v20_story_writer"
    assert paid["writer_reasoning_effort"] == "low"
    assert paid["writer_max_tokens"] == 7000


def test_v20_7_freeze_locks_writer_artifact_boundary_before_story_audit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    writer = profile["writer_state"]
    audit = profile["stage5_story_audit"]

    assert writer["status"] == "WRITER_PRODUCT_FROZEN_AWAITING_STORY_AUDIT"
    assert writer["story_artifact_id"].startswith("writer-story:")
    assert writer["story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert writer["story_manifest_path"] == (
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    assert writer["next_stage"] == "STORY_AUDIT"
    assert writer["paid_story_audit_authorized"] is False
    assert writer["human_story_review_required"] is False

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["stage"] == 5
    assert audit["input_artifact_schema"] == "spineforge-v20-writer-story-artifact.v1"
    assert audit["output_artifact_schema"] == "spineforge-v20-story-audit-artifact.v1"
    assert audit["source_artifact_id"] == writer["story_artifact_id"]
    assert audit["source_story_sha256"] == writer["story_sha256"]
    assert audit["immutable_input_required"] is True
    assert audit["hash_verification_before_inference"] is True
    assert audit["source_mutation_forbidden"] is True
    assert audit["local_repair_routes_to"] == "STORY_LOCAL_REPAIR"
    assert audit["clean_routes_to"] == "ENGLISH_MASTER_SEAL"
    assert audit["structural_or_replan_routes_to"] == "STOP"
    assert audit["paid_execution_authorized"] is False


def test_v20_8_freeze_locks_stage5_dual_audit_harness_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["primary_model"] == "anthropic/claude-sonnet-5.5"
    assert audit["secondary_model"] == "openai/gpt-5.6-sol"
    assert audit["audit_calls_per_execution"] == 2
    assert audit["automatic_retry_enabled"] is False
    assert audit["prompt_path"] == "prompts/spineforge_v20_story_audit.md"
    assert audit["execution_module"] == "src/spineforge_v20_story_audit_once.py"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
    assert audit["legacy_ci_trigger_marker"] == "PAID-V20-AGE12-ISLAND-WRITER2"
    assert audit["ci_transport_job"] == "paid-age12-island-writer2"
    assert audit["paid_wrapper"] == "src/spineforge_v20_paid_story_audit_once.py"
    assert audit["authorization_consumed"] is True
    assert audit["paid_execution_authorized"] is False



def test_v20_11_freeze_records_failed_paid_story_audit_qualification():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt1 = audit["attempt1"]

    assert q["paid_api_calls"] == 17
    assert q["confirmed_cost_usd"] == 0.5895394
    assert q["last_paid_run_id"] == 36978036076
    assert q["last_result"] == "story_audit_attempt5_contract_failure_known_defect_missed"

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert attempt1["run_id"] == 36969500342
    assert attempt1["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert attempt1["known_target_recall"] == 0.0
    assert attempt1["api_calls"] == 2
    assert attempt1["input_tokens"] == 52488
    assert attempt1["output_tokens"] == 2128
    assert attempt1["reasoning_tokens"] == 818
    assert attempt1["total_tokens"] == 54616
    assert attempt1["cost_usd"] == 0.136928
    assert attempt1["source_story_mutated"] is False
    assert attempt1["repair_executed"] is False
    assert attempt1["translation_executed"] is False
    assert attempt1["state_commit_executed"] is False


def test_v20_11_paid_story_audit_qualification_report_is_deterministic_fail():
    from src.spineforge_v20_story_audit_qualification import (
        evaluate_story_audit_qualification,
    )

    result_path = Path(
        "evidence/spineforge-v20-paid-story-audit/36969500342/"
        "age12-island-v20-story-audit1-result.json"
    )
    gold_path = Path(
        "data/specifications/story_lab/"
        "spineforge_v20_story_audit_qualification_gold.json"
    )
    report = evaluate_story_audit_qualification(
        result_path=result_path,
        gold_path=gold_path,
    )
    assert report["status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert report["qualification_pass"] is False
    assert report["target_count"] == 1
    assert report["matched_target_count"] == 0
    assert report["target_recall"] == 0.0
    assert report["target_results"][0]["target_id"] == "HUMAN-LANGUAGE-001"
    assert report["target_results"][0]["matched"] is False


def test_v20_11_writer_artifact_still_verifies_after_paid_story_audit():
    from src.spineforge_v20_story_audit_artifact import (
        load_verified_writer_story_artifact,
    )

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    verified = load_verified_writer_story_artifact(manifest_path=manifest)
    assert verified["input_verified"] is True
    assert verified["manifest"]["story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert "arriving at his shoulder" in verified["story"]


def test_v20_12_story_audit_v2_requires_explicit_decision_for_every_family():
    from src.spineforge_v20_story_audit_once import _normalize_auditor_payload

    order = [
        "physical_feasibility",
        "causal_logic",
        "state_continuity",
        "epistemic_order",
        "spatial_consistency",
        "temporal_consistency",
        "response_causality",
        "closure_integrity",
        "canon_integrity",
        "language_naturalness",
        "age_suitability",
        "spine_fidelity",
        "narrative_coherence",
    ]
    evaluations = []
    for family in order:
        if family == "language_naturalness":
            evaluations.append({
                "family": family,
                "present": True,
                "severity": "minor",
                "repair_scope": "LOCAL_REPAIR",
                "span_ids": ["S005"],
                "exact_text": "arriving at his shoulder",
                "reason": "Understandable but idiomatically unnatural English.",
            })
        else:
            evaluations.append({
                "family": family,
                "present": False,
                "severity": None,
                "repair_scope": None,
                "span_ids": [],
                "exact_text": None,
                "reason": "No concrete defect in this family.",
            })

    normalized = _normalize_auditor_payload(
        raw={"evaluations": evaluations, "summary": "one local defect"}
    )
    assert len(normalized["evaluations"]) == 13
    assert normalized["findings"] == [{
        "family": "language_naturalness",
        "severity": "minor",
        "repair_scope": "LOCAL_REPAIR",
        "span_ids": ["S005"],
        "exact_text": "arriving at his shoulder",
        "reason": "Understandable but idiomatically unnatural English.",
    }]

    try:
        _normalize_auditor_payload(
            raw={"evaluations": evaluations[:-1], "summary": "missing family"}
        )
    except RuntimeError as exc:
        assert "every family exactly once" in str(exc)
    else:
        raise AssertionError("Audit v2 must reject incomplete family coverage.")



def test_v20_12_freeze_locks_story_audit_requalification_contract():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt2_paid_authorized"] is False
    assert audit["audit_contract_revision"] == "family-by-family-multi-finding-v3"
    assert audit["authority_projection"] == "compact-reveal-safe-v1"
    assert audit["prompt_revision"] == "stage5-story-audit-v3"
    assert audit["attempt1"]["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert audit["attempt1"]["known_target_recall"] == 0.0



def test_v20_13_freeze_locks_attempt2_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
    assert audit["attempt2_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["attempt1"]["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"


def _stage5_v2_eval_rows(*, defect_exact_text=None, defect_span_id=None):
    order = [
        "physical_feasibility",
        "causal_logic",
        "state_continuity",
        "epistemic_order",
        "spatial_consistency",
        "temporal_consistency",
        "response_causality",
        "closure_integrity",
        "canon_integrity",
        "language_naturalness",
        "age_suitability",
        "spine_fidelity",
        "narrative_coherence",
    ]
    rows = []
    for family in order:
        if family == "language_naturalness" and defect_exact_text is not None:
            rows.append({
                "family": family,
                "present": True,
                "severity": "minor",
                "repair_scope": "LOCAL_REPAIR",
                "span_ids": [defect_span_id],
                "exact_text": defect_exact_text,
                "reason": "Synthetic local language defect.",
            })
        else:
            rows.append({
                "family": family,
                "present": False,
                "severity": None,
                "repair_scope": None,
                "span_ids": [],
                "exact_text": None,
                "reason": "No concrete defect in this family.",
            })
    return rows


def _stage5_fake_transport(raw, *, prompt_tokens=100, completion_tokens=20, cost=0.01):
    def call(**kwargs):
        return (
            raw,
            {
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cost": cost,
                }
            },
            {
                "temperature": 0.0,
                "max_tokens": 3500,
                "reasoning": None,
                "response_format": {"type": "json_object"},
            },
            [],
        )
    return call


def test_v20_15_stage5_rebinds_wrong_span_when_exact_text_is_unique():
    from src.spineforge_v20_story_audit_once import execute_story_audit_once

    primary = {
        "evaluations": _stage5_v2_eval_rows(
            defect_exact_text="arriving at his shoulder",
            defect_span_id="S999",
        ),
        "summary": "One local language defect.",
    }
    clean = {
        "evaluations": _stage5_v2_eval_rows(),
        "summary": "Clean.",
    }
    result = execute_story_audit_once(
        api_key="not-used",
        primary_call_fn=_stage5_fake_transport(primary),
        secondary_call_fn=_stage5_fake_transport(clean),
    )
    assert result["status"] == "audit_completed"
    assert result["audit_artifact"]["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert result["audit_artifact"]["source_story_mutated"] is False
    assert len(result["locator_corrections"]) == 1
    correction = result["locator_corrections"][0]
    assert correction["exact_text"] == "arriving at his shoulder"
    assert correction["old_span_ids"] == ["S999"]
    assert correction["new_span_ids"] != ["S999"]
    assert result["audit_usage_rollup"]["totals"]["api_calls"] == 2


def test_v20_15_stage5_preserves_paid_evidence_when_exact_text_is_invented():
    from src.spineforge_v20_story_audit_once import execute_story_audit_once

    primary = {
        "evaluations": _stage5_v2_eval_rows(
            defect_exact_text="THIS TEXT DOES NOT EXIST IN THE FROZEN STORY",
            defect_span_id="S001",
        ),
        "summary": "Synthetic invalid locator.",
    }
    clean = {
        "evaluations": _stage5_v2_eval_rows(),
        "summary": "Clean.",
    }
    result = execute_story_audit_once(
        api_key="not-used",
        primary_call_fn=_stage5_fake_transport(primary, cost=0.03),
        secondary_call_fn=_stage5_fake_transport(clean, cost=0.04),
    )
    assert result["status"] == "audit_contract_failure"
    assert "resolve uniquely" in result["artifact_error"]["message"]
    assert result["source_story_mutated"] is False
    assert result["audit_usage_rollup"]["totals"]["api_calls"] == 2
    assert result["audit_usage_rollup"]["totals"]["cost_usd"] == 0.07
    assert result["primary_audit"]["findings"]
    assert result["secondary_audit"]["findings"] == []
    assert result["repair_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False



def test_v20_15_freeze_records_attempt2_post_inference_contract_failure():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt2 = audit["attempt2"]

    assert q["paid_api_calls"] == 17
    assert q["confirmed_cost_usd"] == 0.5895394
    assert q["last_paid_run_id"] == 36978036076
    assert q["last_result"] == "story_audit_attempt5_contract_failure_known_defect_missed"
    assert q["cost_reconciliation_status"] == "PARTIAL"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt2_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["locator_policy"] == "multi_span_unique_exact_text_rebind_v2"
    assert audit["failure_evidence_policy"] == "preserve_raw_audits_and_usage_v1"

    assert attempt2["run_id"] == 36970666881
    assert attempt2["status"] == "unhandled_story_audit_runtime_failure"
    assert attempt2["failure_phase"] == "post_inference_artifact_contract"
    assert attempt2["api_calls"] == 2
    assert attempt2["usage_tokens_reconciled"] is False
    assert attempt2["cost_usd_reconciled"] is False
    assert attempt2["source_story_mutated"] is False
    assert attempt2["automatic_retry_executed"] is False
    assert attempt2["repair_executed"] is False
    assert attempt2["translation_executed"] is False
    assert attempt2["state_commit_executed"] is False
    assert attempt2["audit_artifact_created"] is False


def test_v20_16_freeze_locks_attempt3_harness_not_authorized():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    harness = audit["attempt3_harness"]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt3_paid_authorized"] is False
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
    assert harness["attempt_index"] == 3
    assert harness["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT3"
    assert harness["output_result"] == "age12-island-v20-story-audit3-result.json"
    assert harness["output_envelope"] == "age12-island-v20-story-audit3-envelope.json"
    assert harness["locator_policy"] == "unique_exact_text_rebind_v1"
    assert harness["failure_evidence_policy"] == "preserve_raw_audits_and_usage_v1"
    assert harness["paid_execution_authorized"] is False



def test_v20_16_freeze_locks_attempt3_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
    assert audit["attempt3_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["attempt2"]["qualification_status"] == "UNUSABLE_EVIDENCE_ARTIFACT_VALIDATION_FAILURE"


def _stage5_v3_clean_rows():
    order = [
        "physical_feasibility",
        "causal_logic",
        "state_continuity",
        "epistemic_order",
        "spatial_consistency",
        "temporal_consistency",
        "response_causality",
        "closure_integrity",
        "canon_integrity",
        "language_naturalness",
        "age_suitability",
        "spine_fidelity",
        "narrative_coherence",
    ]
    return [
        {
            "family": family,
            "present": False,
            "findings": [],
            "reason": "No concrete defect in this family.",
        }
        for family in order
    ]


def test_v20_19_stage5_v3_allows_multiple_findings_in_same_family():
    from src.spineforge_v20_story_audit_once import _normalize_auditor_payload

    rows = _stage5_v3_clean_rows()
    language_index = next(
        i for i, row in enumerate(rows)
        if row["family"] == "language_naturalness"
    )
    rows[language_index] = {
        "family": "language_naturalness",
        "present": True,
        "findings": [
            {
                "severity": "minor",
                "repair_scope": "LOCAL_REPAIR",
                "span_ids": ["S006"],
                "exact_text": "arriving at his shoulder",
                "reason": "Idiomatic English is unnatural.",
            },
            {
                "severity": "minor",
                "repair_scope": "LOCAL_REPAIR",
                "span_ids": ["S160"],
                "exact_text": "The bridge made it to them—or rather, didn't.",
                "reason": "The inversion is awkward.",
            },
        ],
        "reason": "",
    }
    normalized = _normalize_auditor_payload(
        raw={"evaluations": rows, "summary": "two language defects"}
    )
    language_findings = [
        row for row in normalized["findings"]
        if row["family"] == "language_naturalness"
    ]
    assert len(language_findings) == 2
    assert {row["exact_text"] for row in language_findings} == {
        "arriving at his shoulder",
        "The bridge made it to them—or rather, didn't.",
    }


def test_v20_19_stage5_multi_span_locator_rebinds_unique_exact_text():
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import _repair_finding_locators

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    source = build_story_audit_source(manifest_path=manifest)
    exact = (
        "The tension released. The bridge fell away beneath him into the cloud sea, "
        "taking the rope's last anchor with it"
    )
    repaired, corrections = _repair_finding_locators(
        findings=[{
            "family": "causal_logic",
            "severity": "serious",
            "repair_scope": "STRUCTURAL_REPAIR",
            "span_ids": ["S999"],
            "exact_text": exact,
            "reason": "Synthetic locator qualification.",
        }],
        story_segments=source["story_segments"],
    )
    assert repaired[0]["span_ids"] == ["S174", "S175"]
    assert corrections[0]["old_span_ids"] == ["S999"]
    assert corrections[0]["new_span_ids"] == ["S174", "S175"]


def test_v20_19_attempt3_gold_recall_is_measurable_despite_artifact_failure():
    from src.spineforge_v20_story_audit_qualification import (
        evaluate_story_audit_qualification,
    )

    report = evaluate_story_audit_qualification(
        result_path=Path(
            "evidence/spineforge-v20-paid-story-audit/36972037743/"
            "age12-island-v20-story-audit3-result.json"
        ),
        gold_path=Path(
            "data/specifications/story_lab/"
            "spineforge_v20_story_audit_qualification_gold.json"
        ),
    )
    assert report["status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert report["qualification_pass"] is False
    assert report["target_recall"] == 0.0
    assert report["findings_source"] == "merged_findings_before_artifact"


def test_v20_19_secondary_prompt_requires_exhaustive_language_sweep():
    prompt = Path(
        "prompts/spineforge_v20_story_audit_secondary.md"
    ).read_text(encoding="utf-8")
    assert "EXHAUSTIVE line-by-line language naturalness" in prompt
    assert "Do not stop after finding one language problem" in prompt
    assert "Each family may contain MULTIPLE findings" in prompt


def test_v20_19_freeze_locks_v3_story_audit_requalification_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    reprocessed = audit["attempt3_reprocess"]

    assert q["paid_api_calls"] == 17
    assert q["confirmed_cost_usd"] == 0.5895394
    assert q["last_paid_run_id"] == 36978036076
    assert q["cost_reconciliation_status"] == "PARTIAL"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt4_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["audit_contract_revision"] == "family-by-family-multi-finding-v3"
    assert audit["prompt_revision"] == "stage5-story-audit-v3"
    assert audit["primary_prompt_path"] == "prompts/spineforge_v20_story_audit.md"
    assert audit["secondary_prompt_path"] == "prompts/spineforge_v20_story_audit_secondary.md"
    assert audit["locator_policy"] == "multi_span_unique_exact_text_rebind_v2"
    assert audit["secondary_specialization"] == (
        "exhaustive_line_by_line_language_naturalness_plus_full_13_family_audit"
    )

    assert reprocessed["status"] == "audit_reprocessed_zero_cost"
    assert reprocessed["model_calls_executed"] == 0
    assert reprocessed["decision"] == "STRUCTURAL_REPAIR_REQUIRED"
    assert reprocessed["next_stage"] == "STOP"
    assert reprocessed["finding_count"] == 11
    assert reprocessed["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert reprocessed["known_target_recall"] == 0.0


def test_v20_19_v3_contract_supports_multiple_findings_in_one_family():
    from src.spineforge_v20_story_audit_once import _normalize_auditor_payload

    order = [
        "physical_feasibility",
        "causal_logic",
        "state_continuity",
        "epistemic_order",
        "spatial_consistency",
        "temporal_consistency",
        "response_causality",
        "closure_integrity",
        "canon_integrity",
        "language_naturalness",
        "age_suitability",
        "spine_fidelity",
        "narrative_coherence",
    ]
    rows = []
    for family in order:
        if family == "language_naturalness":
            rows.append({
                "family": family,
                "present": True,
                "findings": [
                    {
                        "severity": "minor",
                        "repair_scope": "LOCAL_REPAIR",
                        "span_ids": ["S005"],
                        "exact_text": "arriving at his shoulder",
                        "reason": "Understandable but unnatural English.",
                    },
                    {
                        "severity": "minor",
                        "repair_scope": "LOCAL_REPAIR",
                        "span_ids": ["S160"],
                        "exact_text": "The bridge made it to them—or rather, didn't.",
                        "reason": "Awkward semantic reversal.",
                    },
                ],
                "reason": "",
            })
        else:
            rows.append({
                "family": family,
                "present": False,
                "findings": [],
                "reason": "No concrete defect.",
            })

    result = _normalize_auditor_payload(
        raw={"evaluations": rows, "summary": "two language findings"}
    )
    language = [
        row for row in result["findings"]
        if row["family"] == "language_naturalness"
    ]
    assert len(language) == 2
    assert {row["exact_text"] for row in language} == {
        "arriving at his shoulder",
        "The bridge made it to them—or rather, didn't.",
    }


def test_v20_19_secondary_prompt_requires_exhaustive_line_by_line_language_sweep():
    prompt = Path("prompts/spineforge_v20_story_audit_secondary.md").read_text(
        encoding="utf-8"
    )
    assert "EXHAUSTIVE line-by-line language naturalness" in prompt
    assert "Do not stop after finding one language problem" in prompt
    assert "all 13 families" in prompt
    assert "arriving at his shoulder" not in prompt


def test_v20_19_multi_sentence_exact_text_locator_is_valid_without_model_retry():
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import _repair_finding_locators

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    source = build_story_audit_source(manifest_path=manifest)
    segments = source["story_segments"]
    first = next(
        row for row in segments
        if row["text"].startswith("The tension released.")
    )
    second = segments[segments.index(first) + 1]
    exact = (
        "The tension released. The bridge fell away beneath him into the cloud sea, "
        "taking the rope's last anchor with it"
    )
    repaired, corrections = _repair_finding_locators(
        findings=[{
            "family": "causal_logic",
            "severity": "serious",
            "repair_scope": "STRUCTURAL_REPAIR",
            "span_ids": [first["id"], second["id"]],
            "exact_text": exact,
            "reason": "Synthetic multi-sentence locator qualification.",
        }],
        story_segments=segments,
    )
    assert repaired[0]["span_ids"] == [first["id"], second["id"]]
    assert corrections == []


def test_v20_19_attempt3_zero_cost_reprocess_is_deterministic_and_still_fails_human_gold():
    from src.spineforge_v20_story_audit_qualification import (
        evaluate_story_audit_qualification,
    )

    result_path = Path(
        "evidence/spineforge-v20-paid-story-audit/36972037743/"
        "age12-island-v20-story-audit3-reprocessed.json"
    )
    report_path = Path(
        "evidence/spineforge-v20-paid-story-audit/36972037743/"
        "qualification-report-reprocessed.json"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    frozen_report = json.loads(report_path.read_text(encoding="utf-8"))
    live_report = evaluate_story_audit_qualification(
        result_path=result_path,
        gold_path=Path(
            "data/specifications/story_lab/"
            "spineforge_v20_story_audit_qualification_gold.json"
        ),
    )

    assert result["status"] == "audit_reprocessed_zero_cost"
    assert result["reprocess"]["model_calls_executed"] == 0
    assert result["audit_artifact"]["decision"] == "STRUCTURAL_REPAIR_REQUIRED"
    assert result["audit_artifact"]["next_stage"] == "STOP"
    assert result["audit_usage_rollup"]["totals"]["cost_usd"] == 0.0952852
    assert live_report == frozen_report
    assert live_report["status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert live_report["target_recall"] == 0.0


def test_v20_22_freeze_records_attempt4_invalid_json_transport_failure():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    harness = audit["attempt4_harness"]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
    assert audit["attempt4_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True

    assert harness["attempt_index"] == 4
    assert harness["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT4"
    assert harness["output_result"] == "age12-island-v20-story-audit4-result.json"
    assert harness["output_envelope"] == "age12-island-v20-story-audit4-envelope.json"
    assert harness["audit_contract_revision"] == "family-by-family-multi-finding-v3"
    assert harness["primary_prompt_path"] == "prompts/spineforge_v20_story_audit.md"
    assert harness["secondary_prompt_path"] == "prompts/spineforge_v20_story_audit_secondary.md"
    assert harness["locator_policy"] == "multi_span_unique_exact_text_rebind_v2"
    assert harness["paid_execution_authorized"] is False



def test_v20_22_attempt4_failure_evidence_is_frozen_and_unreconciled():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt4 = audit["attempt4"]

    assert q["paid_api_calls"] == 17
    assert q["confirmed_cost_usd"] == 0.5895394
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]
    assert q["unreconciled_paid_api_calls"] == 4

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt4_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert attempt4["run_id"] == 36976651148
    assert attempt4["status"] == "unhandled_story_audit_runtime_failure"
    assert attempt4["failure_type"] == "OpenRouterCallError"
    assert attempt4["failure_phase"] == "secondary_structured_parse"
    assert attempt4["api_calls_completed"] == 2
    assert attempt4["usage_evidence_persisted"] is False
    assert attempt4["source_story_mutated"] is False
    assert attempt4["repair_executed"] is False
    assert attempt4["translation_executed"] is False
    assert attempt4["state_commit_executed"] is False
    assert attempt4["audit_artifact_created"] is False
    assert attempt4["qualification_status"] == "UNUSABLE_EVIDENCE_INVALID_JSON"



def test_v20_23_strict_story_audit_transport_contract_is_zero_cost_qualified():
    from src.model_registry import resolve_model_request_behavior
    from src.spineforge_v19_transport import STRICT_SCHEMA_MAX_BYTES, schema_size_bytes
    from src.spineforge_v20_story_audit_once import (
        AUDIT_REQUEST_CLASS,
        AUDIT_RESPONSE_SCHEMA,
        AUDIT_SCHEMA_NAME,
        _call_auditor,
    )

    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt5_paid_authorized"] is False
    assert audit["transport_contract_revision"] == "strict-json-schema-v1"
    assert audit["request_class"] == "spineforge_v20_story_audit"
    assert audit["structured_output_mode"] == "json_schema_strict"
    assert audit["strict_schema_name"] == "spineforge_v20_story_audit_v3"
    assert audit["max_tokens_per_auditor"] == 6000
    assert audit["failure_trace_persistence_required"] is True

    size = schema_size_bytes(AUDIT_RESPONSE_SCHEMA)
    assert size == audit["strict_schema_bytes"]
    assert size <= STRICT_SCHEMA_MAX_BYTES

    for model in ("anthropic/claude-sonnet-5.5", "openai/gpt-5.6-sol"):
        behavior = resolve_model_request_behavior(model, AUDIT_REQUEST_CLASS)
        assert behavior["reasoning"]["request"] == {"effort": "low", "exclude": True}
        assert behavior["max_tokens"]["cap"] == 6000

    order = [
        "physical_feasibility",
        "causal_logic",
        "state_continuity",
        "epistemic_order",
        "spatial_consistency",
        "temporal_consistency",
        "response_causality",
        "closure_integrity",
        "canon_integrity",
        "language_naturalness",
        "age_suitability",
        "spine_fidelity",
        "narrative_coherence",
    ]
    raw = {
        "evaluations": [
            {
                "family": family,
                "present": False,
                "findings": [],
                "reason": "clean",
            }
            for family in order
        ],
        "summary": "clean",
    }
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return (
            raw,
            {
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost": 0.001,
                }
            },
            {
                "temperature": None,
                "max_tokens": 6000,
                "reasoning": {"effort": "low", "exclude": True},
                "response_format": {"type": "json_schema"},
            },
            [],
        )

    normalized, _ = _call_auditor(
        fn=fake,
        api_key="not-used",
        model="openai/gpt-5.6-sol",
        prompt="test",
        payload={"test": True},
        stage="test",
    )
    assert normalized["findings"] == []
    assert seen["request_class"] == AUDIT_REQUEST_CLASS
    assert seen["schema_name"] == AUDIT_SCHEMA_NAME
    assert seen["schema"] == AUDIT_RESPONSE_SCHEMA
    assert seen["max_tokens"] == 6000


def test_v20_23_paid_story_audit_failure_preserves_provider_trace():
    from src.spineforge_v20_paid_story_audit_once import (
        build_story_audit_failure_result,
    )

    class SyntheticProviderError(RuntimeError):
        def __init__(self):
            super().__init__("synthetic provider parse failure")
            self.trace = {
                "stage": "structured_parse",
                "raw_usage": {
                    "prompt_tokens": 123,
                    "completion_tokens": 45,
                    "total_tokens": 168,
                },
                "cost": {"usd": 0.0123},
            }

    try:
        raise SyntheticProviderError()
    except SyntheticProviderError as exc:
        result = build_story_audit_failure_result(exc)

    trace = result["failure"]["provider_trace"]
    assert result["status"] == "unhandled_story_audit_runtime_failure"
    assert trace["stage"] == "structured_parse"
    assert trace["raw_usage"]["total_tokens"] == 168
    assert trace["cost"]["usd"] == 0.0123
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False



def test_v20_26_freeze_records_attempt5_paid_result_and_seals_harness():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    harness = audit["attempt5_harness"]

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
    assert audit["attempt5_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True

    assert harness["attempt_index"] == 5
    assert harness["authorization_marker"] == audit["authorization_marker"]
    assert harness["output_result"] == "age12-island-v20-story-audit5-result.json"
    assert harness["output_envelope"] == "age12-island-v20-story-audit5-envelope.json"
    assert harness["audit_contract_revision"] == "family-by-family-multi-finding-v3"
    assert harness["transport_contract_revision"] == "strict-json-schema-v1"
    assert harness["request_class"] == "spineforge_v20_story_audit"
    assert harness["strict_schema_name"] == "spineforge_v20_story_audit_v3"
    assert harness["max_tokens_per_auditor"] == 6000
    assert harness["locator_policy"] == "multi_span_unique_exact_text_rebind_v2"
    assert harness["failure_evidence_policy"] == "preserve_provider_trace_and_usage_v2"
    assert harness["paid_execution_authorized"] is False


def test_v20_attempt5_locator_rebinds_when_exact_text_is_valid_but_extra_span_ids_are_invalid():
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import _repair_finding_locators

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    source = build_story_audit_source(manifest_path=manifest)
    exact = "found the great root span torn loose in the wind, its far anchor ripped out"
    repaired, corrections = _repair_finding_locators(
        findings=[{
            "family": "spatial_consistency",
            "severity": "moderate",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": ["S161", "S85", "S86"],
            "exact_text": exact,
            "reason": "Synthetic replay of Attempt5 locator failure.",
        }],
        story_segments=source["story_segments"],
    )

    assert repaired[0]["span_ids"] == ["S161"]
    assert corrections == [{
        "family": "spatial_consistency",
        "exact_text": exact,
        "old_span_ids": ["S161", "S85", "S86"],
        "new_span_ids": ["S161"],
        "reason": "deterministic_unique_exact_text_rebind",
    }]



def test_v20_26_attempt5_paid_result_reprocesses_zero_cost_after_locator_fix():
    from src.spineforge_v20_story_audit_once import reprocess_story_audit_evidence

    result_path = Path(
        "evidence/spineforge-v20-paid-story-audit/36978036076/"
        "age12-island-v20-story-audit5-result.json"
    )
    prior = json.loads(result_path.read_text(encoding="utf-8"))
    reprocessed = reprocess_story_audit_evidence(prior_result=prior)

    assert reprocessed["status"] == "audit_reprocessed_zero_cost"
    assert reprocessed["reprocess"]["model_calls_executed"] == 0
    assert reprocessed["reprocess"]["source_paid_usage_reused"] is True
    assert reprocessed["source_story_mutated"] is False
    assert reprocessed["audit_artifact"]["decision"] == "STRUCTURAL_REPAIR_REQUIRED"
    assert reprocessed["audit_artifact"]["next_stage"] == "STOP"
    assert reprocessed["audit_usage_rollup"]["totals"]["api_calls"] == 2
    assert reprocessed["audit_usage_rollup"]["totals"]["total_tokens"] == 50735
    assert reprocessed["audit_usage_rollup"]["totals"]["cost_usd"] == 0.1460595
    assert any(
        row["old_span_ids"] == ["S161", "S85", "S86"]
        and row["new_span_ids"] == ["S161"]
        for row in reprocessed["locator_corrections"]
    )


def test_v20_26_freeze_records_attempt5_quality_failure_with_reconciled_usage():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt5 = audit["attempt5"]

    assert q["paid_api_calls"] == 17
    assert q["confirmed_cost_usd"] == 0.5895394
    assert q["last_paid_run_id"] == 36978036076
    assert q["last_result"] == "story_audit_attempt5_contract_failure_known_defect_missed"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]
    assert q["unreconciled_paid_api_calls"] == 4
    assert q["confirmed_cost_is_lower_bound"] is True

    assert audit["status"] == "ATTEMPT5_QUALITY_FAILED_KNOWN_DEFECT_MISSED_LOCATOR_REPROCESS_READY"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt5_paid_authorized"] is False
    assert audit["authorization_consumed"] is True

    assert attempt5["run_id"] == 36978036076
    assert attempt5["status"] == "audit_contract_failure"
    assert attempt5["transport_contract_revision"] == "strict-json-schema-v1"
    assert attempt5["api_calls"] == 2
    assert attempt5["input_tokens"] == 46336
    assert attempt5["output_tokens"] == 4399
    assert attempt5["reasoning_tokens"] == 1186
    assert attempt5["total_tokens"] == 50735
    assert attempt5["cost_usd"] == 0.1460595
    assert attempt5["finding_count_before_artifact"] == 25
    assert attempt5["known_target_recall"] == 0.0
    assert attempt5["known_target_detected"] is False
    assert attempt5["source_story_mutated"] is False
    assert attempt5["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
