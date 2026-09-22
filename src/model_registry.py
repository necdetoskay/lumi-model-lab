from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def model_slug(model: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "__", model.strip())
    return value.strip("_.-") or "model"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MODEL_RUNTIME_PROFILE_PATH = Path("configs/model_runtime_profiles.yaml")


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_runtime_profile_registry(
    path: Path = MODEL_RUNTIME_PROFILE_PATH,
) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Model runtime profile registry does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "model-runtime-profile.v1":
        raise RuntimeError(
            f"Unsupported model runtime profile schema: {payload.get('schema_version')!r}"
        )
    if not isinstance(payload.get("generic"), dict):
        raise RuntimeError("Model runtime profile registry requires generic profile")
    return payload


def resolve_model_runtime_profile(
    model: str,
    path: Path = MODEL_RUNTIME_PROFILE_PATH,
) -> dict[str, Any]:
    registry = load_runtime_profile_registry(path)
    generic = dict(registry["generic"])

    exact = next(
        (
            entry
            for entry in registry.get("profiles") or []
            if entry.get("model_id") == model
        ),
        None,
    )
    if exact is not None:
        resolved = _deep_merge(generic, exact)
        resolved["match"] = {"type": "exact", "value": model}
    else:
        families = sorted(
            registry.get("families") or [],
            key=lambda entry: len(str(entry.get("prefix") or "")),
            reverse=True,
        )
        family = next(
            (
                entry
                for entry in families
                if str(entry.get("prefix") or "")
                and model.startswith(str(entry["prefix"]))
            ),
            None,
        )
        if family is not None:
            resolved = _deep_merge(generic, family)
            resolved["model_id"] = model
            resolved["match"] = {"type": "prefix", "value": family["prefix"]}
        else:
            resolved = dict(generic)
            resolved["model_id"] = model
            resolved["display_name"] = model
            resolved["match"] = {"type": "fallback", "value": None}

    resolved["provider"] = registry.get("provider", "openrouter")
    resolved["schema_version"] = registry["schema_version"]
    return resolved


def resolve_model_request_behavior(
    model: str,
    request_class: str = "default",
    path: Path = MODEL_RUNTIME_PROFILE_PATH,
) -> dict[str, Any]:
    profile = resolve_model_runtime_profile(model, path)
    transport = dict(profile.get("transport") or {})
    override = (profile.get("request_overrides") or {}).get(request_class) or {}
    return _deep_merge(transport, override)


def runtime_profile_identity(
    model: str,
    path: Path = MODEL_RUNTIME_PROFILE_PATH,
) -> dict[str, Any]:
    profile = resolve_model_runtime_profile(model, path)
    encoded = json.dumps(profile, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return {
        "schema_version": profile["schema_version"],
        "provider": profile["provider"],
        "model_id": model,
        "display_name": profile.get("display_name"),
        "source": profile.get("source"),
        "match": profile.get("match"),
        "profile_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def normalize_openrouter_request(
    model: str,
    payload: dict[str, Any],
    *,
    request_class: str = "default",
    structured_output: bool = False,
    path: Path = MODEL_RUNTIME_PROFILE_PATH,
) -> dict[str, Any]:
    result = dict(payload)
    behavior = resolve_model_request_behavior(model, request_class, path)

    temperature = behavior.get("temperature") or {}
    if temperature.get("mode") == "omit":
        result.pop("temperature", None)

    max_tokens = behavior.get("max_tokens") or {}
    max_mode = max_tokens.get("mode", "send")
    if max_mode == "omit":
        result.pop("max_tokens", None)
    else:
        if max_tokens.get("value") is not None:
            result["max_tokens"] = int(max_tokens["value"])
        elif max_tokens.get("cap") is not None and result.get("max_tokens") is not None:
            result["max_tokens"] = min(
                int(result["max_tokens"]),
                int(max_tokens["cap"]),
            )

    seed = behavior.get("seed") or {}
    if seed.get("mode") == "omit":
        result.pop("seed", None)

    reasoning = behavior.get("reasoning") or {}
    reasoning_mode = reasoning.get("mode", "provider_default")
    reasoning_request = reasoning.get("request")
    if reasoning_request is not None:
        result["reasoning"] = dict(reasoning_request)
    elif reasoning_mode in {"provider_managed_required", "provider_default", "unsupported"}:
        result.pop("reasoning", None)

    if structured_output:
        structured_mode = behavior.get("structured_output", "provider_default")
        if structured_mode == "json_object":
            result["response_format"] = {"type": "json_object"}
        elif structured_mode == "provider_default":
            result.pop("response_format", None)

    routing = behavior.get("provider_routing")
    if isinstance(routing, dict) and routing:
        result["provider"] = {
            key: value
            for key, value in routing.items()
            if value is not None
        }

    return result


def build_fingerprint(
    model: str,
    qualification_config: dict[str, Any],
    *,
    extra_identity: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str]]:
    files = [Path(str(item)) for item in qualification_config.get("fingerprint_files") or []]
    hashes: dict[str, str] = {}
    for path in files:
        if not path.exists():
            raise RuntimeError(f"Fingerprint file does not exist: {path}")
        hashes[str(path)] = file_sha256(path)

    payload = {
        "model": model,
        "qualification_name": qualification_config.get("name"),
        "files": hashes,
        "model_runtime_profile": runtime_profile_identity(model),
        "runtime_identity": extra_identity or {},
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), hashes


def load_registry(path: Path) -> dict[str, Any]:
    return load_json(path, {"version": 1, "entries": []})


def find_by_fingerprint(registry: dict[str, Any], fingerprint: str) -> dict[str, Any] | None:
    for entry in registry.get("entries") or []:
        if entry.get("fingerprint") == fingerprint:
            return entry
    return None


def upsert_entry(path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    registry = load_registry(path)
    entries = list(registry.get("entries") or [])
    replaced = False
    for index, current in enumerate(entries):
        if current.get("fingerprint") == entry.get("fingerprint"):
            entries[index] = entry
            replaced = True
            break
    if not replaced:
        entries.append(entry)
    registry["entries"] = entries
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(path, registry)
    return registry
