from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_paid_story_quality_loop_once import (
    AUTHORIZATION_MARKER,
    PROFILE_PATH,
    execute_paid_story_quality_loop_once,
)


def _profile(tmp_path: Path, *, authorized: bool, consumed: bool) -> Path:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]
    loop["paid_execution_authorized"] = authorized
    loop["authorization_consumed"] = consumed
    loop["authorization_marker"] = AUTHORIZATION_MARKER
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def test_generic_paid_wrapper_rejects_unapproved_profile(tmp_path: Path):
    called = False

    def fake_repair(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("paid inference must not execute")

    with pytest.raises(RuntimeError, match="not authorized"):
        execute_paid_story_quality_loop_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            profile_path=_profile(tmp_path, authorized=False, consumed=True),
            repair_run_fn=fake_repair,
        )
    assert called is False


def test_generic_paid_wrapper_rejects_consumed_authorization(tmp_path: Path):
    with pytest.raises(RuntimeError, match="already consumed"):
        execute_paid_story_quality_loop_once(
            api_key="not-used",
            run_id="unit",
            output_root=tmp_path,
            profile_path=_profile(tmp_path, authorized=True, consumed=True),
        )


def test_generic_paid_repair_emits_next_reaudit_state_without_authorizing_it(tmp_path: Path):
    profile_path = _profile(tmp_path, authorized=True, consumed=False)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]

    repair_handoff_path = Path(
        "evidence/spineforge-v20-story-quality-loop/"
        "37014477600-repair-handoff.json"
    )
    repair_handoff = json.loads(repair_handoff_path.read_text(encoding="utf-8"))
    loop.update({
        "status": "PAID_EXECUTION_AUTHORIZED",
        "current_action": "LOCAL_REPAIR",
        "current_stage": 10,
        "cycle_index": 3,
        "action_authorization_id": (
            "story-quality-loop:stage10:local-repair:cycle3:attempt4"
        ),
        "source_story_artifact_id": repair_handoff[
            "source_story_artifact_id"
        ],
        "source_story_artifact_path": repair_handoff[
            "source_story_artifact_path"
        ],
        "source_story_artifact_sha256": repair_handoff[
            "source_story_artifact_sha256"
        ],
        "source_story_sha256": repair_handoff["source_story_sha256"],
        "source_reaudit_product_artifact_id": repair_handoff[
            "source_reaudit_product_artifact_id"
        ],
        "source_reaudit_product_path": repair_handoff[
            "source_reaudit_product_path"
        ],
        "source_reaudit_product_sha256": repair_handoff[
            "source_reaudit_product_sha256"
        ],
        "handoff_artifact_id": repair_handoff["artifact_id"],
        "handoff_path": str(repair_handoff_path),
        "handoff_sha256": __import__("hashlib").sha256(
            repair_handoff_path.read_bytes()
        ).hexdigest(),
        "paid_attempt_index": 4,
        "paid_execution_authorized": True,
        "authorization_consumed": False,
    })
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    source_artifact = json.loads(
        Path(loop["source_story_artifact_path"]).read_text(encoding="utf-8")
    )
    source_story = Path(source_artifact["repaired_story_path"]).read_text(encoding="utf-8")
    if source_story.endswith("\n"):
        source_story = source_story[:-1]

    def fake_repair(**kwargs):
        return {
            "schema": "spineforge-v20-story-quality-repair-execution.v1",
            "status": "repair_generated",
            "stage": 10,
            "repair_cycle_index": 3,
            "paid_attempt_index": 4,
            "source_reaudit_product_artifact_id": loop[
                "source_reaudit_product_artifact_id"
            ],
            "source_reaudit_artifact_id": "synthetic",
            "source_story_artifact_id": loop["source_story_artifact_id"],
            "source_story_sha256": loop["source_story_sha256"],
            "repair_model": "anthropic/claude-sonnet-5.5",
            "patches": [],
            "no_change_resolutions": [],
            "changed_span_ids": [],
            "patch_count": 0,
            "no_change_resolution_count": 0,
            "repaired_story": source_story,
            "repaired_story_sha256": loop["source_story_sha256"],
            "source_story_mutated": False,
            "all_findings_addressed": True,
            "changed_spans_subset_of_allowed": True,
            "repair_usage_rollup": {"totals": {"api_calls": 1}},
            "automatic_retry_executed": False,
            "reaudit_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
            "next_stage": "STORY_REAUDIT",
        }

    result, envelope = execute_paid_story_quality_loop_once(
        api_key="not-used",
        run_id="123",
        output_root=tmp_path,
        profile_path=profile_path,
        repair_run_fn=fake_repair,
    )
    assert result["status"] == "repair_generated"
    assert envelope["action"] == "LOCAL_REPAIR"
    next_state = json.loads(
        (tmp_path / "123" / "story-quality-loop-next-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert next_state["status"] == "NEXT_ACTION_READY_NOT_AUTHORIZED"
    assert next_state["current_action"] == "REAUDIT"
    assert next_state["current_stage"] == 11
    assert next_state["cycle_index"] == 3
    assert next_state["paid_execution_authorized"] is False
    assert next_state["automatic_paid_transition_enabled"] is False
    assert (tmp_path / "123" / "age12-island-v20-story-quality-repair-c3-product.json").exists()
    assert (tmp_path / "123" / "age12-island-v20-story-quality-repair-c3-next-handoff.json").exists()


def test_generic_paid_reaudit_writes_completed_envelope_before_product_and_advances_repair_attempt(tmp_path: Path):
    profile_path = _profile(tmp_path, authorized=True, consumed=False)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]

    stage11_handoff_path = Path(
        "evidence/spineforge-v20-paid-writer/37112601598/"
        "age12-island-v20-story-quality-repair-c3-next-handoff.json"
    )
    stage11_handoff = json.loads(stage11_handoff_path.read_text(encoding="utf-8"))
    stage10_key = "story-quality-loop:stage10:local-repair:cycle3:attempt4"
    loop.update({
        "status": "PAID_EXECUTION_AUTHORIZED",
        "current_action": "REAUDIT",
        "current_stage": 11,
        "cycle_index": 3,
        "action_authorization_id": (
            "story-quality-loop:stage11:reaudit:cycle3:attempt3"
        ),
        "source_story_artifact_id": stage11_handoff[
            "source_story_artifact_id"
        ],
        "source_story_artifact_path": stage11_handoff[
            "source_story_artifact_path"
        ],
        "source_story_artifact_sha256": stage11_handoff[
            "source_story_artifact_sha256"
        ],
        "source_story_sha256": stage11_handoff[
            "repaired_story_text_sha256"
        ],
        "handoff_artifact_id": stage11_handoff["artifact_id"],
        "handoff_path": str(stage11_handoff_path),
        "handoff_sha256": __import__("hashlib").sha256(
            stage11_handoff_path.read_bytes()
        ).hexdigest(),
        "paid_execution_authorized": True,
        "authorization_consumed": False,
        "next_repair_paid_attempt_index": 4,
        "last_completed_action": loop["completed_actions"][stage10_key],
    })
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


    assert loop["current_action"] == "REAUDIT"
    assert loop["current_stage"] == 11
    assert loop["cycle_index"] == 3

    def fake_reaudit(**kwargs):
        return {
            "schema": "spineforge-v20-story-quality-reaudit-execution.v1",
            "status": "reaudit_completed",
            "stage": 11,
            "cycle_index": 3,
            "source_story_artifact_id": loop["source_story_artifact_id"],
            "source_repaired_story_sha256": loop["source_story_sha256"],
            "reaudit_artifact": {
                "schema": "spineforge-v20-story-quality-reaudit-artifact.v1",
                "artifact_type": "IMMUTABLE_STORY_QUALITY_REAUDIT",
                "stage": 11,
                "cycle_index": 3,
                "source_story_artifact_id": loop["source_story_artifact_id"],
                "source_repaired_story_sha256": loop["source_story_sha256"],
                "input_verified": True,
                "source_story_mutated": False,
                "full_story_reaudited": True,
                "stable_span_count": 199,
                "decision": "LOCAL_REPAIR_REQUIRED",
                "next_stage": "STORY_LOCAL_REPAIR",
                "findings": [{
                    "family": "language_naturalness",
                    "severity": "minor",
                    "repair_scope": "LOCAL_REPAIR",
                    "span_ids": ["S045"],
                    "exact_text": "less margin",
                    "reason": "Synthetic residual defect.",
                }],
                "artifact_id": "story-quality-reaudit-result:synthetic",
            },
            "secondary_language_sentence_scan": [],
            "secondary_language_sentence_scan_count": 199,
            "locator_corrections": [],
            "reaudit_usage_rollup": {
                "calls": [],
                "totals": {
                    "api_calls": 2,
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "reasoning_tokens": 0,
                    "cached_tokens": 0,
                    "cache_write_tokens": 0,
                    "total_tokens": 120,
                    "cost_usd": 0.01,
                    "latency_seconds": 1.0,
                },
                "by_stage": {},
                "by_model": {},
                "reconciled": {
                    "cost_matches_call_sum": True,
                    "token_matches_call_sum": True,
                },
            },
            "incremental_cost_usd": 0.01,
            "incremental_latency_seconds": 1.0,
            "source_story_mutated": False,
            "automatic_retry_executed": False,
            "repair_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }

    result, envelope = execute_paid_story_quality_loop_once(
        api_key="not-used",
        run_id="reaudit-unit",
        output_root=tmp_path,
        profile_path=profile_path,
        reaudit_run_fn=fake_reaudit,
    )
    assert result["status"] == "reaudit_completed"
    assert envelope["result_status"] == "reaudit_completed"
    next_state = json.loads(
        (tmp_path / "reaudit-unit" / "story-quality-loop-next-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert next_state["current_action"] == "LOCAL_REPAIR"
    assert next_state["current_stage"] == 12
    assert next_state["cycle_index"] == 4
    assert next_state["paid_execution_authorized"] is False

    handoff = json.loads(
        (
            tmp_path
            / "reaudit-unit"
            / "age12-island-v20-story-quality-reaudit-c3-next-handoff.json"
        ).read_text(encoding="utf-8")
    )
    assert handoff["repair_cycle_index"] == 4
    assert handoff["paid_attempt_index"] == 5
    assert handoff["paid_execution_authorized"] is False


def test_generic_paid_wrapper_persists_partial_usage_on_post_provider_contract_failure(tmp_path: Path):
    profile_path = _profile(tmp_path, authorized=True, consumed=False)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]

    stage13_handoff_path = Path(
        "evidence/spineforge-v20-paid-writer/37114732160/"
        "age12-island-v20-story-quality-repair-c4-next-handoff.json"
    )
    stage13_handoff = json.loads(stage13_handoff_path.read_text(encoding="utf-8"))
    loop.update({
        "status": "PAID_EXECUTION_AUTHORIZED",
        "current_action": "REAUDIT",
        "current_stage": 13,
        "cycle_index": 4,
        "action_authorization_id": (
            "story-quality-loop:stage13:reaudit:cycle4:attempt4"
        ),
        "source_story_artifact_id": stage13_handoff[
            "source_story_artifact_id"
        ],
        "source_story_artifact_path": stage13_handoff[
            "source_story_artifact_path"
        ],
        "source_story_artifact_sha256": stage13_handoff[
            "source_story_artifact_sha256"
        ],
        "source_story_sha256": stage13_handoff[
            "repaired_story_text_sha256"
        ],
        "handoff_artifact_id": stage13_handoff["artifact_id"],
        "handoff_path": str(stage13_handoff_path),
        "handoff_sha256": __import__("hashlib").sha256(
            stage13_handoff_path.read_bytes()
        ).hexdigest(),
        "paid_execution_authorized": True,
        "authorization_consumed": False,
    })
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    def fake_reaudit(**kwargs):
        exc = RuntimeError("synthetic primary contract failure")
        setattr(exc, "trace", {
            "phase": "post_provider_auditor_payload_validation",
            "model": "anthropic/claude-sonnet-5.5",
            "raw_response": {"evaluations": []},
            "raw_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "cost": 0.01,
            },
            "model_call": {
                "stage": "spineforge_v20_story_quality_reaudit_primary",
                "model": "anthropic/claude-sonnet-5.5",
                "provider": "openrouter",
                "status": "completed",
                "attempt": 1,
                "input_tokens": 100,
                "output_tokens": 20,
                "reasoning_tokens": 0,
                "cached_tokens": 0,
                "cache_write_tokens": 0,
                "total_tokens": 120,
                "cost_usd": 0.01,
                "latency_seconds": 1.25,
            },
            "request": {},
            "parse_failures": [],
            "retry_suppressed": True,
        })
        raise exc

    result, envelope = execute_paid_story_quality_loop_once(
        api_key="not-used",
        run_id="failure-unit",
        output_root=tmp_path,
        profile_path=profile_path,
        reaudit_run_fn=fake_reaudit,
    )

    assert result["status"] == "unhandled_story_quality_loop_runtime_failure"
    assert result["failure"]["provider_trace"]["phase"] == (
        "post_provider_auditor_payload_validation"
    )
    partial = result["partial_usage_rollup"]
    assert partial["totals"]["api_calls"] == 1
    assert partial["totals"]["input_tokens"] == 100
    assert partial["totals"]["output_tokens"] == 20
    assert partial["totals"]["total_tokens"] == 120
    assert partial["totals"]["cost_usd"] == 0.01
    assert partial["totals"]["latency_seconds"] == 1.25
    assert envelope["usage_rollup"] == partial
    assert envelope["result_status"] == "unhandled_story_quality_loop_runtime_failure"



def test_generic_paid_wrapper_prefers_multi_call_partial_usage_from_exception(tmp_path: Path):
    profile_path = _profile(tmp_path, authorized=True, consumed=False)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loop = profile["story_quality_loop"]

    stage13_handoff_path = Path(
        "evidence/spineforge-v20-paid-writer/37114732160/"
        "age12-island-v20-story-quality-repair-c4-next-handoff.json"
    )
    stage13_handoff = json.loads(stage13_handoff_path.read_text(encoding="utf-8"))
    loop.update({
        "status": "PAID_EXECUTION_AUTHORIZED",
        "current_action": "REAUDIT",
        "current_stage": 13,
        "cycle_index": 4,
        "action_authorization_id": "synthetic-multi-call-failure",
        "source_story_artifact_id": stage13_handoff["source_story_artifact_id"],
        "source_story_artifact_path": stage13_handoff["source_story_artifact_path"],
        "source_story_artifact_sha256": stage13_handoff["source_story_artifact_sha256"],
        "source_story_sha256": stage13_handoff["repaired_story_text_sha256"],
        "handoff_artifact_id": stage13_handoff["artifact_id"],
        "handoff_path": str(stage13_handoff_path),
        "handoff_sha256": __import__("hashlib").sha256(
            stage13_handoff_path.read_bytes()
        ).hexdigest(),
        "paid_execution_authorized": True,
        "authorization_consumed": False,
    })
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    expected = {
        "calls": [],
        "totals": {
            "api_calls": 2,
            "input_tokens": 200,
            "output_tokens": 40,
            "reasoning_tokens": 0,
            "cached_tokens": 0,
            "cache_write_tokens": 0,
            "total_tokens": 240,
            "cost_usd": 0.02,
            "latency_seconds": 2.0,
        },
        "by_stage": {},
        "by_model": {},
        "reconciled": {
            "cost_matches_call_sum": True,
            "token_matches_call_sum": True,
        },
    }

    def fake_reaudit(**kwargs):
        exc = RuntimeError("synthetic post-provider locator failure")
        setattr(exc, "partial_usage_rollup", expected)
        setattr(exc, "trace", {
            "stage": "spineforge_v20_story_quality_reaudit_post_provider_locator",
            "model_calls": [],
        })
        raise exc

    result, envelope = execute_paid_story_quality_loop_once(
        api_key="not-used",
        run_id="multi-call-failure-unit",
        output_root=tmp_path,
        profile_path=profile_path,
        reaudit_run_fn=fake_reaudit,
    )

    assert result["status"] == "unhandled_story_quality_loop_runtime_failure"
    assert result["partial_usage_rollup"] == expected
    assert envelope["usage_rollup"] == expected
