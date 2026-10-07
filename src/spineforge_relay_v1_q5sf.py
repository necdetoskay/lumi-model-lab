"""Q5SF: final semantic guard for the one allowed SC01 rewrite."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from src.generate import OpenRouterCallError
from src.model_registry import normalize_openrouter_request, require_qualification_runtime_profile, runtime_profile_identity
from src.spineforge_relay_v1_guard import (
    SEMANTIC_GUARD_RESPONSE_SCHEMA,
    build_semantic_guard_input,
    combine_scene_validation,
    deterministic_scene_findings,
    normalize_semantic_guard,
)
from src.spineforge_relay_v1_q5 import build_inputs as build_q5_inputs
from src.spineforge_v19_transport import call_strict_json_once
from src.spineforge_v21_model_adapter import provider_usage
from src.spineforge_v6_json_schema import build_json_schema_response_format

MODEL = "anthropic/claude-sonnet-5.5"
REQUEST_CLASS = "spineforge_relay_v1_scene_guard"
AUTH_SCOPE = "SFR_V1_Q5SF_SC01_FINAL_GUARD_ONE_CALL"
SCHEMA_NAME = "spineforge_relay_scene_guard_v1"
PROMPT = Path("prompts/spineforge_relay_v1_scene_guard.md")
SOURCE_RESULT = Path("evidence/spineforge-relay/SFR-V1-Q5SR-PAID-20261007/result.json")
DEFAULT_OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q5SF-PREFLIGHT-20261007")
MAX_TOKENS = 2500
MAX_COST_USD = 0.05

GuardCall = Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]]


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_inputs():
    source = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    candidate = source.get("candidate") or {}
    if candidate.get("attempt") != 2:
        raise RuntimeError("Q5SF requires attempt-2 rewrite candidate")
    prose = str(candidate.get("prose") or "")
    if not prose:
        raise RuntimeError("Q5SF source prose missing")
    _writer_input, state, _plan, _route, contract = build_q5_inputs()
    deterministic = deterministic_scene_findings(prose=prose, contract=contract)
    guard_input = build_semantic_guard_input(
        state=state,
        contract=contract,
        prose=prose,
        deterministic_findings=deterministic,
    )
    return guard_input, state, contract, prose, deterministic


def request_payload(guard_input: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_openrouter_request(
        MODEL,
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PROMPT.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": json.dumps(guard_input, ensure_ascii=False, separators=(",", ":"))},
            ],
            "temperature": 0.0,
            "max_tokens": MAX_TOKENS,
        },
        request_class=REQUEST_CLASS,
        structured_output=False,
    )
    payload["response_format"] = build_json_schema_response_format(
        name=SCHEMA_NAME,
        schema=SEMANTIC_GUARD_RESPONSE_SCHEMA,
    )
    provider = dict(payload.get("provider") or {})
    provider["require_parameters"] = True
    payload["provider"] = provider
    return payload


def dependencies() -> list[Path]:
    return [
        Path(__file__).relative_to(Path.cwd()),
        Path("src/spineforge_relay_v1_guard.py"),
        Path("src/spineforge_relay_v1_q5.py"),
        Path("configs/model_runtime_profiles.yaml"),
        PROMPT,
        SOURCE_RESULT,
    ]


def prepare(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    profile = require_qualification_runtime_profile(MODEL)
    guard_input, state, contract, prose, deterministic = build_inputs()
    request = request_payload(guard_input)
    pricing = (profile.get("metadata") or {}).get("pricing_usd_per_million_tokens") or {}
    input_rate = float(pricing.get("input", 0.0))
    output_rate = float(pricing.get("output", 0.0))
    input_bytes = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    planned = round(input_bytes * input_rate / 1_000_000 + MAX_TOKENS * output_rate / 1_000_000, 6)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "guard-input.json").write_text(
        json.dumps(guard_input, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "schema": "spineforge-relay.q5sf-preflight.v1",
        "status": "OFFLINE_PREPARED_PAID_NOT_AUTHORIZED",
        "qualification_id": "SFR-V1-Q5SF-SC01-FINAL-GUARD-20261007",
        "model": MODEL,
        "request_class": REQUEST_CLASS,
        "model_runtime_profile": runtime_profile_identity(MODEL),
        "source_result_sha256": _sha_file(SOURCE_RESULT),
        "story_state_sha256": hashlib.sha256(
            json.dumps(state.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "scene_contract_sha256": hashlib.sha256(
            json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "candidate_prose_sha256": hashlib.sha256(prose.encode("utf-8")).hexdigest(),
        "deterministic_finding_count": len(deterministic),
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "input_utf8_bytes": input_bytes,
        "pricing_usd_per_million": {"input": input_rate, "output": output_rate},
        "planned_uncached_cost_usd": planned,
        "proposed_max_cost_usd": MAX_COST_USD,
        "max_guard_calls": 1,
        "automatic_retry": False,
        "attempt": 2,
        "rewrite_authorized": False,
        "state_application_authorized": False,
        "paid_execution_authorized": False,
        "files": [{"path": str(p), "sha256": _sha_file(p)} for p in dependencies()],
    }
    payload = dict(report)
    report["artifact_sha256"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (output_dir / "preflight.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def verify(
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    guard_input_path: Path = DEFAULT_OUTPUT / "guard-input.json",
) -> dict[str, Any]:
    report = json.loads(preflight_path.read_text(encoding="utf-8"))
    saved = report.pop("artifact_sha256")
    actual = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if saved != actual:
        raise RuntimeError("Q5SF preflight integrity drift")
    report["artifact_sha256"] = saved
    for row in report["files"]:
        if _sha_file(Path(row["path"])) != row["sha256"]:
            raise RuntimeError("Q5SF frozen dependency drift: " + row["path"])
    guard_input, *_ = build_inputs()
    if json.loads(guard_input_path.read_text(encoding="utf-8")) != guard_input:
        raise RuntimeError("Q5SF guard input drift")
    if report["request"] != request_payload(guard_input):
        raise RuntimeError("Q5SF frozen request drift")
    return report


def decide(raw: dict[str, Any], prose: str, deterministic: list[Any], scene_id: str) -> dict[str, Any]:
    semantic = normalize_semantic_guard(raw=raw, prose=prose)
    validation = combine_scene_validation(
        scene_id=scene_id,
        attempt=2,
        deterministic=deterministic,
        semantic=semantic,
    )
    return {
        "schema": "spineforge-relay.q5sf-decision.v1",
        "decision": validation.decision,
        "scene_validation": validation.model_dump(mode="json"),
        "semantic_report": semantic.model_dump(mode="json"),
        "state_application_authorized": validation.decision == "ACCEPT",
        "publication_ready": validation.decision == "ACCEPT",
    }


def execute_once(
    *,
    api_key: str,
    run_id: str,
    authorization: dict[str, Any],
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    guard_input_path: Path = DEFAULT_OUTPUT / "guard-input.json",
    output_root: Path = Path("evidence/spineforge-relay/q5sf-runs"),
    call_fn: GuardCall | None = None,
) -> dict[str, Any]:
    preflight = verify(preflight_path, guard_input_path)
    if (
        authorization.get("paid_execution_authorized") is not True
        or authorization.get("scope") != AUTH_SCOPE
        or authorization.get("preflight_sha256") != preflight["artifact_sha256"]
        or authorization.get("max_cost_usd") != MAX_COST_USD
        or authorization.get("max_guard_calls") != 1
        or authorization.get("automatic_retry") is not False
        or authorization.get("rewrite_authorized") is not False
        or not authorization.get("explicit_user_message")
    ):
        raise RuntimeError("Separate explicit SFR-v1 Q5SF authorization required")

    output_root.mkdir(parents=True, exist_ok=True)
    claim = output_root / ("authorization-" + hashlib.sha256(
        json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest() + ".claimed")
    claim.open("x").close()
    out = output_root / run_id
    out.mkdir(exist_ok=False)

    guard_input, _state, contract, prose, deterministic = build_inputs()
    request = preflight["request"]
    evidence = {
        "schema": "spineforge-relay.q5sf-call.v1",
        "status": "STARTED",
        "preflight_sha256": preflight["artifact_sha256"],
        "authorization": authorization,
        "api_calls": 0,
        "automatic_retry_executed": False,
        "usage": None,
    }
    path = out / "guard-call.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    started = time.perf_counter()
    try:
        raw, body, actual_request, _ = (call_fn or call_strict_json_once)(
            api_key=api_key,
            model=MODEL,
            system_prompt=request["messages"][0]["content"],
            user_prompt=request["messages"][1]["content"],
            temperature=0.0,
            max_tokens=MAX_TOKENS,
            seed=None,
            request_class=REQUEST_CLASS,
            schema_name=SCHEMA_NAME,
            schema=SEMANTIC_GUARD_RESPONSE_SCHEMA,
        )
        evidence["api_calls"] = 1
        evidence["provider_response"] = {k: body[k] for k in ("id","model","choices","usage") if k in body}
        evidence["actual_request"] = actual_request
        evidence["usage"] = provider_usage(body, "SFR_V1_Q5SF_FINAL_GUARD", time.perf_counter() - started)
        if actual_request != request:
            raise RuntimeError("Q5SF dispatched request differs from frozen preflight")
        if evidence["usage"]["cost_usd"] is None:
            raise RuntimeError("Q5SF provider did not report call cost")
        if float(evidence["usage"]["cost_usd"]) > MAX_COST_USD:
            raise RuntimeError("Q5SF provider-reported cost exceeds authorized ceiling")

        decision = decide(raw, prose, deterministic, contract.scene_id)
        decision["artifact_sha256"] = hashlib.sha256(
            json.dumps(decision, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        (out / "final-guard-decision.json").write_text(
            json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        evidence["status"] = "FINAL_GUARD_" + decision["decision"]
        evidence["decision"] = decision["decision"]
        evidence["state_application_authorized"] = decision["state_application_authorized"]
        evidence["guard_decision_sha256"] = decision["artifact_sha256"]
    except Exception as exc:
        if isinstance(exc, OpenRouterCallError):
            evidence["api_calls"] = 1
            trace = getattr(exc, "trace", None) or {}
            body = trace.get("body") or {}
            evidence["provider_response"] = {k: body[k] for k in ("id","model","choices","usage") if k in body}
            if body:
                try:
                    evidence["usage"] = provider_usage(body, "SFR_V1_Q5SF_FINAL_GUARD", time.perf_counter() - started)
                except RuntimeError:
                    pass
        evidence["status"] = "STOPPED_NO_RETRY"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure_message"] = str(exc)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence
