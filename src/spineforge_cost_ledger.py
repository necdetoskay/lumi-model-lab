from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_spineforge_cost_ledger(
    *,
    case_id:str,
    runtime_id:str,
    attempt_paths:list[Path],
)->dict[str,Any]:
    attempts=[]
    accepted=None
    waste={
        "api_calls":0,
        "total_tokens":0,
        "cost_usd":0.0,
        "latency_seconds":0.0,
    }
    actual={
        "api_calls":0,
        "total_tokens":0,
        "cost_usd":0.0,
        "latency_seconds":0.0,
    }

    for path in attempt_paths:
        result=_read(path)
        totals=(result.get("pipeline_usage_rollup") or {}).get("totals") or {}
        row={
            "attempt_index":int(result.get("attempt_index") or 0),
            "status":result.get("status"),
            "api_calls":int(totals.get("api_calls") or 0),
            "total_tokens":int(totals.get("total_tokens") or 0),
            "cost_usd":float(totals.get("cost_usd") or 0.0),
            "latency_seconds":float(totals.get("latency_seconds") or 0.0),
        }
        attempts.append(row)
        for key in ("api_calls","total_tokens"):
            actual[key]+=row[key]
        for key in ("cost_usd","latency_seconds"):
            actual[key]+=row[key]

        if result.get("status")=="awaiting_human_review":
            if accepted is not None:
                raise RuntimeError("Multiple accepted SpineForge attempts in one ledger.")
            accepted=dict(row)
        else:
            for key in ("api_calls","total_tokens"):
                waste[key]+=row[key]
            for key in ("cost_usd","latency_seconds"):
                waste[key]+=row[key]

    return {
        "schema_version":"spineforge-cost-ledger.v1",
        "case_id":case_id,
        "runtime_id":runtime_id,
        "attempts":attempts,
        "accepted_attempt":accepted,
        "qualification_revision_waste":waste,
        "actual_spend":actual,
        "final_reporting":{
            "base_currency":"USD",
            "local_currency":"TRY",
            "usd_try_rate":None,
            "rate_timestamp":None,
            "accepted_attempt_try":None,
            "actual_total_try":None,
        },
    }
