import json
from pathlib import Path

import pytest

from src.spineforge_relay_v1_q5 import (
    MAX_COST_USD,
    MAX_TOKENS,
    MODEL,
    REQUEST_CLASS,
    _validate_generated_scene,
    build_inputs,
    execute_once,
    prepare,
    request_payload,
    verify,
)


def test_q5_fixture_compiles_to_exact_sc01_contract():
    writer_input, state, plan, route, contract = build_inputs()
    assert state.next_spine_beat == "SC01"
    assert route.beat_ids == ["SC01", "SC02", "SC03", "SC04", "SC05", "SC06"]
    assert plan.spine_beats == ["SC01"]
    assert contract.consumed_spine_beats == ["SC01"]
    assert contract.next_spine_beat == "SC02"
    assert contract.required_exit_state["/objects/compass/location"] == "mother_dragon"
    assert writer_input["continuity_window"] is None


def test_q5_request_is_bounded_low_reasoning_scene_writer():
    writer_input, *_ = build_inputs()
    request = request_payload(writer_input)
    assert request["model"] == MODEL
    assert request["max_tokens"] == MAX_TOKENS == 1600
    assert request["reasoning"] == {"effort": "low", "exclude": True}
    assert request["response_format"] == {"type": "text"}
    assert "seed" not in request
    assert "stream" not in request


def test_q5_prepare_is_zero_cost_and_round_trips(tmp_path):
    report = prepare(tmp_path)
    assert report["status"] == "OFFLINE_PREPARED_PAID_NOT_AUTHORIZED"
    assert report["max_writer_calls"] == 1
    assert report["automatic_retry"] is False
    assert report["paid_execution_authorized"] is False
    assert report["state_application_authorized"] is False
    assert report["proposed_max_cost_usd"] == MAX_COST_USD
    verified = verify(tmp_path / "preflight.json", tmp_path / "writer-input.json")
    assert verified["artifact_sha256"] == report["artifact_sha256"]


def test_q5_unauthorized_execution_fails_before_call(tmp_path):
    report = prepare(tmp_path / "preflight")
    calls = {"n": 0}

    def fake_call(**kwargs):
        calls["n"] += 1
        raise AssertionError("must not call provider")

    with pytest.raises(RuntimeError, match="explicit SFR-v1 Q5 paid authorization"):
        execute_once(
            api_key="not-a-real-key",
            run_id="unauthorized",
            authorization={
                "paid_execution_authorized": False,
                "scope": "SFR_V1_Q5_SINGLE_SCENE_ONE_CALL",
                "preflight_sha256": report["artifact_sha256"],
                "max_cost_usd": MAX_COST_USD,
                "explicit_user_message": "",
            },
            preflight_path=tmp_path / "preflight" / "preflight.json",
            writer_input_path=tmp_path / "preflight" / "writer-input.json",
            output_root=tmp_path / "runs",
            call_fn=fake_call,
        )
    assert calls["n"] == 0


def test_q5_authorized_fake_call_runs_once_and_stays_pending_review(tmp_path):
    report = prepare(tmp_path / "preflight")
    writer_input = json.loads((tmp_path / "preflight" / "writer-input.json").read_text())
    request = request_payload(writer_input)
    calls = {"n": 0}
    prose = " ".join(
        [
            "Ekin held the brass compass near the harbor stalls when a sea dragon swept low and snatched it from her hands.",
            "She shouted and ran after the beating wings, dodging baskets and wet ropes as the animal climbed above the roofs.",
            "A girl nearby called that Ekin was chasing the wrong direction and pointed toward the old lighthouse on the headland.",
            "Ekin skidded to a stop, angry at being corrected, until the girl showed her a brief brass glint in the lighthouse window.",
            "The girl introduced herself as Duru and said she knew the coastal route better than the slippery shortcut Ekin had chosen.",
            "Ekin wanted to argue, but another flash from the lighthouse made the decision for her, and the dragon was already far ahead.",
            "She told Duru she was going after her grandfather's compass whether Duru came or not, trying to make the partnership sound like her own idea.",
            "Duru answered that she had not asked permission and started toward the headland.",
            "Ekin followed beside her, still irritated, while the wind pushed colder air through the harbor and the open lighthouse door waited in the distance.",
            "The compass remained with the dragon; for now, Ekin accepted Duru as the quickest way to reach it."
        ]
    )
    assert 180 <= len(prose.split()) <= 280

    def fake_call(**kwargs):
        calls["n"] += 1
        return (
            prose,
            {
                "choices": [{"finish_reason": "stop", "message": {"content": prose}}],
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 300,
                    "total_tokens": 1300,
                    "cost": 0.0012,
                    "completion_tokens_details": {"reasoning_tokens": 80},
                },
            },
            request,
        )

    result = execute_once(
        api_key="fake-test-key",
        run_id="authorized-fake",
        authorization={
            "paid_execution_authorized": True,
            "scope": "SFR_V1_Q5_SINGLE_SCENE_ONE_CALL",
            "preflight_sha256": report["artifact_sha256"],
            "max_cost_usd": MAX_COST_USD,
            "explicit_user_message": "test authorization fixture",
        },
        preflight_path=tmp_path / "preflight" / "preflight.json",
        writer_input_path=tmp_path / "preflight" / "writer-input.json",
        output_root=tmp_path / "runs",
        call_fn=fake_call,
    )
    assert calls["n"] == 1
    assert result["status"] == "WRITER_GENERATED_PENDING_SCENE_REVIEW"
    assert result["automatic_retry_executed"] is False
    assert result["state_application_authorized"] is False


def test_q5_generated_scene_rejects_wrong_length():
    writer_input, *_ = build_inputs()
    with pytest.raises(RuntimeError, match="word count outside contract"):
        _validate_generated_scene("Too short.", writer_input)
