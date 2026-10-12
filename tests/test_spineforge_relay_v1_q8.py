from pathlib import Path
import json
import pytest

from src.spineforge_relay_v1_q6d import request_for
from src.spineforge_relay_v1_q8 import (
    FIXTURES,
    MAX_TOTAL_COST_USD,
    authorization_for,
    execute_suite,
    prepare,
)


def _guard(payload, prose):
    evidence = []
    for event in payload["scene_contract"]["required_events"]:
        for pred in event["predicates"]:
            evidence.append({
                "event_id": event["id"],
                "predicate_id": pred["id"],
                "subject": pred["subject"],
                "action": pred["action"],
                "target": pred["target"],
                "verdict": "SUPPORTED",
                "provenance": "DIRECT_OBSERVATION",
                "exact_text": prose,
                "evidence_subject": pred["target"],
                "state_pointer": None,
                "reason": "Synthetic Q8 suite evidence.",
            })
    return {
        "event_evidence": evidence,
        "residual": {
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "PASS",
            "findings": [],
            "summary": "No blockers.",
        },
    }


def _fake(**kwargs):
    payload = json.loads(kwargs["user_prompt"])
    writer = "gpt-5.6-sol" in kwargs["model"]
    stage = "writer" if writer else "guard"
    text = " ".join(["clear"] * 210) if writer else json.dumps(_guard(payload, payload["candidate_prose"]))
    _, actual = request_for(stage, payload)
    return text, {
        "choices": [{"finish_reason": "stop", "message": {"content": text}}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 450, "total_tokens": 1650, "cost": 0.01},
    }, actual


def test_q8_preflight_is_two_unrelated_stories_same_runner():
    p = prepare()
    assert p["story_count"] == 2
    assert [x["story_id"] for x in p["stories"]] == ["q8-greenhouse-notebook", "q8-hill-kite"]
    assert len({x["fixture_sha256"] for x in p["stories"]}) == 2
    assert p["same_runner"] == "src/spineforge_relay_v1_runner.py"
    assert p["same_writer"] == "openai/gpt-5.6-sol"
    assert p["same_guard"] == "anthropic/claude-sonnet-5.5"
    assert p["max_rewrites_per_scene"] == 1
    assert p["automatic_retry"] is False
    assert p["max_total_cost_usd"] == MAX_TOTAL_COST_USD == 1.0


def test_q8_authorization_is_exact_and_bounded():
    p = prepare()
    a = authorization_for(p)
    assert a["paid_execution_authorized"] is True
    assert a["story_ids"] == ["q8-greenhouse-notebook", "q8-hill-kite"]
    assert a["automatic_retry"] is False
    assert a["stop_suite_on_story_failure"] is True
    assert a["max_total_cost_usd"] == 1.0


def test_q8_suite_accepts_both_with_same_fake_provider(tmp_path):
    p = prepare()
    a = authorization_for(p)
    out = execute_suite(
        api_key="fake",
        preflight=p,
        authorization=a,
        output=tmp_path / "q8",
        call_fn=_fake,
    )
    assert out["status"] == "ACCEPT"
    assert out["reason"] == "TWO_UNRELATED_STORIES_ACCEPTED_WITH_SAME_RUNNER"
    assert [x["story_id"] for x in out["stories"]] == ["q8-greenhouse-notebook", "q8-hill-kite"]
    assert all(x["status"] == "ACCEPT" for x in out["stories"])


def test_q8_missing_credential_fails_before_claim(tmp_path):
    p = prepare()
    a = authorization_for(p)
    with pytest.raises(RuntimeError, match="Missing credential"):
        execute_suite(
            api_key="",
            preflight=p,
            authorization=a,
            output=tmp_path / "q8",
        )
    assert not (tmp_path / "q8").exists()
