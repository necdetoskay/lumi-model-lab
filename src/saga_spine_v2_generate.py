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
from src.saga_spine_v2_contract import CharacterSagaSpineV2


DEFAULT_FIXTURE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_fixture_v2.json"
)
DEFAULT_PROMPT = Path("prompts/saga_narrative_architect_v2.md")
DEFAULT_SCHEMA = Path(
    "data/specifications/saga_lab/character_saga_spine_v2.schema.json"
)
DEFAULT_OUT = Path("runs/saga-spine-v2-age12/result.json")


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
            "Missing Saga Spine architect model. Pass --model or set SAGA_SPINE_V2_MODEL."
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
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    model = _resolve_model(model_override)
    require_qualification_runtime_profile(model)
    model_runtime_identity = runtime_profile_identity(model)
    fixture = NarrativeFixture.model_validate(_read_json(fixture_path))
    # The full JSON Schema is validated locally after generation. Sending the
    # entire schema to the model made the prompt large and encouraged verbose
    # schema echoing. Keep the model contract compact and deterministic here.
    _read_json(schema_path)
    system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    request_payload = {
        "task": "generate_character_saga_spine_v2",
        "reader_profile": {
            "exact_age": fixture.character.age,
            "audience_band": fixture.audience_band,
            "story_mode": fixture.story_mode,
            "age_rule": (
                "Premise/narrative maturity must fit the exact age independently "
                "from vocabulary difficulty."
            ),
        },
        "frozen_character_world_input": fixture.model_dump(mode="json"),
        "requested_shape": {
            "schema": "character-saga-spine.v2",
            "origin": {
                "summary": "string",
                "origin_facts": "list",
                "formative_events": "list",
                "origin_relationships": "list",
                "unresolved_origin_questions": "list"
            },
            "present_situation": "object",
            "narrative_core": "object",
            "main_saga": {
                "key": "stable_key",
                "title": "string",
                "goal": "string",
                "stakes": "string",
                "central_mystery": "string",
                "themes": "list[string]",
                "entry_anchor_keys": "list[anchor_key]",
                "resolution_anchor_key": "anchor_key",
                "resolution_milestone_keys": "list[milestone_key]",
                "anchors": "exactly 5 SagaAnchor objects",
                "milestones": "exactly 15 SagaMilestone objects",
                "edges": "DAG edges over anchor/milestone keys with >=1 ALTERNATIVE_ROUTE",
                "hidden_truths": "small list using FIXED_HIDDEN and/or UNRESOLVED_BY_DESIGN",
                "reveal_steps": "small list tied to hidden_truths and milestones"
            },
            "latent_side_sagas": "2-4 SideSagaSeed objects",
            "creative_permission_envelope": "object",
            "world_integration": "object",
            "reweave_policy": "object",
            "background_enrichment_policy": "object",
            "safety_and_constraints": "object"
        },
        "compactness_rules": [
            "Generate exactly 5 anchors and exactly 15 milestones for this first qualification candidate.",
            "Keep each summary, purpose, state_condition, rationale, consequence option, and reveal ceiling concise: normally one sentence.",
            "Do not repeat the schema, explain your reasoning, or add prose outside the JSON object.",
            "Use the minimum number of graph edges needed for a meaningful reachable DAG plus real alternate routes.",
            "Prefer 2-4 hidden truths, 3-6 reveal steps, and 2-4 latent side Sagas.",
            "Do not inflate fields merely to consume token budget."
        ],
        "qualification_rules": {
            "human_creative_review_required": True,
            "no_episode_generation": True,
            "no_future_choice_precommitment": True,
            "main_saga_anchor_count": 5,
            "main_saga_milestone_count": 15,
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
            temperature=0.35,
            max_tokens=18000,
            seed=2026092802,
            request_class="saga_architect",
            max_parse_attempts=2,
        )
    except Exception as exc:
        failure = {
            "schema_version": "saga-spine-v2-evidence.v1",
            "status": "provider_or_parse_failure",
            "publication_authority": False,
            "fixture_id": fixture.case_id,
            "model": model,
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

    latency = round(time.perf_counter() - started, 3)
    evidence = {
        "schema_version": "saga-spine-v2-evidence.v1",
        "status": "generated",
        "publication_authority": False,
        "human_creative_review_required": True,
        "fixture_id": fixture.case_id,
        "model": model,
        "model_runtime_identity": model_runtime_identity,
        "started_at": started_at,
        "completed_at": _now_iso(),
        "latency_seconds": latency,
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
        spine = CharacterSagaSpineV2.model_validate(parsed)
    except ValidationError as exc:
        evidence["status"] = "contract_rejected"
        evidence["contract_errors"] = exc.errors(
            include_url=False,
            include_context=False,
            include_input=False,
        )
        _write_json(out_path, evidence)
        raise RuntimeError(
            "Saga Spine v2 generation failed deterministic contract validation."
        ) from exc

    evidence["status"] = "awaiting_human_review"
    evidence["spine"] = spine.model_dump(mode="json", by_alias=True)
    evidence["human_review"] = {
        "verdict": None,
        "allowed_values": ["APPROVE", "REVISE", "REJECT"],
        "assistant_independent_assessment": None,
    }
    _write_json(out_path, evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one Saga Spine v2 qualification artifact.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model")
    args = parser.parse_args()

    payload = generate(
        fixture_path=args.fixture,
        prompt_path=args.prompt,
        schema_path=args.schema,
        out_path=args.out,
        model_override=args.model,
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
