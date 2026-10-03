from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_story_quality_loop import (
    build_local_repair_handoff,
    build_reaudit_handoff,
    build_reaudit_product,
    build_recovered_reaudit_envelope,
    execute_local_repair,
    execute_reaudit,
)


REAUDIT_RESULT = Path(
    "evidence/spineforge-v20-paid-story-reaudit-cycle2/37014477600/"
    "age12-island-v20-story-reaudit2-result.json"
)
REAUDIT_ENVELOPE = Path(
    "evidence/spineforge-v20-paid-story-reaudit-cycle2/37014477600/"
    "age12-island-v20-story-reaudit2-envelope.json"
)
STAGE8_STORY = Path(
    "evidence/spineforge-v20-story-local-repair-cycle2-product/37010331757/"
    "story-local-repair-cycle2-artifact.json"
)
GENERIC_PRODUCT = Path(
    "evidence/spineforge-v20-story-quality-loop/37014477600-reaudit-product.json"
)


FAMILIES = [
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


def _body(prompt=10, completion=5, cost=0.0):
    return {
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "cost": cost,
        }
    }


def _request(max_tokens=6000):
    return {
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "reasoning": None,
        "response_format": {"type": "json_schema"},
    }


def _clean_primary():
    return {
        "evaluations": [
            {
                "family": family,
                "present": False,
                "findings": [],
                "reason": "No concrete defect.",
            }
            for family in FAMILIES
        ],
        "summary": "Clean.",
    }


def _clean_secondary(payload):
    return {
        "language_sentence_scan": [
            {
                "span_id": str(row["id"]),
                "status": "clean",
                "editor_action": "KEEP",
                "rewrite": "",
            }
            for row in payload["story_segments"]
        ],
        "findings": [],
        "summary": "Naturalness clean.",
    }


