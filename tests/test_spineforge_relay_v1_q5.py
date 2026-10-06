import copy
import json

import pytest

from src.spineforge_relay_v1_q5 import (
    MAX_COST_USD,
    MAX_TOKENS,
    MODEL,
    _validate_generated_scene,
    build_inputs,
    execute_once,
    prepare,
    request_payload,
    verify,
)


def valid_prose() -> str:
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
            "The compass remained with the dragon; for now, Ekin accepted Duru as the quickest way to reach it.",
            "Neither girl called the other a friend, and Ekin kept her eyes fixed on the lighthouse instead of admitting that Duru's clue had helped.",
        ]
    )
    assert 180 <= len(prose.split()) <= 280
    return prose


def authorization(report, **overrides):
    value = {
        "paid_execution_authorized": True,
        "scope": "SFR_V1_Q5_SINGLE_SCENE_ONE_CALL",
        "preflight_sha256": report["artifact_sha256"],
        "max_cost_usd": MAX_COST_USD,
        "max_writer_calls": 1,
        "automatic_retry": False,
        "production_write": False,
        "state_application_authorized": False,
        "explicit_user_message": "FAKE TEST AUTHORIZATION, NO LIVE API",
    }
    value.update(overrides)
    return value


def fake_transport_for(writer_input, *, kind="ok"):
    request = request_payload(writer_input)
    prose = valid_prose()

    def call(**kwargs):
        body = {
            "choices": [{"finish_reason": "stop", "message": {"content": prose}}],
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 300,
                "total_tokens": 1300,
                "cost": 0.0012,
                "completion_tokens_details": {"reasoning_tokens": 80},
            },
        }
        text = prose
        if kind == "truncated":
            body["choices"][0]["finish_reason"] = "length"
        elif kind == "over_budget":
            body["usage"]["cost"] = MAX_COST_USD + 0.001
        elif kind == "missing_cost":
            del body["usage"]["cost"]
        elif kind == "too_short":
            text = "Ekin lost the compass."
        return text, body, request

    return call


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
    assert report["proposed_max_cost_usd"] == MAX_COST_USD == 0.01
    assert report["planned_uncached_cost_usd"] < MAX_COST_USD
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
            authorization=authorization(report, paid_execution_authorized=False),
            preflight_path=tmp_path / "preflight" / "preflight.json",
            writer_input_path=tmp_path / "preflight" / "writer-input.json",
            output_root=tmp_path / "runs",
            call_fn=fake_call,
        )
    assert calls["n"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_writer_calls", 2),
        ("automatic_retry", True),
        ("production_write", True),
        ("state_application_authorized", True),
    ],
)
def test_q5_authorization_cannot_expand_scope(tmp_path, field, value):
    report = prepare(tmp_path / "preflight")
    calls = {"n": 0}

    def fake_call(**kwargs):
        calls["n"] += 1
        raise AssertionError("must not call provider")

    with pytest.raises(RuntimeError, match="authorization"):
        execute_once(
            api_key="not-a-real-key",
            run_id="expanded-scope",
            authorization=authorization(report, **{field: value}),
            preflight_path=tmp_path / "preflight" / "preflight.json",
            writer_input_path=tmp_path / "preflight" / "writer-input.json",
            output_root=tmp_path / "runs",
            call_fn=fake_call,
        )
    assert calls["n"] == 0


def test_q5_authorized_fake_call_runs_once_and_stays_pending_review(tmp_path):
    report = prepare(tmp_path / "preflight")
    writer_input = json.loads((tmp_path / "preflight" / "writer-input.json").read_text())

    result = execute_once(
        api_key="fake-test-key",
        run_id="authorized-fake",
        authorization=authorization(report),
        preflight_path=tmp_path / "preflight" / "preflight.json",
        writer_input_path=tmp_path / "preflight" / "writer-input.json",
        output_root=tmp_path / "runs",
        call_fn=fake_transport_for(writer_input),
    )
    assert result["status"] == "WRITER_GENERATED_PENDING_SCENE_REVIEW"
    assert result["api_calls"] == 1
    assert result["automatic_retry_executed"] is False
    assert result["state_application_authorized"] is False
    assert result["raw_response"] == valid_prose()
    artifact = json.loads(
        (tmp_path / "runs/authorized-fake/writer-scene-artifact.json").read_text()
    )
    assert artifact["semantic_guard_qualified"] is False
    assert artifact["state_application_authorized"] is False
    assert artifact["publication_ready"] is False


def test_q5_authorization_claim_is_single_use(tmp_path):
    report = prepare(tmp_path / "preflight")
    writer_input = json.loads((tmp_path / "preflight" / "writer-input.json").read_text())
    auth = authorization(report)

    execute_once(
        api_key="fake-test-key",
        run_id="first",
        authorization=auth,
        preflight_path=tmp_path / "preflight" / "preflight.json",
        writer_input_path=tmp_path / "preflight" / "writer-input.json",
        output_root=tmp_path / "runs",
        call_fn=fake_transport_for(writer_input),
    )
    with pytest.raises(FileExistsError):
        execute_once(
            api_key="fake-test-key",
            run_id="second",
            authorization=auth,
            preflight_path=tmp_path / "preflight" / "preflight.json",
            writer_input_path=tmp_path / "preflight" / "writer-input.json",
            output_root=tmp_path / "runs",
            call_fn=fake_transport_for(writer_input),
        )


@pytest.mark.parametrize("kind", ["truncated", "over_budget", "missing_cost", "too_short"])
def test_q5_failed_response_is_retained_and_never_retried(tmp_path, kind):
    report = prepare(tmp_path / "preflight")
    writer_input = json.loads((tmp_path / "preflight" / "writer-input.json").read_text())
    calls = {"n": 0}
    inner = fake_transport_for(writer_input, kind=kind)

    def transport(**kwargs):
        calls["n"] += 1
        return inner(**kwargs)

    result = execute_once(
        api_key="fake-test-key",
        run_id=kind,
        authorization=authorization(report),
        preflight_path=tmp_path / "preflight" / "preflight.json",
        writer_input_path=tmp_path / "preflight" / "writer-input.json",
        output_root=tmp_path / "runs",
        call_fn=transport,
    )
    assert calls["n"] == 1
    assert result["status"] == "STOPPED_NO_RETRY"
    assert result["api_calls"] == 1
    assert result["raw_response"]
    assert result["provider_response"]
    assert not (tmp_path / f"runs/{kind}/writer-scene-artifact.json").exists()


def test_q5_generated_scene_rejects_wrong_length():
    writer_input, *_ = build_inputs()
    with pytest.raises(RuntimeError, match="word count outside contract"):
        _validate_generated_scene("Too short.", writer_input)
