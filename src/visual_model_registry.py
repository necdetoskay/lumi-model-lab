from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from src.visual_contracts import VisualCategory, VisualModelProfile


VISUAL_MODEL_PROFILE_PATH = Path("configs/visual_model_profiles.yaml")


def load_visual_model_registry(path: Path = VISUAL_MODEL_PROFILE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Visual model profile registry does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "visual-model-registry.v1":
        raise RuntimeError(
            f"Unsupported visual model registry schema: {payload.get('schema_version')!r}"
        )
    profiles = payload.get("profiles") or []
    if not isinstance(profiles, list) or not profiles:
        raise RuntimeError("Visual model registry requires at least one profile")
    ids: set[str] = set()
    for raw in profiles:
        profile = VisualModelProfile.model_validate(raw)
        if profile.model_id in ids:
            raise RuntimeError(f"Duplicate visual model profile: {profile.model_id}")
        ids.add(profile.model_id)
    return payload


def resolve_visual_model_profile(
    model_id: str,
    path: Path = VISUAL_MODEL_PROFILE_PATH,
) -> VisualModelProfile:
    registry = load_visual_model_registry(path)
    raw = next(
        (entry for entry in registry["profiles"] if entry.get("model_id") == model_id),
        None,
    )
    if raw is None:
        raise RuntimeError(f"VISUAL_MODEL_PROFILE_MISSING: {model_id}")
    return VisualModelProfile.model_validate(raw)


def require_visual_model_profile(
    model_id: str,
    *,
    category: VisualCategory | None = None,
    style_id: str | None = None,
    require_qualified: bool = False,
    path: Path = VISUAL_MODEL_PROFILE_PATH,
) -> VisualModelProfile:
    profile = resolve_visual_model_profile(model_id, path)
    if profile.status != "ACTIVE":
        raise RuntimeError(f"VISUAL_MODEL_INACTIVE: {model_id}")
    if category is not None and category not in profile.supported_categories:
        raise RuntimeError(f"VISUAL_MODEL_CATEGORY_UNSUPPORTED: {model_id} -> {category.value}")
    if style_id is not None and profile.supported_styles and style_id not in profile.supported_styles:
        raise RuntimeError(f"VISUAL_MODEL_STYLE_UNSUPPORTED: {model_id} -> {style_id}")
    if require_qualified and not profile.qualification.ready:
        raise RuntimeError(f"VISUAL_MODEL_NOT_QUALIFIED: {model_id}")
    return profile


def visual_model_profile_identity(
    model_id: str,
    path: Path = VISUAL_MODEL_PROFILE_PATH,
) -> dict[str, str]:
    profile = resolve_visual_model_profile(model_id, path)
    payload = profile.model_dump(mode="json")
    runtime = {
        "provider": profile.provider,
        "endpoint": profile.endpoint,
        "capabilities": profile.capabilities.model_dump(mode="json"),
        "runtime_policy": profile.runtime_policy.model_dump(mode="json"),
        "pricing": profile.pricing.model_dump(mode="json"),
    }
    prompt_policy = profile.prompt_policy.model_dump(mode="json")
    encode = lambda value: json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "profile_sha256": hashlib.sha256(encode(payload)).hexdigest(),
        "runtime_contract_sha256": hashlib.sha256(encode(runtime)).hexdigest(),
        "prompt_policy_sha256": hashlib.sha256(encode(prompt_policy)).hexdigest(),
    }