def test_generic_loop_builds_stage9_product_and_stage10_repair_handoff_without_cycle_specific_code():
    product = build_reaudit_product(
        result_path=REAUDIT_RESULT,
        envelope_path=REAUDIT_ENVELOPE,
        source_story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )
    assert product["schema"] == "spineforge-v20-story-quality-reaudit-product.v1"
    assert product["artifact_id"] == (
        "story-quality-reaudit:4aabbacb8c8d3b99c1139b3908b30c6a52e9125a421819ca2af4b626880a6711"
    )
    assert product["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert product["finding_count"] == 12
    assert product["stable_span_count"] == 199

    handoff = build_local_repair_handoff(
        reaudit_product_path=GENERIC_PRODUCT,
        source_story_artifact_path=STAGE8_STORY,
        stage=10,
        repair_cycle_index=3,
        paid_attempt_index=4,
    )
    assert handoff["schema"] == "spineforge-v20-story-quality-repair-handoff.v1"
    assert handoff["artifact_id"] == (
        "story-quality-repair-handoff:cd302abc071b27a831ecccd658afa58007c238de3a14795d76539cdbe58c122e"
    )
    assert handoff["stage"] == 10
    assert handoff["repair_cycle_index"] == 3
    assert handoff["paid_attempt_index"] == 4
    assert handoff["finding_count"] == 12
    assert handoff["allowed_edit_span_count"] == 13
    assert handoff["paid_execution_authorized"] is False


def test_generic_local_repair_then_build_reaudit_handoff_needs_no_new_cycle_module(tmp_path: Path):
    handoff = build_local_repair_handoff(
        reaudit_product_path=GENERIC_PRODUCT,
        source_story_artifact_path=STAGE8_STORY,
        stage=10,
        repair_cycle_index=3,
        paid_attempt_index=4,
    )

    def fake_call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        rows = []
        for target in payload["target_segments"]:
            rows.append({
                "span_id": target["span_id"],
                "replacement_text": target["source_text"] + " [fixed]",
                "addresses_finding_indexes": target["finding_indexes"],
            })
        return {"patches": rows, "summary": "Synthetic."}, _body(), _request(8000), []

    result = execute_local_repair(
        api_key="not-used",
        handoff=handoff,
        call_fn=fake_call,
        system_prompt="PATCHES ONLY",
    )
    assert result["status"] == "repair_generated"
    assert result["stage"] == 10
    assert result["repair_cycle_index"] == 3
    assert result["paid_attempt_index"] == 4
    assert result["patch_count"] == 13
    assert result["no_change_resolution_count"] == 0
    assert result["changed_span_ids"] == handoff["allowed_edit_span_ids"]
    assert result["next_stage"] == "STORY_REAUDIT"
    assert result["automatic_retry_executed"] is False
    assert result["reaudit_executed"] is False


def test_generic_reaudit_can_accept_any_frozen_generic_story_artifact_shape():
    # Stage 8 product is an allowed immutable repaired-story source and proves
    # the generic re-audit path does not depend on a cycle-specific module.
    handoff = build_reaudit_handoff(
        story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )

    def primary(**kwargs):
        return _clean_primary(), _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        return _clean_secondary(payload), _body(90, 10, 0.02), _request(), []

    result = execute_reaudit(
        api_key="not-used",
        handoff=handoff,
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )
    assert result["status"] == "reaudit_completed"
    assert result["secondary_language_sentence_scan_count"] == 199
    assert result["reaudit_artifact"]["decision"] == "ACCEPT"
    assert result["reaudit_artifact"]["next_stage"] == "ENGLISH_MASTER_SEAL"
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False


def test_generic_repair_forbidden_span_is_rejected():
    handoff = build_local_repair_handoff(
        reaudit_product_path=GENERIC_PRODUCT,
        source_story_artifact_path=STAGE8_STORY,
        stage=10,
        repair_cycle_index=3,
        paid_attempt_index=4,
    )

    def fake_call(**kwargs):
        return {
            "patches": [{
                "span_id": "S006",
                "replacement_text": "Forbidden.",
                "addresses_finding_indexes": [0],
            }],
            "summary": "Bad.",
        }, _body(), _request(8000), []

    with pytest.raises(RuntimeError, match="forbidden span"):
        execute_local_repair(
            api_key="not-used",
            handoff=handoff,
            call_fn=fake_call,
            system_prompt="PATCHES ONLY",
        )


def test_generic_reaudit_postprocess_recovery_uses_completed_result_without_reinference():
    result_path = Path(
        "evidence/spineforge-v20-paid-writer/37113502767/"
        "age12-island-v20-story-quality-reaudit-c3-result.json"
    )
    raw_envelope_path = Path(
        "evidence/spineforge-v20-paid-writer/37113502767/"
        "age12-island-v20-story-quality-reaudit-c3-envelope.json"
    )
    recovered = build_recovered_reaudit_envelope(
        result_path=result_path,
        raw_envelope_path=raw_envelope_path,
    )

    assert recovered["schema"] == (
        "spineforge-v20-paid-story-quality-loop-recovered-envelope.v1"
    )
    assert recovered["result_status"] == "reaudit_completed"
    assert recovered["action"] == "REAUDIT"
    assert recovered["usage_rollup"]["totals"]["api_calls"] == 2
    assert recovered["usage_rollup"]["totals"]["cost_usd"] == 0.1394635
    recovery = recovered["postprocess_recovery"]
    assert recovery["reason"] == (
        "envelope_status_write_order_after_successful_inference"
    )
    assert recovery["paid_inference_reexecuted"] is False
    assert recovery["source_raw_envelope_sha256"] == (
        "0654f7a2f1368219de4ab379904e1ffa3a58cbfd19844e9355e88463abd1d3b1"
    )
    assert recovery["source_result_sha256"] == (
        "045fe225869bd2bf69dcafabcb21b8114cd80d65466295479ac9305633be7687"
    )


def test_generic_reaudit_contract_failure_preserves_raw_usage_and_family_manifest():
    handoff = build_reaudit_handoff(
        story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )
    captured = {}

    def invalid_primary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        captured["payload"] = payload
        raw = {
            "evaluations": [
                {
                    "family": family,
                    "present": False,
                    "findings": [],
                    "reason": "Clean.",
                }
                for family in FAMILIES[:9]
            ],
            "summary": "Invalid truncated audit.",
        }
        return raw, _body(100, 20, 0.01), _request(), []

    def secondary_must_not_run(**kwargs):
        raise AssertionError("secondary auditor must not execute after primary contract failure")

    with pytest.raises(RuntimeError, match="every family exactly once") as excinfo:
        execute_reaudit(
            api_key="not-used",
            handoff=handoff,
            primary_call_fn=invalid_primary,
            secondary_call_fn=secondary_must_not_run,
        )

    payload = captured["payload"]
    assert payload["required_evaluation_family_count"] == 13
    assert payload["required_evaluation_families"] == FAMILIES

    trace = getattr(excinfo.value, "trace")
    assert trace["phase"] == "post_provider_auditor_payload_validation"
    assert trace["model"] == "anthropic/claude-sonnet-5.5"
    assert len(trace["raw_response"]["evaluations"]) == 9
    assert trace["raw_usage"]["prompt_tokens"] == 100
    assert trace["raw_usage"]["completion_tokens"] == 20
    assert trace["model_call"]["input_tokens"] == 100
    assert trace["model_call"]["output_tokens"] == 20
    assert trace["model_call"]["total_tokens"] == 120
    assert trace["model_call"]["cost_usd"] == 0.01
    assert trace["retry_suppressed"] is True



def test_generic_reaudit_normalizes_local_quote_to_valid_frozen_span():
    handoff = build_reaudit_handoff(
        story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )
    captured = {}

    def primary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        first = payload["story_segments"][0]
        captured["span_id"] = str(first["id"])
        captured["source_text"] = str(first["text"])
        raw = _clean_primary()
        row = next(
            x for x in raw["evaluations"]
            if x["family"] == "language_naturalness"
        )
        row["present"] = True
        row["findings"] = [{
            "severity": "minor",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": [captured["span_id"]],
            "exact_text": "A paraphrase that is not a literal frozen quote.",
            "reason": "Synthetic quote-normalization qualification.",
        }]
        row["reason"] = "One synthetic language defect."
        return raw, _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        return _clean_secondary(payload), _body(90, 10, 0.02), _request(), []

    result = execute_reaudit(
        api_key="not-used",
        handoff=handoff,
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )

    assert result["status"] == "reaudit_completed"
    finding = next(
        x for x in result["reaudit_artifact"]["findings"]
        if x["family"] == "language_naturalness"
    )
    assert finding["span_ids"] == [captured["span_id"]]
    assert finding["exact_text"] == captured["source_text"]
    assert result["locator_corrections"] == [{
        "family": "language_naturalness",
        "exact_text": "A paraphrase that is not a literal frozen quote.",
        "old_span_ids": [captured["span_id"]],
        "new_span_ids": [captured["span_id"]],
        "normalized_exact_text": captured["source_text"],
        "reason": "deterministic_valid_span_quote_normalization",
    }]


def test_generic_reaudit_locator_failure_preserves_two_call_usage():
    handoff = build_reaudit_handoff(
        story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )

    def primary(**kwargs):
        raw = _clean_primary()
        row = next(
            x for x in raw["evaluations"]
            if x["family"] == "language_naturalness"
        )
        row["present"] = True
        row["findings"] = [{
            "severity": "minor",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": ["S999"],
            "exact_text": "This exact text does not exist in the frozen story.",
            "reason": "Synthetic unrecoverable locator failure.",
        }]
        row["reason"] = "One synthetic language defect."
        return raw, _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        return _clean_secondary(payload), _body(90, 10, 0.02), _request(), []

    with pytest.raises(RuntimeError, match="resolve uniquely") as info:
        execute_reaudit(
            api_key="not-used",
            handoff=handoff,
            primary_call_fn=primary,
            secondary_call_fn=secondary,
        )

    usage = getattr(info.value, "partial_usage_rollup")
    trace = getattr(info.value, "trace")
    assert usage["totals"]["api_calls"] == 2
    assert usage["totals"]["input_tokens"] == 190
    assert usage["totals"]["output_tokens"] == 30
    assert usage["totals"]["total_tokens"] == 220
    assert usage["totals"]["cost_usd"] == 0.03
    assert trace["stage"] == (
        "spineforge_v20_story_quality_reaudit_post_provider_locator"
    )
    assert len(trace["model_calls"]) == 2
