"""Fresh structured-events qualification. One claim, <=2 writers, <=2 guards.

Historical Q5T guard-preflight naming is unrelated; this lane never reads a prior
candidate and never mutates Q5S evidence. A failed/uncertain call ends the run.
"""
from __future__ import annotations

import json
import hashlib
import math
import time
from pathlib import Path
from typing import Any

from src.model_registry import normalize_openrouter_request, require_qualification_runtime_profile
from src.spineforge_v19_transport import _request_once
from src.spineforge_relay_v1_contracts import (
    StrictModel, StoryStateV1, ScenePlanV1, FrozenSpineRouteV1, SceneDeltaV1,
    StateMutation, SceneArtifactV1, canonical_sha256,
)
from src.spineforge_relay_v1_compile import compile_scene_contract, _value_at
from src.spineforge_relay_v1_events import PredicateEvidenceV1, evaluate_events
from src.spineforge_relay_v1_guard import (
    SemanticGuardReportV1, normalize_semantic_guard, deterministic_scene_findings,
    combine_scene_validation, word_count,
)
from src.spineforge_relay_v1_state import apply_scene_delta

WRITER = "openai/gpt-5.6-sol"
GUARD = "anthropic/claude-sonnet-5.5"
FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q5t_lighthouse_scene01.json")
OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q5T-STRUCTURED-20261007")
MAX_CALL_COST = 0.15
MAX_TOTAL_COST = 0.60


class StructuredGuardV1(StrictModel):
    event_evidence: list[PredicateEvidenceV1]
    residual: SemanticGuardReportV1


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def build_inputs():
    f = json.loads(FIXTURE.read_text(encoding="utf-8"))
    historical = json.loads(Path("tests/fixtures/spineforge_relay_v1/q5_lighthouse_scene01.json").read_text(encoding="utf-8"))
    for key in ("story_id", "story_intent", "initial_state", "route", "source_spine_path", "source_spine_sha256"):
        if f[key] != historical[key]:
            raise RuntimeError("Frozen input drift: " + key)
    if hashlib.sha256(Path(f["source_spine_path"]).read_bytes()).hexdigest() != f["source_spine_sha256"]:
        raise RuntimeError("Frozen spine bytes drift")
    state = StoryStateV1.model_validate({**f["initial_state"], "story_id": f["story_id"],
        "global_spine_sha256": f["source_spine_sha256"], "story_intent_sha256": canonical_sha256(f["story_intent"])})
    plan = ScenePlanV1.model_validate(f["scene_plan"])
    route = FrozenSpineRouteV1(global_spine_sha256=state.global_spine_sha256, beat_ids=f["route"])
    contract = compile_scene_contract(state, plan, route)
    return {"story_intent": f["story_intent"], "story_state": state.model_dump(mode="json"),
            "frozen_spine_route": route.model_dump(mode="json"),
            "scene_contract": contract.model_dump(mode="json")}, state, plan, route, contract


