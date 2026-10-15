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


def _spatial_revision_feedback():
    return {
        "schema_version": "episode-spine-revision-feedback.v1",
        "qualification_id": "age18_forbidden_cartographer_fantasy_f2",
        "source_architect_run_id": 38697673557,
        "source_generation_id": "gen-1792048631-jveGGZsYYq0vOOh4qLHw",
        "decision": "REPLAN",
        "required_chronological_route": [
            "vellum_hall", "greyfen", "ashen_gate", "greyfen", "vellum_hall",
        ],
        "must_not_autocorrect_past_output": True,
        "blocking_reasons": [{
            "id": "logistics_location_sequence_beat_mismatch",
            "problem": (
                "The rejected Architect's first beat takes place at Ashen Gate, "
                "but the chronology and route both start at Vellum Hall. "
                "This violates the equality of the deduplicated beats' "
                "location_ref sequence and logistics_plan.location_sequence."
            ),
            "required_revision": (
                "Generate a new fully chronological Spine: start Beat 1 at "
                "Vellum Hall with a credible map/ward anomaly hook; progress "
                "through Greyfen, Ashen Gate, Greyfen, then Vellum Hall. "
                "Set logistics_plan.location_sequence to the exact route, "
                "collapsing consecutive beat-location duplicates. Do not "
                "put an Ashen Gate flash-forward as a physically placed "
                "opening beat. If memory occurs within a present-time scene, "
                "the beat's location_ref must identify the physical scene, "
                "not a remembered location. No unexplained travel or "
                "instant communication. Replan rather than silently rewrite."
            ),
            "must_preserve": [
                "Leyra's high-fantasy cartographic magic",
                "Ashen Gate exterior measurements; no sealed boundary crossing",
                "Age 18 professional autonomy and ethical agency",
                "Nameless Vale only foreshadowed; cause remains unresolved",
                "Meaningful branch-specific Greyfen and mentor consequences",
            ],
        }],
        "hard_freezes": [
            "exact_age=18",
            "STANDARD 1600-2500 words",
            "Leyra does not cross Ashen Gate",
            "Nameless Vale remains foreshadow-only",
            "Only forbidden_passage_observed Main Saga milestone",
            "No automatic or case-specific runtime code change",
        ],
        "paid_next_stage_authorized": False,
    }


def _authorized_mock_grant(tmp_path):
    import subprocess
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    grant = tmp_path / "grant.json"
    grant.write_text(json.dumps({
        "schema": "lumi.v3-single-attempt-paid-grant.v2",
        "authorized": True,
        "stage": "SPINE",
        "case_id": "age18.forbidden-cartographer.fantasy.frozen-01",
        "frozen_runtime_sha": "63e1e3ce82c244bc5bb02b0463a9a1a6715c941b",
        "models": list(SPINE_MODELS),
        "guard_commit_sha": head,
        "max_total_usd": "0.50",
        "grant_id": "V3-F1-TEST-ONE-20261015",
        "human_approval_reference": "OFFLINE_TEST_APPROVAL_ONLY",
        "revision_feedback": _spatial_revision_feedback(),
    }))
    return grant


