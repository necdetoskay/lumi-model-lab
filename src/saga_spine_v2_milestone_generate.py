from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import parse_cost, parse_usage
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.saga_spine_v2_milestone_contract import (
    SagaMilestoneExpansionV2,
    merge_expansion_with_skeleton,
)
from src.saga_spine_v2_skeleton_contract import CharacterSagaSkeletonV2


DEFAULT_SKELETON = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_a_approved_v1.json"
)
DEFAULT_PROMPT = Path("prompts/saga_milestone_architect_v2.md")
DEFAULT_OUT = Path("runs/saga-spine-v2-age12-milestones/result.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _resolve_model(model_override: str | None) -> str:
    model = model_override or os.getenv("SAGA_SPINE_V2_MODEL")
    if not model:
        raise RuntimeError(
            "Missing milestone architect model. Pass --model or set SAGA_SPINE_V2_MODEL."
        )
    return model


def generate(
    *,
    skeleton_path: Path,
    prompt_path: Path,
    out_path: Path,
    model_override: str | None = None,
    api_key: str | None = None,
    reviewed_draft_path: Path | None = None,
    revision_directives_path: Path | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    model = _resolve_model(model_override)
    require_qualification_runtime_profile(model)
    model_identity = runtime_profile_identity(model)

    skeleton = CharacterSagaSkeletonV2.model_validate(_read_json(skeleton_path))
    output_contract = SagaMilestoneExpansionV2.model_json_schema(by_alias=True)
    system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    reviewed_draft = _read_json(reviewed_draft_path) if reviewed_draft_path else None
    previous_expansion = None
    if reviewed_draft is not None:
        previous_expansion = SagaMilestoneExpansionV2.model_validate(
            reviewed_draft["expansion"]
        ).model_dump(mode="json", by_alias=True)

    revision_directives = (
        _read_json(revision_directives_path)
        if revision_directives_path is not None
        else None
    )

    request_payload = {
        "task": "expand_approved_saga_skeleton_into_milestones",
        "approved_skeleton": skeleton.model_dump(mode="json", by_alias=True),
        "previous_reviewed_expansion": previous_expansion,
        "human_revision_directives": revision_directives,
        "revision_rules": [
            "When previous_reviewed_expansion and human_revision_directives are present, perform targeted minimal repair rather than wholesale regeneration.",
            "Satisfy every must_change directive.",
            "Preserve preserve_strengths and stable milestone keys unless a milestone is materially replaced.",
            "Do not alter the approved Gate A skeleton."
        ],
        "output_contract": output_contract,
        "contract_rules": [
            "Match output_contract fields and literal enums exactly.",
            "Do not rewrite approved_skeleton fields.",
            "Return only milestone expansion data.",
            "Every approved reveal intent must receive a valid milestone binding.",
            "Every anchor must receive exactly milestone_target_count milestones.",
            "Milestone types under each anchor must cover its desired_progression_modes.",
        ],
        "qualification_rules": {
            "human_creative_review_required": True,
            "episode_generation_forbidden": True,
            "approved_gate_a_must_remain_unchanged": True,
            "milestone_total": sum(
                a.milestone_target_count for a in skeleton.main_saga.anchors
            ),
            "exact_age": 12,
        },
    }

    started = time.perf_counter()
    started_at = _now_iso()

    try:
        parsed, body, request, parse_failures = call_structured_json_with_retry(
            api_key=key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=json.dumps(request_payload, ensure_ascii=False),
            temperature=0.30,
            max_tokens=12000,
            seed=2026092804,
            request_class="saga_architect",
            max_parse_attempts=2,
        )
    except Exception as exc:
        failure = {
            "schema_version": "saga-milestone-expansion-evidence.v1",
            "status": "provider_or_parse_failure",
            "publication_authority": False,
            "model": model,
            "model_runtime_identity": model_identity,
            "started_at": started_at,
            "completed_at": _now_iso(),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "request_payload": request_payload,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "trace": getattr(exc, "trace", None),
            },
        }
        _write_json(out_path, failure)
        raise

    evidence: dict[str, Any] = {
        "schema_version": "saga-milestone-expansion-evidence.v1",
        "status": "generated",
        "publication_authority": False,
        "human_creative_review_required": True,
        "episode_generation_authorized": False,
        "model": model,
        "model_runtime_identity": model_identity,
        "started_at": started_at,
        "completed_at": _now_iso(),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "approved_skeleton": skeleton.model_dump(mode="json", by_alias=True),
        "previous_reviewed_expansion": previous_expansion,
        "human_revision_directives": revision_directives,
        "raw_generated_payload": parsed,
        "raw_usage": body.get("usage") or {},
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
        "parse_failures": parse_failures,
    }

    try:
        expansion = SagaMilestoneExpansionV2.model_validate(parsed)
        full_spine = merge_expansion_with_skeleton(skeleton, expansion)
    except (ValidationError, ValueError) as exc:
        evidence["status"] = "contract_rejected"
        evidence["contract_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "details": (
                exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=False,
                )
                if isinstance(exc, ValidationError)
                else None
            ),
        }
        _write_json(out_path, evidence)
        raise RuntimeError(
            "Gate B milestone expansion failed deterministic contract validation."
        ) from exc

    evidence["status"] = "awaiting_human_review"
    evidence["expansion"] = expansion.model_dump(mode="json", by_alias=True)
    evidence["full_spine_candidate"] = full_spine.model_dump(mode="json", by_alias=True)
    evidence["human_review"] = {
        "verdict": None,
        "allowed_values": ["APPROVE", "REVISE", "REJECT"],
        "assistant_independent_assessment": None,
        "episode_generation_authorized": False,
    }
    _write_json(out_path, evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Expand one approved Saga Skeleton into Gate B milestones."
    )
    parser.add_argument("--skeleton", type=Path, default=DEFAULT_SKELETON)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model")
    parser.add_argument("--reviewed-draft", type=Path)
    parser.add_argument("--revision-directives", type=Path)
    args = parser.parse_args()

    payload = generate(
        skeleton_path=args.skeleton,
        prompt_path=args.prompt,
        out_path=args.out,
        model_override=args.model,
        reviewed_draft_path=args.reviewed_draft,
        revision_directives_path=args.revision_directives,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "model": payload["model"],
                "latency_seconds": payload["latency_seconds"],
                "usage": payload["raw_usage"],
                "cost": payload["cost"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
