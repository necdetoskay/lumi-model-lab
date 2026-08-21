from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def empty_ledger() -> dict[str, Any]:
    return {
        "api_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
        "cost_try": None,
        "usd_try_rate": None,
        "by_stage": {},
    }


def _add(ledger: dict[str, Any], stage: str, *, input_tokens: int = 0, output_tokens: int = 0,
         total_tokens: int = 0, cost_usd: float = 0.0) -> None:
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    stage_row = ledger["by_stage"].setdefault(stage, {
        "api_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0,
    })
    for row in (ledger, stage_row):
        row["api_calls"] += 1
        row["input_tokens"] += input_tokens
        row["output_tokens"] += output_tokens
        row["total_tokens"] += total_tokens
        row["cost_usd"] = round(float(row["cost_usd"]) + cost_usd, 8)


def _add_generation_record(ledger: dict[str, Any], stage: str, path: Path, seen: set[str]) -> None:
    if not path.exists():
        return
    payload = load_json(path)
    identity = str((payload.get("response_meta") or {}).get("openrouter_id") or path.resolve())
    if identity in seen:
        return
    seen.add(identity)
    usage = payload.get("usage") or {}
    cost = payload.get("cost") or {}
    _add(
        ledger,
        stage,
        input_tokens=_int(usage.get("input_tokens")),
        output_tokens=_int(usage.get("output_tokens")),
        total_tokens=_int(usage.get("total_tokens")),
        cost_usd=_num(cost.get("usd")),
    )


def _add_manifest(ledger: dict[str, Any], manifest_path: Path, stage_prefix: str, seen: set[str]) -> None:
    if not manifest_path.exists():
        return
    manifest = load_json(manifest_path)
    for entry in manifest.get("entries") or []:
        story_path = entry.get("story_path")
        if story_path:
            _add_generation_record(ledger, f"{stage_prefix}_generation", Path(str(story_path)), seen)
        judgment_path = entry.get("judgment_path")
        if judgment_path:
            _add_generation_record(ledger, f"{stage_prefix}_judge", Path(str(judgment_path)), seen)


def _add_extraction(ledger: dict[str, Any], manifest_path: Path) -> None:
    if not manifest_path.exists():
        return
    manifest = load_json(manifest_path)
    for entry in manifest.get("entries") or []:
        story_id = str(entry.get("source_story_id") or "unknown")
        for call in entry.get("calls") or []:
            _add(
                ledger,
                "extraction",
                input_tokens=_int(call.get("input_tokens")),
                output_tokens=_int(call.get("output_tokens")),
                cost_usd=_num(call.get("cost_usd")),
            )


def collect_qualification_costs(run_dir: Path) -> dict[str, Any]:
    ledger = empty_ledger()
    seen: set[str] = set()
    _add_manifest(ledger, run_dir / "screen" / "manifest.json", "screen", seen)
    _add_manifest(ledger, run_dir / "source" / "manifest.json", "source", seen)
    _add_extraction(ledger, run_dir / "extraction" / "manifest.json")

    rate_raw = os.getenv("USD_TRY_RATE")
    if rate_raw:
        try:
            rate = float(rate_raw)
        except ValueError:
            rate = None
        if rate is not None:
            ledger["usd_try_rate"] = rate
            ledger["cost_try"] = round(float(ledger["cost_usd"]) * rate, 4)
    return ledger
