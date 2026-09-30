from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from pydantic import ValidationError

from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_v3_contract import EpisodeSpineV3
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v11_contract import SpineAuditV11


SONNET_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_ARCHITECT_PROMPT = Path("prompts/spineforge_single_owner_architect_v11.md")
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


def _checkpoint(
    *, out_path: Path, evidence: dict[str, Any], calls: list[dict[str, Any]], started: float
) -> None:
    rollup = rollup_model_calls(calls)
    evidence["pipeline_usage_rollup"] = rollup
    evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["checkpointed_at"] = _now()
    _write(out_path, evidence)


def _validate_episode_authority(*, spine: EpisodeSpineV3, pack: SpineContextPackV1) -> None:
    premise = pack.approved_premise
    session = pack.session_target

    if spine.premise_key != premise["key"]:
        raise RuntimeError("Spine premise_key mismatch.")
    if spine.exact_age != int(pack.reader_profile["exact_age"]):
        raise RuntimeError("Spine exact_age mismatch.")
    if spine.session != session["name"]:
        raise RuntimeError("Spine session mismatch.")
    if (
        spine.target_words_min != int(session["target_words_min"])
        or spine.target_words_max != int(session["target_words_max"])
    ):
        raise RuntimeError("Spine word target mismatch.")

    allowed_locations = set(premise["location_refs"])
    used_locations = {beat.location_ref for beat in spine.beats}
    if used_locations - allowed_locations:
        raise RuntimeError(
            "Spine uses location outside approved premise: "
            + ", ".join(sorted(used_locations - allowed_locations))
        )

    full_access = {
        str(row["key"])
        for row in pack.knowledge_boundaries["accessible_locations"]
        if row.get("premise_usage") == "FULL"
    }
    if used_locations - full_access:
        raise RuntimeError(
            "Spine uses location without FULL premise access: "
            + ", ".join(sorted(used_locations - full_access))
        )

    intended = set(pack.saga["intended_milestone_keys"])
    actual = set(spine.saga_progression.intended_milestone_keys)
    if actual != intended:
        raise RuntimeError("Spine intended milestones differ from ContextPack authority.")
    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY",
        "MAIN_SAGA_PROGRESS",
        "MIXED",
    }:
        raise RuntimeError("Main Saga milestone requires a Main Saga episode role.")


def _default_call(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    return call_structured_json_with_retry(max_parse_attempts=1, **kwargs)


def _call_once(
    *,
    call_fn: JsonCall,
    api_key: str,
    stage: str,
    task: str,
    prompt: str,
    payload: dict[str, Any],
    max_tokens: int,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], float]:
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


