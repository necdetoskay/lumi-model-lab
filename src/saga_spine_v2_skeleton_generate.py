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
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_skeleton_contract import CharacterSagaSkeletonV2


DEFAULT_FIXTURE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_fixture_v2.json"
)
DEFAULT_PROMPT = Path("prompts/saga_narrative_architect_skeleton_v2.md")
DEFAULT_SCHEMA = Path(
    "data/specifications/saga_lab/character_saga_skeleton_v2.schema.json"
)
DEFAULT_OUT = Path("runs/saga-spine-v2-age12-skeleton/result.json")


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
            "Missing Saga Skeleton architect model. Pass --model or set SAGA_SPINE_V2_MODEL."
        )
    return model


def generate(
    *,
    fixture_path: Path,
    prompt_path: Path,
    schema_path: Path,
    out_path: Path,
    model_override: str | None = None,
    api_key: str | None = None,
    revision_directives_path: Path | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    model = _resolve_model(model_override)
    require_qualification_runtime_profile(model)
    model_identity = runtime_profile_identity(model)

    fixture = NarrativeFixture.model_validate(_read_json(fixture_path))
    schema = _read_json(schema_path)
    system_prompt = prompt_path.read_text(encoding="utf-8").strip()
    revision_directives = (
        _read_json(revision_directives_path)
        if revision_directives_path is not None
        else None
    )

    request_payload = {
        "task": "generate_character_saga_skeleton_v2",
        "reader_profile": {
            "exact_age": fixture.character.age,
            "audience_band": fixture.audience_band,
            "story_mode": fixture.story_mode,
            "age_rule": (
                "Premise and narrative maturity must fit exact age independently "
                "from vocabulary difficulty."
            ),
        },
        "frozen_character_world_input": fixture.model_dump(mode="json"),
        "output_contract": schema,
        "contract_rules": [
            "Match the output_contract field names and literal enums exactly.",
            "Do not invent substitute field names, enum values, or compact aliases.",
            "If a field is required by output_contract, return it even when empty.",
            "Do not return any field forbidden by output_contract."
        ],
        "requested_shape": {
            "schema": "character-saga-skeleton.v2",
            "origin": "Origin object with summary, origin_facts, formative_events, origin_relationships, unresolved_origin_questions",
            "present_situation": "PresentSituation object",
            "narrative_core": "NarrativeCore object",
            "main_saga": {
                "key": "stable_key",
                "title": "string",
                "goal": "string",
                "stakes": "string",
                "central_mystery": "string",
                "themes": "list[string]",
                "entry_anchor_keys": "list[anchor_key]",
                "resolution_anchor_key": "anchor_key",
                "anchors": "exactly 5 objects with key,title,purpose,target_state,required_for_resolution,milestone_target_count,desired_progression_modes",
                "anchor_edges": "acyclic edges with from_anchor,to_anchor,relationship,rationale and >=1 ALTERNATIVE_ROUTE",
                "hidden_truths": "2-4 HiddenTruth objects using FIXED_HIDDEN or UNRESOLVED_BY_DESIGN",
                "reveal_intents": "3-6 objects with key,truth_key,level,summary,eligibility,anchor_keys,reveal_ceiling"
            },
            "latent_side_sagas": "2-4 SideSagaSeed objects",
            "creative_permission_envelope": "CreativePermissionEnvelope object",
            "world_integration": "WorldIntegration object",
            "reweave_policy": "ReweavePolicy object",
            "background_enrichment_policy": "BackgroundEnrichmentPolicy object",
            "safety_and_constraints": "SafetyAndConstraints object"
        },
        "compactness_rules": [
            "Return exactly 5 anchors.",
            "Set milestone_target_count values so their sum is exactly 15.",
            "Do not generate individual milestone details yet.",
            "Keep each narrative field concise, normally one sentence.",
            "Do not repeat schema definitions or explain reasoning outside JSON."
        ],
        "human_revision_directives": revision_directives,
        "revision_rules": [
            "When human_revision_directives is present, satisfy every must_change requirement.",
            "Preserve preserve_strengths unless they conflict with a must_change requirement.",
            "Respect must_not_change constraints.",
            "A revised artifact is still a fresh proposal and still requires human review."
        ],
        "qualification_rules": {
            "human_creative_review_required": True,
            "milestone_expansion_forbidden_before_human_approve": True,
            "no_episode_generation": True,
            "main_saga_anchor_count": 5,
            "planned_milestone_total": 15,
            "must_include_alternative_route": True,
            "must_support_saga_dormancy": True,
            "must_support_generated_continuity": True,
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
            max_tokens=10000,
            seed=2026092803,
            request_class="saga_architect",
            max_parse_attempts=2,
        )
    except Exception as exc:
        failure = {
            "schema_version": "saga-skeleton-v2-evidence.v1",
            "status": "provider_or_parse_failure",
            "publication_authority": False,
            "fixture_id": fixture.case_id,
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

    evidence = {
        "schema_version": "saga-skeleton-v2-evidence.v1",
        "status": "generated",
        "publication_authority": False,
        "human_creative_review_required": True,
        "milestone_expansion_authorized": False,
        "fixture_id": fixture.case_id,
        "model": model,
        "model_runtime_identity": model_identity,
        "started_at": started_at,
        "completed_at": _now_iso(),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "request_payload": request_payload,
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
        skeleton = CharacterSagaSkeletonV2.model_validate(parsed)
    except ValidationError as exc:
        evidence["status"] = "contract_rejected"
        evidence["contract_errors"] = exc.errors(
            include_url=False,
            include_context=False,
            include_input=False,
        )
        _write_json(out_path, evidence)
        raise RuntimeError(
            "Saga Skeleton v2 generation failed deterministic contract validation."
        ) from exc

    evidence["status"] = "awaiting_human_review"
    evidence["skeleton"] = skeleton.model_dump(mode="json", by_alias=True)
    evidence["human_review"] = {
        "verdict": None,
        "allowed_values": ["APPROVE", "REVISE", "REJECT"],
        "assistant_independent_assessment": None,
        "milestone_expansion_authorized": False,
    }
    _write_json(out_path, evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one compact age12 Saga Skeleton v2 qualification artifact."
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model")
    parser.add_argument("--revision-directives", type=Path)
    args = parser.parse_args()

    payload = generate(
        fixture_path=args.fixture,
        prompt_path=args.prompt,
        schema_path=args.schema,
        out_path=args.out,
        model_override=args.model,
        revision_directives_path=args.revision_directives,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "fixture_id": payload["fixture_id"],
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
