from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from src.english_story_pipeline import StructuredJsonCallError
from src.episode_spine_v3_contract import EpisodeSpineV3
from src.generate import OpenRouterCallError, parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v11 import _validate_episode_authority
from src.spineforge_v18_strict_call import call_strict_audit_once
from src.spineforge_v18_transport import schema_size_bytes, transport_to_typed_audit


SONNET_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_AUDIT_PROMPT = Path("prompts/spineforge_strict_complete_auditor_v18.md")

StrictCall = Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _call_record(stage: str, body: dict[str, Any], latency: float, status: str = "completed") -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=SONNET_MODEL,
        provider=runtime_profile_identity(SONNET_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
        status=status,
    )


def _error_record(stage: str, exc: Exception, latency: float) -> dict[str, Any] | None:
    trace = getattr(exc, "trace", None)
    if not isinstance(trace, dict):
        return None
    body = trace.get("body") or {}
    raw_usage = trace.get("raw_usage") or body.get("usage") or {}
    cost = trace.get("cost") or parse_cost(body).model_dump(mode="json")
    return normalize_model_call(
        stage=stage,
        model=SONNET_MODEL,
        provider=runtime_profile_identity(SONNET_MODEL).get("provider"),
        raw_usage=raw_usage,
        cost=cost,
        latency_seconds=latency,
        status="failed",
    )


def _checkpoint(out_path: Path, evidence: dict[str, Any], calls: list[dict[str, Any]], started: float) -> None:
    rollup = rollup_model_calls(calls)
    evidence["pipeline_usage_rollup"] = rollup
    evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["checkpointed_at"] = _now()
    _write(out_path, evidence)


def run(
    *,
    source_evidence_path: Path,
    out_path: Path,
    audit_prompt_path: Path = DEFAULT_AUDIT_PROMPT,
    api_key: str | None = None,
    call_fn: StrictCall | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    require_qualification_runtime_profile(SONNET_MODEL)
    source = _read(source_evidence_path)
    pack = SpineContextPackV1.model_validate(source["context_pack"])
    spine = EpisodeSpineV3.model_validate(source["repaired_episode_spine"])
    _validate_episode_authority(spine=spine, pack=pack)

    calls: list[dict[str, Any]] = []
    started = time.perf_counter()
    evidence: dict[str, Any] = {
        "schema_version": "spineforge-v18-evidence.v1",
        "status": "started",
        "source_evidence_path": str(source_evidence_path),
        "source_context_pack_id": pack.context_pack_id,
        "source_context_fingerprint": pack.context_fingerprint,
        "context_pack": pack.model_dump(mode="json", by_alias=True),
        "episode_spine": spine.model_dump(mode="json", by_alias=True),
        "audit_only": True,
        "provider_strict_json_schema": True,
        "strict_schema_size_bytes": schema_size_bytes(),
        "architect_recalled": False,
        "repair_called": False,
        "writer_authorized": False,
        "started_at": _now(),
    }
    _checkpoint(out_path, evidence, calls, started)

    payload = {
        "task": "strict_complete_final_spine_audit",
        "spine_context_pack": pack.model_dump(mode="json", by_alias=True),
        "validated_episode_spine": spine.model_dump(mode="json", by_alias=True),
    }

    caller = call_fn or call_strict_audit_once
    call_started = time.perf_counter()
    try:
        raw, body, request, failures = caller(
            api_key=key,
            system_prompt=audit_prompt_path.read_text(encoding="utf-8").strip(),
            user_prompt=json.dumps(payload, ensure_ascii=False),
            temperature=0.0,
            max_tokens=6000,
            request_class="editorial_audit",
        )
        latency = round(time.perf_counter() - call_started, 3)
        calls.append(_call_record("spineforge_v18_strict_audit", body, latency))
        evidence["audit_transport"] = {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
            "parse_failures": failures,
            "max_tokens": 6000,
        }
        evidence["audit_raw_transport"] = raw
        audit = transport_to_typed_audit(raw)
    except (StructuredJsonCallError, OpenRouterCallError) as exc:
        latency = round(time.perf_counter() - call_started, 3)
        record = _error_record("spineforge_v18_strict_audit", exc, latency)
        if record is not None:
            calls.append(record)
        evidence["status"] = "strict_audit_transport_failed"
        evidence["failure"] = {
            "stage": "audit",
            "type": type(exc).__name__,
            "message": str(exc),
            "trace": getattr(exc, "trace", None),
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path, evidence, calls, started)
        return evidence
    except Exception as exc:
        evidence["status"] = "audit_contract_rejected"
        evidence["failure"] = {
            "stage": "audit",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path, evidence, calls, started)
        return evidence

    evidence["audit"] = audit.model_dump(mode="json", by_alias=True)
    evidence["audit_completeness"] = {
        "present_count": len(audit.dimensions),
        "required_count": 18,
        "complete": len(audit.dimensions) == 18,
    }
    evidence["status"] = "awaiting_human_review" if audit.decision == "ACCEPT" else "repair_required"
    evidence["completed_at"] = _now()
    _checkpoint(out_path, evidence, calls, started)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-prompt", type=Path, default=DEFAULT_AUDIT_PROMPT)
    args = parser.parse_args()
    result = run(source_evidence_path=args.source_evidence, out_path=args.out, audit_prompt_path=args.audit_prompt)
    print(json.dumps({
        "status": result["status"],
        "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
        "strict_schema_size_bytes": result["strict_schema_size_bytes"],
        "writer_authorized": result["writer_authorized"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
