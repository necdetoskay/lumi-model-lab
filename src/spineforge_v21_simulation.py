"""Offline harness proof. Fake verdicts are NOT story-quality evidence."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.spineforge_v21_freeze import AUDIT, verify_v21_runtime
from src.spineforge_v21_model_adapter import (
    execute_initial_audit_call, execute_scene_repair_call, execute_final_audit_call,
)
from src.spineforge_v21_paid_quality_once import execute_paid_quality_once

CASES = {
    "clean": ("ACCEPT", 1, 0, False),
    "repair_succeeds": ("ACCEPT", 3, 1, True),
    "non_convergent": ("REJECT_NON_CONVERGENT", 3, 1, True),
    "initial_cost_ceiling": ("REJECT_COST_CEILING", 1, 0, False),
    "repair_cost_ceiling": ("REJECT_COST_CEILING", 2, 1, False),
    "final_cost_ceiling": ("REJECT_COST_CEILING", 3, 1, True),
}


def simulate_case(name: str, output_root: Path) -> dict:
    observed = []
    findings = json.loads(AUDIT.read_text())["findings"]
    # Historical fixture calls a bounded span repair LOCAL_REPAIR; v21 wire schema calls it SCENE_REPAIR.
    findings = [{**r, "repair_scope": "SCENE_REPAIR" if r["repair_scope"] == "LOCAL_REPAIR" else r["repair_scope"]}
                for r in findings]
    def transport(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        stage = kwargs["request_class"]
        observed.append(stage)
        cost = 0.01
        if "initial" in stage:
            assert payload["reader_profile"]["exact_age"] == 12
            assert payload["approved_constraints"]["artifact_sha256"]
            raw = {"findings": [] if name == "clean" else findings, "summary": "synthetic initial result"}
            if name == "initial_cost_ceiling":
                cost = 0.041
        elif "scene_repair" in stage:
            assert payload["source_scene"]
            assert payload["scene_cluster"]["start_span_id"] == "S159"
            assert payload["scene_cluster"]["end_span_id"] == "S177"
            assert payload["entry_boundary"]["span_id"] == "S158"
            assert payload["exit_boundary"]["span_id"] == "S178"
            raw = {"replacement_scene": "Arda cut the line. Nisa helped him reach solid ground.",
                   "resolved_blocking_finding_indexes": [r["index"] for r in payload["blocking_findings"]],
                   "preserved_invariants": [], "summary": "Synthetic mechanics fixture, NOT a qualified story repair"}
            if name == "repair_cost_ceiling":
                cost = 0.036
        else:
            assert "full_story" not in payload and "story_segments" not in payload
            assert payload["routing_policy"]["scope"] == "REPAIRED_SCENE_PLUS_BOUNDARIES"
            assert payload["constraints_sha256"]
            assert any(r["role"] == "exit_dependency" for r in payload["approved_constraints"]["constraints"])
            raw = {"findings": [], "summary": "synthetic final result"}
            if name == "non_convergent":
                raw["findings"] = [{"family": "physical_feasibility", "severity": "serious",
                                    "repair_scope": "NO_REPAIR", "span_ids": ["R001"],
                                    "exact_text": "Arda cut the line.", "reason": "Force chain still unresolved"}]
            if name == "final_cost_ceiling":
                cost = 0.026
        body = {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120, "cost": cost}}
        return raw, body, {"max_tokens": kwargs["max_tokens"], "response_format": {"type": "json_schema"}}, []

    def callback(adapter):
        return lambda payload: adapter(api_key="", payload=payload, call_fn=transport)
    result, envelope = execute_paid_quality_once(
        api_key="", run_id=name, output_root=output_root, simulation=True,
        initial_audit_fn=callback(execute_initial_audit_call),
        scene_repair_fn=callback(execute_scene_repair_call),
        final_audit_fn=callback(execute_final_audit_call))
    expected = CASES[name]
    actual = (result["status"], result["quality_model_calls"], result["repair_count"], result["final_audit_executed"])
    assert actual == expected, (name, actual, expected)
    assert len(observed) == result["quality_model_calls"] <= 3
    assert result["automatic_second_repair_executed"] is False
    assert result["quality_usage_rollup"]["total_tokens"] == len(observed) * 120
    return {"scenario": name, "status": result["status"], "calls": len(observed),
            "repair_count": result["repair_count"], "final_audit": result["final_audit_executed"],
            "simulated_cost_usd": result["quality_usage_rollup"]["cost_usd"], "pass": True}


def main():
    freeze = verify_v21_runtime()
    with tempfile.TemporaryDirectory(prefix="v21-offline-") as tmp:
        rows = [simulate_case(name, Path(tmp)) for name in CASES]
    report = {"schema": "spineforge-v21-harness-simulation.v1", "status": "PASS", "paid_api_calls": 0,
              "provider_cost_usd": 0, "story_quality_proven": False,
              "runtime_revision": freeze["runtime_revision"], "profile_sha256": freeze["profile_sha256"],
              "scenarios": rows}
    path = Path("evidence/spineforge-v21-zero-cost/harness-simulation.json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
