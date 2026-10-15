"""No-network, original frozen V3 Writer integration proofs."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from requests import Timeout

from src.episode_writer_v2_generate import generate, WRITER_MODEL
from src.generate import OpenRouterCallError
from src.v3_single_attempt_guard import SafetyStop
from src.v3_single_attempt_aion_writer_guard import (
    SingleAttemptAionWriterGuard,
)

APPROVED = Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
PROMPT = Path("prompts/episode_writer_v3_generic.md")
TEXT = " ".join(["Deniz recorded the light and continued the work carefully."] * 190)


class FakeResponse:
    ok = True
    headers = {}
    status_code = 200

    def __init__(self, *, status=200, text=TEXT, cost=0.032, generation_id="gen-offline-writer-12345"):
        self.status_code = status
        self.ok = status == 200
        self._text = text
        self._cost = cost
        self._generation_id = generation_id

    def json(self):
        if not self.ok:
            return {"error": {"message": "FAKE_FAILURE"}}
        return {
            "id": self._generation_id,
            "choices": [{"message": {"role": "assistant", "content": self._text},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2500, "completion_tokens": 3300,
                      "total_tokens": 5800, "cost": self._cost},
        }

    @property
    def text(self):
        return '{"error":{"message":"FAKE_FAILURE"}}'


def run_writer(tmp_path):
    return generate(
        approved_path=APPROVED,
        prompt_path=PROMPT,
        out_path=tmp_path / "writer-result.json",
        story_out_path=tmp_path / "story.txt",
        api_key="OFFLINE_SIMULATED_NEVER_SENT",
        authority_packet_version="v2",
    )


def events(path):
    return [json.loads(p.read_text()) for p in sorted(path.glob("*.json"))]


def test_approved_aion_writer_succeeds_after_one_post(tmp_path):
    assert WRITER_MODEL == "aion-labs/aion-3.5-mini"
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs["json"]["model"])
        return FakeResponse()

    with patch("requests.post", side_effect=fake_post):
        with guard.installed_writer():
            result = run_writer(tmp_path)
    assert calls == [WRITER_MODEL] and guard.calls == 1
    assert guard.spent == Decimal("0.032")
    assert result["status"] == "writer_generated"
    assert result["deterministic_checks"]["length_pass"] is True
    assert result["next_stage_authorized"] is False
    assert len([x for x in events(e) if x["kind"] == "POST_INTENT"]) == 1
    assert len([x for x in events(e) if x["kind"] == "PROVIDER_OBSERVED"]) == 1
    assert (tmp_path / "story.txt").is_file()


@pytest.mark.parametrize("status", [429, 500, 503])
def test_http_errors_do_not_repeat(tmp_path, status):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        return FakeResponse(status=status)

    with patch("requests.post", side_effect=fake_post):
        with guard.installed_writer():
            with pytest.raises(OpenRouterCallError):
                run_writer(tmp_path)
    assert calls == [1] and guard.calls == 1
    assert json.loads((tmp_path / "writer-result.json").read_text())["status"] == "writer_provider_failure"
    assert not (tmp_path / "story.txt").exists()


def test_timeout_does_not_repeat(tmp_path):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    posts = []

    def fake_timeout(url, **kwargs):
        posts.append(1)
        raise Timeout("FAKE_TRANSPORT_TIMEOUT")

    with patch("requests.post", side_effect=fake_timeout):
        with guard.installed_writer():
            with pytest.raises(OpenRouterCallError):
                run_writer(tmp_path)
    assert posts == [1]
    assert len([x for x in events(e) if x["kind"] == "TRANSPORT_FAULT"]) == 1


def test_invalid_model_is_never_sent(tmp_path):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    with patch("requests.post") as post:
        with guard.installed_writer():
            from src.generate import call_openrouter
            with pytest.raises(SafetyStop, match="WRONG_MODEL_OR_UNEXPECTED_RETRY"):
                call_openrouter(api_key="OFFLINE", model="anthropic/claude-sonnet-5.5",
                    system_prompt="fake", user_prompt="fake", temperature=0.1,
                    max_tokens=10, seed=None, structured_output=False)
    post.assert_not_called()


def test_cost_ceiling_is_post_response_and_blocks_publication(tmp_path):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.010"))
    with patch("requests.post", return_value=FakeResponse(cost=0.032)):
        with guard.installed_writer():
            with pytest.raises(SafetyStop, match="CUMULATIVE_COST_CEILING_REACHED"):
                run_writer(tmp_path)
    assert guard.calls == 1
    assert guard.spent == Decimal("0.032")
    assert not (tmp_path / "story.txt").exists()
    assert len([x for x in events(e) if x["kind"] == "POLICY_STOP"]) == 1


@pytest.mark.parametrize("invalid_cost", [None, -1, float("nan")])
def test_invalid_provider_cost_fails_closed(tmp_path, invalid_cost):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    with patch("requests.post", return_value=FakeResponse(cost=invalid_cost)):
        with guard.installed_writer():
            with pytest.raises(SafetyStop, match="PROVIDER_COST_MISSING_OR_INVALID"):
                run_writer(tmp_path)
    assert guard.calls == 1
    assert not (tmp_path / "story.txt").exists()


def test_invalid_generation_id_fails_closed(tmp_path):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    with patch("requests.post", return_value=FakeResponse(generation_id="FAKE_ID")):
        with guard.installed_writer():
            with pytest.raises(SafetyStop, match="GENERATION_ID_MISSING_OR_INVALID"):
                run_writer(tmp_path)
    assert guard.calls == 1
    assert not (tmp_path / "story.txt").exists()


def test_second_post_is_blocked_without_network(tmp_path):
    e = tmp_path / "evidence"
    e.mkdir()
    guard = SingleAttemptAionWriterGuard(e, Decimal("0.50"))
    calls = []
    def fake_post(url, **kwargs):
        calls.append(1)
        return FakeResponse()

    with patch("requests.post", side_effect=fake_post):
        with guard.installed_writer():
            run_writer(tmp_path)
            from src.generate import call_openrouter
            with pytest.raises(SafetyStop, match="EXTRA_PROVIDER_POST_BLOCKED"):
                call_openrouter(api_key="OFFLINE", model=WRITER_MODEL,
                    system_prompt="fake", user_prompt="fake", temperature=0.1,
                    max_tokens=None, seed=None, structured_output=False)
    assert calls == [1]


def test_original_v3_freeze_still_valid():
    from src.frozen_lane_verify import verify_frozen_lane
    assert verify_frozen_lane(Path(
        "data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json"
    ))["verified_files"] == 43



def _fake_writer_grant(tmp_path, *, stage="WRITER"):
    import subprocess
    from experiments.v3_aion_writer_single_attempt_probe import (
        CASE_ID, APPROVED_SHA,
    )
    grant = {
        "schema": "lumi.v3-aion-mini-writer-paid-grant.v1",
        "authorized": True,
        "stage": stage,
        "case_id": CASE_ID,
        "model": WRITER_MODEL,
        "frozen_runtime_sha": "63e1e3ce82c244bc5bb02b0463a9a1a6715c941b",
        "approved_spine_sha256": APPROVED_SHA,
        "human_paid_authorization_reference": "OFFLINE_TEST_ONLY",
        "guard_commit_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True,
        ).strip(),
        "grant_id": "OFFLINE-WRITER-GRANT-00000001",
        "max_total_usd": "0.50",
    }
    path = tmp_path / "grant.json"
    path.write_text(json.dumps(grant))
    return path


def test_old_spine_grant_cannot_authorize_paid_writer(tmp_path):
    from experiments.v3_aion_writer_single_attempt_probe import run
    grant = _fake_writer_grant(tmp_path, stage="SPINE")
    with pytest.raises(SafetyStop, match="WRITER_GRANT_SCOPE_MISMATCH"):
        run(
            grant_file=grant, evidence_dir=tmp_path / "evidence",
            claim_dir=tmp_path / "claims",
        )
    assert not (tmp_path / "claims").exists()


def test_writer_authorization_needs_specific_reference(tmp_path):
    from experiments.v3_aion_writer_single_attempt_probe import run
    grant = _fake_writer_grant(tmp_path)
    data = json.loads(grant.read_text())
    data["human_paid_authorization_reference"] = ""
    grant.write_text(json.dumps(data))
    with pytest.raises(SafetyStop, match="WRITER_SPECIFIC_PAID_AUTHORIZATION_REQUIRED"):
        run(
            grant_file=grant, evidence_dir=tmp_path / "evidence",
            claim_dir=tmp_path / "claims",
        )
    assert not (tmp_path / "claims").exists()


def test_writer_proof_entrypoint_is_one_use_and_no_network(tmp_path, monkeypatch):
    import subprocess
    from experiments import v3_aion_writer_single_attempt_probe as runner
    grant = _fake_writer_grant(tmp_path)
    old = subprocess.check_output

    def fake_command(args, **kwargs):
        if args[:2] == ["git", "status"]:
            return ""
        if args[:2] == ["git", "diff"]:
            return "src/v3_single_attempt_aion_writer_guard.py" + chr(10)
        return old(args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "check_output", fake_command)
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_ONLY_NO_EXTERNAL_REQUEST")
    post_calls = []
    def synthetic_post(url, **kwargs):
        post_calls.append(kwargs["json"]["model"])
        return FakeResponse()

    with patch("requests.post", side_effect=synthetic_post):
        first = runner.run(
            grant_file=grant, evidence_dir=tmp_path / "evidence1",
            claim_dir=tmp_path / "claims",
        )
        assert first["status"] == "writer_generated"
        with pytest.raises(SafetyStop, match="WRITER_GRANT_ALREADY_CONSUMED"):
            runner.run(
                grant_file=grant, evidence_dir=tmp_path / "evidence2",
                claim_dir=tmp_path / "claims",
            )
    assert post_calls == [WRITER_MODEL]
    assert not (tmp_path / "evidence2").exists()
    assert len(list((tmp_path / "claims").glob("*.json"))) == 1
