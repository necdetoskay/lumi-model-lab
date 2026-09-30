from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_v3_contract import EpisodeSpineV3
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v11 import _validate_episode_authority
from src.spineforge_v11_contract import SpineAuditV11
from src.spineforge_v12_normalizer import normalize_mechanical_fields
from src.spineforge_v13_audit_normalizer import normalize_audit_contract_aliases


SONNET_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_REPAIR_PROMPT = Path("prompts/spineforge_targeted_semantic_repair_v14.md")
DEFAULT_AUDIT_PROMPT = Path("prompts/spineforge_single_owner_auditor_v11.md")

JsonCall = Callable[..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _model_call(stage: str, body: dict[str, Any], latency: float) -> dict[str, Any]:
    return normalize_model_call(
        stage=stage,
        model=SONNET_MODEL,
        provider=runtime_profile_identity(SONNET_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )


def _checkpoint(*, out_path: Path, evidence: dict[str, Any], calls: list[dict[str, Any]], started: float) -> None:
    rollup = rollup_model_calls(calls)
    evidence["pipeline_usage_rollup"] = rollup
    evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["checkpointed_at"] = _now()
    _write(out_path, evidence)


def _default_call(**kwargs: Any):
    return call_structured_json_with_retry(max_parse_attempts=1, **kwargs)


def _call_once(
    *,
    call_fn: JsonCall,
    api_key: str,
    stage: str,
    prompt: str,
    payload: dict[str, Any],
    max_tokens: int,
    request_class: str,
):
    started = time.perf_counter()
    raw, body, request, parse_failures = call_fn(
        api_key=api_key,
        model=SONNET_MODEL,
        system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=max_tokens,
        seed=None,
        request_class=request_class,
    )
    return raw, body, request, parse_failures, round(time.perf_counter() - started, 3)


def _repair_brief(audit: SpineAuditV11) -> dict[str, Any]:
    return {
        "decision": audit.decision,
        "blocking_defects": list(audit.blocking_defects),
        "repair_targets": [
            row.model_dump(mode="json") for row in audit.repair_targets
        ],
        "preserve": list(audit.preserve),
        "decision_reason": audit.decision_reason,
        "weak_dimensions": [
            {
                "name": row.name,
                "score": row.score,
                "blocking_failure": row.blocking_failure,
                "reason": row.reason,
            }
            for row in audit.dimensions
            if row.score < 4 or row.blocking_failure
        ],
    }


def run(
    *,
    source_evidence_path: Path,
    out_path: Path,
    repair_prompt_path: Path = DEFAULT_REPAIR_PROMPT,
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
    base_spine = EpisodeSpineV3.model_validate(source["episode_spine"])
    _validate_episode_authority(spine=base_spine, pack=pack)

    normalized_audit_raw, source_audit_normalization = normalize_audit_contract_aliases(
        source["audit_raw"]
    )
    source_audit = SpineAuditV11.model_validate(normalized_audit_raw)
    if source_audit.decision != "REPAIR":
        raise RuntimeError("v14 repair-only runtime requires a typed REPAIR audit.")

    calls: list[dict[str, Any]] = []
    started = time.perf_counter()
    evidence: dict[str, Any] = {
        "schema_version": "spineforge-v14-evidence.v1",
        "status": "started",
        "source_evidence_path": str(source_evidence_path),
        "source_context_pack_id": pack.context_pack_id,
        "source_context_fingerprint": pack.context_fingerprint,
        "context_pack": pack.model_dump(mode="json", by_alias=True),
        "base_episode_spine": base_spine.model_dump(mode="json", by_alias=True),
        "source_audit": source_audit.model_dump(mode="json", by_alias=True),
        "source_audit_contract_normalization": source_audit_normalization.model_dump(
            mode="json", by_alias=True
        ),
        "models": {
            "repair_editor": SONNET_MODEL,
            "reauditor": SONNET_MODEL,
        },
        "generation_topology": [
            "FROZEN_VALIDATED_SPINE_AND_TYPED_REPAIR_AUDIT",
            "SONNET_TARGETED_SEMANTIC_REPAIR",
            "DETERMINISTIC_MECHANICAL_NORMALIZATION",
            "CONTRACT_AND_AUTHORITY_VALIDATION",
            "SONNET_AGGRESSIVE_REAUDIT",
            "STOP_FOR_HUMAN_OR_FUTURE_EXPLICIT_REPAIR",
        ],
        "automatic_repair_loop_enabled": False,
        "writer_authorized": False,
        "human_review": {"required": True, "verdict": None},
        "started_at": _now(),
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    caller = call_fn or _default_call
    pack_payload = pack.model_dump(mode="json", by_alias=True)
    repair_payload = {
        "task": "targeted_semantic_episode_spine_repair",
        "spine_context_pack": pack_payload,
        "current_episode_spine": base_spine.model_dump(mode="json", by_alias=True),
        "repair_brief": _repair_brief(source_audit),
        "application_derived_fields": {
            "logistics_plan.location_sequence": (
                "application recomputes this mechanically from ordered beat.location_ref transitions"
            )
        },
        "output_contract": EpisodeSpineV3.model_json_schema(by_alias=True),
    }

    try:
        raw, body, request, failures, latency = _call_once(
            call_fn=caller,
            api_key=key,
            stage="spineforge_v14_repair",
            prompt=repair_prompt_path.read_text(encoding="utf-8").strip(),
            payload=repair_payload,
            max_tokens=10000,
            request_class="saga_architect",
        )
        calls.append(_model_call("spineforge_v14_repair", body, latency))
        evidence["repair_transport"] = {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
            "parse_failures": failures,
        }
        evidence["repair_raw"] = raw
        normalized, normalization = normalize_mechanical_fields(raw)
        evidence["repair_mechanical_normalization"] = normalization.model_dump(
            mode="json", by_alias=True
        )
        evidence["repair_normalized"] = normalized
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

        repaired_spine = EpisodeSpineV3.model_validate(normalized)
        _validate_episode_authority(spine=repaired_spine, pack=pack)
    except Exception as exc:
        evidence["status"] = "repair_contract_or_authority_rejected"
        evidence["failure"] = {
            "stage": "repair",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["repaired_episode_spine"] = repaired_spine.model_dump(
        mode="json", by_alias=True
    )
    evidence["deterministic_checks"] = {
        "repair_episode_spine_contract_valid": True,
        "repair_context_pack_authority_valid": True,
        "context_fingerprint_bound": True,
        "writer_blocked": True,
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    audit_payload = {
        "task": "aggressively_reaudit_repaired_roleplay_episode_spine",
        "spine_context_pack": pack_payload,
        "previous_audit": source_audit.model_dump(mode="json", by_alias=True),
        "repaired_episode_spine": repaired_spine.model_dump(mode="json", by_alias=True),
        "output_contract": SpineAuditV11.model_json_schema(by_alias=True),
    }

    try:
        raw, body, request, failures, latency = _call_once(
            call_fn=caller,
            api_key=key,
            stage="spineforge_v14_reaudit",
            prompt=audit_prompt_path.read_text(encoding="utf-8").strip(),
            payload=audit_payload,
            max_tokens=4500,
            request_class="editorial_audit",
        )
        calls.append(_model_call("spineforge_v14_reaudit", body, latency))
        evidence["reaudit_transport"] = {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
            "parse_failures": failures,
        }
        evidence["reaudit_raw"] = raw
        normalized_audit, audit_normalization = normalize_audit_contract_aliases(raw)
        evidence["reaudit_contract_normalization"] = audit_normalization.model_dump(
            mode="json", by_alias=True
        )
        evidence["reaudit_normalized"] = normalized_audit
        reaudited = SpineAuditV11.model_validate(normalized_audit)
    except Exception as exc:
        evidence["status"] = "reaudit_contract_rejected"
        evidence["failure"] = {
            "stage": "reaudit",
            "type": type(exc).__name__,
            "message": str(exc),
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["reaudit"] = reaudited.model_dump(mode="json", by_alias=True)
    if reaudited.decision == "REPAIR":
        evidence["status"] = "repair_still_required"
        evidence["next_repair_candidate"] = {
            "automatic_execution": False,
            "targets": [
                row.model_dump(mode="json") for row in reaudited.repair_targets
            ],
            "preserve": reaudited.preserve,
        }
    else:
        evidence["status"] = "awaiting_human_review"

    evidence["completed_at"] = _now()
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repair-prompt", type=Path, default=DEFAULT_REPAIR_PROMPT)
    parser.add_argument("--audit-prompt", type=Path, default=DEFAULT_AUDIT_PROMPT)
    args = parser.parse_args()
    result = run(
        source_evidence_path=args.source_evidence,
        out_path=args.out,
        repair_prompt_path=args.repair_prompt,
        audit_prompt_path=args.audit_prompt,
    )
    print(json.dumps({
        "status": result["status"],
        "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
        "writer_authorized": result["writer_authorized"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
