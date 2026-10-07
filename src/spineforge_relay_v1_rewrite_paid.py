"""Q5R: bounded targeted rewrite for the qualified SFR-v1 SC01 candidate."""
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
from src.spineforge_relay_v1_q5 import build_inputs as build_q5_inputs
from src.spineforge_v19_transport import _request_once
from src.spineforge_v21_model_adapter import provider_usage

MODEL = "aion-labs/aion-3.5-mini"
REQUEST_CLASS = "spineforge_relay_v1_scene_writer"
AUTH_SCOPE = "SFR_V1_Q5R_SC01_TARGETED_REWRITE_ONE_CALL"
PROMPT = Path("prompts/spineforge_relay_v1_scene_rewrite.md")
SOURCE_RESULT = Path("evidence/spineforge-relay/SFR-V1-Q5B-PAID-20261006/result.json")
GUARD_RESULT = Path("evidence/spineforge-relay/SFR-V1-Q5G-PAID-20261007/result.json")
DEFAULT_OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q5R-PREFLIGHT-20261007")
MAX_TOKENS = 5000
TEMPERATURE = 0.62
MAX_COST_USD = 0.02

TextCall = Callable[..., tuple[str, dict[str, Any], dict[str, Any]]]


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def build_rewrite_input() -> tuple[dict[str, Any], dict[str, Any]]:
    q5b = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    q5g = json.loads(GUARD_RESULT.read_text(encoding="utf-8"))
    writer_input, state, _plan, route, contract = build_q5_inputs()
    prose = str((q5b.get("candidate") or {}).get("prose") or "")
    if not prose:
        raise RuntimeError("Q5R source scene missing")
    if q5g.get("status") != "GUARD_QUALIFIED_REWRITE" or not q5g.get("qualification_pass"):
        raise RuntimeError("Q5R requires qualified Q5G REWRITE evidence")

    repair = {
        "schema": "spineforge-relay.scene-rewrite-input.v1",
        "scene_id": contract.scene_id,
        "attempt": 2,
        "story_intent": writer_input["story_intent"],
        "frozen_spine_route": route.model_dump(mode="json"),
        "current_story_state": state.model_dump(mode="json"),
        "scene_contract": contract.model_dump(mode="json"),
        "source_scene": prose,
        "blocking_findings": q5g["blocking_findings"],
        "warnings": q5g.get("warnings", []),
        "rewrite_policy": {
            "targeted_only": True,
            "preserve_required_events": True,
            "no_new_persistent_facts": True,
            "no_later_spine_beats": True,
            "automatic_retry": False,
            "state_application_authorized": False,
        },
    }
    return repair, q5g


def request_payload(rewrite_input: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_openrouter_request(
        MODEL,
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": PROMPT.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": json.dumps(rewrite_input, ensure_ascii=False, separators=(",", ":"))},
            ],
            "temperature": TEMPERATURE,
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
        PROMPT,
        SOURCE_RESULT,
        GUARD_RESULT,
        Path("src/spineforge_relay_v1_q5.py"),
        Path("src/spineforge_relay_v1_contracts.py"),
        Path("src/spineforge_relay_v1_compile.py"),
        Path("configs/model_runtime_profiles.yaml"),
    ]


def prepare(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    profile = require_qualification_runtime_profile(MODEL)
    rewrite_input, q5g = build_rewrite_input()
    request = request_payload(rewrite_input)
    pricing = (profile.get("metadata") or {}).get("pricing_usd_per_million_tokens") or {}
    input_rate = float(pricing.get("input", 0.0))
    output_rate = float(pricing.get("output", 0.0))
    input_bytes = len(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    planned = round(input_bytes * input_rate / 1_000_000 + MAX_TOKENS * output_rate / 1_000_000, 6)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rewrite-input.json").write_text(
        json.dumps(rewrite_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "spineforge-relay.q5r-preflight.v1",
        "status": "OFFLINE_PREPARED_PAID_NOT_AUTHORIZED",
        "qualification_id": "SFR-V1-Q5R-SC01-TARGETED-REWRITE-20261007",
        "model": MODEL,
        "request_class": REQUEST_CLASS,
        "model_runtime_profile": runtime_profile_identity(MODEL),
        "source_result_sha256": _sha_file(SOURCE_RESULT),
        "guard_result_sha256": _sha_file(GUARD_RESULT),
        "guard_preflight_sha256": q5g["preflight_sha256"],
        "rewrite_input_sha256": hashlib.sha256(
            json.dumps(rewrite_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "input_utf8_bytes": input_bytes,
        "pricing_usd_per_million": {"input": input_rate, "output": output_rate},
        "planned_uncached_cost_usd": planned,
        "proposed_max_cost_usd": MAX_COST_USD,
        "max_rewrite_calls": 1,
        "automatic_retry": False,
        "attempt": 2,
        "final_guard_required": True,
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
    rewrite_input_path: Path = DEFAULT_OUTPUT / "rewrite-input.json",
) -> dict[str, Any]:
    report = json.loads(preflight_path.read_text(encoding="utf-8"))
    saved = report.pop("artifact_sha256")
    actual = hashlib.sha256(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if saved != actual:
        raise RuntimeError("Q5R preflight integrity drift")
    report["artifact_sha256"] = saved
    for row in report["files"]:
        if _sha_file(Path(row["path"])) != row["sha256"]:
            raise RuntimeError("Q5R frozen dependency drift: " + row["path"])
    fresh, _ = build_rewrite_input()
    if json.loads(rewrite_input_path.read_text(encoding="utf-8")) != fresh:
        raise RuntimeError("Q5R rewrite input drift")
    if report["request"] != request_payload(fresh):
        raise RuntimeError("Q5R frozen request drift")
    return report


def validate_rewrite(text: str, rewrite_input: dict[str, Any]) -> dict[str, Any]:
    prose = text.strip()
    if not prose or prose.startswith(("{", "[")) or "[[" in prose or "]]" in prose:
        raise RuntimeError("Q5R rewrite violated plain-prose output contract")
    words = _word_count(prose)
    contract = rewrite_input["scene_contract"]
    if not contract["target_words_min"] <= words <= contract["target_words_max"]:
        raise RuntimeError(
            f"Q5R word count outside contract: {words} not in "
            f"[{contract['target_words_min']}, {contract['target_words_max']}]"
        )
    return {
        "schema": "spineforge-relay.q5r-candidate.v1",
        "status": "REWRITE_GENERATED_PENDING_FINAL_GUARD",
        "scene_id": rewrite_input["scene_id"],
        "attempt": 2,
        "prose": prose,
        "prose_sha256": hashlib.sha256(prose.encode()).hexdigest(),
        "word_count": words,
        "rewrite_input_sha256": hashlib.sha256(
            json.dumps(rewrite_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "state_application_authorized": False,
        "final_guard_required": True,
        "publication_ready": False,
    }


def execute_once(
    *,
    api_key: str,
    run_id: str,
    authorization: dict[str, Any],
    preflight_path: Path = DEFAULT_OUTPUT / "preflight.json",
    rewrite_input_path: Path = DEFAULT_OUTPUT / "rewrite-input.json",
    output_root: Path = Path("evidence/spineforge-relay/q5r-runs"),
    call_fn: TextCall | None = None,
) -> dict[str, Any]:
    report = verify(preflight_path, rewrite_input_path)
    if (
        authorization.get("paid_execution_authorized") is not True
        or authorization.get("scope") != AUTH_SCOPE
        or authorization.get("preflight_sha256") != report["artifact_sha256"]
        or authorization.get("max_cost_usd") != MAX_COST_USD
        or authorization.get("max_rewrite_calls") != 1
        or authorization.get("automatic_retry") is not False
        or authorization.get("state_application_authorized") is not False
        or not authorization.get("explicit_user_message")
    ):
        raise RuntimeError("Separate explicit SFR-v1 Q5R paid authorization required")

    output_root.mkdir(parents=True, exist_ok=True)
    claim = output_root / ("authorization-" + hashlib.sha256(
        json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest() + ".claimed")
    claim.open("x").close()
    out = output_root / run_id
    out.mkdir(exist_ok=False)

    rewrite_input = json.loads(rewrite_input_path.read_text(encoding="utf-8"))
    request = report["request"]
    evidence = {
        "schema": "spineforge-relay.q5r-call.v1",
        "status": "STARTED",
        "preflight_sha256": report["artifact_sha256"],
        "authorization": authorization,
        "api_calls": 0,
        "automatic_retry_executed": False,
        "state_application_authorized": False,
        "usage": None,
    }
    path = out / "rewrite-call.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        evidence["provider_response"] = {k: body[k] for k in ("id","model","choices","usage") if k in body}
        evidence["actual_request"] = actual_request
        evidence["usage"] = provider_usage(body, "SFR_V1_Q5R_SCENE_REWRITE", time.perf_counter() - started)
        if actual_request != request:
            raise RuntimeError("Q5R dispatched request differs from frozen preflight")
        finish = (body.get("choices") or [{}])[0].get("finish_reason")
        if finish != "stop":
            raise RuntimeError("Q5R writer incomplete response: " + str(finish))
        if evidence["usage"]["cost_usd"] is None:
            raise RuntimeError("Q5R provider did not report call cost")
        if float(evidence["usage"]["cost_usd"]) > MAX_COST_USD:
            raise RuntimeError("Q5R provider-reported cost exceeds authorized ceiling")
        artifact = validate_rewrite(text, rewrite_input)
        artifact["artifact_sha256"] = hashlib.sha256(
            json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        (out / "rewrite-artifact.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (out / "rewrite-scene.txt").write_text(artifact["prose"], encoding="utf-8")
        evidence["status"] = artifact["status"]
        evidence["rewrite_artifact_sha256"] = artifact["artifact_sha256"]
    except Exception as exc:
        if isinstance(exc, OpenRouterCallError):
            evidence["api_calls"] = 1
            trace = getattr(exc, "trace", None) or {}
            body = trace.get("body") or {}
            evidence["provider_response"] = {k: body[k] for k in ("id","model","choices","usage") if k in body}
            if body:
                try:
                    evidence["usage"] = provider_usage(body, "SFR_V1_Q5R_SCENE_REWRITE", time.perf_counter() - started)
                except RuntimeError:
                    pass
        evidence["status"] = "STOPPED_NO_RETRY"
        evidence["failure_type"] = type(exc).__name__
        evidence["failure_message"] = str(exc)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence
