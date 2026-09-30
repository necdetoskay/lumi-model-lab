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
    rollup = result.get("pipeline_usage_rollup") or {}
    totals = rollup.get("totals") or {}
    stage_calls = rollup.get("calls") or rollup.get("model_calls") or []
    return {
        "schema_version": "spineforge-v8-log-summary.v1",
        "status": result.get("status"),
        "attempt_index": result.get("attempt_index"),
        "context_pack_id": result.get("context_pack_id"),
        "context_fingerprint": result.get("context_fingerprint"),
        "failure": {
            "stage": failure.get("stage"),
            "type": failure.get("type"),
            "message": failure.get("message"),
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
        "stage_call_count": len(stage_calls) if isinstance(stage_calls, list) else None,
        "stage_evidence_keys": sorted((result.get("stage_evidence") or {}).keys()),
        "revision_feedback": {
            "retry_stage": revision.get("retry_stage"),
            "must_change": revision.get("must_change"),
            "source_status": revision.get("source_status"),
            "preserved_blueprint_sha256": _hash(revision.get("preserved_blueprint")),
            "preserved_frame_sha256": _hash(revision.get("preserved_frame")),
            "preserved_beats_sha256": _hash(revision.get("preserved_beats")),
        },
        "writer_authorized": (result.get("human_review") or {}).get("writer_authorized", False),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not args.result.exists():
        print(json.dumps({
            "schema_version": "spineforge-v8-log-summary.v1",
            "status": "RESULT_FILE_MISSING",
            "result_path": str(args.result),
        }, ensure_ascii=False))
        raise SystemExit(2)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    summary = build_summary(result)
    rendered = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    print("SPINEFORGE_V8_EVIDENCE_SUMMARY=" + rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
