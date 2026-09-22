from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import requests
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.model_registry import (
    MODEL_RUNTIME_PROFILE_PATH,
    file_sha256,
    model_slug,
    normalize_openrouter_request,
    runtime_profile_identity,
)
from src.saga_blueprint_contract import (
    CharacterNarrativeBlueprint,
    NarrativeArchitectProfile,
    NarrativeFixture,
    fixture_fingerprint,
    load_fixture_manifest,
    load_profile,
    validate_blueprint_payload,
    validate_profile_against_manifest,
)
from src.saga_blueprint_validate import validate_static


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
RUNNER_VERSION = "saga-narrative-architect-runner-v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProviderIdentity(StrictModel):
    provider_runtime: str
    model_id: str | None = None
    model_revision: str | None = None


class ProviderConfig(StrictModel):
    type: Literal["fixture", "openrouter"]
    identity: ProviderIdentity
    fixture_response_path: str | None = None
    model_env: str | None = None


class RequestConfig(StrictModel):
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(ge=512, le=64000)
    timeout_seconds: int = Field(ge=1, le=600)
    max_retries: int = Field(ge=0, le=5)
    seed: int | None
    reasoning: dict[str, Any] | None
    response_format_json_object: bool


class RunnerConfig(StrictModel):
    profile_path: str
    fixture_manifest_path: str
    prompt_path: str
    output_root: str
    provider: ProviderConfig
    request: RequestConfig


class ProviderError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_runner_config(path: Path) -> RunnerConfig:
    return RunnerConfig.model_validate(_load_yaml(path))


def _canonical_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _find_fixture(manifest: Any, fixture_id: str) -> NarrativeFixture:
    for case in manifest.cases:
        if case.case_id == fixture_id:
            return case
    raise ValueError(f"Unknown fixture_id: {fixture_id}")


