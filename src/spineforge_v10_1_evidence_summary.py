from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _hash(value: Any) -> str | None:
    if value is None:
        return None
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_summary(result: dict[str, Any]) -> dict[str, Any]:
    failure = result.get("failure") or {}
    revision = result.get("revision_feedback_candidate") or {}
    totals = (result.get("pipeline_usage_rollup") or {}).get("totals") or {}
    calls = (result.get("pipeline_usage_rollup") or {}).get("calls") or []
    return {
        "schema_version": "spineforge-v10.1-log-summary.v1",
        "status": result.get("status"),
        "attempt_index": result.get("attempt_index"),
        "context_pack_id": result.get("context_pack_id"),
        "context_fingerprint": result.get("context_fingerprint"),
        "failure": {
            "stage": failure.get("stage"),
            "type": failure.get("type"),
            "message": failure.get("message"),
            "owning_partition": failure.get("owning_partition"),
        },
        "usage": {
            "api_calls": totals.get("api_calls"),
            "input_tokens": totals.get("input_tokens"),
            "output_tokens": totals.get("output_tokens"),
            "reasoning_tokens": totals.get("reasoning_tokens"),
            "cached_tokens": totals.get("cached_tokens"),
            "total_tokens": totals.get("total_tokens"),
            "cost_usd": totals.get("cost_usd"),
            "latency_seconds": totals.get("latency_seconds"),
        },
        "stage_call_count": len(calls) if isinstance(calls, list) else None,
        "revision_feedback": {
            "retry_stage": revision.get("retry_stage"),
            "source_status": revision.get("source_status"),
            "preserved_blueprint_sha256": _hash(revision.get("preserved_blueprint")),
            "preserved_frame_sha256": _hash(revision.get("preserved_frame")),
            "preserved_beats_sha256": _hash(revision.get("preserved_beats")),
        },
        "writer_authorized": (result.get("human_review") or {}).get("writer_authorized", False),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--result", type=Path, required=True)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    if not a.result.exists():
        print("SPINEFORGE_V10_1_EVIDENCE_SUMMARY=" + json.dumps({
            "schema_version": "spineforge-v10.1-log-summary.v1",
            "status": "RESULT_FILE_MISSING",
        }))
        raise SystemExit(2)
    result = json.loads(a.result.read_text(encoding="utf-8"))
    summary = build_summary(result)
    print("SPINEFORGE_V10_1_EVIDENCE_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
