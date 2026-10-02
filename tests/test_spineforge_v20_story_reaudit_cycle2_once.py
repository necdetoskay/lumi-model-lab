from __future__ import annotations

import json

from src.spineforge_v20_story_reaudit_cycle2_once import (
    execute_story_reaudit_cycle2_once,
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


def _body(prompt: int, completion: int, cost: float):
    return {
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "cost": cost,
        }
    }


def _request():
    return {
        "temperature": 0.0,
        "max_tokens": 6000,
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


def test_stage9_full_reaudit_accepts_clean_second_repaired_story():
    seen = []

    def primary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("primary", payload))
        return _clean_primary(), _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("secondary", payload))
        return _clean_secondary(payload), _body(90, 10, 0.02), _request(), []

    result = execute_story_reaudit_cycle2_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )

    assert result["status"] == "reaudit_completed"
    assert result["stage"] == 9
    assert result["source_stage8_artifact_id"] == (
        "story-local-repair-cycle2:61237a22b0d46ba41cc44f51026b9dc4cf83030d794fdb5668e44bad00a1fa87"
    )
    assert result["source_repaired_story_sha256"] == (
        "b9a4675cd79f458ee8d29fd11f1bb5fdddfe4abec68c394efcddf60fb892eb95"
    )
    assert result["secondary_language_sentence_scan_count"] == 199
    assert result["source_story_mutated"] is False
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False

    assert len(seen[0][1]["story_segments"]) == 199
    assert len(seen[1][1]["story_segments"]) == 199
    assert seen[0][1]["repair_lineage"]["no_change_span_ids"] == ["S161", "S182"]

    artifact = result["reaudit_artifact"]
    assert artifact["decision"] == "ACCEPT"
    assert artifact["next_stage"] == "ENGLISH_MASTER_SEAL"
    assert artifact["full_story_reaudited"] is True
    assert artifact["stable_span_count"] == 199


def test_stage9_local_finding_routes_back_to_story_local_repair():
    def primary(**kwargs):
        return _clean_primary(), _body(10, 5, 0.0), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        raw = _clean_secondary(payload)
        target = next(row for row in payload["story_segments"] if row["id"] == "S182")
        raw["language_sentence_scan"][181] = {
            "span_id": "S182",
            "status": "defect",
            "editor_action": "REWRITE",
            "rewrite": target["text"] + " Clarified.",
        }
        raw["findings"] = [{
            "severity": "minor",
            "span_ids": ["S182"],
            "exact_text": "felt smaller than it had",
            "reason": "Synthetic residual finding.",
        }]
        return raw, _body(10, 5, 0.0), _request(), []

    result = execute_story_reaudit_cycle2_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )
    artifact = result["reaudit_artifact"]
    assert artifact["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert artifact["next_stage"] == "STORY_LOCAL_REPAIR"