def _dependency_hashes():
    paths = sorted(set([*Path("src").glob("*.py"), *Path("prompts").glob("spineforge_relay_v1_q5t_*.md"),
        FIXTURE, Path("configs/model_runtime_profiles.yaml"),
        *Path("evidence/spineforge-relay").glob("SFR-V1-Q5S*/**/*.json")]))
    return {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def prepare():
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    inputs, state, plan, route, contract = build_inputs()
    return {"qualification_id": "SFR-V1-Q5T-STRUCTURED-20261007", "inputs": inputs,
        "state_sha256": canonical_sha256(state), "plan_sha256": canonical_sha256(plan),
        "route_sha256": canonical_sha256(route), "contract_sha256": canonical_sha256(contract),
        "dependencies": _dependency_hashes(), "writer": WRITER, "guard": GUARD,
        "max_rewrites": 1, "automatic_retry": False, "production_write": False,
        "max_call_cost_usd": MAX_CALL_COST, "max_total_cost_usd": MAX_TOTAL_COST}


def request_for(stage, payload):
    writer = stage == "writer"
    model = WRITER if writer else GUARD
    prompt = Path(f"prompts/spineforge_relay_v1_q5t_{stage}.md").read_text(encoding="utf-8").strip()
    schema = StructuredGuardV1.model_json_schema()
    def strict(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["required"] = list(node.get("properties", {}))
            for value in node.values(): strict(value)
        elif isinstance(node, list):
            for value in node: strict(value)
    strict(schema)
    response_format = {"type": "text"} if writer else {
        "type": "json_schema", "json_schema": {"name": "structured_event_guard", "strict": True,
                                                  "schema": schema}}
    kwargs = dict(model=model, system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        temperature=0.7 if writer else 0.0, max_tokens=3500 if writer else 5000,
        seed=None, request_class="spineforge_relay_v1_scene_writer_sol" if writer else "spineforge_relay_v1_q5t_guard",
        response_format=response_format, require_parameters=True)
    expected = normalize_openrouter_request(model, {"model": model,
        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": kwargs["user_prompt"]}],
        "temperature": kwargs["temperature"], "max_tokens": kwargs["max_tokens"]},
        request_class=kwargs["request_class"], structured_output=False)
    expected["response_format"] = response_format
    expected["provider"] = {**expected.get("provider", {}), "require_parameters": True}
    return kwargs, expected


def freeze_scene(state, contract, prose, validation):
    if validation.decision != "ACCEPT" or not validation.semantic_guard_used:
        raise RuntimeError("Only guarded ACCEPT can freeze")
    mutations = []
    for pointer, after in contract.required_exit_state.items():
        exists, before = _value_at(state.model_dump(mode="json"), pointer)
        if not exists or before != after:
            mutations.append(StateMutation(path=pointer, op="SET" if exists else "ADD", before=before, after=after))
    delta = SceneDeltaV1(scene_id=contract.scene_id, source_state_revision=state.revision,
        source_state_sha256=canonical_sha256(state), contract_sha256=canonical_sha256(contract), mutations=mutations)
    after = apply_scene_delta(state, delta, contract)
    artifact = SceneArtifactV1(scene_id=contract.scene_id, attempt=validation.attempt, status="ACCEPTED",
        prose=prose, word_count=word_count(prose), contract_sha256=canonical_sha256(contract),
        state_before_sha256=canonical_sha256(state), validation_sha256=canonical_sha256(validation),
        state_after_sha256=canonical_sha256(after))
    return delta, after, artifact


def execute(*, api_key, preflight, authorization, output=OUTPUT, call_fn=None):
    if preflight != prepare():
        raise RuntimeError("Q5T frozen preflight drift")
    if authorization != {"preflight_sha256": canonical_sha256(preflight), "paid_execution_authorized": True,
        "max_rewrites": 1, "automatic_retry": False, "state_application_on_accept": True,
        "user_instruction": "2026-10-07: fresh Q5T Sol/Sonnet qualification; max 1 rewrite; no retry; freeze only on PASS"}:
        raise RuntimeError("Q5T authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential; no claim or call made")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)  # Durable local claim; never resume or overwrite.
    claims = output.parent / "claims"
    claims.mkdir(exist_ok=True)
    save(claims / "q5t-structured-20261007.json", {"status": "CLAIMED_BEFORE_INFERENCE", **authorization})
    save(output / "authorization.json", authorization)
    save(output / "preflight.json", preflight)
    inputs, state, _, _, contract = build_inputs()
    ledger = []
    result = {"status": "REJECT_NON_CONVERGENT", "reason": "UNFINISHED", "ledger": ledger,
              "state_advanced": False, "automatic_retry": False, "max_rewrites": 1}

    def call(stage, attempt, payload):
        kwargs, request = request_for(stage, payload)
        rates = require_qualification_runtime_profile(kwargs["model"])["metadata"]["pricing_usd_per_million_tokens"]
        planned = (len(json.dumps(request, ensure_ascii=False).encode("utf-8")) * float(rates["input"])
                   + request["max_tokens"] * float(rates["output"])) / 1_000_000
        if planned > MAX_CALL_COST or planned + sum(r["cost_usd"] or 0 for r in ledger) > MAX_TOTAL_COST:
            raise RuntimeError("Conservative pre-dispatch cost estimate exceeds ceiling")
        row = {"stage": stage, "attempt": attempt, "model": kwargs["model"],
               "request_sha256": canonical_sha256(request), "status": "STARTED",
               "planned_uncached_cost_usd": round(planned, 8), "provider_spend_cap_guaranteed": False,
               "input_tokens": None, "output_tokens": None, "total_tokens": None, "cost_usd": None}
        ledger.append(row)
        prefix = output / f"{attempt}-{stage}"
        save(str(prefix) + "-request.json", request)
        save(str(prefix) + "-started.json", row)
        start = time.perf_counter()
        body = {}
        try:
            text, body, actual = (call_fn or _request_once)(api_key=api_key, **kwargs)
            save(str(prefix) + "-response.json", {k: body[k] for k in ("id", "model", "choices", "usage") if k in body})
            save(str(prefix) + "-text.json", {"text": text})
            if actual != request:
                raise RuntimeError("Dispatched request drift")
            if (body.get("choices") or [{}])[0].get("finish_reason") != "stop":
                raise RuntimeError("Incomplete provider response")
            usage = body.get("usage") or {}
            for source, target in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens"), ("total_tokens", "total_tokens"), ("cost", "cost_usd")):
                value = usage.get(source)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise RuntimeError("Missing or invalid ledger field: " + source)
                row[target] = value
            if row["cost_usd"] > MAX_CALL_COST or sum(x["cost_usd"] or 0 for x in ledger) > MAX_TOTAL_COST:
                raise RuntimeError("Cost ceiling exceeded")
            row["status"] = "COMPLETE"
            return text
        except Exception as exc:
            row["status"] = "FAILED_NO_RETRY"
            row["failure_type"] = type(exc).__name__
            # Preserve response usage even on parsing/transport failures where available.
            failed_body = body or (getattr(exc, "trace", {}) or {}).get("body", {})
            row["raw_usage"] = failed_body.get("usage")
            for source, target in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens"), ("total_tokens", "total_tokens"), ("cost", "cost_usd")):
                value = (row["raw_usage"] or {}).get(source)
                if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                    row[target] = value
            if failed_body and not body:
                save(str(prefix) + "-failure-response.json", {k: failed_body[k] for k in ("id", "model", "choices", "usage") if k in failed_body})
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - start, 3)
            save(str(prefix) + "-ledger.json", row)

    try:
        rewrite = None
        for attempt in (1, 2):
            payload = {**inputs, "attempt": attempt, "rewrite": rewrite}
            prose = call("writer", attempt, payload).strip()
            det = deterministic_scene_findings(prose=prose, contract=contract)
            if not prose or prose.startswith(("{", "[", "```")):
                raise RuntimeError("Writer response is not plain prose")
            raw = json.loads(call("guard", attempt, {**inputs, "candidate_prose": prose,
                "deterministic_findings": [f.model_dump(mode="json") for f in det]}))
            report = StructuredGuardV1.model_validate(raw)
            semantic = normalize_semantic_guard(raw=report.residual.model_dump(mode="json"), prose=prose)
            det += evaluate_events(contract=contract, state=state, prose=prose, evidence=report.event_evidence)
            validation = combine_scene_validation(scene_id=contract.scene_id, attempt=attempt, deterministic=det, semantic=semantic)
            save(output / f"{attempt}-validation.json", validation.model_dump(mode="json"))
            if validation.decision == "ACCEPT":
                delta, after, artifact = freeze_scene(state, contract, prose, validation)
                # One atomic evidence bundle prevents a partial freeze being mistaken for success.
                save(output / "accepted-scene.json", {"delta": delta.model_dump(mode="json"),
                    "state_after": after.model_dump(mode="json"), "artifact": artifact.model_dump(mode="json")})
                result.update(status="ACCEPT", reason="ALL_EVENTS_AND_RESIDUAL_GUARD_PASS", state_advanced=True,
                              revision=after.revision, next_spine_beat=after.next_spine_beat)
                break
            rewrite = {"candidate_prose": prose, "validation": validation.model_dump(mode="json")}
            result["reason"] = "BLOCKING_FINDINGS_REMAIN"
    except Exception as exc:
        result["reason"] = "FAILED_CLOSED_NO_RETRY"
        result["failure_type"] = type(exc).__name__
        # Never include credentials or arbitrary provider error strings in the summary.
    result["known_cost_usd"] = round(sum(r["cost_usd"] or 0 for r in ledger), 8)
    result["usage_complete"] = all(all(r[k] is not None for k in ("cost_usd", "input_tokens", "output_tokens", "total_tokens")) for r in ledger)
    save(output / "result.json", result)
    return result


if __name__ == "__main__":
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "execute"])
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--authorization", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        save(args.preflight, prepare())
        print("Q5T preflight frozen; no paid calls.")
    else:
        if not args.authorization:
            parser.error("execute requires --authorization")
        result = execute(api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            preflight=json.loads(args.preflight.read_text(encoding="utf-8")),
            authorization=json.loads(args.authorization.read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["status"] == "ACCEPT" else 2)
