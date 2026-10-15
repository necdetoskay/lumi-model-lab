import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from requests import Timeout

from src.english_story_pipeline import StructuredJsonCallError
from src.generate import OpenRouterCallError
from src.v3_single_attempt_guard import SingleAttemptSpineGuard, SafetyStop, SPINE_MODELS
from experiments.v3_single_attempt_spine_probe import run


class MockResponse:
    def __init__(self, status=200, *, model_cost=0.02, completion=None):
        self.status_code = status
        self.ok = status == 200
        self.headers = {}
        self._cost = model_cost
        self._completion = completion or '{"ok": true}'
    def json(self):
        if not self.ok:
            return {"error": {"message": "simulated"}}
        return {
            "id": "gen-test-offline-123456",
            "choices": [{"message": {"content": self._completion}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7, "cost": self._cost},
        }
    @property
    def text(self):
        return '{"error": {"message": "simulated"}}'


def call_json(model, max_parse_attempts=2):
    from src.episode_spine_v2_generate import call_structured_json_with_retry
    return call_structured_json_with_retry(
        api_key="OFFLINE_ONLY", model=model, system_prompt="test", user_prompt="test",
        temperature=0.1, max_tokens=5, seed=None,
        request_class="saga_architect", max_parse_attempts=max_parse_attempts)


def test_transport_timeout_never_retries(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    calls = []
    def timeout(*args, **kwargs):
        calls.append(1)
        raise Timeout("fake")
    with patch("requests.post", side_effect=timeout):
        with g.installed():
            with pytest.raises(OpenRouterCallError):
                call_json(SPINE_MODELS[0])
    assert len(calls) == g.calls == 1
    records = [json.loads(p.read_text()) for p in sorted(tmp_path.glob("*.json"))]
    assert any(r["kind"] == "TRANSPORT_FAULT" for r in records)
    assert not any("OFFLINE_ONLY" in p.read_text() for p in tmp_path.glob("*.json"))


def test_http_503_never_retries(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    calls = []
    with patch("requests.post", side_effect=lambda *a, **k: (calls.append(1), MockResponse(503))[1]):
        with g.installed():
            with pytest.raises(OpenRouterCallError):
                call_json(SPINE_MODELS[0])
    assert len(calls) == 1


def test_invalid_json_never_generates_second_response(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    calls = []
    with patch("requests.post", side_effect=lambda *a, **k: (calls.append(1), MockResponse(completion="NOT JSON"))[1]):
        with g.installed():
            with pytest.raises(StructuredJsonCallError):
                call_json(SPINE_MODELS[0])
    assert len(calls) == 1


def test_success_architect_then_gate_exactly_once_each(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    calls = []
    def ok(*args, **kwargs):
        calls.append(kwargs["json"]["model"])
        return MockResponse()
    with patch("requests.post", side_effect=ok):
        with g.installed():
            assert call_json(SPINE_MODELS[0])[0] == {"ok": True}
            assert call_json(SPINE_MODELS[1])[0] == {"ok": True}
            with pytest.raises(SafetyStop, match="EXTRA_PROVIDER_POST_BLOCKED"):
                call_json(SPINE_MODELS[1])
    assert calls == list(SPINE_MODELS) and g.calls == 2
    records = [json.loads(p.read_text()) for p in tmp_path.glob("*.json")]
    assert len([x for x in records if x["kind"] == "PROVIDER_OBSERVED"]) == 2


def test_wrong_model_and_missing_cost_fail_closed(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    with patch("requests.post") as post:
        with g.installed():
            with pytest.raises(SafetyStop, match="WRONG_MODEL_OR_UNEXPECTED_RETRY"):
                call_json(SPINE_MODELS[1])
    post.assert_not_called()
    g2 = SingleAttemptSpineGuard(tmp_path / "other", Decimal("0.50"))
    (tmp_path / "other").mkdir()
    with patch("requests.post", return_value=MockResponse(model_cost=float("nan"))):
        with g2.installed():
            with pytest.raises(SafetyStop, match="PROVIDER_COST_MISSING_OR_INVALID"):
                call_json(SPINE_MODELS[0])


def test_unapproved_grant_never_starts(tmp_path):
    grant = tmp_path / "grant.json"
    grant.write_text('{"schema":"invalid","authorized":false}')
    with pytest.raises(SafetyStop, match="PAID_GRANT_SCOPE_MISMATCH"):
        run(grant_file=grant, evidence_dir=tmp_path / "artifact")
    assert not (tmp_path / "artifact").exists()



def test_rate_limit_429_never_retries(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    calls = []
    with patch("requests.post", side_effect=lambda *a, **k: (calls.append(1), MockResponse(429))[1]):
        with g.installed():
            with pytest.raises(OpenRouterCallError):
                call_json(SPINE_MODELS[0])
    assert calls == [1] and g.calls == 1


def test_over_budget_stops_before_next_stage(tmp_path):
    g = SingleAttemptSpineGuard(tmp_path, Decimal("0.01"))
    calls = []
    with patch("requests.post", side_effect=lambda *a, **k: (calls.append(1), MockResponse(model_cost=0.02))[1]):
        with g.installed():
            with pytest.raises(SafetyStop, match="CUMULATIVE_COST_CEILING_REACHED"):
                call_json(SPINE_MODELS[0])
            with pytest.raises(SafetyStop, match="WRONG_MODEL_OR_UNEXPECTED_RETRY"):
                call_json(SPINE_MODELS[0])
    assert calls == [1]


def test_frozen_inputs_unchanged(tmp_path):
    from src.frozen_lane_verify import verify_frozen_lane
    from pathlib import Path
    profile=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
    before=profile.read_bytes()
    verified=verify_frozen_lane(profile)
    g=SingleAttemptSpineGuard(tmp_path, Decimal("0.50"))
    with patch("requests.post", return_value=MockResponse()):
        with g.installed():
            assert call_json(SPINE_MODELS[0])[0]=={"ok": True}
    assert verify_frozen_lane(profile)["verified_files"]==verified["verified_files"]==43
    assert profile.read_bytes()==before
