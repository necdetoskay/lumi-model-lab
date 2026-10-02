from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v19_transport import STRICT_SCHEMA_MAX_BYTES, schema_size_bytes
from src.spineforge_v20_story_local_repair_handoff import (
    build_story_local_repair_handoff,
)
from src.spineforge_v20_story_local_repair_once import (
    REPAIR_MODEL,
    REPAIR_REQUEST_CLASS,
    REPAIR_RESPONSE_SCHEMA,
    REPAIR_SCHEMA_NAME,
    _normalize_repair_payload,
    execute_story_local_repair_once,
)


def _fake_body() -> dict:
    return {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cost": 0.01,
        }
    }


def _fake_request() -> dict:
    return {
        "temperature": 0.0,
        "max_tokens": 8000,
        "reasoning": None,
        "response_format": {"type": "json_schema"},
    }


def _all_target_patches(handoff: dict) -> list[dict]:
    patches = []
    for row in handoff["target_segments"]:
        source = str(row["source_text"])
        replacement = source + " Revised."
        patches.append({
            "span_id": row["span_id"],
            "replacement_text": replacement,
            "addresses_finding_indexes": list(row["finding_indexes"]),
        })
    return patches


def test_stage6_handoff_is_immutable_and_bound_to_qualified_attempt8():
    handoff = build_story_local_repair_handoff()

    assert handoff["schema"] == "spineforge-v20-story-local-repair-handoff.v1"
    assert handoff["artifact_type"] == "IMMUTABLE_STAGE6_LOCAL_REPAIR_INPUT"
    assert handoff["stage"] == 6
    assert handoff["status"] == "READY_NOT_AUTHORIZED"
    assert handoff["immutable"] is True
    assert handoff["source_writer_artifact_id"] == (
        "writer-story:f1000691c85665ea6894e45e0318faaf5cdf7c1dac91fa453153e392af8192f3"
    )
    assert handoff["source_story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert handoff["source_audit_artifact_id"] == (
        "story-audit:8ed94a19c3b8637df0378dc3ec64eacef97096efaa3013f19231ee4cf73e4876"
    )
    assert handoff["finding_count"] == 25
    assert handoff["allowed_edit_span_count"] == 25
    assert len(handoff["allowed_edit_span_ids"]) == 25
    assert handoff["allowed_edit_span_ids"][0] == "S006"
    assert handoff["allowed_edit_span_ids"][-1] == "S199"
    assert handoff["repair_model"] == "anthropic/claude-sonnet-5.5"
    assert handoff["repair_attempt_index"] == 1
    assert handoff["paid_execution_authorized"] is False
    assert handoff["automatic_retry_enabled"] is False
    assert handoff["next_stage_after_success"] == "STORY_REAUDIT"
    assert handoff["repair_policy"]["source_story_mutation_forbidden"] is True
    assert handoff["repair_policy"]["unreferenced_span_edit_forbidden"] is True
    assert handoff["repair_policy"]["structural_rewrite_forbidden"] is True
    assert handoff["repair_policy"]["all_findings_must_be_addressed"] is True

    gold = next(
        row for row in handoff["findings"]
        if row["exact_text"] == "arriving at his shoulder"
    )
    assert gold["finding_index"] == 13
    assert gold["span_ids"] == ["S006"]


def test_stage6_repair_schema_is_strict_and_small():
    assert REPAIR_MODEL == "anthropic/claude-sonnet-5.5"
    assert REPAIR_REQUEST_CLASS == "spineforge_v20_story_local_repair"
    assert REPAIR_SCHEMA_NAME == "spineforge_v20_story_local_repair_v1"
    assert schema_size_bytes(REPAIR_RESPONSE_SCHEMA) <= STRICT_SCHEMA_MAX_BYTES


def test_stage6_normalizer_rejects_forbidden_span():
    handoff = build_story_local_repair_handoff()
    raw = {
        "patches": [{
            "span_id": "S001",
            "replacement_text": "Forbidden change.",
            "addresses_finding_indexes": [0],
        }],
        "summary": "bad",
    }
    with pytest.raises(RuntimeError, match="forbidden span"):
        _normalize_repair_payload(raw=raw, handoff=handoff)


def test_stage6_normalizer_requires_every_finding_addressed():
    handoff = build_story_local_repair_handoff()
    row = handoff["target_segments"][0]
    raw = {
        "patches": [{
            "span_id": row["span_id"],
            "replacement_text": str(row["source_text"]) + " Revised.",
            "addresses_finding_indexes": list(row["finding_indexes"]),
        }],
        "summary": "incomplete",
    }
    with pytest.raises(RuntimeError, match="did not address every finding"):
        _normalize_repair_payload(raw=raw, handoff=handoff)


def test_stage6_fake_repair_changes_only_allowed_spans_and_routes_to_reaudit():
    handoff = build_story_local_repair_handoff()
    captured = {}

    def fake_call(**kwargs):
        captured.update(kwargs)
        raw = {
            "patches": _all_target_patches(handoff),
            "summary": "Synthetic local repair.",
        }
        return raw, _fake_body(), _fake_request(), []

    result = execute_story_local_repair_once(
        api_key="not-used",
        handoff=handoff,
        call_fn=fake_call,
    )

    assert captured["model"] == REPAIR_MODEL
    assert captured["request_class"] == REPAIR_REQUEST_CLASS
    assert captured["schema_name"] == REPAIR_SCHEMA_NAME
    payload = json.loads(captured["user_prompt"])
    assert payload["source_story_sha256"] == handoff["source_story_sha256"]
    assert payload["source_audit_artifact_id"] == handoff["source_audit_artifact_id"]
    assert len(payload["story_segments"]) == 199

    assert result["status"] == "repair_generated"
    assert result["source_story_mutated"] is False
    assert result["all_findings_addressed"] is True
    assert result["changed_spans_subset_of_allowed"] is True
    assert set(result["changed_span_ids"]) == set(handoff["allowed_edit_span_ids"])
    assert result["repaired_story_sha256"] != handoff["source_story_sha256"]
    assert result["automatic_retry_executed"] is False
    assert result["reaudit_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False
    assert result["next_stage"] == "STORY_REAUDIT"
    assert result["repair_usage_rollup"]["totals"]["api_calls"] == 1
    assert result["incremental_cost_usd"] == 0.01


def test_stage6_prompt_does_not_leak_human_gold_phrase():
    prompt = Path("prompts/spineforge_v20_story_local_repair.md").read_text(
        encoding="utf-8"
    )
    assert "PATCHES ONLY" in prompt
    assert "allowed_edit_span_ids" in prompt
    assert "arriving at his shoulder" not in prompt
