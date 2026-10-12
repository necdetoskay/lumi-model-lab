"""Q6B: SC02 -> SC03 sequential relay with immutable character canon.

Fresh qualification lane after Q6A proved state relay but exposed a Duru pronoun
canon gap. Q6B preserves the same accepted SC01 source and Q6 scene plans while
adding relevant_character_canon to both writer and guard payloads.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from src.model_registry import normalize_openrouter_request, require_qualification_runtime_profile
from src.spineforge_v19_transport import _request_once
from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_events import evaluate_events
from src.spineforge_relay_v1_guard import (
    combine_scene_validation,
    deterministic_scene_findings,
    normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5t import StructuredGuardV1, freeze_scene, save
from src.spineforge_relay_v1_q6 import (
    build_chain,
    _sha,
    MAX_CALL_COST,
    MAX_TOTAL_COST,
    WRITER,
    GUARD,
)

CANON_FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q6b_identity_probe.json")
WRITER_PROMPT = Path("prompts/spineforge_relay_v1_q6b_writer.md")
GUARD_PROMPT = Path("prompts/spineforge_relay_v1_q6b_guard.md")
OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q6B-SC02-SC03-20261007")


def relevant_character_canon():
    return json.loads(CANON_FIXTURE.read_text(encoding="utf-8"))["relevant_character_canon"]


def _strict_schema():
    schema = StructuredGuardV1.model_json_schema()
    def strict(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                strict(value)
        elif isinstance(node, list):
            for value in node:
                strict(value)
    strict(schema)
    return schema


def request_for(stage, payload):
    writer = stage == "writer"
    model = WRITER if writer else GUARD
    prompt = (WRITER_PROMPT if writer else GUARD_PROMPT).read_text(encoding="utf-8").strip()
    response_format = {"type": "text"} if writer else {
        "type": "json_schema",
        "json_schema": {
            "name": "q6b_structured_event_guard",
            "strict": True,
            "schema": _strict_schema(),
        },
    }
    kwargs = dict(
        model=model,
        system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        temperature=0.7 if writer else 0.0,
        max_tokens=3500 if writer else 5000,
        seed=None,
        request_class="spineforge_relay_v1_scene_writer_sol" if writer else "spineforge_relay_v1_q5t_guard",
        response_format=response_format,
        require_parameters=True,
    )
    expected = normalize_openrouter_request(
        model,
        {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": kwargs["user_prompt"]},
            ],
            "temperature": kwargs["temperature"],
            "max_tokens": kwargs["max_tokens"],
        },
        request_class=kwargs["request_class"],
        structured_output=False,
    )
    expected["response_format"] = response_format
    expected["provider"] = {**expected.get("provider", {}), "require_parameters": True}
    return kwargs, expected


def prepare():
    for model in (WRITER, GUARD):
        require_qualification_runtime_profile(model)
    fixture, intent, route, start, rows, expected = build_chain()
    canon = relevant_character_canon()
    return {
        "qualification_id": "SFR-V1-Q6B-SC02-SC03-20261007",
        "source_q6a_review_sha256": _sha(Path("evidence/spineforge-relay/SFR-V1-Q6A-REVIEW-20261007/result.json")),
        "identity_guard_preflight_sha256": _sha(Path("evidence/spineforge-relay/SFR-V1-Q6B-ID-GUARD-PREFLIGHT-20261007/preflight.json")),
        "relevant_character_canon": canon,
        "relevant_character_canon_sha256": canonical_sha256(canon),
        "story_intent_sha256": canonical_sha256(intent),
        "route_sha256": canonical_sha256(route),
        "start_state_sha256": canonical_sha256(start),
        "scene_contracts": [
            {
                "scene_id": plan.scene_id,
                "state_revision": before.revision,
                "state_sha256": canonical_sha256(before),
                "plan_sha256": canonical_sha256(plan),
                "contract_sha256": canonical_sha256(contract),
            }
            for plan, contract, before in rows
        ],
        "expected_final_state_sha256": canonical_sha256(expected),
        "writer": WRITER,
        "guard": GUARD,
        "writer_prompt_sha256": _sha(WRITER_PROMPT),
        "guard_prompt_sha256": _sha(GUARD_PROMPT),
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_chain_on_scene_failure": True,
        "production_write": False,
        "max_call_cost_usd": MAX_CALL_COST,
        "max_total_cost_usd": MAX_TOTAL_COST,
    }


def authorization_for(preflight):
    return {
        "preflight_sha256": canonical_sha256(preflight),
        "paid_execution_authorized": True,
        "scenes": ["SC02", "SC03"],
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_chain_on_scene_failure": True,
        "state_application_on_accept": True,
        "max_total_cost_usd": MAX_TOTAL_COST,
        "user_instruction": (
            "2026-10-07: fresh Q6B sequential relay after identity guard qualification; "
            "shared immutable character canon; SC02 then SC03; no retry; stop on scene failure"
        ),
    }


def execute(*, api_key: str, preflight: dict, authorization: dict, output=OUTPUT, call_fn=None):
    if preflight != prepare():
        raise RuntimeError("Q6B frozen preflight drift")
    if authorization != authorization_for(preflight):
        raise RuntimeError("Q6B authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    claims = output.parent / "claims"
    claims.mkdir(exist_ok=True)
    claim = claims / "q6b-sc02-sc03-20261007.json"
    with claim.open("x", encoding="utf-8") as handle:
        json.dump({"status": "CLAIMED_BEFORE_INFERENCE", **authorization}, handle, indent=2)
        handle.write("\n")

    save(output / "authorization.json", authorization)
    save(output / "preflight.json", preflight)

    _fixture, intent, route, state, rows, expected_final = build_chain()
    canon = relevant_character_canon()
    ledger = []
    result = {
        "status": "REJECT_NON_CONVERGENT",
        "reason": "UNFINISHED",
        "accepted_scenes": [],
        "ledger": ledger,
        "automatic_retry": False,
        "state_advanced_to_revision": state.revision,
        "next_spine_beat": state.next_spine_beat,
    }

    def call(scene_id, stage, attempt, payload):
        kwargs, request = request_for(stage, payload)
        rates = require_qualification_runtime_profile(kwargs["model"])["metadata"]["pricing_usd_per_million_tokens"]
        planned = (
            len(json.dumps(request, ensure_ascii=False).encode("utf-8")) * float(rates["input"])
            + request["max_tokens"] * float(rates["output"])
        ) / 1_000_000
        if planned > MAX_CALL_COST or planned + sum(r["cost_usd"] or 0 for r in ledger) > MAX_TOTAL_COST:
            raise RuntimeError("Q6B conservative cost ceiling")

        row = {
            "scene_id": scene_id,
            "stage": stage,
            "attempt": attempt,
            "model": kwargs["model"],
            "request_sha256": canonical_sha256(request),
            "status": "STARTED",
            "planned_uncached_cost_usd": round(planned, 8),
            "provider_spend_cap_guaranteed": False,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "cost_usd": None,
        }
        ledger.append(row)
        prefix = output / f"{scene_id}-{attempt}-{stage}"
        save(str(prefix) + "-request.json", request)
        start = time.perf_counter()
        try:
            text, body, actual = (call_fn or _request_once)(api_key=api_key, **kwargs)
            save(str(prefix) + "-response.json", {
                k: body[k] for k in ("id", "model", "choices", "usage") if k in body
            })
            save(str(prefix) + "-text.json", {"text": text})
            if actual != request:
                raise RuntimeError("Q6B dispatched request drift")
            if (body.get("choices") or [{}])[0].get("finish_reason") != "stop":
                raise RuntimeError("Incomplete provider response")
            usage = body.get("usage") or {}
            for source, target in (
                ("prompt_tokens", "input_tokens"),
                ("completion_tokens", "output_tokens"),
                ("total_tokens", "total_tokens"),
                ("cost", "cost_usd"),
            ):
                value = usage.get(source)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise RuntimeError("Missing/invalid ledger field: " + source)
                row[target] = value
            if row["cost_usd"] > MAX_CALL_COST or sum(x["cost_usd"] or 0 for x in ledger) > MAX_TOTAL_COST:
                raise RuntimeError("Q6B cost ceiling exceeded")
            row["status"] = "COMPLETE"
            return text
        except Exception as exc:
            row["status"] = "FAILED_NO_RETRY"
            row["failure_type"] = type(exc).__name__
            raise
        finally:
            row["latency_seconds"] = round(time.perf_counter() - start, 3)
            save(str(prefix) + "-ledger.json", row)

    try:
        for plan, _precompiled, _expected_before in rows:
            if state.next_spine_beat != plan.spine_beats[0]:
                raise RuntimeError("Q6B stale progression before scene")
            contract = compile_scene_contract(state, plan, route)
            rewrite = None
            scene_accepted = False
            for attempt in (1, 2):
                inputs = {
                    "story_intent": intent,
                    "story_state": state.model_dump(mode="json"),
                    "frozen_spine_route": route.model_dump(mode="json"),
                    "scene_contract": contract.model_dump(mode="json"),
                    "relevant_character_canon": canon,
                }
                payload = {**inputs, "attempt": attempt, "rewrite": rewrite}
                prose = call(plan.scene_id, "writer", attempt, payload).strip()
                det = deterministic_scene_findings(prose=prose, contract=contract)
                if not prose or prose.startswith(("{", "[", "```")):
                    raise RuntimeError("Writer response is not plain prose")

                raw = json.loads(call(
                    plan.scene_id,
                    "guard",
                    attempt,
                    {
                        **inputs,
                        "candidate_prose": prose,
                        "deterministic_findings": [f.model_dump(mode="json") for f in det],
                    },
                ))
                report = StructuredGuardV1.model_validate(raw)
                semantic = normalize_semantic_guard(
                    raw=report.residual.model_dump(mode="json"),
                    prose=prose,
                )
                det += evaluate_events(
                    contract=contract,
                    state=state,
                    prose=prose,
                    evidence=report.event_evidence,
                )
                validation = combine_scene_validation(
                    scene_id=contract.scene_id,
                    attempt=attempt,
                    deterministic=det,
                    semantic=semantic,
                )
                save(
                    output / f"{plan.scene_id}-{attempt}-validation.json",
                    validation.model_dump(mode="json"),
                )
                if validation.decision == "ACCEPT":
                    delta, after, artifact = freeze_scene(
                        state, contract, prose, validation
                    )
                    bundle = {
                        "delta": delta.model_dump(mode="json"),
                        "state_after": after.model_dump(mode="json"),
                        "artifact": artifact.model_dump(mode="json"),
                    }
                    save(output / f"{plan.scene_id}-accepted.json", bundle)
                    state = after
                    scene_accepted = True
                    result["accepted_scenes"].append(plan.scene_id)
                    result["state_advanced_to_revision"] = state.revision
                    result["next_spine_beat"] = state.next_spine_beat
                    break

                rewrite = {
                    "candidate_prose": prose,
                    "validation": validation.model_dump(mode="json"),
                }

            if not scene_accepted:
                result["reason"] = "SCENE_REJECT_NON_CONVERGENT:" + plan.scene_id
                break
        else:
            if canonical_sha256(state) != canonical_sha256(expected_final):
                raise RuntimeError("Q6B final state differs from deterministic expected state")
            result["status"] = "ACCEPT"
            result["reason"] = "SC02_SC03_ACCEPTED_WITH_CHARACTER_CANON"
    except Exception as exc:
        result["reason"] = "FAILED_CLOSED_NO_RETRY"
        result["failure_type"] = type(exc).__name__

    result["known_cost_usd"] = round(
        sum(r["cost_usd"] or 0 for r in ledger), 8
    )
    result["usage_complete"] = all(
        all(r[k] is not None for k in ("cost_usd", "input_tokens", "output_tokens", "total_tokens"))
        for r in ledger
    )
    save(output / "result.json", result)
    return result
