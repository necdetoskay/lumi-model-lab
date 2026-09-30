from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.model_usage_rollup import rollup_model_calls


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_story(payload: dict[str, Any]) -> str:
    for key in (
        "repaired_story",
        "accepted_english_master",
        "english_story",
        "story",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError("Source payload does not contain an English story.")


def extract_turkish(payload: dict[str, Any]) -> str:
    for key in ("turkish_delivery", "turkish_delivery_story", "translation_tr"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError("Source payload does not contain a Turkish translation.")


def source_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rollup = payload.get("pipeline_usage_rollup") or payload.get("source_pipeline_usage_rollup") or {}
    return list(rollup.get("calls") or [])


def combined_rollup(payload: dict[str, Any], new_calls: list[dict[str, Any]]) -> dict[str, Any]:
    return rollup_model_calls(source_calls(payload) + list(new_calls))