def run(
    *,
    context_pack_path: Path,
    out_path: Path,
    architect_prompt_path: Path = DEFAULT_ARCHITECT_PROMPT,
    audit_prompt_path: Path = DEFAULT_AUDIT_PROMPT,
    api_key: str | None = None,
    call_fn: JsonCall | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    require_qualification_runtime_profile(SONNET_MODEL)
    pack = SpineContextPackV1.model_validate(_read(context_pack_path))
    pack_payload = pack.model_dump(mode="json", by_alias=True)

    calls: list[dict[str, Any]] = []
    started = time.perf_counter()
    evidence: dict[str, Any] = {
        "schema_version": "spineforge-v11-evidence.v1",
        "status": "started",
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "context_pack": pack_payload,
        "models": {
            "spine_architect": SONNET_MODEL,
            "spine_auditor": SONNET_MODEL,
        },
        "generation_topology": [
            "SONNET_STORY_SPINE_ARCHITECT",
            "DETERMINISTIC_CONTRACT_AND_AUTHORITY_VALIDATION",
            "SONNET_AGGRESSIVE_RED_TEAM_AUDIT",
            "STOP_FOR_HUMAN_OR_EXPLICIT_REPAIR",
        ],
        "automatic_repair_enabled": False,
        "writer_authorized": False,
        "human_review": {"required": True, "verdict": None},
        "started_at": _now(),
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    caller = call_fn or _default_call
    architect_payload = {
        "task": "create_complete_roleplay_episode_spine",
        "spine_context_pack": pack_payload,
        "experience_contract": {
            "story_first_not_schema_first": True,
            "active_protagonist": True,
            "roleplay_first": True,
            "sceneable_beats": True,
            "world_specific": True,
            "causal_escalation": True,
            "evidence_grounded_reversal": True,
            "consequential_decision": True,
            "earned_climax": True,
            "local_payoff_required": True,
            "hidden_saga_truth_forbidden": True,
        },
        "output_contract": EpisodeSpineV3.model_json_schema(by_alias=True),
    }

    try:
        raw, body, request, failures, latency = _call_once(
            call_fn=caller,
            api_key=key,
            stage="spineforge_v11_architect",
            task="create_complete_roleplay_episode_spine",
            prompt=architect_prompt_path.read_text(encoding="utf-8").strip(),
            payload=architect_payload,
            max_tokens=11000,
            request_class="saga_architect",
        )
        calls.append(_model_call("spineforge_v11_architect", body, latency))
        evidence["architect_transport"] = {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
            "parse_failures": failures,
        }
        evidence["architect_raw"] = raw
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

        spine = EpisodeSpineV3.model_validate(raw)
        _validate_episode_authority(spine=spine, pack=pack)
    except Exception as exc:
        evidence["status"] = "architect_contract_or_authority_rejected"
        evidence["failure"] = {"stage": "architect", "type": type(exc).__name__, "message": str(exc)}
        evidence["repair_candidate"] = {
            "scope": "ARCHITECT",
            "automatic_execution": False,
            "must_change": [str(exc)],
        }
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["episode_spine"] = spine.model_dump(mode="json", by_alias=True)
    evidence["deterministic_checks"] = {
        "episode_spine_contract_valid": True,
        "context_pack_authority_valid": True,
        "context_fingerprint_bound": True,
        "writer_blocked": True,
    }
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)

    audit_payload = {
        "task": "aggressively_audit_roleplay_episode_spine",
        "spine_context_pack": pack_payload,
        "episode_spine": spine.model_dump(mode="json", by_alias=True),
        "output_contract": SpineAuditV11.model_json_schema(by_alias=True),
    }

    try:
        raw, body, request, failures, latency = _call_once(
            call_fn=caller,
            api_key=key,
            stage="spineforge_v11_audit",
            task="aggressively_audit_roleplay_episode_spine",
            prompt=audit_prompt_path.read_text(encoding="utf-8").strip(),
            payload=audit_payload,
            max_tokens=4500,
            request_class="editorial_audit",
        )
        calls.append(_model_call("spineforge_v11_audit", body, latency))
        evidence["audit_transport"] = {
            "response_format": request.get("response_format"),
            "provider": request.get("provider"),
            "parse_failures": failures,
        }
        evidence["audit_raw"] = raw
        audit = SpineAuditV11.model_validate(raw)
    except Exception as exc:
        evidence["status"] = "audit_contract_rejected"
        evidence["failure"] = {"stage": "audit", "type": type(exc).__name__, "message": str(exc)}
        evidence["completed_at"] = _now()
        _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
        return evidence

    evidence["audit"] = audit.model_dump(mode="json", by_alias=True)
    if audit.decision == "REPAIR":
        evidence["status"] = "repair_required"
        evidence["repair_candidate"] = {
            "scope": "TARGETED_SPINE_REPAIR",
            "automatic_execution": False,
            "targets": [row.model_dump(mode="json") for row in audit.repair_targets],
            "preserve": audit.preserve,
        }
    else:
        evidence["status"] = "awaiting_human_review"

    evidence["completed_at"] = _now()
    _checkpoint(out_path=out_path, evidence=evidence, calls=calls, started=started)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-pack", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--architect-prompt", type=Path, default=DEFAULT_ARCHITECT_PROMPT)
    parser.add_argument("--audit-prompt", type=Path, default=DEFAULT_AUDIT_PROMPT)
    args = parser.parse_args()
    result = run(
        context_pack_path=args.context_pack,
        out_path=args.out,
        architect_prompt_path=args.architect_prompt,
        audit_prompt_path=args.audit_prompt,
    )
    print(json.dumps({
        "status": result["status"],
        "context_pack_id": result["context_pack_id"],
        "context_fingerprint": result["context_fingerprint"],
        "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
        "writer_authorized": result["writer_authorized"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
