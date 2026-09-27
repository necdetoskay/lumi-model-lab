from __future__ import annotations

import json
from pathlib import Path

from src.visual_contracts import VisualArtifact, VisualInvocationRecord


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def append_invocation(path: Path, invocation: VisualInvocationRecord) -> None:
    append_jsonl(path, invocation.model_dump(mode="json", by_alias=True))


def append_artifact(path: Path, artifact: VisualArtifact) -> None:
    append_jsonl(path, artifact.model_dump(mode="json", by_alias=True))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def aggregate_visual_cost(invocations: list[VisualInvocationRecord]) -> dict:
    success = [item for item in invocations if item.status == "SUCCESS"]
    costs = [item.cost_usd for item in success if item.cost_usd is not None]
    latencies = [item.latency_ms for item in success]
    return {
        "api_calls": len(invocations),
        "successful_calls": len(success),
        "images": sum(item.image_count for item in success),
        "cost_usd": round(sum(costs), 8) if costs else 0.0,
        "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "retry_attempts": sum(item.retry_attempt for item in invocations),
    }
