from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize(result_path: Path) -> dict[str, Any]:
    if not result_path.exists():
        return {"schema_version": "spineforge-v16-evidence-summary.v1", "status": "RESULT_MISSING"}

    result = json.loads(result_path.read_text(encoding="utf-8"))
    rollup = result.get("pipeline_usage_rollup") or {}
    totals = rollup.get("totals") or {}
    calls = rollup.get("calls") or []

    return {
        "schema_version": "spineforge-v16-evidence-summary.v1",
        "status": result.get("status"),
        "source_evidence_path": result.get("source_evidence_path"),
        "context_pack_id": result.get("source_context_pack_id"),
        "context_fingerprint": result.get("source_context_fingerprint"),
        "source_audit_completeness": result.get("source_audit_completeness"),
        "model_calls": len(calls),
        "call_stages": [row.get("stage") for row in calls],
        "input_tokens": totals.get("input_tokens"),
        "output_tokens": totals.get("output_tokens"),
        "reasoning_tokens": totals.get("reasoning_tokens"),
        "cached_tokens": totals.get("cached_tokens"),
        "total_tokens": totals.get("total_tokens"),
        "cost_usd": totals.get("cost_usd"),
        "latency_seconds": result.get("latency_seconds"),
        "repair_mechanical_normalization": result.get("repair_mechanical_normalization"),
        "reaudit_contract_normalization": result.get("reaudit_contract_normalization"),
        "reaudit_decision": (result.get("reaudit") or {}).get("decision"),
        "writer_authorized": result.get("writer_authorized"),
        "automatic_repair_loop_enabled": result.get("automatic_repair_loop_enabled"),
        "failure": result.get("failure"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    value = summarize(args.result)
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
