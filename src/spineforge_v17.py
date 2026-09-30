from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from src.english_story_pipeline import StructuredJsonCallError, call_structured_json_with_retry
from src.episode_spine_v3_contract import EpisodeSpineV3
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v11 import _validate_episode_authority
from src.spineforge_v11_contract import AUDIT_DIMENSIONS, SpineAuditV11
from src.spineforge_v13_audit_normalizer import normalize_audit_contract_aliases


SONNET_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_AUDIT_PROMPT = Path("prompts/spineforge_compact_complete_auditor_v17.md")

JsonCall = Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _checkpoint(*, out_path: Path, evidence: dict[str, Any], calls: list[dict[str, Any]], started: float) -> None:
    rollup = rollup_model_calls(calls)
    evidence["pipeline_usage_rollup"] = rollup
    evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["checkpointed_at"] = _now()
    _write(out_path, evidence)


def _default_call(**kwargs: Any):
    return call_structured_json_with_retry(max_parse_attempts=1, **kwargs)


def _call_from_body(stage: str, body: dict[str, Any], latency: float, status: str = "completed") -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=SONNET_MODEL,
        provider=runtime_profile_identity(SONNET_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
        status=status,
    )


def _call_from_structured_error(stage: str, exc: StructuredJsonCallError, latency: float) -> dict[str, Any]:
    trace = exc.trace or {}
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
        status="failed_structured_output",
    )


def run(
    *,
    source_evidence_path: Path,
    out_path: Path,
    audit_prompt_path: Path = DEFAULT_AUDIT_PROMPT,
    api_key: str | None = None,
    call_fn: JsonCall | None = None,
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
        "schema_version": "spineforge-v17-evidence.v1",
        "status": "started",
        "source_evidence_path": str(source_evidence_path),
        "source_context_pack_id": pack.context_pack_id,
        "source_context_fingerprint": pack.context_fingerprint,
        "context_pack": pack.model_dump(mode="json", by_alias=True),
        "episode_spine": spine.model_dump(mode="json", by_alias=True),
        "deterministic_checks": {
            "episode_spine_contract_valid": True,
            "context_pack_authority_valid": True,
            "context_fingerprint_bound": True,
            "writer_blocked": True,
        },
        "model": SONNET_MODEL,
        "audit_only": True,
        "architect_recalled": False,
        "repair_called": False,
        "writer_authorized": False,
        "human_review": {"required": True, "verdict": None},
        "started_at": _now(),
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    payload = {
        "task": "compact_complete_final_spine_audit",
        "spine_context_pack": pack.model_dump(mode="json", by_alias=True),
        "validated_episode_spine": spine.model_dump(mode="json", by_alias=True),
        "mandatory_audit_dimensions": [
            "STORY_DESIRE",
            "ROLEPLAY_POTENTIAL",
            "SCENE_POTENTIAL",
            "CHARACTER_DRIVENNESS",
            "WORLD_SPECIFICITY",
            "WONDER_OR_INTRIGUE",
            "AGE_MATURITY",
            "CAUSAL_COHERENCE",
            "ESCALATION",
            "REVERSAL_QUALITY",
            "AGENCY",
            "BRANCH_EXECUTABILITY",
            "CLIMAX_PAYOFF",
            "LOCAL_SATISFACTION",
            "SAGA_ALIGNMENT",
            "AUTHORITY_SAFETY",
            "WRITER_EXECUTABILITY",
            "FRESHNESS",
        ],
        "output_contract": SpineAuditV11.model_json_schema(by_alias=True),
    }

    caller = call_fn or _default_call
    call_started = time.perf_counter()
    try:
        raw, body, request, failures = caller(
            api_key=key,
            model=SONNET_MODEL,
            system_prompt=audit_prompt_path.read_text(encoding="utf-8").strip(),
            user_prompt=json.dumps(payload, ensure_ascii=False),
            temperature=0.0,
            max_tokens=8000,
            seed=None,
            request_class="editorial_audit",
        )
        call_latency = round(time.perf_counter() - call_started, 3)
        calls.append(_call_from_body("spineforge_v17_audit", body, call_latency))
        evidence["audit_transport"] = {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
            "parse_failures": failures,
            "max_tokens": 8000,
        }
        evidence["audit_raw"] = raw
        normalized, normalization = normalize_audit_contract_aliases(raw)
        evidence["audit_contract_normalization"] = normalization.model_dump(mode="json", by_alias=True)
        evidence["audit_normalized"] = normalized
        audit = SpineAuditV11.model_validate(normalized)
    except StructuredJsonCallError as exc:
        call_latency = round(time.perf_counter() - call_started, 3)
        calls.append(_call_from_structured_error("spineforge_v17_audit", exc, call_latency))
        evidence["status"] = "audit_structured_output_failed"
        evidence["failure"] = {
            "stage": "audit",
            "type": type(exc).__name__,
            "message": str(exc),
            "trace": exc.trace,
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence
    except Exception as exc:
        evidence["status"] = "audit_contract_rejected"
        evidence["failure"] = {
            "stage": "audit",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["audit"] = audit.model_dump(mode="json", by_alias=True)
    evidence["audit_completeness"] = {
        "present_count": len(audit.dimensions),
        "required_count": len(AUDIT_DIMENSIONS),
        "present_dimensions": sorted(row.name for row in audit.dimensions),
        "missing_dimensions": [],
        "complete": True,
    }
    evidence["status"] = "awaiting_human_review" if audit.decision == "ACCEPT" else "repair_required"
    evidence["completed_at"] = _now()
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-prompt", type=Path, default=DEFAULT_AUDIT_PROMPT)
    args = parser.parse_args()
    result = run(
        source_evidence_path=args.source_evidence,
        out_path=args.out,
        audit_prompt_path=args.audit_prompt,
    )
    print(json.dumps({
        "status": result["status"],
        "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
        "writer_authorized": result["writer_authorized"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
