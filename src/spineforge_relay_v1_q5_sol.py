"""Q5S: fresh single-scene writer qualification using GPT-5.6 Sol.

This is a NEW qualification run, not a second rewrite of the rejected Aion run.
The frozen StoryState, ScenePlan, FrozenSpineRoute and SceneContract remain unchanged.
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
from src.spineforge_relay_v1_q5 import build_inputs as build_frozen_q5_inputs
from src.spineforge_v19_transport import _request_once
from src.spineforge_v21_model_adapter import provider_usage

MODEL = "openai/gpt-5.6-sol"
REQUEST_CLASS = "spineforge_relay_v1_scene_writer"
AUTH_SCOPE = "SFR_V1_Q5S_SOL_SC01_ONE_CALL"
PROMPT = Path("prompts/spineforge_relay_v1_scene_writer.md")
DEFAULT_OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q5S-PREFLIGHT-20261007")
MAX_TOKENS = 3500
MAX_COST_USD = 0.05

TextCall = Callable[..., tuple[str, dict[str, Any], dict[str, Any]]]


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def build_inputs():
    writer_input, state, plan, route, contract = build_frozen_q5_inputs()
    return writer_input, state, plan, route, contract


def request_payload(writer_input: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_openrouter_request(
        MODEL,
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PROMPT.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": json.dumps(writer_input, ensure_ascii=False, separators=(",", ":"))},
            ],
            "temperature": 0.7,
            "max_tokens": MAX_TOKENS,
        },
        request_class=REQUEST_CLASS,
        structured_output=False,
    )
    payload["response_format"] = {"type": "text"}
    return payload


def dependencies() -> list[Path]:
    return [
        Path(__file__).relative_to(Path.cwd()),
        Path("src/spineforge_relay_v1_q5.py"),
        Path("src/spineforge_relay_v1_contracts.py"),
        Path("src/spineforge_relay_v1_compile.py"),
        Path("configs/model_runtime_profiles.yaml"),
        PROMPT,
        Path("tests/fixtures/spineforge_relay_v1/q5_lighthouse_scene01.json"),
        Path("docs/experiments/lighthouse-context-and-spine-draft.md"),
    ]


def prepare(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    profile = require_qualification_runtime_profile(MODEL)
    writer_input, state, plan, route, contract = build_inputs()
    request = request_payload(writer_input)
    pricing = (profile.get("metadata") or {}).get("pricing_usd_per_million_tokens") or {}
    input_rate = float(pricing.get("input", 0.0))
    output_rate = float(pricing.get("output", 0.0))
    input_bytes = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    planned = round(
        input_bytes * input_rate / 1_000_000
        + MAX_TOKENS * output_rate / 1_000_000,
        6,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "writer-input.json").write_text(
        json.dumps(writer_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "spineforge-relay.q5s-preflight.v1",
        "status": "OFFLINE_PREPARED_PAID_NOT_AUTHORIZED",
        "qualification_id": "SFR-V1-Q5S-SOL-SC01-20261007",
        "parent_architecture": "SFR-v1",
        "supersedes_aion_writer": False,
        "new_run_reason": "Aion writer/rewrite showed nondeterministic hidden-reasoning budget exhaustion; test a stable writer boundary without changing frozen story inputs.",
        "model": MODEL,
        "request_class": REQUEST_CLASS,
        "model_runtime_profile": runtime_profile_identity(MODEL),
        "story_state_sha256": hashlib.sha256(
            json.dumps(state.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "scene_plan_sha256": hashlib.sha256(
            json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "frozen_spine_route_sha256": hashlib.sha256(
            json.dumps(route.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "scene_contract_sha256": hashlib.sha256(
            json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "writer_input_sha256": hashlib.sha256(
            json.dumps(writer_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "input_utf8_bytes": input_bytes,
        "pricing_usd_per_million": {"input": input_rate, "output": output_rate},
        "max_tokens": MAX_TOKENS,
        "planned_uncached_cost_usd": planned,
        "proposed_max_cost_usd": MAX_COST_USD,
        "max_writer_calls": 1,
        "automatic_retry": False,
        "semantic_guard_required": True,
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
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def verify(
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    writer_input_path: Path = DEFAULT_OUTPUT / "writer-input.json",
) -> dict[str, Any]:
    report = json.loads(preflight_path.read_text(encoding="utf-8"))
    saved = report.pop("artifact_sha256")
    actual = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if saved != actual:
        raise RuntimeError("Q5S preflight integrity drift")
    report["artifact_sha256"] = saved
    for row in report["files"]:
        if _sha_file(Path(row["path"])) != row["sha256"]:
            raise RuntimeError("Q5S frozen dependency drift: " + row["path"])
    writer_input, *_ = build_inputs()
    if json.loads(writer_input_path.read_text(encoding="utf-8")) != writer_input:
        raise RuntimeError("Q5S writer input drift")
    if report["request"] != request_payload(writer_input):
        raise RuntimeError("Q5S frozen request drift")
    return report


def validate_candidate(text: str, writer_input: dict[str, Any]) -> dict[str, Any]:
    prose = text.strip()
    if not prose or prose.startswith(("{", "[")) or "[[" in prose or "]]" in prose:
        raise RuntimeError("Q5S writer violated plain-prose output contract")
    words = _word_count(prose)
    contract = writer_input["scene_contract"]
    if not contract["target_words_min"] <= words <= contract["target_words_max"]:
        raise RuntimeError(
            f"Q5S word count outside contract: {words} not in "
            f"[{contract['target_words_min']}, {contract['target_words_max']}]"
        )
    return {
        "schema": "spineforge-relay.q5s-candidate.v1",
        "status": "WRITER_GENERATED_PENDING_SCENE_GUARD",
        "scene_id": contract["scene_id"],
        "attempt": 1,
        "prose": prose,
        "prose_sha256": hashlib.sha256(prose.encode()).hexdigest(),
        "word_count": words,
        "writer_input_sha256": hashlib.sha256(
            json.dumps(writer_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "semantic_guard_required": True,
        "state_application_authorized": False,
        "publication_ready": False,
    }


def execute_once(
    *,
    api_key: str,
    run_id: str,
    authorization: dict[str, Any],
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    writer_input_path: Path = DEFAULT_OUTPUT / "writer-input.json",
    output_root: Path = Path("evidence/spineforge-relay/q5s-runs"),
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
        or authorization.get("state_application_authorized") is not False
        or not authorization.get("explicit_user_message")
    ):
        raise RuntimeError("Separate explicit SFR-v1 Q5S paid authorization required")

    output_root.mkdir(parents=True, exist_ok=True)
    claim = output_root / ("authorization-" + hashlib.sha256(
        json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest() + ".claimed")
    claim.open("x").close()
    out = output_root / run_id
    out.mkdir(exist_ok=False)

    writer_input = json.loads(writer_input_path.read_text(encoding="utf-8"))
    request = report["request"]
    evidence = {
        "schema": "spineforge-relay.q5s-call.v1",
        "status": "STARTED",
        "preflight_sha256": report["artifact_sha256"],
        "authorization": authorization,
        "api_calls": 0,
        "automatic_retry_executed": False,
        "state_application_authorized": False,
        "usage": None,
    }
    path = out / "writer-call.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    started = time.perf_counter()
    try:
        text, body, actual_request = (call_fn or _request_once)(
            api_key=api_key,
            model=MODEL,
            system_prompt=request["messages"][0]["content"],
            user_prompt=request["messages"][1]["content"],
            temperature=0.7,
            max_tokens=MAX_TOKENS,
            seed=None,
            request_class=REQUEST_CLASS,
            response_format={"type": "text"},
            require_parameters=True,
        )
        evidence["api_calls"] = 1
        evidence["raw_response"] = text
        evidence["provider_response"] = {k: body[k] for k in ("id","model","choices","usage") if k in body}
        evidence["actual_request"] = actual_request
        evidence["usage"] = provider_usage(body, "SFR_V1_Q5S_SOL_SCENE_WRITER", time.perf_counter() - started)
        if actual_request != request:
            raise RuntimeError("Q5S dispatched request differs from frozen preflight")
        finish = (body.get("choices") or [{}])[0].get("finish_reason")
        if finish != "stop":
            raise RuntimeError("Q5S writer incomplete response: " + str(finish))
        if evidence["usage"]["cost_usd"] is None:
            raise RuntimeError("Q5S provider did not report call cost")
        if float(evidence["usage"]["cost_usd"]) > MAX_COST_USD:
            raise RuntimeError("Q5S provider-reported cost exceeds authorized ceiling")
        artifact = validate_candidate(text, writer_input)
        artifact["artifact_sha256"] = hashlib.sha256(
            json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        (out / "writer-artifact.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (out / "writer-scene.txt").write_text(artifact["prose"], encoding="utf-8")
        evidence["status"] = artifact["status"]
        evidence["writer_artifact_sha256"] = artifact["artifact_sha256"]
    except Exception as exc:
        if isinstance(exc, OpenRouterCallError):
            evidence["api_calls"] = 1
            trace = getattr(exc, "trace", None) or {}
            body = trace.get("body") or {}
            evidence["provider_response"] = {k: body[k] for k in ("id","model","choices","usage") if k in body}
            if body:
                try:
                    evidence["usage"] = provider_usage(body, "SFR_V1_Q5S_SOL_SCENE_WRITER", time.perf_counter() - started)
                except RuntimeError:
                    pass
        evidence["status"] = "STOPPED_NO_RETRY"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure_message"] = str(exc)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence
