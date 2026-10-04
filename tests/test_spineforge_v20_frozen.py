from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_obligations import load_qualification_cases


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json")


def test_v20_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-STORY-FIRST-FROZEN-v20.84"
    assert result["verified_files"] == 192


def test_v20_freeze_locks_story_first_topology_and_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    product = profile["product_contract"]
    paid = profile["paid_boundary_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v20.story-first-single-owner"
    assert profile["runtime_freeze"]["runtime_source_commit"] == "6680c948d"
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
    assert state["paid_api_calls"] == 52
    assert state["confirmed_cost_usd"] == 2.3789534
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

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
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

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["primary_model"] == "anthropic/claude-sonnet-5.5"
    assert audit["secondary_model"] == "openai/gpt-5.6-sol"
    assert audit["audit_calls_per_execution"] == 2
    assert audit["automatic_retry_enabled"] is False
    assert audit["prompt_path"] == "prompts/spineforge_v20_story_audit.md"
    assert audit["execution_module"] == "src/spineforge_v20_story_audit_once.py"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
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

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
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

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt2_paid_authorized"] is False
    assert audit["audit_contract_revision"] == "primary-v3-plus-language-specialist-v2"
    assert audit["authority_projection"] == "compact-reveal-safe-v1"
    assert audit["prompt_revision"] == "stage5-story-audit-v3"
    assert audit["attempt1"]["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert audit["attempt1"]["known_target_recall"] == 0.0



def test_v20_13_freeze_locks_attempt2_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
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
        import copy

        emitted = copy.deepcopy(raw)
        if kwargs.get("schema_name") == "spineforge_v20_language_specialist_v2":
            payload = json.loads(kwargs["user_prompt"])
            specialist_findings = []
            language_ids = set()
            for evaluation in emitted.get("evaluations") or []:
                if evaluation.get("family") != "language_naturalness":
                    continue
                findings = evaluation.get("findings")
                if isinstance(findings, list):
                    for finding in findings:
                        row = {
                            "severity": finding["severity"],
                            "span_ids": list(finding.get("span_ids") or []),
                            "exact_text": finding["exact_text"],
                            "reason": finding["reason"],
                        }
                        specialist_findings.append(row)
                        language_ids.update(str(x) for x in row["span_ids"])
                elif evaluation.get("present"):
                    row = {
                        "severity": evaluation["severity"],
                        "span_ids": list(evaluation.get("span_ids") or []),
                        "exact_text": evaluation["exact_text"],
                        "reason": evaluation["reason"],
                    }
                    specialist_findings.append(row)
                    language_ids.update(str(x) for x in row["span_ids"])
            emitted = {
                "language_sentence_scan": [
                    {
                        "span_id": str(row["id"]),
                        "status": (
                            "defect"
                            if str(row["id"]) in language_ids
                            else "clean"
                        ),
                        "editor_action": (
                            "REWRITE"
                            if str(row["id"]) in language_ids
                            else "KEEP"
                        ),
                        "rewrite": (
                            "Synthetic minimal native-English rewrite."
                            if str(row["id"]) in language_ids
                            else ""
                        ),
                    }
                    for row in payload["story_segments"]
                ],
                "findings": specialist_findings,
                "summary": str(emitted.get("summary") or ""),
            }
        return (
            emitted,
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
                "max_tokens": 6000,
                "reasoning": None,
                "response_format": {"type": "json_schema"},
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

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["cost_reconciliation_status"] == "PARTIAL"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148, 36995792496]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
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

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt3_paid_authorized"] is False
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
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
    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
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
    assert "English Naturalness Specialist v1" in prompt
    assert "Do not stop after finding several issues" in prompt
    assert "Your ONLY job is English prose naturalness" in prompt


def test_v20_19_freeze_locks_v3_story_audit_requalification_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    reprocessed = audit["attempt3_reprocess"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["cost_reconciliation_status"] == "PARTIAL"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148, 36995792496]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt4_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["audit_contract_revision"] == "primary-v3-plus-language-specialist-v2"
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
    assert "English Naturalness Specialist v1" in prompt
    assert "Do not stop after finding several issues" in prompt
    assert "Do not audit plot, canon, causality" in prompt
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

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
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

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148, 36995792496]
    assert q["unreconciled_paid_api_calls"] == 5

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
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
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import (
        AUDIT_REQUEST_CLASS,
        AUDIT_RESPONSE_SCHEMA,
        AUDIT_SCHEMA_NAME,
        _call_auditor,
    )

    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
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

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt5_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True

    assert harness["attempt_index"] == 5
    assert harness["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT5"
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

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148, 36995792496]
    assert q["unreconciled_paid_api_calls"] == 5
    assert q["confirmed_cost_is_lower_bound"] is True

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
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



def test_v20_27_freeze_locks_attempt5_reprocessed_artifact_without_new_model_calls():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    reprocessed = audit["attempt5_reprocess"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert reprocessed["status"] == "audit_reprocessed_zero_cost"
    assert reprocessed["model_calls_executed"] == 0
    assert reprocessed["source_paid_usage_reused"] is True
    assert reprocessed["source_story_mutated"] is False
    assert reprocessed["audit_artifact_id"] == (
        "story-audit:7c6560e4e843c7a540501ff47f57eae96579943c70cce3a319621dd5637f4a9e"
    )
    assert reprocessed["decision"] == "STRUCTURAL_REPAIR_REQUIRED"
    assert reprocessed["next_stage"] == "STOP"
    assert reprocessed["finding_count"] == 25
    assert reprocessed["locator_correction_count"] == 1
    assert reprocessed["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert reprocessed["known_target_recall"] == 0.0

    result = json.loads(Path(reprocessed["reprocessed_result_path"]).read_text(encoding="utf-8"))
    report = json.loads(Path(reprocessed["qualification_report_path"]).read_text(encoding="utf-8"))
    assert result["status"] == "audit_reprocessed_zero_cost"
    assert result["reprocess"]["model_calls_executed"] == 0
    assert result["audit_artifact"]["artifact_id"] == reprocessed["audit_artifact_id"]
    assert report["status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert report["target_recall"] == 0.0


def test_v20_28_secondary_sentence_scan_contract_covers_every_frozen_story_sentence():
    from src.spineforge_v19_transport import schema_size_bytes
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import (
        SECONDARY_AUDIT_RESPONSE_SCHEMA,
        SECONDARY_AUDIT_SCHEMA_NAME,
        _normalize_auditor_payload,
    )

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    source = build_story_audit_source(manifest_path=manifest)
    expected_ids = [str(row["id"]) for row in source["story_segments"]]
    assert len(expected_ids) == 199
    assert expected_ids[5] == "S006"

    rows = _stage5_v3_clean_rows()
    language_index = next(
        i for i, row in enumerate(rows)
        if row["family"] == "language_naturalness"
    )
    rows[language_index] = {
        "family": "language_naturalness",
        "present": True,
        "findings": [{
            "severity": "minor",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": ["S006"],
            "exact_text": "arriving at his shoulder",
            "reason": "Idiomatic movement phrasing is unnatural.",
        }],
        "reason": "",
    }
    scan = [
        {
            "span_id": span_id,
            "status": "defect" if span_id == "S006" else "clean",
        }
        for span_id in expected_ids
    ]
    normalized = _normalize_auditor_payload(
        raw={
            "language_sentence_scan": scan,
            "evaluations": rows,
            "summary": "One language defect.",
        },
        require_language_sentence_scan=True,
        expected_span_ids=expected_ids,
    )
    assert len(normalized["language_sentence_scan"]) == 199
    assert normalized["language_sentence_scan"][5] == {
        "span_id": "S006",
        "status": "defect",
    }
    assert normalized["findings"][0]["exact_text"] == "arriving at his shoulder"
    assert SECONDARY_AUDIT_SCHEMA_NAME == "spineforge_v20_language_specialist_v2"
    assert schema_size_bytes(SECONDARY_AUDIT_RESPONSE_SCHEMA) <= 4096


def test_v20_28_secondary_sentence_scan_rejects_missing_or_unmatched_coverage():
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import _normalize_auditor_payload

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    source = build_story_audit_source(manifest_path=manifest)
    expected_ids = [str(row["id"]) for row in source["story_segments"]]
    rows = _stage5_v3_clean_rows()

    incomplete_scan = [
        {"span_id": span_id, "status": "clean"}
        for span_id in expected_ids[:-1]
    ]
    try:
        _normalize_auditor_payload(
            raw={
                "language_sentence_scan": incomplete_scan,
                "evaluations": rows,
                "summary": "Incomplete scan.",
            },
            require_language_sentence_scan=True,
            expected_span_ids=expected_ids,
        )
    except RuntimeError as exc:
        assert "every story sentence exactly once" in str(exc)
    else:
        raise AssertionError("Secondary sentence scan must reject missing coverage.")

    mismatch_scan = [
        {
            "span_id": span_id,
            "status": "defect" if span_id == "S006" else "clean",
        }
        for span_id in expected_ids
    ]
    try:
        _normalize_auditor_payload(
            raw={
                "language_sentence_scan": mismatch_scan,
                "evaluations": rows,
                "summary": "Scan/finding mismatch.",
            },
            require_language_sentence_scan=True,
            expected_span_ids=expected_ids,
        )
    except RuntimeError as exc:
        assert "must exactly match language_naturalness" in str(exc)
    else:
        raise AssertionError("Secondary scan defects must match language findings.")


def test_v20_28_freeze_locks_secondary_sentence_coverage_before_attempt6():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    coverage = audit["secondary_sentence_coverage"]
    reprocessed = audit["attempt5_reprocess"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt6_paid_authorized"] is False
    assert audit["next_harness_requirement"] == "stage6_story_local_repair_handoff_ready"

    assert reprocessed["status"] == "audit_reprocessed_zero_cost"
    assert reprocessed["model_calls_executed"] == 0
    assert reprocessed["decision"] == "STRUCTURAL_REPAIR_REQUIRED"
    assert reprocessed["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert reprocessed["known_target_recall"] == 0.0
    assert reprocessed["reprocessed_result_path"].endswith(
        "age12-island-v20-story-audit5-reprocessed.json"
    )

    assert coverage["contract_revision"] == "language-sentence-scan-v1"
    assert coverage["schema_name"] == "spineforge_v20_story_audit_secondary_v4"
    assert coverage["prompt_revision"] == "stage5-secondary-v4-sentence-coverage"
    assert coverage["required"] is True
    assert coverage["expected_sentence_count"] == 199
    assert coverage["exact_canonical_order_required"] is True
    assert coverage["every_sentence_exactly_once_required"] is True
    assert coverage["statuses"] == ["clean", "defect"]
    assert coverage["defect_scan_ids_must_equal_language_finding_span_ids"] is True
    assert coverage["max_tokens_per_auditor"] == 6000


def test_v20_28_secondary_language_sentence_scan_covers_every_story_segment_without_gold_leak():
    from src.spineforge_v19_transport import STRICT_SCHEMA_MAX_BYTES, schema_size_bytes
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import (
        SECONDARY_AUDIT_RESPONSE_SCHEMA,
        SECONDARY_AUDIT_SCHEMA_NAME,
        _normalize_auditor_payload,
    )

    manifest = Path(
        "evidence/spineforge-v20-writer-product/36965340665/"
        "writer-story-artifact.json"
    )
    source = build_story_audit_source(manifest_path=manifest)
    expected_ids = [str(row["id"]) for row in source["story_segments"]]
    assert len(expected_ids) == 199
    assert len(expected_ids) == len(set(expected_ids))

    gold = json.loads(Path(
        "data/specifications/story_lab/"
        "spineforge_v20_story_audit_qualification_gold.json"
    ).read_text(encoding="utf-8"))
    anchor = gold["targets"][0]["anchor"]
    target_segment = next(
        row for row in source["story_segments"] if anchor in row["text"]
    )
    target_id = str(target_segment["id"])

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
    evaluations = [
        {
            "family": family,
            "present": False,
            "findings": [],
            "reason": "clean",
        }
        for family in order
    ]
    evaluations[order.index("language_naturalness")] = {
        "family": "language_naturalness",
        "present": True,
        "findings": [{
            "severity": "minor",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": [target_id],
            "exact_text": anchor,
            "reason": "Synthetic human-gold qualification target.",
        }],
        "reason": "",
    }
    scan = [
        {
            "span_id": span_id,
            "status": "defect" if span_id == target_id else "clean",
        }
        for span_id in expected_ids
    ]
    raw = {
        "language_sentence_scan": scan,
        "evaluations": evaluations,
        "summary": "Synthetic exhaustive sentence scan.",
    }

    normalized = _normalize_auditor_payload(
        raw=raw,
        require_language_sentence_scan=True,
        expected_span_ids=expected_ids,
    )
    assert normalized["language_sentence_scan"] == scan
    assert len(normalized["language_sentence_scan"]) == 199
    assert normalized["findings"][0]["exact_text"] == anchor

    broken = dict(raw)
    broken["language_sentence_scan"] = scan[:-1]
    try:
        _normalize_auditor_payload(
            raw=broken,
            require_language_sentence_scan=True,
            expected_span_ids=expected_ids,
        )
    except RuntimeError as exc:
        assert "every story sentence exactly once" in str(exc)
    else:
        raise AssertionError("Secondary audit must reject incomplete sentence coverage.")

    assert SECONDARY_AUDIT_SCHEMA_NAME == "spineforge_v20_language_specialist_v2"
    assert "language_sentence_scan" in SECONDARY_AUDIT_RESPONSE_SCHEMA["required"]
    assert schema_size_bytes(SECONDARY_AUDIT_RESPONSE_SCHEMA) <= STRICT_SCHEMA_MAX_BYTES

    prompt = Path(
        "prompts/spineforge_v20_story_audit_secondary.md"
    ).read_text(encoding="utf-8")
    assert anchor not in prompt


def test_v20_28_freeze_locks_attempt6_sentence_coverage_requalification_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    coverage = audit["secondary_sentence_coverage"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt6_paid_authorized"] is False
    assert coverage["contract_revision"] == "language-sentence-scan-v1"
    assert coverage["schema_name"] == "spineforge_v20_story_audit_secondary_v4"
    assert coverage["prompt_revision"] == "stage5-secondary-v4-sentence-coverage"
    assert coverage["required"] is True
    assert coverage["expected_sentence_count"] == 199
    assert coverage["exact_canonical_order_required"] is True
    assert coverage["every_sentence_exactly_once_required"] is True
    assert coverage["statuses"] == ["clean", "defect"]
    assert coverage["defect_scan_ids_must_equal_language_finding_span_ids"] is True
    assert coverage["max_tokens_per_auditor"] == 6000



def test_v20_29_freeze_locks_attempt6_sentence_coverage_harness_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    harness = audit["attempt6_harness"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt6_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["next_harness_requirement"] == "stage6_story_local_repair_handoff_ready"

    assert harness["attempt_index"] == 6
    assert harness["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT6"
    assert harness["output_result"] == "age12-island-v20-story-audit6-result.json"
    assert harness["output_envelope"] == "age12-island-v20-story-audit6-envelope.json"
    assert harness["transport_contract_revision"] == "strict-json-schema-v1"
    assert harness["primary_schema_name"] == "spineforge_v20_story_audit_v3"
    assert harness["secondary_schema_name"] == "spineforge_v20_story_audit_secondary_v4"
    assert harness["secondary_sentence_coverage_contract"] == "language-sentence-scan-v1"
    assert harness["expected_sentence_count"] == 199
    assert harness["request_class"] == "spineforge_v20_story_audit"
    assert harness["max_tokens_per_auditor"] == 6000
    assert harness["paid_execution_authorized"] is False


def test_v20_31_freeze_records_attempt6_paid_result_and_zero_cost_reprocess():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt6 = audit["attempt6"]
    reprocessed = audit["attempt6_reprocess"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"

    assert attempt6["run_id"] == 36981205470
    assert attempt6["status"] == "audit_contract_failure"
    assert attempt6["secondary_sentence_scan_count"] == 199
    assert attempt6["s006_scan_status"] == "clean"
    assert attempt6["api_calls"] == 2
    assert attempt6["input_tokens"] == 46652
    assert attempt6["output_tokens"] == 5999
    assert attempt6["reasoning_tokens"] == 1200
    assert attempt6["total_tokens"] == 52651
    assert attempt6["cost_usd"] == 0.1628495
    assert attempt6["latency_seconds"] == 66.183
    assert attempt6["known_target_recall"] == 0.0
    assert attempt6["known_target_detected"] is False
    assert attempt6["source_story_mutated"] is False
    assert attempt6["repair_executed"] is False
    assert attempt6["translation_executed"] is False
    assert attempt6["state_commit_executed"] is False

    assert reprocessed["status"] == "audit_reprocessed_zero_cost"
    assert reprocessed["model_calls_executed"] == 0
    assert reprocessed["source_paid_usage_reused"] is True
    assert reprocessed["source_story_mutated"] is False
    assert reprocessed["decision"] == "STRUCTURAL_REPAIR_REQUIRED"
    assert reprocessed["next_stage"] == "STOP"
    assert reprocessed["finding_count"] == 18
    assert reprocessed["locator_correction_count"] == 2
    assert reprocessed["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert reprocessed["known_target_recall"] == 0.0

    result = json.loads(
        Path(reprocessed["reprocessed_result_path"]).read_text(encoding="utf-8")
    )
    report = json.loads(
        Path(reprocessed["qualification_report_path"]).read_text(encoding="utf-8")
    )
    assert result["audit_artifact"]["artifact_id"] == reprocessed["audit_artifact_id"]
    assert result["reprocess"]["model_calls_executed"] == 0
    assert report["status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert report["target_recall"] == 0.0


def test_v20_32_freeze_locks_language_specialist_requalification_without_paid_authorization():
    from src.spineforge_v19_transport import STRICT_SCHEMA_MAX_BYTES, schema_size_bytes
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import (
        SECONDARY_AUDIT_RESPONSE_SCHEMA,
        SECONDARY_AUDIT_SCHEMA_NAME,
        _normalize_language_specialist_payload,
    )

    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    specialist = audit["secondary_language_specialist"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["audit_contract_revision"] == "primary-v3-plus-language-specialist-v2"
    assert audit["next_harness_requirement"] == "stage6_story_local_repair_handoff_ready"

    assert specialist["contract_revision"] == "language-specialist-v2"
    assert specialist["model"] == "openai/gpt-5.6-sol"
    assert specialist["schema_name"] == "spineforge_v20_language_specialist_v2"
    assert specialist["request_class"] == "spineforge_v20_story_audit"
    assert specialist["task"] == "contrastive_edit_frozen_story_english_naturalness"
    assert specialist["input_policy"] == "frozen-story-plus-exact-age-only"
    assert specialist["full_authority_context_included"] is False
    assert specialist["approved_spine_included"] is False
    assert specialist["expected_sentence_count"] == 199
    assert specialist["every_sentence_exactly_once_required"] is True
    assert specialist["exact_canonical_order_required"] is True
    assert specialist["defect_scan_ids_must_equal_finding_span_ids"] is True
    assert specialist["finding_family"] == "language_naturalness"
    assert specialist["finding_repair_scope"] == "LOCAL_REPAIR"
    assert specialist["max_tokens"] == 6000
    assert specialist["paid_execution_authorized"] is False

    source = build_story_audit_source(
        manifest_path=Path(
            "evidence/spineforge-v20-writer-product/36965340665/"
            "writer-story-artifact.json"
        )
    )
    expected_ids = [str(row["id"]) for row in source["story_segments"]]
    scan = [
        {
            "span_id": span_id,
            "status": "defect" if span_id == "S006" else "clean",
            "editor_action": "REWRITE" if span_id == "S006" else "KEEP",
            "rewrite": (
                "Nisa said, coming up beside him."
                if span_id == "S006"
                else ""
            ),
        }
        for span_id in expected_ids
    ]
    normalized = _normalize_language_specialist_payload(
        raw={
            "language_sentence_scan": scan,
            "findings": [{
                "severity": "minor",
                "span_ids": ["S006"],
                "exact_text": "arriving at his shoulder",
                "reason": "Synthetic generic movement-phrase naturalness case.",
            }],
            "summary": "Synthetic language specialist qualification.",
        },
        expected_span_ids=expected_ids,
    )
    assert normalized["findings"] == [{
        "family": "language_naturalness",
        "severity": "minor",
        "repair_scope": "LOCAL_REPAIR",
        "span_ids": ["S006"],
        "exact_text": "arriving at his shoulder",
        "reason": "Synthetic generic movement-phrase naturalness case.",
    }]
    assert len(normalized["language_sentence_scan"]) == 199
    assert SECONDARY_AUDIT_SCHEMA_NAME == "spineforge_v20_language_specialist_v2"
    assert schema_size_bytes(SECONDARY_AUDIT_RESPONSE_SCHEMA) <= STRICT_SCHEMA_MAX_BYTES

    prompt = Path(
        "prompts/spineforge_v20_story_audit_secondary.md"
    ).read_text(encoding="utf-8")
    assert "Your ONLY job is English prose naturalness" in prompt
    assert "movement/body-position expression" in prompt
    assert "dialogue-attribution or action-tag construction" in prompt
    assert "arriving at his shoulder" not in prompt


def test_v20_33_freeze_locks_attempt7_language_specialist_harness_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    harness = audit["attempt7_harness"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt7_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["next_harness_requirement"] == "stage6_story_local_repair_handoff_ready"

    assert harness["attempt_index"] == 7
    assert harness["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT7"
    assert harness["output_result"] == "age12-island-v20-story-audit7-result.json"
    assert harness["output_envelope"] == "age12-island-v20-story-audit7-envelope.json"
    assert harness["audit_contract_revision"] == "primary-v3-plus-language-specialist-v1"
    assert harness["transport_contract_revision"] == "strict-json-schema-v1"
    assert harness["primary_schema_name"] == "spineforge_v20_story_audit_v3"
    assert harness["secondary_schema_name"] == "spineforge_v20_language_specialist_v1"
    assert harness["secondary_contract_revision"] == "language-specialist-v1"
    assert harness["secondary_input_policy"] == "frozen-story-plus-exact-age-only"
    assert harness["secondary_expected_sentence_count"] == 199
    assert harness["request_class"] == "spineforge_v20_story_audit"
    assert harness["max_tokens_per_auditor"] == 6000
    assert harness["locator_policy"] == "multi_span_unique_exact_text_rebind_v3"
    assert harness["automatic_retry_enabled"] is False
    assert harness["paid_execution_authorized"] is False


def test_v20_35_freeze_records_attempt7_quality_failure_and_reconciled_usage():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt7 = audit["attempt7"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt7_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["next_harness_requirement"] == (
        "stage6_story_local_repair_handoff_ready"
    )

    assert attempt7["run_id"] == 36987409819
    assert attempt7["status"] == "audit_completed"
    assert attempt7["secondary_sentence_scan_count"] == 199
    assert attempt7["s006_scan_status"] == "clean"
    assert attempt7["api_calls"] == 2
    assert attempt7["input_tokens"] == 39717
    assert attempt7["output_tokens"] == 4906
    assert attempt7["reasoning_tokens"] == 952
    assert attempt7["total_tokens"] == 44623
    assert attempt7["cost_usd"] == 0.134582
    assert attempt7["latency_seconds"] == 47.303
    assert attempt7["artifact_id"] == (
        "story-audit:dfd0dface3e4e49c41fb41fb55d4356a22f3c777645943a49d81c043c1257fee"
    )
    assert attempt7["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert attempt7["next_stage"] == "STORY_LOCAL_REPAIR"
    assert attempt7["finding_count"] == 15
    assert attempt7["known_target_recall"] == 0.0
    assert attempt7["known_target_detected"] is False
    assert attempt7["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert attempt7["automatic_retry_executed"] is False
    assert attempt7["source_story_mutated"] is False
    assert attempt7["repair_executed"] is False
    assert attempt7["translation_executed"] is False
    assert attempt7["state_commit_executed"] is False
    assert attempt7["audit_artifact_created"] is True


def test_v20_36_freeze_locks_contrastive_editor_requalification():
    from src.spineforge_v19_transport import STRICT_SCHEMA_MAX_BYTES, schema_size_bytes
    from src.spineforge_v20_story_audit_artifact import build_story_audit_source
    from src.spineforge_v20_story_audit_once import (
        SECONDARY_AUDIT_RESPONSE_SCHEMA,
        SECONDARY_AUDIT_SCHEMA_NAME,
        _normalize_language_specialist_payload,
    )

    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    specialist = audit["secondary_language_specialist"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt8_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["audit_contract_revision"] == (
        "primary-v3-plus-language-specialist-v2"
    )
    assert audit["next_harness_requirement"] == (
        "stage6_story_local_repair_handoff_ready"
    )

    assert specialist["contract_revision"] == "language-specialist-v2"
    assert specialist["schema_name"] == "spineforge_v20_language_specialist_v2"
    assert specialist["task"] == (
        "contrastive_edit_frozen_story_english_naturalness"
    )
    assert specialist["decision_values"] == ["KEEP", "REWRITE"]
    assert specialist["clean_requires"] == "KEEP+empty_rewrite"
    assert specialist["defect_requires"] == (
        "REWRITE+nonempty_changed_rewrite"
    )
    assert specialist["prompt_revision"] == "contrastive-editor-v2"
    assert specialist["paid_execution_authorized"] is False

    source = build_story_audit_source(
        manifest_path=Path(
            "evidence/spineforge-v20-writer-product/36965340665/"
            "writer-story-artifact.json"
        )
    )
    expected_ids = [str(row["id"]) for row in source["story_segments"]]
    story_text_by_id = {
        str(row["id"]): str(row["text"])
        for row in source["story_segments"]
    }
    scan = [
        {
            "span_id": span_id,
            "status": "defect" if span_id == "S006" else "clean",
            "editor_action": "REWRITE" if span_id == "S006" else "KEEP",
            "rewrite": (
                "Nisa said, coming up beside him."
                if span_id == "S006"
                else ""
            ),
        }
        for span_id in expected_ids
    ]
    normalized = _normalize_language_specialist_payload(
        raw={
            "language_sentence_scan": scan,
            "findings": [{
                "severity": "minor",
                "span_ids": ["S006"],
                "exact_text": "arriving at his shoulder",
                "reason": "Synthetic contrastive movement-phrase qualification.",
            }],
            "summary": "Synthetic contrastive editor qualification.",
        },
        expected_span_ids=expected_ids,
        story_text_by_id=story_text_by_id,
    )
    assert normalized["language_sentence_scan"][5] == {
        "span_id": "S006",
        "status": "defect",
        "editor_action": "REWRITE",
        "rewrite": "Nisa said, coming up beside him.",
    }
    assert normalized["findings"][0]["exact_text"] == (
        "arriving at his shoulder"
    )
    assert SECONDARY_AUDIT_SCHEMA_NAME == (
        "spineforge_v20_language_specialist_v2"
    )
    assert schema_size_bytes(SECONDARY_AUDIT_RESPONSE_SCHEMA) <= (
        STRICT_SCHEMA_MAX_BYTES
    )

    prompt = Path(
        "prompts/spineforge_v20_story_audit_secondary.md"
    ).read_text(encoding="utf-8")
    assert "Contrastive editor challenge" in prompt
    assert "KEEP" in prompt
    assert "REWRITE" in prompt
    assert "arriving at his shoulder" not in prompt


def test_v20_37_freeze_locks_attempt8_contrastive_harness_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    harness = audit["attempt8_harness"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt8_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["next_harness_requirement"] == "stage6_story_local_repair_handoff_ready"

    assert harness["attempt_index"] == 8
    assert harness["authorization_marker"] == audit["authorization_marker"]
    assert harness["output_result"] == "age12-island-v20-story-audit8-result.json"
    assert harness["output_envelope"] == "age12-island-v20-story-audit8-envelope.json"
    assert harness["audit_contract_revision"] == (
        "primary-v3-plus-language-specialist-v2"
    )
    assert harness["transport_contract_revision"] == "strict-json-schema-v1"
    assert harness["primary_schema_name"] == "spineforge_v20_story_audit_v3"
    assert harness["secondary_schema_name"] == (
        "spineforge_v20_language_specialist_v2"
    )
    assert harness["secondary_contract_revision"] == "language-specialist-v2"
    assert harness["secondary_input_policy"] == "frozen-story-plus-exact-age-only"
    assert harness["secondary_expected_sentence_count"] == 199
    assert harness["secondary_decision_contract"] == "KEEP_or_REWRITE"
    assert harness["request_class"] == "spineforge_v20_story_audit"
    assert harness["max_tokens_per_auditor"] == 6000
    assert harness["locator_policy"] == "multi_span_unique_exact_text_rebind_v3"
    assert harness["automatic_retry_enabled"] is False
    assert harness["paid_execution_authorized"] is False


def test_v20_39_freeze_records_attempt8_qualification_success_and_routes_stage6():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt8 = audit["attempt8"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["confirmed_cost_is_lower_bound"] is True

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt8_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["next_harness_requirement"] == (
        "stage6_story_local_repair_handoff_ready"
    )

    assert attempt8["run_id"] == 36990160527
    assert attempt8["status"] == "audit_completed"
    assert attempt8["audit_contract_revision"] == (
        "primary-v3-plus-language-specialist-v2"
    )
    assert attempt8["secondary_contract_revision"] == "language-specialist-v2"
    assert attempt8["secondary_sentence_scan_count"] == 199
    assert attempt8["s006_scan_status"] == "defect"
    assert attempt8["s006_editor_action"] == "REWRITE"
    assert attempt8["api_calls"] == 2
    assert attempt8["input_tokens"] == 39978
    assert attempt8["output_tokens"] == 7058
    assert attempt8["reasoning_tokens"] == 369
    assert attempt8["total_tokens"] == 47036
    assert attempt8["cost_usd"] == 0.1567545
    assert attempt8["latency_seconds"] == 55.268
    assert attempt8["artifact_id"] == (
        "story-audit:8ed94a19c3b8637df0378dc3ec64eacef97096efaa3013f19231ee4cf73e4876"
    )
    assert attempt8["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert attempt8["next_stage"] == "STORY_LOCAL_REPAIR"
    assert attempt8["finding_count"] == 25
    assert attempt8["known_target_recall"] == 1.0
    assert attempt8["known_target_detected"] is True
    assert attempt8["qualification_status"] == "PASS"
    assert attempt8["automatic_retry_executed"] is False
    assert attempt8["source_story_mutated"] is False
    assert attempt8["repair_executed"] is False
    assert attempt8["translation_executed"] is False
    assert attempt8["state_commit_executed"] is False
    assert attempt8["audit_artifact_created"] is True


def test_v20_39_freeze_records_attempt8_qualification_pass_and_stage5_product():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt8 = audit["attempt8"]
    product = audit["stage5_output_artifact"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"

    assert audit["status"] == (
        "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    )
    assert audit["paid_execution_authorized"] is False
    assert audit["attempt8_paid_authorized"] is False
    assert audit["authorization_consumed"] is True
    assert audit["next_harness_requirement"] == (
        "stage6_story_local_repair_handoff_ready"
    )

    assert attempt8["run_id"] == 36990160527
    assert attempt8["status"] == "audit_completed"
    assert attempt8["secondary_sentence_scan_count"] == 199
    assert attempt8["s006_scan_status"] == "defect"
    assert attempt8["s006_editor_action"] == "REWRITE"
    assert attempt8["known_target_detected"] is True
    assert attempt8["known_target_recall"] == 1.0
    assert attempt8["qualification_status"] == "PASS"
    assert attempt8["api_calls"] == 2
    assert attempt8["input_tokens"] == 39978
    assert attempt8["output_tokens"] == 7058
    assert attempt8["reasoning_tokens"] == 369
    assert attempt8["total_tokens"] == 47036
    assert attempt8["cost_usd"] == 0.1567545
    assert attempt8["latency_seconds"] == 55.268
    assert attempt8["primary_finding_count"] == 13
    assert attempt8["secondary_finding_count"] == 12
    assert attempt8["finding_count"] == 25
    assert attempt8["artifact_id"] == (
        "story-audit:8ed94a19c3b8637df0378dc3ec64eacef97096efaa3013f19231ee4cf73e4876"
    )
    assert attempt8["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert attempt8["next_stage"] == "STORY_LOCAL_REPAIR"
    assert attempt8["automatic_retry_executed"] is False
    assert attempt8["source_story_mutated"] is False
    assert attempt8["repair_executed"] is False
    assert attempt8["translation_executed"] is False
    assert attempt8["state_commit_executed"] is False
    assert attempt8["audit_artifact_created"] is True

    assert product["artifact_id"] == attempt8["artifact_id"]
    assert product["source_story_sha256"] == attempt8["source_story_sha256"]
    assert product["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert product["next_stage"] == "STORY_LOCAL_REPAIR"
    assert product["finding_count"] == 25
    assert product["qualification_status"] == "PASS"
    assert product["immutable"] is True


def test_v20_39_freeze_exposes_immutable_stage5_output_artifact():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    out = audit["stage5_output_artifact"]

    assert out["artifact_id"] == (
        "story-audit:8ed94a19c3b8637df0378dc3ec64eacef97096efaa3013f19231ee4cf73e4876"
    )
    assert out["source_story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert out["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert out["next_stage"] == "STORY_LOCAL_REPAIR"
    assert out["finding_count"] == 25
    assert out["qualification_status"] == "PASS"
    assert out["immutable"] is True


def test_v20_40_freeze_locks_stage6_story_local_repair_handoff():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    stage6 = profile["stage6_story_local_repair"]

    assert audit["status"] == "ATTEMPT8_QUALIFIED_LOCAL_REPAIR_REQUIRED"
    assert audit["next_harness_requirement"] == (
        "stage6_story_local_repair_handoff_ready"
    )

    assert stage6["status"] == "ATTEMPT2_REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage6["stage"] == 6
    assert stage6["input_artifact_schema"] == (
        "spineforge-v20-story-local-repair-handoff.v1"
    )
    assert stage6["source_stage5_artifact_id"] == (
        "story-audit:8ed94a19c3b8637df0378dc3ec64eacef97096efaa3013f19231ee4cf73e4876"
    )
    assert stage6["source_story_artifact_id"] == (
        "writer-story:f1000691c85665ea6894e45e0318faaf5cdf7c1dac91fa453153e392af8192f3"
    )
    assert stage6["source_story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert stage6["handoff_artifact_id"] == (
        "story-local-repair-handoff:6f27c399c81ca3f8137005af4a36d4be6afd93881555e380e07b127eff5f98e1"
    )
    assert stage6["handoff_sha256"] == (
        "d96428c26c35f27b54e8337dc3ad3b7c203ab4cd41f9f7caf982b607a9a65356"
    )
    assert stage6["finding_count"] == 25
    assert stage6["allowed_edit_span_count"] == 25
    assert "S006" in stage6["allowed_edit_span_ids"]
    assert stage6["artifact_type"] == "IMMUTABLE_STAGE6_LOCAL_REPAIR_INPUT"
    assert stage6["repair_model"] == "anthropic/claude-sonnet-5.5"
    assert stage6["repair_attempt_index"] == 2
    assert stage6["repair_policy"]["patches_only"] is True
    assert stage6["repair_policy"]["all_findings_must_be_addressed"] is True
    assert stage6["output_contract"]["next_stage"] == "STORY_REAUDIT"
    assert stage6["next_stage_after_success"] == "STORY_REAUDIT"
    assert stage6["paid_execution_authorized"] is False
    assert stage6["automatic_retry_enabled"] is False
    assert stage6["automatic_repair_loop_enabled"] is False
    assert stage6["next_harness_requirement"] == "stage7_story_reaudit_handoff_ready"


def test_v20_41_freeze_locks_stage6_paid_harness_without_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stage6 = profile["stage6_story_local_repair"]
    harness = stage6["attempt1_harness"]

    assert stage6["status"] == "ATTEMPT2_REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage6["authorization_marker"] == (
        "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR2"
    )
    assert stage6["legacy_ci_trigger_marker"] == (
        "PAID-V20-AGE12-ISLAND-WRITER2"
    )
    assert stage6["ci_transport_job"] == "paid-age12-island-writer2"
    assert stage6["paid_wrapper"] == (
        "src/spineforge_v20_paid_story_local_repair_once.py"
    )
    assert stage6["execution_module"] == (
        "src/spineforge_v20_story_local_repair_once.py"
    )
    assert stage6["prompt_path"] == (
        "prompts/spineforge_v20_story_local_repair.md"
    )
    assert stage6["repair_request_class"] == (
        "spineforge_v20_story_local_repair"
    )
    assert stage6["repair_schema_name"] == (
        "spineforge_v20_story_local_repair_v1"
    )
    assert stage6["transport_contract_revision"] == "strict-json-schema-v1"
    assert stage6["model_calls_per_execution"] == 1
    assert stage6["reasoning_effort"] == "low"
    assert stage6["max_tokens"] == 8000
    assert stage6["paid_execution_authorized"] is False
    assert stage6["authorization_consumed"] is True
    assert stage6["next_harness_requirement"] == "stage7_story_reaudit_handoff_ready"

    assert harness["attempt_index"] == 1
    assert harness["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR1"
    assert harness["legacy_ci_trigger_marker"] == (
        "PAID-V20-AGE12-ISLAND-WRITER2"
    )
    assert harness["output_result"] == (
        "age12-island-v20-story-local-repair1-result.json"
    )
    assert harness["output_story"] == (
        "age12-island-v20-story-local-repair1-story.txt"
    )
    assert harness["output_envelope"] == (
        "age12-island-v20-story-local-repair1-envelope.json"
    )
    assert harness["model"] == "anthropic/claude-sonnet-5.5"
    assert harness["request_class"] == "spineforge_v20_story_local_repair"
    assert harness["schema_name"] == "spineforge_v20_story_local_repair_v1"
    assert harness["reasoning_effort"] == "low"
    assert harness["max_tokens"] == 8000
    assert harness["model_calls_per_execution"] == 1
    assert harness["automatic_retry_enabled"] is False
    assert harness["automatic_repair_loop_enabled"] is False
    assert harness["reaudit_executed"] is False
    assert harness["translation_executed"] is False
    assert harness["state_commit_executed"] is False
    assert harness["paid_execution_authorized"] is False


def test_v20_43_freeze_records_stage6_attempt1_noop_failure():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    stage6 = profile["stage6_story_local_repair"]
    attempt1 = stage6["attempt1"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert 36995792496 in q["unreconciled_paid_runs"]
    assert q["unreconciled_paid_api_calls"] == 5

    assert stage6["status"] == "ATTEMPT2_REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage6["paid_execution_authorized"] is False
    assert stage6["authorization_consumed"] is True
    assert stage6["next_harness_requirement"] == "stage7_story_reaudit_handoff_ready"
    assert stage6["paid_harness"]["paid_execution_authorized"] is False

    assert attempt1["run_id"] == 36995792496
    assert attempt1["status"] == "unhandled_story_local_repair_runtime_failure"
    assert attempt1["failure_type"] == "RuntimeError"
    assert attempt1["failure_reason"] == (
        "Repair replacement did not change source: S173"
    )
    assert attempt1["failure_phase"] == (
        "post_provider_repair_payload_validation"
    )
    assert attempt1["provider_call_completed"] is True
    assert attempt1["api_calls"] == 1
    assert attempt1["usage_evidence_persisted"] is False
    assert attempt1["cost_usd"] is None
    assert attempt1["automatic_retry_executed"] is False
    assert attempt1["source_story_mutated"] is False
    assert attempt1["repair_artifact_created"] is False
    assert attempt1["repaired_story_created"] is False
    assert attempt1["reaudit_executed"] is False
    assert attempt1["translation_executed"] is False
    assert attempt1["state_commit_executed"] is False


def test_v20_44_freeze_locks_noop_disposition_and_provider_evidence_capture():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stage6 = profile["stage6_story_local_repair"]

    assert stage6["status"] == "ATTEMPT2_REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage6["paid_execution_authorized"] is False
    assert stage6["authorization_consumed"] is True
    assert stage6["next_harness_requirement"] == (
        "stage7_story_reaudit_handoff_ready"
    )
    assert stage6["repair_contract_revision"] == (
        "local-repair-v2-noop-disposition"
    )
    assert stage6["provider_evidence_capture_revision"] == (
        "post-provider-validation-v2"
    )
    assert stage6["repair_policy"]["no_change_disposition_allowed"] is True
    assert stage6["repair_policy"]["no_change_requires_mandatory_reaudit"] is True
    assert stage6["output_contract"]["no_change_resolutions_preserved"] is True
    assert stage6["output_contract"][
        "provider_usage_preserved_on_post_validation_failure"
    ] is True

    attempt1 = stage6["attempt1"]
    assert attempt1["run_id"] == 36995792496
    assert attempt1["failure_reason"] == (
        "Repair replacement did not change source: S173"
    )
    assert attempt1["provider_call_completed"] is True
    assert attempt1["usage_evidence_persisted"] is False


def test_v20_45_freeze_locks_stage6_attempt2_harness_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    stage6 = profile["stage6_story_local_repair"]
    harness = stage6["paid_harness"]
    attempt1_harness = stage6["attempt1_harness"]

    assert stage6["status"] == "ATTEMPT2_REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage6["repair_attempt_index"] == 2
    assert stage6["authorization_marker"] == (
        "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR2"
    )
    assert stage6["paid_execution_authorized"] is False
    assert stage6["authorization_consumed"] is True
    assert stage6["next_harness_requirement"] == (
        "stage7_story_reaudit_handoff_ready"
    )

    assert attempt1_harness["attempt_index"] == 1
    assert attempt1_harness["authorization_marker"] == (
        "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR1"
    )
    assert attempt1_harness["output_result"] == (
        "age12-island-v20-story-local-repair1-result.json"
    )
    assert attempt1_harness["paid_execution_authorized"] is False

    assert harness["attempt_index"] == 2
    assert harness["authorization_marker"] == stage6["authorization_marker"]
    assert harness["output_result"] == (
        "age12-island-v20-story-local-repair2-result.json"
    )
    assert harness["output_story"] == (
        "age12-island-v20-story-local-repair2-story.txt"
    )
    assert harness["output_envelope"] == (
        "age12-island-v20-story-local-repair2-envelope.json"
    )
    assert harness["repair_contract_revision"] == (
        "local-repair-v2-noop-disposition"
    )
    assert harness["provider_evidence_capture_revision"] == (
        "post-provider-validation-v2"
    )
    assert harness["model_calls_per_execution"] == 1
    assert harness["automatic_retry_enabled"] is False
    assert harness["automatic_repair_loop_enabled"] is False
    assert harness["paid_execution_authorized"] is False


def test_v20_47_freeze_records_stage6_attempt2_and_arms_stage7_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    stage6 = profile["stage6_story_local_repair"]
    attempt2 = stage6["attempt2"]
    product = stage6["stage6_output_artifact"]
    stage7 = profile["stage7_story_reaudit"]
    harness = stage7["paid_harness"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["confirmed_cost_is_lower_bound"] is True

    assert stage6["status"] == "ATTEMPT2_REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage6["paid_execution_authorized"] is False
    assert stage6["authorization_consumed"] is True
    assert stage6["next_harness_requirement"] == "stage7_story_reaudit_handoff_ready"

    assert attempt2["status"] == "repair_generated"
    assert attempt2["api_calls"] == 1
    assert attempt2["input_tokens"] == 20137
    assert attempt2["output_tokens"] == 1958
    assert attempt2["total_tokens"] == 22095
    assert attempt2["cost_usd"] == 0.059854
    assert attempt2["latency_seconds"] == 12.577
    assert attempt2["patch_count"] == 24
    assert attempt2["no_change_resolution_count"] == 1
    assert attempt2["no_change_span_ids"] == ["S161"]
    assert attempt2["repaired_story_text_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
    assert attempt2["automatic_retry_executed"] is False
    assert attempt2["reaudit_executed"] is False

    assert product["artifact_id"] == (
        "story-local-repair:eca2fd757acea1bc5bf982ea3ded100a62fdae68687d0652d61ff729795614f1"
    )
    assert product["stable_span_count"] == 199
    assert product["patch_count"] == 24
    assert product["no_change_resolution_count"] == 1
    assert product["immutable"] is True
    assert product["next_stage"] == "STORY_REAUDIT"

    assert stage7["status"] == "REAUDIT_COMPLETED_LOCAL_REPAIR_REQUIRED"
    assert stage7["stage"] == 7
    assert stage7["source_stage6_artifact_id"] == product["artifact_id"]
    assert stage7["source_repaired_story_sha256"] == product["repaired_story_text_sha256"]
    assert stage7["handoff_artifact_id"] == (
        "story-reaudit-handoff:cff54c7a1491cc5d10724a0d44e8157c8b9e580279b53004c2894e0dc5b06cf3"
    )
    assert stage7["stable_span_count"] == 199
    assert stage7["changed_span_count"] == 24
    assert stage7["no_change_span_ids"] == ["S161"]
    assert stage7["full_story_reaudit_required"] is True
    assert stage7["all_199_stable_spans_required"] is True
    assert stage7["changed_spans_only_forbidden"] is True
    assert stage7["primary_model"] == "anthropic/claude-sonnet-5.5"
    assert stage7["secondary_model"] == "openai/gpt-5.6-sol"
    assert stage7["model_calls_per_execution"] == 2
    assert stage7["paid_execution_authorized"] is False
    assert stage7["authorization_consumed"] is True
    assert stage7["automatic_retry_enabled"] is False
    assert stage7["automatic_repair_loop_enabled"] is False
    assert stage7["next_harness_requirement"] == "stage8_story_local_repair_handoff_ready"
    assert stage7["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-REAUDIT1"

    assert harness["attempt_index"] == 1
    assert harness["model_calls_per_execution"] == 2
    assert harness["automatic_retry_enabled"] is False
    assert harness["automatic_repair_loop_enabled"] is False
    assert harness["paid_execution_authorized"] is False


def test_v20_49_freeze_records_stage7_result_and_arms_stage8_local_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    stage7 = profile["stage7_story_reaudit"]
    attempt1 = stage7["attempt1"]
    product = stage7["stage7_output_artifact"]
    stage8 = profile["stage8_story_local_repair"]
    harness = stage8["paid_harness"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"

    assert stage7["status"] == "REAUDIT_COMPLETED_LOCAL_REPAIR_REQUIRED"
    assert stage7["paid_execution_authorized"] is False
    assert stage7["authorization_consumed"] is True
    assert stage7["next_harness_requirement"] == (
        "stage8_story_local_repair_handoff_ready"
    )

    assert attempt1["status"] == "reaudit_completed"
    assert attempt1["api_calls"] == 2
    assert attempt1["input_tokens"] == 33716
    assert attempt1["output_tokens"] == 6646
    assert attempt1["reasoning_tokens"] == 627
    assert attempt1["total_tokens"] == 40362
    assert attempt1["cost_usd"] == 0.138644
    assert attempt1["latency_seconds"] == 53.53
    assert attempt1["secondary_sentence_scan_count"] == 199
    assert attempt1["artifact_id"] == (
        "story-reaudit:bb0eab55d2c5e5f868fff67c7ce742ecd2a5877c5a82263d6cee8dafbe514874"
    )
    assert attempt1["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert attempt1["next_stage"] == "STORY_LOCAL_REPAIR"
    assert attempt1["finding_count"] == 16
    assert attempt1["s161_language_status"] == "clean"
    assert attempt1["s161_language_editor_action"] == "KEEP"
    assert attempt1["automatic_retry_executed"] is False
    assert attempt1["source_story_mutated"] is False

    assert product["artifact_id"] == (
        "story-reaudit-product:7ec8360d92ab8a77431e78a039340b56277cc2ec7ac2ea301fe847f059655abe"
    )
    assert product["finding_count"] == 16
    assert product["stable_span_count"] == 199
    assert product["immutable"] is True
    assert product["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert product["next_stage"] == "STORY_LOCAL_REPAIR"

    assert stage8["status"] == "REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage8["stage"] == 8
    assert stage8["source_stage7_product_artifact_id"] == product["artifact_id"]
    assert stage8["source_story_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
    assert stage8["handoff_artifact_id"] == (
        "story-local-repair-cycle2-handoff:ccbb5ef3fbed5b5babb5a1ec07f57daa04d62b83eed68d0864b65258d87a1804"
    )
    assert stage8["finding_count"] == 16
    assert stage8["allowed_edit_span_count"] == 16
    assert stage8["repair_cycle_index"] == 2
    assert stage8["paid_attempt_index"] == 3
    assert stage8["model_calls_per_execution"] == 1
    assert stage8["paid_execution_authorized"] is False
    assert stage8["authorization_consumed"] is True
    assert stage8["automatic_retry_enabled"] is False
    assert stage8["automatic_repair_loop_enabled"] is False
    assert stage8["next_harness_requirement"] == "stage9_story_reaudit_handoff_ready"
    assert stage8["authorization_marker"] == (
        "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR3"
    )

    assert harness["paid_attempt_index"] == 3
    assert harness["model_calls_per_execution"] == 1
    assert harness["paid_execution_authorized"] is False


def test_v20_51_freeze_records_stage8_result_and_arms_stage9_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    stage8 = profile["stage8_story_local_repair"]
    attempt3 = stage8["attempt3"]
    product = stage8["stage8_output_artifact"]
    stage9 = profile["stage9_story_reaudit"]
    harness = stage9["paid_harness"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"

    assert stage8["status"] == "REPAIR_GENERATED_AWAITING_REAUDIT"
    assert stage8["paid_execution_authorized"] is False
    assert stage8["authorization_consumed"] is True
    assert stage8["next_harness_requirement"] == "stage9_story_reaudit_handoff_ready"
    assert attempt3["api_calls"] == 1
    assert attempt3["total_tokens"] == 6824
    assert attempt3["cost_usd"] == 0.024016
    assert attempt3["patch_count"] == 14
    assert attempt3["no_change_resolution_count"] == 2
    assert attempt3["no_change_span_ids"] == ["S161", "S182"]
    assert attempt3["repaired_story_text_sha256"] == (
        "b9a4675cd79f458ee8d29fd11f1bb5fdddfe4abec68c394efcddf60fb892eb95"
    )

    assert product["artifact_id"] == (
        "story-local-repair-cycle2:61237a22b0d46ba41cc44f51026b9dc4cf83030d794fdb5668e44bad00a1fa87"
    )
    assert product["stable_span_count"] == 199
    assert product["patch_count"] == 14
    assert product["no_change_resolution_count"] == 2
    assert product["immutable"] is True

    assert stage9["status"] == "REAUDIT_COMPLETED_LOCAL_REPAIR_REQUIRED"
    assert stage9["stage"] == 9
    assert stage9["source_stage8_artifact_id"] == product["artifact_id"]
    assert stage9["source_repaired_story_sha256"] == product["repaired_story_text_sha256"]
    assert stage9["handoff_artifact_id"] == (
        "story-reaudit-cycle2-handoff:1558e2ec00a6c6c0d2365d442dc4eafbafc9663de23443540b53e4f874387474"
    )
    assert stage9["stable_span_count"] == 199
    assert stage9["changed_span_count"] == 14
    assert stage9["no_change_span_ids"] == ["S161", "S182"]
    assert stage9["full_story_reaudit_required"] is True
    assert stage9["all_199_stable_spans_required"] is True
    assert stage9["changed_spans_only_forbidden"] is True
    assert stage9["model_calls_per_execution"] == 2
    assert stage9["paid_execution_authorized"] is False
    assert stage9["authorization_consumed"] is True
    assert stage9["automatic_retry_enabled"] is False
    assert stage9["automatic_repair_loop_enabled"] is False
    assert stage9["next_harness_requirement"] == "story_quality_loop_stage10_handoff_ready"
    assert stage9["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-REAUDIT2"
    assert harness["reaudit_attempt_index"] == 2
    assert harness["model_calls_per_execution"] == 2
    assert harness["paid_execution_authorized"] is False


def test_v20_53_freeze_records_stage9_result_and_arms_generic_quality_loop():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    stage9 = profile["stage9_story_reaudit"]
    attempt2 = stage9["attempt2"]
    generic_product = stage9["generic_output_artifact"]
    loop = profile["story_quality_loop"]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["confirmed_cost_is_lower_bound"] is True

    assert stage9["status"] == "REAUDIT_COMPLETED_LOCAL_REPAIR_REQUIRED"
    assert stage9["paid_execution_authorized"] is False
    assert stage9["authorization_consumed"] is True
    assert stage9["next_harness_requirement"] == (
        "story_quality_loop_stage10_handoff_ready"
    )
    assert stage9["paid_harness"]["paid_execution_authorized"] is False

    assert attempt2["status"] == "reaudit_completed"
    assert attempt2["api_calls"] == 2
    assert attempt2["input_tokens"] == 33657
    assert attempt2["output_tokens"] == 6173
    assert attempt2["reasoning_tokens"] == 456
    assert attempt2["total_tokens"] == 39830
    assert attempt2["cost_usd"] == 0.133791
    assert attempt2["latency_seconds"] == 49.587
    assert attempt2["secondary_sentence_scan_count"] == 199
    assert attempt2["artifact_id"] == (
        "story-reaudit-cycle2:2780e90ca97e25a57131c5632fe8ececf146e62f60ae1be86032376a7d6e3744"
    )
    assert attempt2["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert attempt2["finding_count"] == 12
    assert attempt2["s161_language_status"] == "clean"
    assert attempt2["s182_language_status"] == "clean"

    assert generic_product["artifact_id"] == (
        "story-quality-reaudit:4aabbacb8c8d3b99c1139b3908b30c6a52e9125a421819ca2af4b626880a6711"
    )
    assert generic_product["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert generic_product["finding_count"] == 12
    assert generic_product["stable_span_count"] == 199
    assert generic_product["immutable"] is True

    # Mutable loop execution state advances in later freezes. Historical
    # v20.53 regression locks only stable generic-loop identity here.
    assert loop["loop_revision"] == "story-quality-loop-v1"
    assert loop["authorization_marker"] == "PAID-V20-STORY-QUALITY-LOOP"
    assert loop["generic_core"] == "src/spineforge_v20_story_quality_loop.py"
    assert loop["generic_paid_wrapper"] == (
        "src/spineforge_v20_paid_story_quality_loop_once.py"
    )


def test_v20_55_freeze_records_generic_stage10_and_arms_stage11_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage10:local-repair:cycle3:attempt4"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37112601598
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 10
    assert completed["cycle_index"] == 3
    assert completed["paid_attempt_index"] == 4
    assert completed["action_authorization_id"] == (
        "story-quality-loop:stage10:local-repair:cycle3:attempt4"
    )
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 4602
    assert completed["output_tokens"] == 963
    assert completed["total_tokens"] == 5565
    assert completed["cost_usd"] == 0.018834
    assert completed["latency_seconds"] == 7.895
    assert completed["patch_count"] == 13
    assert completed["no_change_resolution_count"] == 0
    assert completed["repaired_story_sha256"] == (
        "4d0eba33f863b71922d58c83428ba59c9238132c424c9c672398b4f873ea9e50"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:04c796ccc1d32a7ef8d5de968a6827b2df06c77bf36a70afd24dd6f53185bc3f"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:35fcf5c6f4fd244128e135777eb774648187b6c636e7be821d0dcff0ed7a67c1"
    )
    assert completed["next_state_status"] == "NEXT_ACTION_READY_NOT_AUTHORIZED"
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 11
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["product_sha256"] == (
        "2a8b4d52c4075f3d6fb0995503c6185d4d831288561712bcce59e8f8a83b9f85"
    )
    assert artifacts["handoff_sha256"] == (
        "eab9d735c53a52fd79c189b5c1ad77053b477871cc40a107db1d37a1cfaa38dc"
    )
    assert artifacts["story_file_sha256"] == (
        "c6cf5165517eda19fbce51960a924d9924e256dcdaff5fa789d4e288d2e35b05"
    )



def test_v20_57_freeze_recovers_stage11_postprocess_and_arms_stage12_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage11:reaudit:cycle3:attempt3"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37113502767
    assert completed["workflow_conclusion"] == "failure"
    assert completed["model_inference_completed"] is True
    assert completed["postprocess_recovered"] is True
    assert completed["paid_inference_reexecuted"] is False
    assert completed["action"] == "REAUDIT"
    assert completed["stage"] == 11
    assert completed["cycle_index"] == 3
    assert completed["status"] == "reaudit_completed"
    assert completed["api_calls"] == 2
    assert completed["input_tokens"] == 33646
    assert completed["output_tokens"] == 6742
    assert completed["reasoning_tokens"] == 625
    assert completed["cache_write_tokens"] == 9503
    assert completed["total_tokens"] == 40388
    assert completed["cost_usd"] == 0.1394635
    assert completed["latency_seconds"] == 50.696
    assert completed["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert completed["finding_count"] == 16
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:04c796ccc1d32a7ef8d5de968a6827b2df06c77bf36a70afd24dd6f53185bc3f"
    )
    assert completed["source_story_sha256"] == (
        "4d0eba33f863b71922d58c83428ba59c9238132c424c9c672398b4f873ea9e50"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-reaudit:8d05687aba9dbdd29ad56a228bf64031d3295b2f907b17373c03b71ebc9d587c"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-repair-handoff:5279ec83916ff6bb653594fa5b91beba663d6f2ee825131c8ba54708bff70cf6"
    )
    assert completed["next_action"] == "LOCAL_REPAIR"
    assert completed["next_stage"] == 12
    assert completed["next_cycle_index"] == 4
    assert completed["next_paid_attempt_index"] == 5
    assert completed["next_paid_execution_authorized"] is False
    assert completed["recovery_artifact_id"] == (
        "story-quality-postprocess-recovery:8bd9675b25211d5ed7ffef8d8ec3c99dc23209cd8de140e892311fb4521248d2"
    )

    assert artifacts["result_sha256"] == (
        "045fe225869bd2bf69dcafabcb21b8114cd80d65466295479ac9305633be7687"
    )
    assert artifacts["raw_envelope_sha256"] == (
        "0654f7a2f1368219de4ab379904e1ffa3a58cbfd19844e9355e88463abd1d3b1"
    )
    assert artifacts["recovered_envelope_sha256"] == (
        "52cee93821ca5897bda8d608b1b0323eed644aa1d92a5c7aefe5e18c8b2f3dbd"
    )
    assert artifacts["product_sha256"] == (
        "1b9a68943f1bd302c347667cd84892cad41f04faa7eca47152c54d548734ee74"
    )
    assert artifacts["handoff_sha256"] == (
        "e56d3791a6fcc4247ce493fdb8266de440fd8a9cb3b8cda9106dbc78ad6b7ae6"
    )
    assert artifacts["next_state_sha256"] == (
        "664771ee0d6bf22a2baf3921a308dd1369ecbf95b0d117ff1b5857ec8ad61726"
    )
    assert artifacts["recovery_sha256"] == (
        "019451f76d4d5257c3d6d7b34cacea02691c1396a5ad7f1e04105042f0a160dd"
    )



def test_v20_59_freeze_records_stage12_repair_and_arms_stage13_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage12:local-repair:cycle4:attempt5"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["confirmed_cost_is_lower_bound"] is True

    assert completed["run_id"] == 37114732160
    assert completed["workflow_conclusion"] == "success"
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 12
    assert completed["cycle_index"] == 4
    assert completed["paid_attempt_index"] == 5
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 5585
    assert completed["output_tokens"] == 1257
    assert completed["reasoning_tokens"] == 0
    assert completed["total_tokens"] == 6842
    assert completed["cost_usd"] == 0.02374
    assert completed["latency_seconds"] == 9.231
    assert completed["patch_count"] == 16
    assert completed["no_change_resolution_count"] == 1
    assert completed["no_change_span_ids"] == ["S041"]
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:04c796ccc1d32a7ef8d5de968a6827b2df06c77bf36a70afd24dd6f53185bc3f"
    )
    assert completed["source_story_sha256"] == (
        "4d0eba33f863b71922d58c83428ba59c9238132c424c9c672398b4f873ea9e50"
    )
    assert completed["repaired_story_sha256"] == (
        "5ed1b79faf8ef59aa3f5f998c7712f147553ee5e3e5dbd7e769290928e732dad"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:5fdefd5afee8f57e6d88b5269acbb370849a01e889d249e8a3d9ad74afa95979"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:159d8b48c9d51e34b506975e61754d89d3011c5e55445b38e19152dd2f90c437"
    )
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 13
    assert completed["next_cycle_index"] == 4
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "def9f41d1b105c9d3c3aa7d046494e158421a8dbac8a6dba2617bf84baaeb863"
    )
    assert artifacts["story_file_sha256"] == (
        "88207a25444560ab468b204f1a7387095f185305cee788f0f2e3f1540fa66cc8"
    )
    assert artifacts["product_sha256"] == (
        "cae7cd0029808e5b51c346cc94c1bfca2f7884ae185aa2d5367969f5909b1332"
    )
    assert artifacts["handoff_sha256"] == (
        "1abe614940a84d8c6c20bcfce7f5472c6049e928378895f819538651aedf49fd"
    )
    assert artifacts["envelope_sha256"] == (
        "5b63ddcebba94d5b35aaf88f487c6685616e819714ff91a1e9da50b9c9bcf029"
    )
    assert artifacts["next_state_sha256"] == (
        "67aa242f3cbc8ae684c340654373caf774e119727755ef7e261a7d6eeba75add"
    )



def test_v20_61_freeze_records_stage13_primary_contract_failure_and_retry_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage13:reaudit:cycle4:attempt4"
    failed = loop["failed_actions"][key]
    artifacts = loop["failed_artifacts"][key]

    assert failed["run_id"] == 37117361651
    assert failed["workflow_conclusion"] == "success"
    assert failed["action"] == "REAUDIT"
    assert failed["stage"] == 13
    assert failed["cycle_index"] == 4
    assert failed["action_authorization_id"] == key
    assert failed["status"] == "unhandled_story_quality_loop_runtime_failure"
    assert failed["failure_type"] == "RuntimeError"
    assert failed["provider_call_confirmed"] is True
    assert failed["provider_call_count"] == 1
    assert failed["provider_call_usage_reconciled"] is False
    assert failed["provider_call_cost_reconciled"] is False
    assert failed["secondary_auditor_executed"] is False
    assert failed["automatic_retry_executed"] is False
    assert failed["automatic_paid_transition_executed"] is False
    assert failed["raw_response_persisted"] is False
    assert failed["failure_phase"] == "post_provider_auditor_payload_validation"
    assert failed["contract_failure"] == (
        "PRIMARY_AUDIT_CANONICAL_FAMILY_SET_INCOMPLETE"
    )
    assert "canon_integrity" in failed["failure_message"]

    assert artifacts["result_sha256"] == (
        "8fece1b998b4e947961a25540a3e1ccb1e15d9c5a4b644a1bf5df08c72da363b"
    )
    assert artifacts["envelope_sha256"] == (
        "ddbddae9ddcf31c47d956a0574650185e650f976fcaeff74113729e80cc1653e"
    )




def test_v20_63_freeze_records_stage13_retry1_and_arms_stage14_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage13:reaudit:cycle4:attempt4-retry1"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37118083538
    assert completed["workflow_conclusion"] == "success"
    assert completed["model_inference_completed"] is True
    assert completed["postprocess_recovered"] is False
    assert completed["paid_inference_reexecuted"] is True
    assert completed["retry_of_action_authorization_id"] == (
        "story-quality-loop:stage13:reaudit:cycle4:attempt4"
    )
    assert completed["action"] == "REAUDIT"
    assert completed["stage"] == 13
    assert completed["cycle_index"] == 4
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "reaudit_completed"
    assert completed["api_calls"] == 2
    assert completed["input_tokens"] == 33924
    assert completed["output_tokens"] == 6577
    assert completed["reasoning_tokens"] == 468
    assert completed["cache_write_tokens"] == 9514
    assert completed["total_tokens"] == 40501
    assert completed["cost_usd"] == 0.138375
    assert completed["latency_seconds"] == 47.602
    assert completed["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert completed["finding_count"] == 16
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:5fdefd5afee8f57e6d88b5269acbb370849a01e889d249e8a3d9ad74afa95979"
    )
    assert completed["source_story_sha256"] == (
        "5ed1b79faf8ef59aa3f5f998c7712f147553ee5e3e5dbd7e769290928e732dad"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-reaudit:c9833daeaf489c799d44f57c7732283b8e2e21d1a6e5b5402cce02b08cf55097"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-repair-handoff:069193908f57d3daa13786b9747184bc7afab24aeba0397b0367c38b6dab10a2"
    )
    assert completed["next_action"] == "LOCAL_REPAIR"
    assert completed["next_stage"] == 14
    assert completed["next_cycle_index"] == 5
    assert completed["next_paid_attempt_index"] == 6
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["automatic_paid_transition_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "023dccff5a9b33408936fa72db84a0c4f73dc1c69597ca0d5a80299720e354bc"
    )
    assert artifacts["product_sha256"] == (
        "2a92b5591e12a5498042445cd291f3a3aa961cb111d96b34d3d56c52ecfd3536"
    )
    assert artifacts["handoff_sha256"] == (
        "7df0530f260305fa48277b794139a3d750c1fc14540fb4813b8da15f38606c5d"
    )
    assert artifacts["envelope_sha256"] == (
        "babcb14ad0a676d41c5e9baebaec22711f59e8d18d16d594c94f6d92e679cf98"
    )
    assert artifacts["next_state_sha256"] == (
        "e78c264010a9de7e740564908517e7febb8e865dcd17f98f640db4ef801181b2"
    )



def test_v20_65_freeze_records_stage14_repair_and_arms_stage15_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage14:local-repair:cycle5:attempt6"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37118698592
    assert completed["workflow_conclusion"] == "success"
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 14
    assert completed["cycle_index"] == 5
    assert completed["paid_attempt_index"] == 6
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 5642
    assert completed["output_tokens"] == 1250
    assert completed["reasoning_tokens"] == 0
    assert completed["total_tokens"] == 6892
    assert completed["cost_usd"] == 0.023784
    assert completed["latency_seconds"] == 9.108
    assert completed["patch_count"] == 17
    assert completed["no_change_resolution_count"] == 1
    assert completed["no_change_span_ids"] == ["S074"]
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:5fdefd5afee8f57e6d88b5269acbb370849a01e889d249e8a3d9ad74afa95979"
    )
    assert completed["source_story_sha256"] == (
        "5ed1b79faf8ef59aa3f5f998c7712f147553ee5e3e5dbd7e769290928e732dad"
    )
    assert completed["repaired_story_sha256"] == (
        "87cf6fa5c147f26061a5f7ab1705e6c9fc6ede7d8f41c83b671ef796f8af7084"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:e019e707707a99c7cabf1c4c9d97e546b7ee89a8baafc4da96b7748beb864abd"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:7f1594a1c2b1eace1813e725ac797d3436138a8bb4ff3c75e7945cde94cd5a87"
    )
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 15
    assert completed["next_cycle_index"] == 5
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "3e538b1bde961ae6150bcefcf842d2d2be9295d2fb98c87cf6c1e80b33649f7a"
    )
    assert artifacts["story_file_sha256"] == (
        "7edd824f4a054304aa7ac98f535df107b3a500ced83ba52c21a2e6d4caa262aa"
    )
    assert artifacts["product_sha256"] == (
        "5b2303522a4098a6d537b23d81019c3c3370d5cba6f221c866e2451a4f9972f5"
    )
    assert artifacts["handoff_sha256"] == (
        "8883d2b39f7fb51ab246e746d5825ac55c6cf95c5f3c10b0a3969a155d8d41a6"
    )
    assert artifacts["envelope_sha256"] == (
        "faa181802348350d6da97557958ff547c339a1a83346b9d30fa214f0f79edd00"
    )
    assert artifacts["next_state_sha256"] == (
        "1992aa23733b20f0a367147f0980d0370074069c38a0c38a4e304e7105cb6964"
    )



def test_v20_67_freeze_records_stage15_reaudit_and_arms_stage16_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage15:reaudit:cycle5:attempt5"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37119148378
    assert completed["workflow_conclusion"] == "success"
    assert completed["model_inference_completed"] is True
    assert completed["postprocess_recovered"] is False
    assert completed["paid_inference_reexecuted"] is False
    assert completed["action"] == "REAUDIT"
    assert completed["stage"] == 15
    assert completed["cycle_index"] == 5
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "reaudit_completed"
    assert completed["api_calls"] == 2
    assert completed["input_tokens"] == 33949
    assert completed["output_tokens"] == 6930
    assert completed["reasoning_tokens"] == 909
    assert completed["cache_write_tokens"] == 9526
    assert completed["total_tokens"] == 40879
    assert completed["cost_usd"] == 0.141961
    assert completed["latency_seconds"] == 53.76
    assert completed["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert completed["finding_count"] == 17
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:e019e707707a99c7cabf1c4c9d97e546b7ee89a8baafc4da96b7748beb864abd"
    )
    assert completed["source_story_sha256"] == (
        "87cf6fa5c147f26061a5f7ab1705e6c9fc6ede7d8f41c83b671ef796f8af7084"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-reaudit:1dbbc7858e205e7a9d02e89d48813dbdd8791e83558e1e9716ff00312d8b1e30"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-repair-handoff:2b62a5957076ae11c9b338333be8c061cfc9d16a1d7fdf6089b873b0a5d2519e"
    )
    assert completed["next_action"] == "LOCAL_REPAIR"
    assert completed["next_stage"] == 16
    assert completed["next_cycle_index"] == 6
    assert completed["next_paid_attempt_index"] == 7
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["automatic_paid_transition_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "fa2652c8be1b966536ddbc128f216816bfcd199995e96f894d5c9bfa93004a64"
    )
    assert artifacts["product_sha256"] == (
        "e7209a569f55844827ddd79c11df4268846448d9e42e479ecc6e76cf90db1ad0"
    )
    assert artifacts["handoff_sha256"] == (
        "a2f0b9a9b1aac48ccc73c6a15df6e631a3154ff67fc12ed3144905a313c8798c"
    )
    assert artifacts["envelope_sha256"] == (
        "6bc53b926ba2ba25ad6e8994f8b0c6f15e34111b379aa9f08dc8a3bf61d86aed"
    )
    assert artifacts["next_state_sha256"] == (
        "5567f185969c24e46d497ade16e4cedeb9cb1db76f0f186717350dfecf77e4a6"
    )



def test_v20_69_freeze_records_stage16_repair_and_arms_stage17_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage16:local-repair:cycle6:attempt7"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37120885185
    assert completed["workflow_conclusion"] == "success"
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 16
    assert completed["cycle_index"] == 6
    assert completed["paid_attempt_index"] == 7
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 5640
    assert completed["output_tokens"] == 1224
    assert completed["reasoning_tokens"] == 0
    assert completed["total_tokens"] == 6864
    assert completed["cost_usd"] == 0.02352
    assert completed["latency_seconds"] == 7.97
    assert completed["patch_count"] == 16
    assert completed["no_change_resolution_count"] == 1
    assert completed["no_change_span_ids"] == ["S172"]
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:e019e707707a99c7cabf1c4c9d97e546b7ee89a8baafc4da96b7748beb864abd"
    )
    assert completed["source_story_sha256"] == (
        "87cf6fa5c147f26061a5f7ab1705e6c9fc6ede7d8f41c83b671ef796f8af7084"
    )
    assert completed["repaired_story_sha256"] == (
        "41563f875a3f6b32837ec0ff7d65bc5b596cb83c01d596d5b1e107fc3ad07701"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:450b24aaaa9630dabe2edee652f92390fb889711fea8cd02a06061e06c56a520"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:b14f97527b5db64c79bdf7a0c15a0627e870ea0920f318b414c7c0fa953524e3"
    )
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 17
    assert completed["next_cycle_index"] == 6
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "c2cd27f3998859f2aee73f3131b795b6364b45c3d6284a57ef1cb5fdaf00179b"
    )
    assert artifacts["story_file_sha256"] == (
        "9136d8dd8746a5fc67976d3fc06ae224c12c9ca8df816bda3b1ddd742253e137"
    )
    assert artifacts["product_sha256"] == (
        "2e2c72876131933d45d60b25dc5d8cf79266a1ee045b4483acf711c22c4a77bd"
    )
    assert artifacts["handoff_sha256"] == (
        "8b4676822ed84cb0486c8a86637ef6860dfe60601b918aed5a73a0a6268dd77f"
    )
    assert artifacts["envelope_sha256"] == (
        "44f68749a1763daefae1d9aa3be9dbea1881ac812a88aa0dd40501c22d713e13"
    )
    assert artifacts["next_state_sha256"] == (
        "ca68a118a1bbe24c458cae5b3d2088d2ab33c45bed84e7ada7fe44dc1062f7c7"
    )



def test_v20_71_freeze_records_stage17_reaudit_and_arms_stage18_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage17:reaudit:cycle6:attempt6"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37124277479
    assert completed["workflow_conclusion"] == "success"
    assert completed["model_inference_completed"] is True
    assert completed["postprocess_recovered"] is False
    assert completed["paid_inference_reexecuted"] is False
    assert completed["action"] == "REAUDIT"
    assert completed["stage"] == 17
    assert completed["cycle_index"] == 6
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "reaudit_completed"
    assert completed["api_calls"] == 2
    assert completed["input_tokens"] == 33914
    assert completed["output_tokens"] == 6503
    assert completed["reasoning_tokens"] == 849
    assert completed["cache_write_tokens"] == 9512
    assert completed["total_tokens"] == 40417
    assert completed["cost_usd"] == 0.137614
    assert completed["latency_seconds"] == 50.83
    assert completed["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert completed["finding_count"] == 13
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:450b24aaaa9630dabe2edee652f92390fb889711fea8cd02a06061e06c56a520"
    )
    assert completed["source_story_sha256"] == (
        "41563f875a3f6b32837ec0ff7d65bc5b596cb83c01d596d5b1e107fc3ad07701"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-reaudit:913fda3c0030c1b837a0735d7c36e88f86982bb83d4b00488540def157d10c93"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-repair-handoff:0667c9e17606377a2c84fde823b91957b9c34da2db9d054f402c6566b1d82416"
    )
    assert completed["next_action"] == "LOCAL_REPAIR"
    assert completed["next_stage"] == 18
    assert completed["next_cycle_index"] == 7
    assert completed["next_paid_attempt_index"] == 8
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["automatic_paid_transition_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "3bd4fc301cb0374f6c3ebf73ef970f4efe5f35122c7e052579808050a234cd21"
    )
    assert artifacts["product_sha256"] == (
        "9fd3bc9feb79fe6e6de50dbd549d75e268e9550ec90df2c90ba508ff61c40014"
    )
    assert artifacts["handoff_sha256"] == (
        "b16e3b4b0fe5ff3340c2d155844cdff31bacb81b6fd5cd0cafd8e7928912712a"
    )
    assert artifacts["envelope_sha256"] == (
        "bea6584fe2660715a5e0f303a6a54c1648ca76fcbbba58019f00fbbcdcad60e0"
    )
    assert artifacts["next_state_sha256"] == (
        "d448585b5666410c3ef26ca5f3cd0bdc75c98e7c23d022ce90d5f64571754d7f"
    )



def test_v20_73_freeze_records_stage18_repair_and_arms_stage19_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage18:local-repair:cycle7:attempt8"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert completed["run_id"] == 37125599738
    assert completed["workflow_conclusion"] == "success"
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 18
    assert completed["cycle_index"] == 7
    assert completed["paid_attempt_index"] == 8
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 4582
    assert completed["output_tokens"] == 890
    assert completed["reasoning_tokens"] == 0
    assert completed["total_tokens"] == 5472
    assert completed["cost_usd"] == 0.018064
    assert completed["latency_seconds"] == 6.959
    assert completed["patch_count"] == 12
    assert completed["no_change_resolution_count"] == 1
    assert completed["no_change_span_ids"] == ["S175"]
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:450b24aaaa9630dabe2edee652f92390fb889711fea8cd02a06061e06c56a520"
    )
    assert completed["source_story_sha256"] == (
        "41563f875a3f6b32837ec0ff7d65bc5b596cb83c01d596d5b1e107fc3ad07701"
    )
    assert completed["repaired_story_sha256"] == (
        "e85e8322cd50cbbc835f1e536c446e3c4173f24ca81bb87bacd4524dd14a2810"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:c5d305cf7cae34e1d56ca8516313d0d8f95e5ef06189af65bf5f8ed620f3f614"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:84b26be211e538d62778d59c69d90f8a17c8e72b60a78478c010e5d513285ee7"
    )
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 19
    assert completed["next_cycle_index"] == 7
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "f24090aa988e2e92dd51a2fb442f85e4b16b6a254426d277de83bc37bd6fd5de"
    )
    assert artifacts["story_file_sha256"] == (
        "4917292f62c6be211de0e228bfbb8322a5ae7a55398086ba1cd4a6512d691766"
    )
    assert artifacts["product_sha256"] == (
        "322b9b064f5c519882fa36c0e609f712b7c5a7944179dceed4c371654bf187a6"
    )
    assert artifacts["handoff_sha256"] == (
        "8694a6b40f28f85ab3c2e7128cdbc01cf4178f0c716aee22066d8f6a0fcc6661"
    )
    assert artifacts["envelope_sha256"] == (
        "09ecb4eaa8e55ab38339edb25c445d1049b14f9f865ed7f48eb715bedb1de4b6"
    )
    assert artifacts["next_state_sha256"] == (
        "201c99c060d16fab8966d023597191170cf21456173b87a1a0b5aa95236fd635"
    )



def test_v20_75_freeze_records_stage19_locator_failure_and_arms_retry1():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage19:reaudit:cycle7:attempt7"
    failed = loop["failed_actions"][key]
    artifacts = loop["failed_artifacts"][key]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == (
        "story_quality_loop_stage22_repair_generated"
    )
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_run_ids"] == [37117361651, 37126453862]
    assert q["latest_unreconciled_paid_run_id"] == 37126453862
    assert q["latest_unreconciled_paid_call_count"] == 2
    assert q["latest_unreconciled_paid_reason"] == (
        "STAGE19_POST_PROVIDER_LOCATOR_FAILURE_USAGE_NOT_PERSISTED"
    )
    assert q["unreconciled_paid_call_counts_by_run"] == {
        "37117361651": 1,
        "37126453862": 2,
    }

    assert failed["run_id"] == 37126453862
    assert failed["workflow_conclusion"] == "success"
    assert failed["action"] == "REAUDIT"
    assert failed["stage"] == 19
    assert failed["cycle_index"] == 7
    assert failed["action_authorization_id"] == key
    assert failed["status"] == "unhandled_story_quality_loop_runtime_failure"
    assert failed["failure_type"] == "RuntimeError"
    assert failed["failure_message"] == (
        "Story Audit locator repair requires exact_text to resolve uniquely "
        "in frozen story: language_naturalness:0"
    )
    assert failed["provider_call_confirmed"] is True
    assert failed["provider_call_count"] == 2
    assert failed["provider_call_usage_reconciled"] is False
    assert failed["provider_call_cost_reconciled"] is False
    assert failed["primary_auditor_executed"] is True
    assert failed["secondary_auditor_executed"] is True
    assert failed["automatic_retry_executed"] is False
    assert failed["automatic_paid_transition_executed"] is False
    assert failed["raw_response_persisted"] is False
    assert failed["failure_phase"] == "post_provider_locator_repair"
    assert failed["contract_failure"] == (
        "LOCAL_REPAIR_EXACT_TEXT_NOT_LITERAL_IN_VALID_FROZEN_SPAN"
    )

    assert artifacts["result_sha256"] == (
        "5109c6a65f3d0238c27f87e0306c83b550717341b362fed1a36b14f73696727d"
    )
    assert artifacts["envelope_sha256"] == (
        "2a08431ae5cba0cffa2148de2e422d5a8c973c343b43d159c3c32afcc96fc3e1"
    )


def test_v20_77_freeze_records_stage19_retry1_and_arms_stage20_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage19:reaudit:cycle7:attempt7-retry1"
    failed_key = "story-quality-loop:stage19:reaudit:cycle7:attempt7"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == (
        "story_quality_loop_stage22_repair_generated"
    )
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_run_ids"] == [37117361651, 37126453862]
    assert q["latest_unreconciled_paid_run_id"] == 37126453862
    assert q["latest_unreconciled_paid_call_count"] == 2

    assert completed["run_id"] == 37194766432
    assert completed["workflow_conclusion"] == "success"
    assert completed["model_inference_completed"] is True
    assert completed["postprocess_recovered"] is False
    assert completed["paid_inference_reexecuted"] is True
    assert completed["retry_of_action_authorization_id"] == failed_key
    assert completed["action"] == "REAUDIT"
    assert completed["stage"] == 19
    assert completed["cycle_index"] == 7
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "reaudit_completed"
    assert completed["api_calls"] == 2
    assert completed["input_tokens"] == 33876
    assert completed["output_tokens"] == 6022
    assert completed["reasoning_tokens"] == 327
    assert completed["cache_write_tokens"] == 9503
    assert completed["total_tokens"] == 39898
    assert completed["cost_usd"] == 0.1327235
    assert completed["latency_seconds"] == 41.187
    assert completed["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert completed["finding_count"] == 12
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:c5d305cf7cae34e1d56ca8516313d0d8f95e5ef06189af65bf5f8ed620f3f614"
    )
    assert completed["source_story_sha256"] == (
        "e85e8322cd50cbbc835f1e536c446e3c4173f24ca81bb87bacd4524dd14a2810"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-reaudit:542094661143c22c823ffcd207068ecb1057511973921a1d99bf00ab4e798761"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-repair-handoff:dfeeedb17cdcd396a569059fe5f418cd002ab7a364fe0e2b03774560ed4ed88a"
    )
    assert completed["next_action"] == "LOCAL_REPAIR"
    assert completed["next_stage"] == 20
    assert completed["next_cycle_index"] == 8
    assert completed["next_paid_attempt_index"] == 9
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["automatic_paid_transition_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "31980c5f5e9da514fee5f4194004d17438e1e9a5b016f832551505b3c0928007"
    )
    assert artifacts["product_sha256"] == (
        "284e47fd5f5bd9b5235abf3dd3d61be52986e88737c98c48b40a7583a7735c07"
    )
    assert artifacts["handoff_sha256"] == (
        "b4ef959d38274d829b4e9514f8d8b9eb39277f44cf38464470699375d0c7c043"
    )
    assert artifacts["envelope_sha256"] == (
        "7ac69794170da85901fe4c97954255886f473d8786b391c820eb5dce1007db79"
    )
    assert artifacts["next_state_sha256"] == (
        "84e9d79c963e25bfb7295bf0f7f9d913ad2da36addea035e85f10599639ee882"
    )


def test_v20_79_freeze_records_stage20_repair_and_arms_stage21_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage20:local-repair:cycle8:attempt9"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_run_ids"] == [37117361651, 37126453862]

    assert completed["run_id"] == 37196489485
    assert completed["workflow_conclusion"] == "success"
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 20
    assert completed["cycle_index"] == 8
    assert completed["paid_attempt_index"] == 9
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 5053
    assert completed["output_tokens"] == 1291
    assert completed["reasoning_tokens"] == 0
    assert completed["total_tokens"] == 6344
    assert completed["cost_usd"] == 0.023016
    assert completed["latency_seconds"] == 9.103
    assert completed["patch_count"] == 16
    assert completed["no_change_resolution_count"] == 2
    assert completed["no_change_span_ids"] == ["S080", "S183"]
    assert completed["changed_span_ids"] == [
        "S042", "S050", "S052", "S058", "S074", "S082", "S158", "S161",
        "S167", "S170", "S172", "S174", "S175", "S176", "S177", "S195",
    ]
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:c5d305cf7cae34e1d56ca8516313d0d8f95e5ef06189af65bf5f8ed620f3f614"
    )
    assert completed["source_story_sha256"] == (
        "e85e8322cd50cbbc835f1e536c446e3c4173f24ca81bb87bacd4524dd14a2810"
    )
    assert completed["repaired_story_sha256"] == (
        "82c54f27838fa43c601e28b30c61eec9dfd476403c618da3bba67b49d2a20e4e"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:64e2ca03b51a9ef11f7b89ea97de7ed93a16aee7b24036ad1f23ebe94b09cf3e"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:43e4c7e6692e806418d6a31abd1ad2ab4c9eaf728977ef2b4e45fd8505741375"
    )
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 21
    assert completed["next_cycle_index"] == 8
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "14ffaa4a597f1abaf89d08670a48db7f3b096bbc3c6eed9a5d57510c4b2f8505"
    )
    assert artifacts["story_file_sha256"] == (
        "c48f6ddc67c07d9e1c09411caccd7ab98454a9c018c83dc3592a1b379aaaafff"
    )
    assert artifacts["product_sha256"] == (
        "916e6ae2dc1b9e547fd3513e8dd4f7db247a45e168971e246bd4f7062c4a3611"
    )
    assert artifacts["handoff_sha256"] == (
        "e7c7b71d0724248eff7387c11d6013b6248172bf3bfe1cd15524f175c59a2d81"
    )
    assert artifacts["envelope_sha256"] == (
        "f86ff1822f7bde3bb8ad2dad7bf1e4c855a8119ca743672b5eeb55a05f42baab"
    )
    assert artifacts["next_state_sha256"] == (
        "69d3245faafc5ff7f6aeee8539178b9b53a1b27360afc706668e795dc1c4d9c6"
    )


def test_v20_81_freeze_records_stage21_reaudit_and_arms_stage22_repair():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage21:reaudit:cycle8:attempt8"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == (
        "story_quality_loop_stage22_repair_generated"
    )
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_run_ids"] == [37117361651, 37126453862]

    assert completed["run_id"] == 37196986989
    assert completed["workflow_conclusion"] == "success"
    assert completed["model_inference_completed"] is True
    assert completed["postprocess_recovered"] is False
    assert completed["paid_inference_reexecuted"] is False
    assert completed["action"] == "REAUDIT"
    assert completed["stage"] == 21
    assert completed["cycle_index"] == 8
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "reaudit_completed"
    assert completed["api_calls"] == 2
    assert completed["input_tokens"] == 34008
    assert completed["output_tokens"] == 6438
    assert completed["reasoning_tokens"] == 484
    assert completed["cache_write_tokens"] == 9556
    assert completed["total_tokens"] == 40446
    assert completed["cost_usd"] == 0.137174
    assert completed["latency_seconds"] == 47.237
    assert completed["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert completed["finding_count"] == 15
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:64e2ca03b51a9ef11f7b89ea97de7ed93a16aee7b24036ad1f23ebe94b09cf3e"
    )
    assert completed["source_story_sha256"] == (
        "82c54f27838fa43c601e28b30c61eec9dfd476403c618da3bba67b49d2a20e4e"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-reaudit:c615452238419a3fc9068834643721d8f677b205f3ab8af0fba752cecbcb0e26"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-repair-handoff:d12ca08791cf26ce15e5aff229aa0da5442dbe4fb44f416bc9db725a5fd93a31"
    )
    assert completed["next_action"] == "LOCAL_REPAIR"
    assert completed["next_stage"] == 22
    assert completed["next_cycle_index"] == 9
    assert completed["next_paid_attempt_index"] == 10
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["automatic_paid_transition_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert artifacts["result_sha256"] == (
        "7b6e35900f50702530f9e8463f055360c360e2141cd73bf92fbb6715b6170328"
    )
    assert artifacts["product_sha256"] == (
        "6181dfdbdaf3a3b17418879ae3739849427ae78e3e40329a6cc88e8f44d1f33a"
    )
    assert artifacts["handoff_sha256"] == (
        "d492214fa8b15cfda3688bc4d2fe76e9adcaf727ae5c4682a3d4eb8f2c0043da"
    )
    assert artifacts["envelope_sha256"] == (
        "a175da273726cfe23ddd0480a8c0ef3972ad6ed07ac8861e5dac47dfdb39354e"
    )
    assert artifacts["next_state_sha256"] == (
        "276b41396c7e76f284ae2ff6cdeb91db9a6ee4271b355eed31cb08115ae06e1d"
    )


def test_v20_83_freeze_records_stage22_repair_and_arms_stage23_reaudit():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    loop = profile["story_quality_loop"]
    key = "story-quality-loop:stage22:local-repair:cycle9:attempt10"
    completed = loop["completed_actions"][key]
    artifacts = loop["completed_artifacts"][key]

    assert q["paid_api_calls"] == 52
    assert q["confirmed_cost_usd"] == 2.3789534
    assert q["last_paid_run_id"] == 37203303622
    assert q["last_result"] == "story_quality_loop_stage22_repair_generated"
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_run_ids"] == [37117361651, 37126453862]

    assert completed["run_id"] == 37203303622
    assert completed["workflow_conclusion"] == "success"
    assert completed["action"] == "LOCAL_REPAIR"
    assert completed["stage"] == 22
    assert completed["cycle_index"] == 9
    assert completed["paid_attempt_index"] == 10
    assert completed["action_authorization_id"] == key
    assert completed["status"] == "repair_generated"
    assert completed["api_calls"] == 1
    assert completed["input_tokens"] == 5077
    assert completed["output_tokens"] == 1050
    assert completed["reasoning_tokens"] == 0
    assert completed["total_tokens"] == 6127
    assert completed["cost_usd"] == 0.020654
    assert completed["latency_seconds"] == 8.522
    assert completed["patch_count"] == 13
    assert completed["no_change_resolution_count"] == 1
    assert completed["no_change_span_ids"] == ["S173"]
    assert completed["changed_span_ids"] == [
        "S038", "S058", "S074", "S080", "S122", "S158", "S161",
        "S172", "S174", "S175", "S176", "S177", "S183",
    ]
    assert completed["source_story_artifact_id"] == (
        "story-quality-story:64e2ca03b51a9ef11f7b89ea97de7ed93a16aee7b24036ad1f23ebe94b09cf3e"
    )
    assert completed["source_story_sha256"] == (
        "82c54f27838fa43c601e28b30c61eec9dfd476403c618da3bba67b49d2a20e4e"
    )
    assert completed["repaired_story_sha256"] == (
        "5d01796e8a6e4c10228a31489d29ff83f24fec5189e220e3a40c0f3e0d11834a"
    )
    assert completed["product_artifact_id"] == (
        "story-quality-story:625552cddc38aa2ac4ac552338c3a80acfe9d188b00f00854048d13d20e08baf"
    )
    assert completed["next_handoff_artifact_id"] == (
        "story-quality-reaudit-handoff:348703e12752a2ae22dbf2b187d68a2e9a9a35d3c535777280984386b43c49a3"
    )
    assert completed["next_action"] == "REAUDIT"
    assert completed["next_stage"] == 23
    assert completed["next_cycle_index"] == 9
    assert completed["next_paid_execution_authorized"] is False
    assert completed["automatic_retry_executed"] is False
    assert completed["reaudit_executed"] is False
    assert completed["translation_executed"] is False
    assert completed["state_commit_executed"] is False

    assert loop["status"] == "PAID_EXECUTION_AUTHORIZED"
    assert loop["current_action"] == "REAUDIT"
    assert loop["current_stage"] == 23
    assert loop["cycle_index"] == 9
    assert loop["action_authorization_id"] == (
        "story-quality-loop:stage23:reaudit:cycle9:attempt9"
    )
    assert loop["source_story_artifact_id"] == completed["product_artifact_id"]
    assert loop["source_story_sha256"] == completed["repaired_story_sha256"]
    assert loop["handoff_artifact_id"] == completed["next_handoff_artifact_id"]
    assert loop["finding_count"] is None
    assert loop["allowed_edit_span_count"] is None
    assert loop["allowed_edit_span_ids"] == []
    assert loop["next_repair_paid_attempt_index"] == 11
    assert loop["paid_execution_authorized"] is True
    assert loop["authorization_consumed"] is False
    assert loop["automatic_retry_enabled"] is False
    assert loop["automatic_paid_transition_enabled"] is False
    assert loop["automatic_repair_loop_enabled"] is False
    assert loop["next_harness_requirement"] == "stage23_paid_result"
    assert "paid_attempt_index" not in loop
    assert "source_reaudit_product_artifact_id" not in loop

    assert artifacts["result_sha256"] == (
        "743fe600f6067a4d083bac7fdba86e29341f8d37c8e4cc937824dec7f47f931d"
    )
    assert artifacts["story_file_sha256"] == (
        "35a272d5cd3a9422845e8c331940bfaca3afc26f0fbdfabd5548fb616303c95e"
    )
    assert artifacts["product_sha256"] == (
        "afcf777968b3d3852d28f898c50b3dbdb84a8aa2380a5f996783fad11c25e424"
    )
    assert artifacts["handoff_sha256"] == (
        "8a2d172f457ddafa17bcbccb8a846307d657ce3f7c5f5ab5fba07e5f9e15a391"
    )
    assert artifacts["envelope_sha256"] == (
        "7b17227eb0cb218400754836147ef9c1df6df50990882684a236a44e792d1da5"
    )
    assert artifacts["next_state_sha256"] == (
        "e93bd44815bd5bc2757931be08a3007b2e111132a1ff57a535c44d78b555b1ec"
    )
