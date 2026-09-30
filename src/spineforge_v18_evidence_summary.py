from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize(result_path: Path) -> dict[str, Any]:
    if not result_path.exists():
        return {"schema_version": "spineforge-v18-evidence-summary.v1", "status": "RESULT_MISSING"}
    result = json.loads(result_path.read_text(encoding="utf-8"))
    rollup = result.get("pipeline_usage_rollup") or {}
    totals = rollup.get("totals") or {}
    calls = rollup.get("calls") or []
    return {
        "schema_version": "spineforge-v18-evidence-summary.v1",
        "status": result.get("status"),
        "source_evidence_path": result.get("source_evidence_path"),
        "context_pack_id": result.get("source_context_pack_id"),
        "context_fingerprint": result.get("source_context_fingerprint"),
        "strict_schema_size_bytes": result.get("strict_schema_size_bytes"),
        "provider_strict_json_schema": result.get("provider_strict_json_schema"),
        "model_calls": len(calls),
        "call_stages": [row.get("stage") for row in calls],
        "input_tokens": totals.get("input_tokens"),
        "output_tokens": totals.get("output_tokens"),
        "total_tokens": totals.get("total_tokens"),
        "cost_usd": totals.get("cost_usd"),
        "latency_seconds": result.get("latency_seconds"),
        "audit_decision": (result.get("audit") or {}).get("decision"),
        "audit_completeness": result.get("audit_completeness"),
        "repair_called": result.get("repair_called"),
        "writer_authorized": result.get("writer_authorized"),
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
