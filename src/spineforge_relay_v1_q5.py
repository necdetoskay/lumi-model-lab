"""Q5 single-scene paid qualification preflight for SpineForge Relay v1.

This module is fail-closed by design:
- preparation and tests are zero-cost;
- paid execution requires a separate exact authorization artifact;
- one authorization can claim exactly one writer call;
- no retry/fallback is executed;
- generated prose is NOT automatically accepted into StoryState.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from src.generate import OpenRouterCallError
from src.model_registry import (
    normalize_openrouter_request,
    require_qualification_runtime_profile,
    runtime_profile_identity,
)
from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_contracts import (
    FrozenSpineRouteV1,
    ScenePlanV1,
    StoryStateV1,
    canonical_sha256,
)
from src.spineforge_v19_transport import _request_once
from src.spineforge_v21_model_adapter import provider_usage


MODEL = "aion-labs/aion-3.5-mini"
REQUEST_CLASS = "spineforge_relay_v1_scene_writer"
AUTH_SCOPE = "SFR_V1_Q5B_SINGLE_SCENE_ONE_CALL"
PROMPT = Path("prompts/spineforge_relay_v1_scene_writer.md")
FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q5_lighthouse_scene01.json")
DEFAULT_OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q5B-PREFLIGHT-20261006")
MAX_TOKENS = 5000
TEMPERATURE = 0.76
MAX_COST_USD = 0.015

TextCall = Callable[..., tuple[str, dict[str, Any], dict[str, Any]]]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def _dependencies() -> list[Path]:
    return [
        Path(__file__).relative_to(Path.cwd()),
        Path("src/spineforge_relay_v1_contracts.py"),
        Path("src/spineforge_relay_v1_compile.py"),
        Path("src/model_registry.py"),
        Path("src/spineforge_v19_transport.py"),
        Path("configs/model_runtime_profiles.yaml"),
        PROMPT,
        FIXTURE,
        Path("docs/experiments/lighthouse-context-and-spine-draft.md"),
    ]


def build_inputs() -> tuple[dict[str, Any], StoryStateV1, ScenePlanV1, FrozenSpineRouteV1, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = Path(fixture["source_spine_path"])
    if _file_sha256(source) != fixture["source_spine_sha256"]:
        raise RuntimeError("Q5 source spine drift")

    intent_sha = canonical_sha256(fixture["story_intent"])
    state = StoryStateV1.model_validate({
        **fixture["initial_state"],
        "story_id": fixture["story_id"],
        "global_spine_sha256": fixture["source_spine_sha256"],
        "story_intent_sha256": intent_sha,
    })
    route = FrozenSpineRouteV1(
        global_spine_sha256=fixture["source_spine_sha256"],
        beat_ids=fixture["route"],
    )
    plan = ScenePlanV1.model_validate(fixture["scene_plan"])
    contract = compile_scene_contract(state, plan, route)

    writer_input = {
        "schema": "spineforge-relay.scene-writer-input.v1",
        "fixture_id": fixture["fixture_id"],
        "source_kind": fixture["source_kind"],
        "story_intent": fixture["story_intent"],
        "frozen_spine_route": route.model_dump(mode="json"),
        "current_story_state": state.model_dump(mode="json"),
        "scene_contract": contract.model_dump(mode="json"),
        "continuity_window": None,
    }
    return writer_input, state, plan, route, contract


def request_payload(writer_input: dict[str, Any]) -> dict[str, Any]:
    request = normalize_openrouter_request(
        MODEL,
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PROMPT.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": json.dumps(writer_input, ensure_ascii=False, separators=(",", ":"))},
            ],
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
        },
        request_class=REQUEST_CLASS,
        structured_output=False,
    )
    request["response_format"] = {"type": "text"}
    return request


def prepare(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    profile = require_qualification_runtime_profile(MODEL)
    writer_input, state, plan, route, contract = build_inputs()
    request = request_payload(writer_input)
    input_bytes = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    pricing = (profile.get("metadata") or {}).get("pricing_usd_per_million_tokens") or {}
    input_rate = float(pricing.get("input", 0.0))
    output_rate = float(pricing.get("output", 0.0))
    conservative_planned_cost = round(
        input_bytes * input_rate / 1_000_000
        + MAX_TOKENS * output_rate / 1_000_000,
        6,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    writer_input_path = output_dir / "writer-input.json"
    writer_input_path.write_text(
        json.dumps(writer_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report = {
        "schema": "spineforge-relay.q5b-preflight.v1",
        "status": "OFFLINE_PREPARED_PAID_NOT_AUTHORIZED",
        "qualification_id": "SFR-V1-Q5B-SINGLE-SCENE-20261006",
        "fixture_id": writer_input["fixture_id"],
        "source_kind": writer_input["source_kind"],
        "model": MODEL,
        "request_class": REQUEST_CLASS,
        "model_runtime_profile": runtime_profile_identity(MODEL),
        "story_state_sha256": canonical_sha256(state),
        "scene_plan_sha256": canonical_sha256(plan),
        "frozen_spine_route_sha256": canonical_sha256(route),
        "scene_contract_sha256": canonical_sha256(contract),
        "writer_input_sha256": canonical_sha256(writer_input),
        "request": request,
        "request_sha256": canonical_sha256(request),
        "input_utf8_bytes": input_bytes,
        "planning_method": "UTF8_BYTES_AS_CONSERVATIVE_INPUT_TOKEN_ALLOWANCE_NOT_EXACT_TOKENIZATION",
        "pricing_usd_per_million": {
            "input": input_rate,
            "output": output_rate,
        },
        "max_tokens": MAX_TOKENS,
        "planned_uncached_cost_usd": conservative_planned_cost,
        "proposed_max_cost_usd": MAX_COST_USD,
        "max_writer_calls": 1,
        "automatic_retry": False,
        "provider_spend_cap_guaranteed": False,
        "semantic_guard_qualified": False,
        "post_call_status": "WRITER_GENERATED_PENDING_SCENE_REVIEW",
        "state_application_authorized": False,
        "paid_execution_authorized": False,
        "production_write": False,
        "files": [
            {"path": str(path), "sha256": _file_sha256(path)}
            for path in _dependencies()
        ],
    }
    report["artifact_sha256"] = canonical_sha256(report)
    (output_dir / "preflight.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def verify(
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    writer_input_path: Path = DEFAULT_OUTPUT / "writer-input.json",
) -> dict[str, Any]:
    report = json.loads(preflight_path.read_text(encoding="utf-8"))
    artifact_sha = report.pop("artifact_sha256")
    if canonical_sha256(report) != artifact_sha:
        raise RuntimeError("Q5 preflight integrity drift")
    report["artifact_sha256"] = artifact_sha

    for row in report["files"]:
        if _file_sha256(Path(row["path"])) != row["sha256"]:
            raise RuntimeError("Q5 frozen dependency drift: " + row["path"])

    writer_input, state, plan, route, contract = build_inputs()
    if json.loads(writer_input_path.read_text(encoding="utf-8")) != writer_input:
        raise RuntimeError("Q5 writer input drift")
    if report["writer_input_sha256"] != canonical_sha256(writer_input):
        raise RuntimeError("Q5 writer input fingerprint drift")
    if report["story_state_sha256"] != canonical_sha256(state):
        raise RuntimeError("Q5 story state fingerprint drift")
    if report["scene_plan_sha256"] != canonical_sha256(plan):
        raise RuntimeError("Q5 scene plan fingerprint drift")
    if report["frozen_spine_route_sha256"] != canonical_sha256(route):
        raise RuntimeError("Q5 spine route fingerprint drift")
    if report["scene_contract_sha256"] != canonical_sha256(contract):
        raise RuntimeError("Q5 scene contract fingerprint drift")
    if report["request"] != request_payload(writer_input):
        raise RuntimeError("Q5 frozen request drift")
    return report


def _validate_generated_scene(text: str, writer_input: dict[str, Any]) -> dict[str, Any]:
    if not text.strip() or "\r" in text:
        raise RuntimeError("Q5 writer returned empty or non-LF prose")
    if "[[" in text or "]]" in text or text.lstrip().startswith(("{", "[")):
        raise RuntimeError("Q5 writer violated plain-prose output contract")
    words = _word_count(text)
    contract = writer_input["scene_contract"]
    if not contract["target_words_min"] <= words <= contract["target_words_max"]:
        raise RuntimeError(
            f"Q5 scene word count outside contract: {words} not in "
            f"[{contract['target_words_min']}, {contract['target_words_max']}]"
        )
    return {
        "schema": "spineforge-relay.q5b-writer-artifact.v1",
        "status": "WRITER_GENERATED_PENDING_SCENE_REVIEW",
        "scene_id": contract["scene_id"],
        "prose": text.strip(),
        "prose_sha256": hashlib.sha256(text.strip().encode("utf-8")).hexdigest(),
        "word_count": words,
        "writer_input_sha256": canonical_sha256(writer_input),
        "scene_contract_sha256": canonical_sha256(contract),
        "semantic_guard_qualified": False,
        "state_application_authorized": False,
        "publication_ready": False,
    }


def _usage(body: dict[str, Any], latency_seconds: float) -> dict[str, Any]:
    raw = body.get("usage") or {}
    details = raw.get("completion_tokens_details") or {}
    return {
        "api_calls": 1,
        "input_tokens": raw.get("prompt_tokens"),
        "output_tokens": raw.get("completion_tokens"),
        "total_tokens": raw.get("total_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens", raw.get("reasoning_tokens", 0)),
        "cost_usd": raw.get("cost"),
        "latency_seconds": round(latency_seconds, 3),
    }


def execute_once(
    *,
    api_key: str,
    run_id: str,
    authorization: dict[str, Any],
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    writer_input_path: Path = DEFAULT_OUTPUT / "writer-input.json",
    output_root: Path = Path("evidence/spineforge-relay/q5-runs"),
    call_fn: TextCall | None = None,
) -> dict[str, Any]:
    report = verify(preflight_path, writer_input_path)
    if (
        authorization.get("paid_execution_authorized") is not True
        or authorization.get("scope") != AUTH_SCOPE
        or authorization.get("preflight_sha256") != report["artifact_sha256"]
        or authorization.get("max_cost_usd") != MAX_COST_USD
        or authorization.get("max_writer_calls") != 1
        or authorization.get("automatic_retry") is not False
        or authorization.get("production_write") is not False
        or authorization.get("state_application_authorized") is not False
        or not authorization.get("explicit_user_message")
    ):
        raise RuntimeError("Separate explicit SFR-v1 Q5B paid authorization required")
    if not api_key or not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise RuntimeError("Q5 API key/run id missing or invalid")

    output_root.mkdir(parents=True, exist_ok=True)
    claim = output_root / ("authorization-" + canonical_sha256(authorization) + ".claimed")
    claim.open("x").close()
    out = output_root / run_id
    out.mkdir(exist_ok=False)

    writer_input = json.loads(writer_input_path.read_text(encoding="utf-8"))
    request = report["request"]
    evidence = {
        "schema": "spineforge-relay.q5b-call.v1",
        "status": "STARTED",
        "preflight_sha256": report["artifact_sha256"],
        "authorization": authorization,
        "request_sha256": report["request_sha256"],
        "automatic_retry_executed": False,
        "api_calls": 0,
        "usage": None,
        "state_application_authorized": False,
    }
    call_path = out / "writer-call.json"
    call_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    started = time.perf_counter()
    try:
        text, body, actual_request = (call_fn or _request_once)(
            api_key=api_key,
            model=MODEL,
            system_prompt=request["messages"][0]["content"],
            user_prompt=request["messages"][1]["content"],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            seed=None,
            request_class=REQUEST_CLASS,
            response_format={"type": "text"},
            require_parameters=False,
        )
        evidence["api_calls"] = 1
        evidence["raw_response"] = text
        evidence["provider_response"] = {
            key: body[key] for key in ("id", "model", "choices", "usage") if key in body
        }
        evidence["actual_request"] = actual_request
        call_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        evidence["usage"] = provider_usage(
            body,
            "SFR_V1_Q5B_SCENE_WRITER",
            time.perf_counter() - started,
        )
        if actual_request != request:
            raise RuntimeError("Q5 dispatched request differs from frozen preflight")
        finish = (body.get("choices") or [{}])[0].get("finish_reason")
        if finish != "stop":
            raise RuntimeError("Q5 writer incomplete response: " + str(finish))
        if evidence["usage"]["cost_usd"] is None:
            raise RuntimeError("Q5 provider did not report call cost")
        if float(evidence["usage"]["cost_usd"]) > MAX_COST_USD:
            raise RuntimeError("Q5 provider-reported cost exceeds authorized ceiling")

        artifact = _validate_generated_scene(text, writer_input)
        artifact["artifact_sha256"] = canonical_sha256(artifact)
        (out / "writer-scene-artifact.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out / "writer-scene.txt").write_text(artifact["prose"], encoding="utf-8")
        evidence["status"] = artifact["status"]
        evidence["writer_artifact_sha256"] = artifact["artifact_sha256"]
    except Exception as exc:
        if isinstance(exc, OpenRouterCallError):
            evidence["api_calls"] = 1
            trace = getattr(exc, "trace", None) or {}
            body = trace.get("body") or {}
            evidence["provider_response"] = {
                key: body[key] for key in ("id", "model", "choices", "usage") if key in body
            }
            if body:
                try:
                    evidence["usage"] = provider_usage(
                        body,
                        "SFR_V1_Q5B_SCENE_WRITER",
                        time.perf_counter() - started,
                    )
                except RuntimeError:
                    pass
            evidence["provider_failure_stage"] = trace.get("stage")
        evidence["status"] = "STOPPED_NO_RETRY"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure_message"] = (
            exc.args[0] if isinstance(exc, RuntimeError) and exc.args else type(exc).__name__
        )

    call_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    import sys
    result = prepare() if "--prepare" in sys.argv else verify()
    print(json.dumps({
        key: result[key]
        for key in (
            "status",
            "model",
            "max_tokens",
            "planned_uncached_cost_usd",
            "proposed_max_cost_usd",
            "max_writer_calls",
            "paid_execution_authorized",
        )
    }, indent=2))