def test_valid_grant_is_consumed_once_even_if_evidence_dir_changes(tmp_path, monkeypatch):
    import os
    import subprocess
    from experiments import v3_single_attempt_spine_probe as probe
    grant = _authorized_mock_grant(tmp_path)
    claim_dir = tmp_path / "claims"
    # During local development the checkout is dirty; simulate only the status
    # command, while the actual ancestry/diff calculations stay real.
    check_output = subprocess.check_output
    def mock_check_output(args, **kwargs):
        if args[:2] == ["git", "status"]:
            return ""
        return check_output(args, **kwargs)
    monkeypatch.setattr(probe.subprocess, "check_output", mock_check_output)
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_TEST_ONLY")
    observed = []
    def zero_network_stage(*, trigger_path, out_dir):
        observed.append(trigger_path)
        return {"stage": "SPINE", "result_status": "MOCK_SPINE_COMPLETE"}
    monkeypatch.setattr(probe, "frozen_stage_run", zero_network_stage)
    # This unit test exercises one-use claiming, not model/gate validation.
    # Gate validation is independently tested with the real stage below.
    monkeypatch.setattr(probe, "enforce_spine_gate",
                        lambda **kwargs: "ACCEPT_AWAITING_HUMAN_APPROVAL")
    got = run(grant_file=grant, evidence_dir=tmp_path / "one", claim_dir=claim_dir)
    assert got["result_status"] == "MOCK_SPINE_COMPLETE"
    assert len(observed) == 1
    with pytest.raises(SafetyStop, match="PAID_GRANT_ALREADY_CLAIMED"):
        run(grant_file=grant, evidence_dir=tmp_path / "two", claim_dir=claim_dir)
    assert len(observed) == 1
    assert not (tmp_path / "two").exists()
    claims=list(claim_dir.glob("*.json"))
    assert len(claims) == 1
    assert json.loads(claims[0].read_text())["schema"] == "v3-single-attempt-claim.v1"


def test_wrong_guard_sha_rejected_before_any_claim(tmp_path, monkeypatch):
    grant = _authorized_mock_grant(tmp_path)
    obj = json.loads(grant.read_text())
    obj["guard_commit_sha"] = "0" * 40
    grant.write_text(json.dumps(obj))
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_TEST_ONLY")
    with pytest.raises(SafetyStop, match="GUARD_COMMIT_NOT_EXACTLY_APPROVED"):
        run(grant_file=grant, evidence_dir=tmp_path / "one", claim_dir=tmp_path / "claims")
    assert not (tmp_path / "claims").exists()


def test_dirty_checkout_rejected_prior_to_claim(tmp_path, monkeypatch):
    from experiments import v3_single_attempt_spine_probe as probe
    import subprocess
    grant = _authorized_mock_grant(tmp_path)
    old = subprocess.check_output
    def fake_command(args, **kwargs):
        if args[:2] == ["git", "status"]:
            return " M src/episode_spine_v2_generate.py\\n"
        return old(args, **kwargs)
    monkeypatch.setattr(probe.subprocess, "check_output", fake_command)
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_TEST_ONLY")
    with pytest.raises(SafetyStop, match="DIRTY_CHECKOUT_BLOCKED"):
        run(grant_file=grant, evidence_dir=tmp_path / "one", claim_dir=tmp_path / "claims")
    assert not (tmp_path / "claims").exists()


def test_valid_paid_grant_requires_persistent_claim_root(tmp_path, monkeypatch):
    from experiments import v3_single_attempt_spine_probe as probe
    import subprocess
    grant = _authorized_mock_grant(tmp_path)
    old = subprocess.check_output
    def fake_command(args, **kwargs):
        if args[:2] == ["git", "status"]:
            return ""
        return old(args, **kwargs)
    monkeypatch.setattr(probe.subprocess, "check_output", fake_command)
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_TEST_ONLY")
    with pytest.raises(SafetyStop, match="PERSISTENT_CLAIM_DIRECTORY_REQUIRED"):
        run(grant_file=grant, evidence_dir=tmp_path / "one")
    assert not (tmp_path / "one").exists()

