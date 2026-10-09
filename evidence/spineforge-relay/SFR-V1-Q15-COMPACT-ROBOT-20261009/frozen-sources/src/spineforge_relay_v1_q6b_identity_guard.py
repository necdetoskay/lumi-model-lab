"""Q6B identity-canon semantic guard qualification.

Uses the rejected Q6A SC03 prose as a fixed adversarial fixture. This probe must
catch the two masculine references to canonically she/her Duru before Q6B may
generate any new scenes.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from src.model_registry import (
    normalize_openrouter_request,
    require_qualification_runtime_profile,
    runtime_profile_identity,
)
from src.spineforge_relay_v1_guard import normalize_semantic_guard
from src.spineforge_relay_v1_q5t import StructuredGuardV1
from src.spineforge_relay_v1_q6 import build_chain
from src.spineforge_v19_transport import call_strict_json_once
from src.spineforge_v21_model_adapter import provider_usage

MODEL = "anthropic/claude-sonnet-5.5"
REQUEST_CLASS = "spineforge_relay_v1_q5t_guard"
PROMPT = Path("prompts/spineforge_relay_v1_q6b_guard.md")
FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q6b_identity_probe.json")
DEFAULT_OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q6B-ID-GUARD-PREFLIGHT-20261007")
AUTH_SCOPE = "SFR_V1_Q6B_IDENTITY_GUARD_ONE_CALL"
MAX_TOKENS = 5000
MAX_COST_USD = 0.08

GuardCall = Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_input():
    probe = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _fixture, intent, route, _start, rows, _final = build_chain()
    _plan, sc03_contract, sc03_state = rows[1]
    payload = {
        "schema": "spineforge-relay.q6b-identity-guard-input.v1",
        "story_intent": intent,
        "story_state": sc03_state.model_dump(mode="json"),
        "frozen_spine_route": route.model_dump(mode="json"),
        "scene_contract": sc03_contract.model_dump(mode="json"),
        "relevant_character_canon": probe["relevant_character_canon"],
        "candidate_prose": probe["candidate_prose"],
        "deterministic_findings": [],
    }
    return payload, probe


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


def request_payload(payload):
    schema = _strict_schema()
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "q6b_identity_guard",
            "strict": True,
            "schema": schema,
        },
    }
    req = normalize_openrouter_request(
        MODEL,
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PROMPT.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
            ],
            "temperature": 0.0,
            "max_tokens": MAX_TOKENS,
        },
        request_class=REQUEST_CLASS,
        structured_output=False,
    )
    req["response_format"] = response_format
    req["provider"] = {**req.get("provider", {}), "require_parameters": True}
    return req


def dependencies():
    return [
        Path(__file__).relative_to(Path.cwd()),
        PROMPT,
        FIXTURE,
        Path("src/spineforge_relay_v1_q6.py"),
        Path("src/spineforge_relay_v1_q5t.py"),
        Path("src/spineforge_relay_v1_guard.py"),
        Path("configs/model_runtime_profiles.yaml"),
    ]


def prepare(output_dir: Path = DEFAULT_OUTPUT):
    profile = require_qualification_runtime_profile(MODEL)
    payload, probe = build_input()
    request = request_payload(payload)
    pricing = (profile.get("metadata") or {}).get("pricing_usd_per_million_tokens") or {}
    input_bytes = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    planned = round(
        input_bytes * float(pricing.get("input", 0.0)) / 1_000_000
        + MAX_TOKENS * float(pricing.get("output", 0.0)) / 1_000_000,
        6,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "guard-input.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "spineforge-relay.q6b-identity-guard-preflight.v1",
        "status": "OFFLINE_PREPARED_PAID_NOT_AUTHORIZED",
        "qualification_id": "SFR-V1-Q6B-IDENTITY-GUARD-20261007",
        "model": MODEL,
        "request_class": REQUEST_CLASS,
        "model_runtime_profile": runtime_profile_identity(MODEL),
        "expected_blocking_anchors": probe["expected_blocking_anchors"],
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "planned_uncached_cost_usd": planned,
        "proposed_max_cost_usd": MAX_COST_USD,
        "max_guard_calls": 1,
        "automatic_retry": False,
        "state_application_authorized": False,
        "paid_execution_authorized": False,
        "files": [{"path": str(p), "sha256": _sha(p)} for p in dependencies()],
    }
    payload_hash = dict(report)
    report["artifact_sha256"] = hashlib.sha256(
        json.dumps(payload_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (output_dir / "preflight.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def verify(
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    input_path: Path = DEFAULT_OUTPUT / "guard-input.json",
):
    report = json.loads(preflight_path.read_text(encoding="utf-8"))
    saved = report.pop("artifact_sha256")
    actual = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if saved != actual:
        raise RuntimeError("Q6B identity preflight drift")
    report["artifact_sha256"] = saved
    for row in report["files"]:
        if _sha(Path(row["path"])) != row["sha256"]:
            raise RuntimeError("Q6B identity dependency drift: " + row["path"])
    fresh, _ = build_input()
    if json.loads(input_path.read_text(encoding="utf-8")) != fresh:
        raise RuntimeError("Q6B identity input drift")
    if report["request"] != request_payload(fresh):
        raise RuntimeError("Q6B identity request drift")
    return report


def qualify(raw: dict[str, Any], prose: str, anchors: list[str]):
    parsed = StructuredGuardV1.model_validate(raw)
    residual = normalize_semantic_guard(
        raw=parsed.residual.model_dump(mode="json"),
        prose=prose,
    )
    blocking = [x for x in residual.findings if x.severity == "BLOCKING"]
    matches = [
        {
            "anchor": anchor,
            "matched": any(anchor in finding.exact_text for finding in blocking),
        }
        for anchor in anchors
    ]
    passed = residual.decision == "REWRITE" and all(x["matched"] for x in matches)
    return {
        "qualification_pass": passed,
        "decision": residual.decision,
        "blocking_count": len(blocking),
        "targets": matches,
        "residual": residual.model_dump(mode="json"),
    }


def execute_once(
    *,
    api_key: str,
    run_id: str,
    authorization: dict[str, Any],
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    input_path: Path = DEFAULT_OUTPUT / "guard-input.json",
    output_root: Path = Path("evidence/spineforge-relay/q6b-id-runs"),
    call_fn: GuardCall | None = None,
):
    preflight = verify(preflight_path, input_path)
    if not (
        authorization.get("paid_execution_authorized") is True
        and authorization.get("scope") == AUTH_SCOPE
        and authorization.get("preflight_sha256") == preflight["artifact_sha256"]
        and authorization.get("max_cost_usd") == MAX_COST_USD
        and authorization.get("max_guard_calls") == 1
        and authorization.get("automatic_retry") is False
        and authorization.get("state_application_authorized") is False
        and authorization.get("explicit_user_message")
    ):
        raise RuntimeError("Separate explicit Q6B identity guard authorization required")

    output_root.mkdir(parents=True, exist_ok=True)
    claim = output_root / (
        "authorization-"
        + hashlib.sha256(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        + ".claimed"
    )
    claim.open("x").close()
    out = output_root / run_id
    out.mkdir(exist_ok=False)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    request = preflight["request"]
    evidence = {
        "status": "STARTED",
        "api_calls": 0,
        "automatic_retry_executed": False,
        "state_application_authorized": False,
        "usage": None,
    }
    started = time.perf_counter()
    try:
        raw, body, actual, _ = (call_fn or call_strict_json_once)(
            api_key=api_key,
            model=MODEL,
            system_prompt=request["messages"][0]["content"],
            user_prompt=request["messages"][1]["content"],
            temperature=0.0,
            max_tokens=MAX_TOKENS,
            seed=None,
            request_class=REQUEST_CLASS,
            schema_name="q6b_identity_guard",
            schema=_strict_schema(),
        )
        evidence["api_calls"] = 1
        evidence["usage"] = provider_usage(
            body,
            "SFR_V1_Q6B_IDENTITY_GUARD",
            time.perf_counter() - started,
        )
        if actual != request:
            raise RuntimeError("Q6B identity dispatched request drift")
        if evidence["usage"]["cost_usd"] is None or float(evidence["usage"]["cost_usd"]) > MAX_COST_USD:
            raise RuntimeError("Q6B identity cost missing or over ceiling")
        result = qualify(
            raw,
            payload["candidate_prose"],
            preflight["expected_blocking_anchors"],
        )
        (out / "guard-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        evidence["qualification_pass"] = result["qualification_pass"]
        evidence["status"] = (
            "IDENTITY_GUARD_QUALIFIED"
            if result["qualification_pass"]
            else "IDENTITY_GUARD_FAILED"
        )
    except Exception as exc:
        evidence["status"] = "STOPPED_NO_RETRY"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure_message"] = str(exc)
    (out / "guard-call.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return evidence