def build_user_prompt(fixture: NarrativeFixture) -> str:
    return (
        "Create one complete Character Narrative Blueprint for this frozen "
        "Character + World input.\n\n"
        "Do not add commentary outside JSON.\n\n"
        "FROZEN INPUT:\n"
        + json.dumps(
            fixture.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )


def _extract_text_content(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ProviderError("provider response contains no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                text = item["text"].strip()
                if text:
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    raise ProviderError("provider response contains no text content")


def _provider_usage(body: dict[str, Any]) -> dict[str, Any]:
    usage = body.get("usage") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    raw_cost = usage.get("cost")
    usd_cost = float(raw_cost) if raw_cost is not None else None
    rate_raw = os.getenv("USD_TRY_RATE")
    rate = float(rate_raw) if rate_raw else None
    return {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "cost_usd": usd_cost,
        "usd_try_rate": rate,
        "cost_try": usd_cost * rate if usd_cost is not None and rate is not None else None,
    }


def _call_openrouter(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    request: RequestConfig,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    if request.seed is not None:
        payload["seed"] = request.seed
    if request.reasoning is not None:
        payload["reasoning"] = request.reasoning
    if request.response_format_json_object:
        payload["response_format"] = {"type": "json_object"}
    payload = normalize_openrouter_request(
        model,
        payload,
        request_class="structured_large",
        structured_output=True,
    )

    attempts = 0
    last_error: Exception | None = None
    for attempt in range(request.max_retries + 1):
        attempts = attempt + 1
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
                    "X-Title": "LUMI Model Lab Saga Architect",
                },
                json=payload,
                timeout=request.timeout_seconds,
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < request.max_retries:
                    continue
            if not response.ok:
                try:
                    error_body: Any = response.json()
                except ValueError:
                    error_body = response.text[:2000]
                raise ProviderError(
                    f"OpenRouter HTTP {response.status_code} for model {model}: "
                    f"{error_body}"
                )
            try:
                body = response.json()
            except ValueError as exc:
                raise ProviderError("OpenRouter returned non-JSON response") from exc
            return body, payload, attempts
        except (requests.RequestException, ProviderError) as exc:
            last_error = exc
            if attempt >= request.max_retries:
                break
    raise ProviderError(str(last_error or "unknown provider error"))


def _fixture_provider(
    *,
    config: ProviderConfig,
    fixture_id: str,
    model: str,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    if not config.fixture_response_path:
        raise ProviderError("fixture provider requires fixture_response_path")
    raw = json.loads(Path(config.fixture_response_path).read_text(encoding="utf-8"))
    if raw.get("fixture_id") != fixture_id:
        raise ProviderError(
            f"fixture response is for {raw.get('fixture_id')!r}, not {fixture_id!r}"
        )
    if raw.get("model_identity") != model:
        raise ProviderError("fixture response model_identity does not match config")
    blueprint = raw.get("blueprint")
    if not isinstance(blueprint, dict):
        raise ProviderError("fixture response missing blueprint object")
    content = json.dumps(blueprint, ensure_ascii=False)
    body = {
        "id": raw.get("fixture_response_id"),
        "model": model,
        "provider": "local-fixture",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": content},
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
        },
    }
    request_payload = {
        "model": model,
        "fixture_response_path": config.fixture_response_path,
    }
    return body, request_payload, 1


def _resolve_model(
    config: RunnerConfig,
    model_override: str | None,
) -> str:
    if config.provider.type == "fixture":
        if model_override:
            raise ValueError("--model cannot override fixture provider identity")
        if not config.provider.identity.model_id:
            raise ValueError("fixture provider requires identity.model_id")
        return config.provider.identity.model_id

    if model_override:
        return model_override
    model_env = config.provider.model_env or "SAGA_ARCHITECT_MODEL"
    model = os.getenv(model_env)
    if not model:
        raise ValueError(
            f"Missing model name in --model or environment variable {model_env}"
        )
    return model


def build_experiment_fingerprint(
    *,
    config_path: Path,
    config: RunnerConfig,
    profile: NarrativeArchitectProfile,
    fixture: NarrativeFixture,
    model: str,
) -> tuple[str, dict[str, str]]:
    files = {
        "runner_config": config_path,
        "profile": Path(config.profile_path),
        "fixture_manifest": Path(config.fixture_manifest_path),
        "prompt": Path(config.prompt_path),
        "output_schema": Path(profile.output_schema),
    }
    if config.provider.type == "fixture" and config.provider.fixture_response_path:
        files["fixture_response"] = Path(config.provider.fixture_response_path)
    if config.provider.type == "openrouter":
        files["model_runtime_profiles"] = MODEL_RUNTIME_PROFILE_PATH

    hashes = {name: file_sha256(path) for name, path in files.items()}
    semantic_hashes = {
        name: sha
        for name, sha in hashes.items()
        if name != "runner_config"
    }
    identity = {
        "runner_version": RUNNER_VERSION,
        "role_id": profile.role_id,
        "profile_version": profile.profile_version,
        "prompt_contract": profile.prompt_contract,
        "fixture_id": fixture.case_id,
        "fixture_fingerprint": fixture_fingerprint(fixture),
        "provider_type": config.provider.type,
        "provider_runtime": config.provider.identity.provider_runtime,
        "provider_model_revision": config.provider.identity.model_revision,
        "model": model,
        "model_runtime_profile": (
            runtime_profile_identity(model)
            if config.provider.type == "openrouter"
            else None
        ),
        "request": config.request.model_dump(mode="json"),
        "files": semantic_hashes,
    }
    return _canonical_sha(identity), hashes


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _run_directory(
    *,
    output_root: Path,
    model: str,
    fixture_id: str,
    fingerprint: str,
    rerun: bool,
) -> Path:
    base = output_root / model_slug(model) / fixture_id / fingerprint
    if rerun:
        return base.parent / f"{fingerprint}__rerun_{_timestamp_slug()}"
    return base


def run_generation(
    *,
    config_path: Path,
    fixture_id: str,
    model_override: str | None = None,
    rerun: bool = False,
) -> dict[str, Any]:
    config = load_runner_config(config_path)
    profile = load_profile(Path(config.profile_path))
    fixture_manifest = load_fixture_manifest(Path(config.fixture_manifest_path))
    validate_profile_against_manifest(profile, fixture_manifest)
    fixture = _find_fixture(fixture_manifest, fixture_id)
    model = _resolve_model(config, model_override)

    fingerprint, file_hashes = build_experiment_fingerprint(
        config_path=config_path,
        config=config,
        profile=profile,
        fixture=fixture,
        model=model,
    )
    run_dir = _run_directory(
        output_root=Path(config.output_root),
        model=model,
        fixture_id=fixture_id,
        fingerprint=fingerprint,
        rerun=rerun,
    )
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists() and not rerun:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "status": "ALREADY_EXISTS",
            "fingerprint": fingerprint,
            "run_dir": str(run_dir),
            "existing_status": existing.get("status"),
        }

    run_dir.mkdir(parents=True, exist_ok=False)
    system_prompt = Path(config.prompt_path).read_text(encoding="utf-8").strip()
    user_prompt = build_user_prompt(fixture)
    fixture_payload = fixture.model_dump(mode="json")
    _write_json(run_dir / "input_fixture.json", fixture_payload)
    (run_dir / "system_prompt.txt").write_text(system_prompt + "\n", encoding="utf-8")
    (run_dir / "user_prompt.txt").write_text(user_prompt + "\n", encoding="utf-8")

    request_evidence = {
        "provider_type": config.provider.type,
        "provider_runtime": config.provider.identity.provider_runtime,
        "model": model,
        "model_revision": config.provider.identity.model_revision,
        "model_runtime_profile": (
            runtime_profile_identity(model)
            if config.provider.type == "openrouter"
            else None
        ),
        "request": config.request.model_dump(mode="json"),
    }
    _write_json(run_dir / "request_config.json", request_evidence)

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "runner_version": RUNNER_VERSION,
        "status": "started",
        "started_at": _now_iso(),
        "finished_at": None,
        "fingerprint": fingerprint,
        "file_hashes": file_hashes,
        "role_id": profile.role_id,
        "profile_version": profile.profile_version,
        "prompt_contract": profile.prompt_contract,
        "fixture_id": fixture_id,
        "fixture_fingerprint": fixture_fingerprint(fixture),
        "provider_type": config.provider.type,
        "provider_runtime": config.provider.identity.provider_runtime,
        "model": model,
        "model_revision": config.provider.identity.model_revision,
        "model_runtime_profile": (
            runtime_profile_identity(model)
            if config.provider.type == "openrouter"
            else None
        ),
        "attempts": 0,
        "latency_ms": None,
        "usage": {},
        "response_meta": {},
        "validation": {"status": "not_run", "errors": []},
        "run_dir": str(run_dir),
    }
    _write_json(manifest_path, manifest)

    started = time.perf_counter()
    try:
        if config.provider.type == "fixture":
            body, provider_request, attempts = _fixture_provider(
                config=config.provider,
                fixture_id=fixture_id,
                model=model,
            )
        else:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ProviderError("Missing OPENROUTER_API_KEY")
            body, provider_request, attempts = _call_openrouter(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                request=config.request,
            )
    except Exception as exc:
        manifest["status"] = "provider_error"
        manifest["finished_at"] = _now_iso()
        manifest["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        manifest["provider_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        _write_json(manifest_path, manifest)
        return manifest

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    manifest["attempts"] = attempts
    manifest["latency_ms"] = latency_ms
    manifest["usage"] = _provider_usage(body)
    choices = body.get("choices") or [{}]
    finish_reason = choices[0].get("finish_reason")
    manifest["response_meta"] = {
        "id": body.get("id"),
        "model": body.get("model"),
        "provider": body.get("provider"),
        "finish_reason": finish_reason,
    }
    _write_json(run_dir / "provider_request.json", provider_request)
    _write_json(run_dir / "raw_response.json", body)

    if finish_reason not in (None, "stop"):
        manifest["status"] = "generation_incomplete"
        manifest["finished_at"] = _now_iso()
        manifest["validation"] = {
            "status": "generation_incomplete",
            "errors": [
                {
                    "type": "finish_reason",
                    "message": f"unexpected finish_reason: {finish_reason!r}",
                }
            ],
        }
        _write_json(run_dir / "validation.json", manifest["validation"])
        _write_json(manifest_path, manifest)
        return manifest

    try:
        content = _extract_text_content(body)
    except Exception as exc:
        manifest["status"] = "provider_error"
        manifest["finished_at"] = _now_iso()
        manifest["provider_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        _write_json(manifest_path, manifest)
        return manifest

    (run_dir / "raw_content.txt").write_text(content + "\n", encoding="utf-8")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        manifest["status"] = "parse_failed"
        manifest["finished_at"] = _now_iso()
        manifest["validation"] = {
            "status": "parse_failed",
            "errors": [
                {
                    "type": "JSONDecodeError",
                    "message": str(exc),
                }
            ],
        }
        _write_json(manifest_path, manifest)
        return manifest

    _write_json(run_dir / "parsed_blueprint.json", parsed)

    try:
        validated = validate_blueprint_payload(parsed)
    except ValidationError as exc:
        manifest["status"] = "validation_failed"
        manifest["finished_at"] = _now_iso()
        manifest["validation"] = {
            "status": "validation_failed",
            "errors": exc.errors(include_input=False),
        }
        _write_json(run_dir / "validation.json", manifest["validation"])
        _write_json(manifest_path, manifest)
        return manifest

    normalized = validated.model_dump(mode="json", by_alias=True)
    _write_json(run_dir / "validated_blueprint.json", normalized)
    manifest["validation"] = {
        "status": "pass",
        "errors": [],
        "schema": "character-narrative-blueprint.v1",
    }
    _write_json(run_dir / "validation.json", manifest["validation"])

    static_validation = validate_static(normalized)
    manifest["static_validation"] = static_validation
    _write_json(run_dir / "static_validation.json", static_validation)
    if static_validation["status"] == "FAIL":
        manifest["status"] = "static_validation_failed"
        manifest["finished_at"] = _now_iso()
        _write_json(manifest_path, manifest)
        return manifest

    manifest["status"] = "complete"
    manifest["finished_at"] = _now_iso()
    _write_json(manifest_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the lab-only LUMI Narrative Architect generator."
    )
    parser.add_argument(
        "--config",
        default="configs/saga_lab/narrative_architect_fixture_v1.yaml",
    )
    parser.add_argument("--fixture-id", required=True)
    parser.add_argument("--model")
    parser.add_argument("--rerun", action="store_true")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    result = run_generation(
        config_path=Path(args.config),
        fixture_id=args.fixture_id,
        model_override=args.model,
        rerun=args.rerun,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") in {
        "provider_error",
        "generation_incomplete",
        "parse_failed",
        "validation_failed",
        "static_validation_failed",
    }:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
