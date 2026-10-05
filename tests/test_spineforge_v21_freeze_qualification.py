from __future__ import annotations

import copy
import hashlib
import json
import shutil
import socket
from pathlib import Path

import pytest

from src.spineforge_v21_constraints import digest_json, load_constraints, select
from src.spineforge_v21_freeze import PROFILE, SOURCE, APPROVAL, verify_v21_runtime
from src.spineforge_v21_model_adapter import execute_initial_audit_call
from src.spineforge_v21_paid_quality_once import execute_paid_quality_once
from src.spineforge_v21_quality_runtime import run_bounded_quality
from src.spineforge_v21_simulation import CASES, simulate_case


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Zero-cost qualification attempted network access")
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)


@pytest.mark.parametrize("case", CASES)
def test_real_harness_and_adapter_offline_scenarios(case, tmp_path):
    assert simulate_case(case, tmp_path)["pass"]


def test_constraint_text_is_exactly_approved_and_hash_bound():
    profile = json.loads(PROFILE.read_text())
    artifact = load_constraints(profile)
    spine = json.loads(APPROVAL.read_text())["approved_spine"]
    for row in artifact["constraints"]:
        assert row["text"] == select(spine, row["source_pointer"])
    assert any("cuts the line loose to free himself" in r["text"] for r in artifact["constraints"])
    assert any(r["role"] == "exit_dependency" for r in artifact["constraints"])
    assert any(r["role"] == "reveal_limit" for r in artifact["constraints"])


@pytest.fixture
def copied_freeze(tmp_path, monkeypatch):
    root = Path.cwd()
    profile = json.loads(PROFILE.read_text())
    for path in [PROFILE] + [Path(r["path"]) for r in profile["runtime_freeze"]["files"]]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / path, target)
    monkeypatch.chdir(tmp_path)
    return profile


@pytest.mark.parametrize("target", ["source", "spine", "prompt", "adapter", "runtime", "constraints", "hash", "authorization", "cost"])
def test_freeze_mutations_stop_before_transport(target, copied_freeze, tmp_path):
    profile = copied_freeze
    paths = {"source": Path(json.loads(SOURCE.read_text())["repaired_story_path"]),
             "spine": APPROVAL, "prompt": Path("prompts/spineforge_v21_scene_repair.md"),
             "adapter": Path("src/spineforge_v21_model_adapter.py"),
             "runtime": Path("src/spineforge_v21_quality_runtime.py"),
             "constraints": Path(profile["approved_spine"]["constraints_path"])}
    if target in paths:
        with paths[target].open("a") as handle:
            handle.write("\nMUTATION\n")
    else:
        if target == "hash":
            profile["runtime_freeze"]["files"][0]["sha256"] = "0" * 64
        elif target == "authorization":
            profile["paid_boundary"]["paid_execution_authorized"] = True
        else:
            profile["cost_policy"]["quality_stage_limits_usd"]["initial_audit"] = 1.0
        PROFILE.write_text(json.dumps(profile))
    calls = []
    def callback(_):
        calls.append(1)
        pytest.fail("Mutation reached callback")
    with pytest.raises(RuntimeError):
        execute_paid_quality_once(api_key="", run_id="mutated", simulation=True,
                                  output_root=tmp_path / "result", initial_audit_fn=callback,
                                  scene_repair_fn=callback, final_audit_fn=callback)
    assert not calls


def usage(cost=0.01):
    return {"api_calls": 1, "input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
            "reasoning_tokens": 0, "cost_usd": cost, "latency_seconds": 1.0}


def runtime_args():
    artifact = json.loads(SOURCE.read_text())
    story = Path(artifact["repaired_story_path"]).read_text().removesuffix("\n")
    def forbidden(_):
        pytest.fail("Rejected stage reached downstream")
    return {"source_story_artifact_id": artifact["artifact_id"],
            "source_story_sha256": artifact["repaired_story_text_sha256"],
            "source_story": story, "story_segments": artifact["repaired_segments"],
            "approved_spine_hash": "test", "canon_invariants": [],
            "scene_repair_fn": forbidden, "final_audit_fn": forbidden}


@pytest.mark.parametrize("field,value", [("cost_usd", None), ("cost_usd", float("nan")),
    ("cost_usd", -1), ("api_calls", 2), ("api_calls", 0), ("total_tokens", 999),
    ("input_tokens", "100"), ("latency_seconds", float("inf"))])
def test_bad_accounting_stops_and_does_not_invent_zero_cost(field, value):
    u = usage(); u[field] = value
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda _: {"findings": [], "usage": u})
    assert result["status"] == "REJECT_USAGE_ACCOUNTING"
    assert result["quality_model_calls"] == 1
    assert result["quality_usage_rollup"]["cost_usd"] is None


def test_source_sha_mutation_blocks_clean_path_before_call():
    args = runtime_args(); args["source_story"] += "changed"
    with pytest.raises(RuntimeError, match="SHA"):
        run_bounded_quality(**args, initial_audit_fn=lambda _: pytest.fail("source mutated"))


@pytest.mark.parametrize("raw", [{}, {"findings": None}, {"findings": [{}]}])
def test_invalid_audit_is_never_treated_as_clean(raw):
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda _: {**raw, "usage": usage()})
    assert result["status"] == "REJECT_INVALID_RESPONSE"


@pytest.mark.parametrize("scope", ["REPLAN", "STRUCTURAL_REPAIR"])
def test_unbounded_scope_stops_after_one_call(scope):
    finding = {"family": "causal_logic", "severity": "serious", "repair_scope": scope,
               "span_ids": ["S159"], "exact_text": "x", "reason": "unbounded"}
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda _: {"findings": [finding], "usage": usage()})
    assert result["status"] == "REJECT_UNBOUNDED_REPAIR_SCOPE"
    assert result["quality_model_calls"] == 1


@pytest.mark.parametrize("claims", [[], [0, 1], [0, 0], [True], ["0"]])
def test_claim_set_is_exact_before_final_audit(claims):
    args = runtime_args()
    args["scene_repair_fn"] = lambda _: {"replacement_scene": "A scene.", "resolved_blocking_finding_indexes": claims, "usage": usage()}
    finding = {"family": "causal_logic", "severity": "serious", "repair_scope": "SCENE_REPAIR",
               "span_ids": ["S159"], "exact_text": "x", "reason": "bounded"}
    result = run_bounded_quality(**args, initial_audit_fn=lambda _: {"findings": [finding], "usage": usage()})
    assert result["status"] == "REJECT_INVALID_REPAIR_CLAIM"
    assert result["quality_model_calls"] == 2
    assert result["quality_usage_rollup"]["cost_usd"] == 0.02


def test_provider_missing_cost_is_not_normalized_to_free_call():
    def transport(**_):
        return {"findings": [], "summary": "ok"}, {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}, {}, []
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda payload: execute_initial_audit_call(api_key="", payload=payload, call_fn=transport))
    assert result["status"] == "REJECT_PROVIDER_FAILURE"
    assert result["quality_usage_rollup"]["cost_usd"] is None


def test_invalid_provider_response_preserves_confirmed_charge():
    def transport(**_):
        return {}, {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120, "cost": 0.01234567891}}, {}, []
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda payload: execute_initial_audit_call(api_key="", payload=payload, call_fn=transport))
    assert result["status"] == "REJECT_PROVIDER_FAILURE"
    assert result["quality_usage_rollup"]["cost_usd"] == 0.01234567891


def test_budget_equal_to_ceiling_is_allowed():
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda _: {"findings": [], "usage": usage(0.04)})
    assert result["status"] == "ACCEPT"


def test_ledger_failure_prevents_dispatch():
    def fail(_):
        raise OSError("ledger unavailable")
    with pytest.raises(OSError):
        run_bounded_quality(**runtime_args(), initial_audit_fn=lambda _: pytest.fail("ledger failed"), record_event=fail)


@pytest.mark.parametrize("invalid_field,invalid_value,expected_path", [
    ("family", "not_a_family", "$.findings[0].family"),
    ("repair_scope", "LOCAL_REPAIR", "$.findings[0].repair_scope"),
    ("reason", "x" * 501, "$.findings[0].reason"),
])
def test_failed_final_response_retains_diagnostics_and_never_looks_clean(invalid_field, invalid_value, expected_path):
    from src.spineforge_v21_model_adapter import execute_final_audit_call
    from src.spineforge_v21_constraints import digest_json
    finding = {"family": "causal_logic", "severity": "serious", "repair_scope": "SCENE_REPAIR",
               "span_ids": ["S159"], "exact_text": "x", "reason": "bounded"}
    final = {**finding, "span_ids": ["R001"], invalid_field: invalid_value}
    raw = {"findings": [final], "summary": "Synthetic invalid response; not the lost paid response"}
    calls, events = [], []
    def transport(**kwargs):
        calls.append(kwargs["request_class"])
        return raw, {"usage": {"prompt_tokens": 100, "completion_tokens": 20,
                               "total_tokens": 120, "cost": 0.01},
                     "choices": [{"message": {"content": json.dumps(raw)}}],
                     "headers": {"Authorization": "NEVER_STORE_THIS"}}, {}, []
    args = runtime_args()
    args["scene_repair_fn"] = lambda _: {"replacement_scene": "A scene.", "resolved_blocking_finding_indexes": [0], "usage": usage()}
    args["final_audit_fn"] = lambda p: execute_final_audit_call(api_key="", payload=p, call_fn=transport)
    result = run_bounded_quality(**args, record_event=events.append,
                                 initial_audit_fn=lambda _: {"findings": [finding], "usage": usage()})
    assert result["status"] == "REJECT_PROVIDER_FAILURE"
    assert result["quality_model_calls"] == 3 and result["repair_count"] == 1
    assert len(calls) == 1
    assert result["quality_usage_rollup"]["cost_usd"] == 0.03
    assert result["final_audit_validated"] is False
    assert result["final_blocking_count"] is None
    assert result["accepted_story"] is None
    assert expected_path in result["failure_reason"]
    assert expected_path in events[-1]["failure_message"]
    evidence = events[-1]["provider_evidence"]
    assert evidence["parsed_response"] == raw
    assert evidence["parsed_response_sha256"] == digest_json(raw)
    assert evidence["provider_response"]["choices"][0]["message"]["content"] == json.dumps(raw)
    assert "NEVER_STORE_THIS" not in json.dumps(result)


def test_transport_parse_failure_preserves_available_response_body():
    from src.generate import OpenRouterCallError
    def transport(**_):
        raise OpenRouterCallError("private diagnostic", {
            "stage": "structured_parse", "request": {"secret": "NEVER_STORE_THIS"},
            "body": {"choices": [{"message": {"content": "{invalid JSON"}}],
                     "usage": {"prompt_tokens": 100, "completion_tokens": 20,
                               "total_tokens": 120, "cost": 0.01}}})
    result = run_bounded_quality(**runtime_args(), initial_audit_fn=lambda p: execute_initial_audit_call(api_key="", payload=p, call_fn=transport))
    evidence = result["quality_calls"][0]["provider_evidence"]
    assert evidence["phase"] == "structured_parse"
    assert evidence["provider_response"]["choices"][0]["message"]["content"] == "{invalid JSON"
    assert "NEVER_STORE_THIS" not in json.dumps(result)
    assert result["quality_model_calls"] == 1
