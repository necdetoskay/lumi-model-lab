from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from src.visual_contracts import VisualStyleProfile


VISUAL_STYLE_PROFILE_PATH = Path("configs/visual_style_profiles.yaml")


def load_visual_style_registry(path: Path = VISUAL_STYLE_PROFILE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Visual style profile registry does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "visual-style-registry.v1":
        raise RuntimeError(
            f"Unsupported visual style registry schema: {payload.get('schema_version')!r}"
        )
    profiles = payload.get("profiles") or []
    if not isinstance(profiles, list) or not profiles:
        raise RuntimeError("Visual style registry requires at least one profile")
    keys: set[tuple[str, str]] = set()
    for raw in profiles:
        profile = VisualStyleProfile.model_validate(raw)
        key = (profile.id, profile.version)
        if key in keys:
            raise RuntimeError(f"Duplicate visual style profile: {key}")
        keys.add(key)
    return payload


def resolve_visual_style_profile(
    style_id: str,
    version: str | None = None,
    path: Path = VISUAL_STYLE_PROFILE_PATH,
) -> VisualStyleProfile:
    registry = load_visual_style_registry(path)
    matches = [
        VisualStyleProfile.model_validate(entry)
        for entry in registry["profiles"]
        if entry.get("id") == style_id
        and (version is None or entry.get("version") == version)
    ]
    if not matches:
        suffix = f"@{version}" if version else ""
        raise RuntimeError(f"VISUAL_STYLE_PROFILE_MISSING: {style_id}{suffix}")
    if version is None:
        matches.sort(key=lambda item: tuple(int(p) for p in item.version.split(".")), reverse=True)
    profile = matches[0]
    if profile.status != "ACTIVE":
        raise RuntimeError(f"VISUAL_STYLE_INACTIVE: {style_id}@{profile.version}")
    return profile


def visual_style_profile_identity(
    style_id: str,
    version: str | None = None,
    path: Path = VISUAL_STYLE_PROFILE_PATH,
) -> dict[str, str]:
    profile = resolve_visual_style_profile(style_id, version, path)
    payload = profile.model_dump(mode="json")
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return {"profile_sha256": hashlib.sha256(encoded).hexdigest()}
