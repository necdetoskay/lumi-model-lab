from __future__ import annotations

import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_obligations import load_qualification_cases


PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json")


def test_v20_frozen_runtime_hashes_verify():
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-STORY-FIRST-FROZEN-v20.38"
    assert result["verified_files"] == 71


def test_v20_freeze_locks_story_first_topology_and_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    runtime = profile["runtime"]
    product = profile["product_contract"]
    paid = profile["paid_boundary_policy"]

    assert profile["runtime_id"] == "spineforge.contextpack.v20.story-first-single-owner"
    assert profile["runtime_freeze"]["runtime_source_commit"] == "d6c5b6088"
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
    assert state["paid_api_calls"] == 21
    assert state["confirmed_cost_usd"] == 0.8869709
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
    assert writer["paid_story_audit_authorized"] is True
    assert writer["human_story_review_required"] is False

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
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
    assert audit["paid_execution_authorized"] is True


def test_v20_8_freeze_locks_stage5_dual_audit_harness_without_paid_authorization():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
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
    assert audit["authorization_consumed"] is False
    assert audit["paid_execution_authorized"] is True



def test_v20_11_freeze_records_failed_paid_story_audit_qualification():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    q = profile["qualification_state"]
    audit = profile["stage5_story_audit"]
    attempt1 = audit["attempt1"]

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["last_paid_run_id"] == 36987409819
    assert q["last_result"] == "story_audit_attempt7_quality_failed_known_defect_missed"

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt2_paid_authorized"] is False
    assert audit["audit_contract_revision"] == "primary-v3-plus-language-specialist-v2"
    assert audit["authority_projection"] == "compact-reveal-safe-v1"
    assert audit["prompt_revision"] == "stage5-story-audit-v3"
    assert audit["attempt1"]["qualification_status"] == "FAIL_KNOWN_DEFECT_MISSED"
    assert audit["attempt1"]["known_target_recall"] == 0.0



def test_v20_13_freeze_locks_attempt2_paid_boundary():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    audit = profile["stage5_story_audit"]
    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt2_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
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

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["last_paid_run_id"] == 36987409819
    assert q["last_result"] == "story_audit_attempt7_quality_failed_known_defect_missed"
    assert q["cost_reconciliation_status"] == "PARTIAL"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt2_paid_authorized"] is False
    assert audit["authorization_consumed"] is False
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
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
    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt3_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
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

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["last_paid_run_id"] == 36987409819
    assert q["cost_reconciliation_status"] == "PARTIAL"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt4_paid_authorized"] is False
    assert audit["authorization_consumed"] is False
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt4_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False

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

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["confirmed_cost_is_lower_bound"] is True
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]
    assert q["unreconciled_paid_api_calls"] == 4

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt4_paid_authorized"] is False
    assert audit["authorization_consumed"] is False
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt5_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False

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

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["last_paid_run_id"] == 36987409819
    assert q["last_result"] == "story_audit_attempt7_quality_failed_known_defect_missed"
    assert q["unreconciled_paid_runs"] == [36970666881, 36976651148]
    assert q["unreconciled_paid_api_calls"] == 4
    assert q["confirmed_cost_is_lower_bound"] is True

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt5_paid_authorized"] is False
    assert audit["authorization_consumed"] is False

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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt6_paid_authorized"] is False
    assert audit["next_harness_requirement"] == "attempt8_paid_result"

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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt6_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
    assert audit["next_harness_requirement"] == "attempt8_paid_result"

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

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["last_paid_run_id"] == 36987409819
    assert q["last_result"] == (
        "story_audit_attempt7_quality_failed_known_defect_missed"
    )

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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
    assert audit["audit_contract_revision"] == "primary-v3-plus-language-specialist-v2"
    assert audit["next_harness_requirement"] == "attempt8_paid_result"

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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt7_paid_authorized"] is False
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
    assert audit["next_harness_requirement"] == "attempt8_paid_result"

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

    assert q["paid_api_calls"] == 21
    assert q["confirmed_cost_usd"] == 0.8869709
    assert q["last_paid_run_id"] == 36987409819
    assert q["last_result"] == "story_audit_attempt7_quality_failed_known_defect_missed"

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt7_paid_authorized"] is False
    assert audit["authorization_consumed"] is False
    assert audit["next_harness_requirement"] == (
        "attempt8_paid_result"
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["paid_execution_authorized"] is True
    assert audit["attempt8_paid_authorized"] is True
    assert audit["authorization_consumed"] is False
    assert audit["audit_contract_revision"] == (
        "primary-v3-plus-language-specialist-v2"
    )
    assert audit["next_harness_requirement"] == (
        "attempt8_paid_result"
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

    assert audit["status"] == "ATTEMPT8_PAID_EXECUTION_AUTHORIZED"
    assert audit["authorization_marker"] == "PAID-V20-AGE12-ISLAND-STORY-AUDIT8"
    assert audit["attempt8_paid_authorized"] is True
    assert audit["paid_execution_authorized"] is True
    assert audit["authorization_consumed"] is False
    assert audit["next_harness_requirement"] == "attempt8_paid_result"

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
    assert harness["paid_execution_authorized"] is True