def test_replay_archived_f1_replan_is_stopped_after_exactly_two_fake_posts(
    tmp_path, monkeypatch
):
    """Real frozen stage is run; only previously archived provider replies mocked."""
    import subprocess
    from experiments import v3_single_attempt_spine_probe as probe
    historical = json.loads(Path(
        "data/specifications/story_lab/"
        "age18_forbidden_cartographer_f1_result_36657233678.json"
    ).read_text())
    replies = {
        SPINE_MODELS[0]: historical["episode_spine"],
        SPINE_MODELS[1]: historical["gate"],
    }
    class ReplayResponse:
        ok = True
        status_code = 200
        headers = {}
        def __init__(self, model):
            self.model = model
        def json(self):
            return {
                "id": "gen-v3-f1-archive-replay",
                "choices": [{"message": {
                    "content": json.dumps(replies[self.model], ensure_ascii=False),
                }, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 800,
                          "total_tokens": 1800, "cost": 0.025},
            }
    posts = []
    def fake_post(url, **kwargs):
        model = kwargs["json"]["model"]
        posts.append(model)
        return ReplayResponse(model)

    grant = _authorized_mock_grant(tmp_path)
    real_check_output = subprocess.check_output
    def clean_status(args, **kwargs):
        if args[:2] == ["git", "status"]:
            return ""
        return real_check_output(args, **kwargs)
    monkeypatch.setattr(probe.subprocess, "check_output", clean_status)
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_REPLAY_NO_NETWORK")
    with patch("requests.post", side_effect=fake_post):
        with pytest.raises(SafetyStop, match="SPINE_GATE_REPLAN_STOP"):
            run(grant_file=grant, evidence_dir=tmp_path / "evidence",
                claim_dir=tmp_path / "claims")
    assert posts == list(SPINE_MODELS)
    stage = json.loads((tmp_path / "evidence" / "stage-output" / "result.json").read_text())
    assert stage["gate"]["decision"] == "REPLAN"
    assert stage["human_review"]["episode_writer_authorized"] is False
    ev = [json.loads(f.read_text())
          for f in (tmp_path / "evidence").glob("[0-9][0-9][0-9]-*.json")]
    assert any(x["kind"] == "GATE_VERDICT_OBSERVED"
               and x["decision"] == "REPLAN" for x in ev)
    assert any(x["kind"] == "STAGE_STOP" and x["post_count"] == 2 for x in ev)
    assert not any(x["kind"] == "STAGE_FINISHED" for x in ev)
    assert len(list((tmp_path / "claims").glob("*.json"))) == 1


def test_gate_accept_is_pending_human_approval_only(tmp_path):
    from experiments.v3_single_attempt_spine_probe import enforce_spine_gate
    out = tmp_path / "stage-output"
    out.mkdir()
    result_path = out / "result.json"
    result_path.write_text(json.dumps({
        "status": "awaiting_human_review",
        "gate": {"decision": "ACCEPT"},
        "episode_writer_authorized": False,
        "human_review": {"verdict": None, "episode_writer_authorized": False},
    }))
    reports = []
    envelope = {
        "stage": "SPINE", "result_status": "awaiting_human_review",
        "result_path": str(result_path),
    }
    got = enforce_spine_gate(envelope=envelope, evidence_dir=tmp_path,
                             post_count=2,
                             event=lambda kind, **kw: reports.append((kind, kw)))
    assert got == "ACCEPT_AWAITING_HUMAN_APPROVAL"
    assert reports[0][1]["decision"] == "ACCEPT"


def test_gate_invalid_decision_and_spoofed_result_path_stop(tmp_path):
    from experiments.v3_single_attempt_spine_probe import enforce_spine_gate
    out = tmp_path / "stage-output"
    out.mkdir()
    result_path = out / "result.json"
    result_path.write_text(json.dumps({
        "status": "awaiting_human_review", "gate": {"decision": "MAYBE"},
        "episode_writer_authorized": False,
        "human_review": {"verdict": None, "episode_writer_authorized": False},
    }))
    envelope = {"stage": "SPINE",
                "result_status": "awaiting_human_review",
                "result_path": str(result_path)}
    with pytest.raises(SafetyStop, match="SPINE_GATE_DECISION_INVALID"):
        enforce_spine_gate(envelope=envelope, evidence_dir=tmp_path,
                           post_count=2, event=lambda *a, **k: None)
    with pytest.raises(SafetyStop, match="SPINE_STAGE_EVIDENCE_PATH_INVALID"):
        enforce_spine_gate(envelope={**envelope, "result_path": str(tmp_path / "evil")},
                           evidence_dir=tmp_path,
                           post_count=2, event=lambda *a, **k: None)

def test_replan_feedback_is_mandatory_and_fail_closed_before_any_claim(tmp_path):
    from experiments.v3_single_attempt_spine_probe import run
    grant = _authorized_mock_grant(tmp_path)
    obj = json.loads(grant.read_text())
    obj.pop("revision_feedback")
    grant.write_text(json.dumps(obj))
    with pytest.raises(SafetyStop, match="REPLAN_FEEDBACK_MISSING"):
        run(grant_file=grant, evidence_dir=tmp_path / "output",
            claim_dir=tmp_path / "claims")
    assert not (tmp_path / "claims").exists()


def test_replan_route_tampering_is_rejected_before_network(tmp_path):
    from experiments.v3_single_attempt_spine_probe import run
    grant = _authorized_mock_grant(tmp_path)
    obj = json.loads(grant.read_text())
    obj["revision_feedback"]["required_chronological_route"][0] = "ashen_gate"
    grant.write_text(json.dumps(obj))
    with pytest.raises(SafetyStop, match="REPLAN_REQUIRED_ROUTE_MISMATCH"):
        run(grant_file=grant, evidence_dir=tmp_path / "output",
            claim_dir=tmp_path / "claims")
    assert not (tmp_path / "claims").exists()


def test_replan_is_present_in_real_frozen_architect_prompt_context(
    tmp_path, monkeypatch,
):
    from experiments import v3_single_attempt_spine_probe as probe
    import subprocess
    grant = _authorized_mock_grant(tmp_path)
    old = subprocess.check_output

    def fake_clean(args, **kwargs):
        if args[:2] == ["git", "status"]:
            return ""
        return old(args, **kwargs)

    monkeypatch.setattr(probe.subprocess, "check_output", fake_clean)
    monkeypatch.setenv("OPENROUTER_API_KEY", "OFFLINE_TEST_ONLY")
    # Test actual frozen Architect JSON input, not paid provider behavior.
    original = json.loads(Path(
        "data/specifications/story_lab/"
        "age18_forbidden_cartographer_f1_result_36657233678.json"
    ).read_text())
    captured = []
    class FakeResponse:
        ok = True
        status_code = 200
        headers = {}
        def __init__(self, model):
            self.model = model
        def json(self):
            item = (original["episode_spine"] if self.model == SPINE_MODELS[0]
                    else original["gate"])
            return {
                "id": "gen-offline-model-archived",
                "choices": [{"message": {"content": json.dumps(item)},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 700,
                          "total_tokens": 1700, "cost": 0.02},
            }
    def fake_post(url, **kwargs):
        payload = kwargs["json"]
        if payload["model"] == SPINE_MODELS[0]:
            user_message = payload["messages"][1]["content"]
            architect_input = json.loads(user_message)
            feedback = architect_input["revision_feedback"]
            assert feedback["required_chronological_route"] == [
                "vellum_hall", "greyfen", "ashen_gate", "greyfen", "vellum_hall",
            ]
            captured.append(True)
        return FakeResponse(payload["model"])
    with patch("requests.post", side_effect=fake_post):
        with pytest.raises(SafetyStop, match="SPINE_GATE_REPLAN_STOP"):
            run(grant_file=grant, evidence_dir=tmp_path / "output",
                claim_dir=tmp_path / "claims")
    assert captured == [True]
    ev = [json.loads(f.read_text()) for f in
          (tmp_path / "output").glob("[0-9][0-9][0-9]-*.json")]
    assert any(e["kind"] == "REVISION_FEEDBACK_LOCKED" for e in ev)
    assert any(e["kind"] == "GATE_VERDICT_OBSERVED" and
               e["decision"] == "REPLAN" for e in ev)
