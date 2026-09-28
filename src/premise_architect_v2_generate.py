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
from src.premise_architect_v2_contract import (
    PremiseCandidateBatchV2,
    PremiseGateV2,
    PremiseLabStateV1,
    build_premise_gate_protected_context,
    build_reveal_safe_premise_projection,
)
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2


DEFAULT_SPINE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_full_spine_v1.json"
)
DEFAULT_READER = Path(
    "data/specifications/reader_profiles/age12_adventure_v2.json"
)
DEFAULT_FIXTURE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_fixture_v2.json"
)
DEFAULT_STATE = Path(
    "data/specifications/story_lab/age12_shattered_meridian_initial_state_v1.json"
)
DEFAULT_ARCHITECT_PROMPT = Path("prompts/premise_architect_v2.md")
DEFAULT_GATE_PROMPT = Path("prompts/premise_gate_v2.md")
DEFAULT_OUT = Path("runs/premise-v2-age12/result.json")


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


def _resolve_model(override: str | None, env_name: str, default: str) -> str:
    return override or os.getenv(env_name) or default


def _model_call_evidence(body: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_usage": body.get("usage") or {},
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
    }


def generate(
    *,
    spine_path: Path,
    reader_path: Path,
    fixture_path: Path,
    state_path: Path,
    architect_prompt_path: Path,
    gate_prompt_path: Path,
    out_path: Path,
    architect_model_override: str | None = None,
    gate_model_override: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    architect_model = _resolve_model(
        architect_model_override,
        "PREMISE_ARCHITECT_MODEL",
        "anthropic/claude-sonnet-5",
    )
    gate_model = _resolve_model(
        gate_model_override,
        "PREMISE_GATE_MODEL",
        "openai/gpt-5.6-luna",
    )
    require_qualification_runtime_profile(architect_model)
    require_qualification_runtime_profile(gate_model)

    spine = CharacterSagaSpineV2.model_validate(_read_json(spine_path))
    reader = ReaderDevelopmentProfileV2.model_validate(_read_json(reader_path))
    fixture = NarrativeFixture.model_validate(_read_json(fixture_path))
    state = PremiseLabStateV1.model_validate(_read_json(state_path))

    if fixture.character.age != reader.exact_age:
        raise RuntimeError(
            f"reader/fixture age mismatch: {reader.exact_age} != {fixture.character.age}"
        )

    projection = build_reveal_safe_premise_projection(
        spine=spine,
        reader=reader,
        fixture=fixture,
        state=state,
    )

    protected_gate_context = build_premise_gate_protected_context(
        spine=spine,
        state=state,
    )

    eligible_main = {
        row["key"] for row in projection["eligible_main_saga_milestones"]
    }
    active_side = {
        row["key"] for row in projection["active_side_sagas"]
    }
    available_target_refs = sorted(
        eligible_main
        | active_side
        | {"WORLD_EXPLORATION", "SAGA_FREE"}
    )
    location_access = {
        row["key"]: row
        for row in projection["world"]["location_access"]
    }
    available_location_refs = sorted(
        key
        for key, row in location_access.items()
        if row["status"] == "AVAILABLE" and row["premise_usage"] == "FULL"
    )

    started = time.perf_counter()
    started_at = _now_iso()
    architect_prompt = architect_prompt_path.read_text(encoding="utf-8").strip()
    gate_prompt = gate_prompt_path.read_text(encoding="utf-8").strip()

    architect_input = {
        "task": "generate_three_materially_different_episode_premises",
        "premise_context": projection,
        "available_target_refs": available_target_refs,
        "available_primary_location_refs": available_location_refs,
        "location_access_policy": projection["world"]["location_access"],
        "output_contract": PremiseCandidateBatchV2.model_json_schema(by_alias=True),
        "hard_rules": {
            "exactly_three_candidates": True,
            "episode_prose_forbidden": True,
            "future_choice_precommitment_forbidden": True,
            "hidden_truth_inference_forbidden": True,
            "main_saga_progression_optional": True,
            "human_review_required": True,
        },
    }

    try:
        architect_raw, architect_body, architect_request, architect_parse_failures = (
            call_structured_json_with_retry(
                api_key=key,
                model=architect_model,
                system_prompt=architect_prompt,
                user_prompt=json.dumps(architect_input, ensure_ascii=False),
                temperature=0.55,
                max_tokens=9000,
                seed=2026092805,
                request_class="story_planning",
                max_parse_attempts=2,
            )
        )
    except Exception as exc:
        failure = {
            "schema_version": "premise-v2-evidence.v1",
            "status": "architect_failure",
            "publication_authority": False,
            "episode_spine_authorized": False,
            "started_at": started_at,
            "completed_at": _now_iso(),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "architect_model": architect_model,
            "gate_model": gate_model,
            "projection": projection,
            "architect_input": architect_input,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "trace": getattr(exc, "trace", None),
            },
        }
        _write_json(out_path, failure)
        raise

    evidence: dict[str, Any] = {
        "schema_version": "premise-v2-evidence.v1",
        "status": "architect_generated",
        "publication_authority": False,
        "episode_spine_authorized": False,
        "human_creative_review_required": True,
        "started_at": started_at,
        "architect_model": architect_model,
        "gate_model": gate_model,
        "architect_runtime_identity": runtime_profile_identity(architect_model),
        "gate_runtime_identity": runtime_profile_identity(gate_model),
        "projection": projection,
        "available_target_refs": available_target_refs,
        "protected_gate_context_present": True,
        "architect_raw_payload": architect_raw,
        "architect_parse_failures": architect_parse_failures,
        "architect_call": _model_call_evidence(
            architect_body,
            architect_request,
        ),
    }

    try:
        batch = PremiseCandidateBatchV2.model_validate(architect_raw)
        for candidate in batch.candidates:
            unknown = sorted(set(candidate.target_refs) - set(available_target_refs))
            if unknown:
                raise ValueError(
                    f"{candidate.key}: unknown/unavailable target refs: "
                    + ", ".join(unknown)
                )
            unknown_locations = sorted(
                set(candidate.location_refs) - set(location_access)
            )
            if unknown_locations:
                raise ValueError(
                    f"{candidate.key}: unknown location refs: "
                    + ", ".join(unknown_locations)
                )
            locked_locations = [
                ref
                for ref in candidate.location_refs
                if location_access[ref]["status"] != "AVAILABLE"
                or location_access[ref]["premise_usage"] != "FULL"
            ]
            if locked_locations:
                raise ValueError(
                    f"{candidate.key}: premise uses locked/non-FULL locations as active locations: "
                    + ", ".join(sorted(locked_locations))
                )
            if candidate.saga_progression_required:
                if not (set(candidate.target_refs) & eligible_main):
                    raise ValueError(
                        f"{candidate.key}: saga_progression_required requires an eligible Main Saga milestone target"
                    )
    except (ValidationError, ValueError) as exc:
        evidence["status"] = "architect_contract_rejected"
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
        evidence["completed_at"] = _now_iso()
        evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(out_path, evidence)
        raise RuntimeError("Premise Architect output failed contract validation.") from exc

    gate_input = {
        "task": "evaluate_premise_candidates",
        "premise_context": projection,
        "protected_judge_context": protected_gate_context,
        "candidates": batch.model_dump(mode="json", by_alias=True),
        "output_contract": PremiseGateV2.model_json_schema(by_alias=True),
        "selection_rule": "ACCEPT one genuinely strong candidate or REJECT_ALL; never select the least bad option.",
        "protected_context_rule": "Use protected_judge_context only to detect violations. Never reward a candidate for matching hidden truth and never treat hidden truth as information available to the character.",
    }

    try:
        gate_raw, gate_body, gate_request, gate_parse_failures = (
            call_structured_json_with_retry(
                api_key=key,
                model=gate_model,
                system_prompt=gate_prompt,
                user_prompt=json.dumps(gate_input, ensure_ascii=False),
                temperature=0.10,
                max_tokens=6500,
                seed=2026092806,
                request_class="editorial_audit",
                max_parse_attempts=2,
            )
        )
    except Exception as exc:
        evidence["status"] = "gate_failure"
        evidence["batch"] = batch.model_dump(mode="json", by_alias=True)
        evidence["gate_input"] = gate_input
        evidence["failure"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "trace": getattr(exc, "trace", None),
        }
        evidence["completed_at"] = _now_iso()
        evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(out_path, evidence)
        raise

    evidence["gate_raw_payload"] = gate_raw
    evidence["gate_parse_failures"] = gate_parse_failures
    evidence["gate_call"] = _model_call_evidence(gate_body, gate_request)

    try:
        gate = PremiseGateV2.model_validate(gate_raw)
        candidate_keys = {item.key for item in batch.candidates}
        evaluation_keys = {item.candidate_key for item in gate.evaluations}
        if evaluation_keys != candidate_keys:
            raise ValueError(
                "gate must evaluate every candidate exactly once; "
                f"candidates={sorted(candidate_keys)}, evaluations={sorted(evaluation_keys)}"
            )
        if gate.selected_candidate_key is not None:
            if gate.selected_candidate_key not in candidate_keys:
                raise ValueError("gate selected unknown premise candidate")
    except (ValidationError, ValueError) as exc:
        evidence["status"] = "gate_contract_rejected"
        evidence["batch"] = batch.model_dump(mode="json", by_alias=True)
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
        evidence["completed_at"] = _now_iso()
        evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(out_path, evidence)
        raise RuntimeError("Premise Gate output failed contract validation.") from exc

    total_cost = round(
        float(evidence["architect_call"]["cost"]["usd"] or 0.0)
        + float(evidence["gate_call"]["cost"]["usd"] or 0.0),
        9,
    )

    evidence["status"] = "awaiting_human_review"
    evidence["batch"] = batch.model_dump(mode="json", by_alias=True)
    evidence["gate"] = gate.model_dump(mode="json", by_alias=True)
    evidence["total_cost_usd"] = total_cost
    evidence["completed_at"] = _now_iso()
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["human_review"] = {
        "verdict": None,
        "allowed_values": ["APPROVE", "REVISE", "REJECT"],
        "selected_candidate_key": None,
        "assistant_independent_assessment": None,
        "episode_spine_authorized": False,
    }
    _write_json(out_path, evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and gate three reveal-safe Episode premise candidates."
    )
    parser.add_argument("--spine", type=Path, default=DEFAULT_SPINE)
    parser.add_argument("--reader", type=Path, default=DEFAULT_READER)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument(
        "--architect-prompt",
        type=Path,
        default=DEFAULT_ARCHITECT_PROMPT,
    )
    parser.add_argument("--gate-prompt", type=Path, default=DEFAULT_GATE_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--architect-model")
    parser.add_argument("--gate-model")
    args = parser.parse_args()

    payload = generate(
        spine_path=args.spine,
        reader_path=args.reader,
        fixture_path=args.fixture,
        state_path=args.state,
        architect_prompt_path=args.architect_prompt,
        gate_prompt_path=args.gate_prompt,
        out_path=args.out,
        architect_model_override=args.architect_model,
        gate_model_override=args.gate_model,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "architect_model": payload["architect_model"],
                "gate_model": payload["gate_model"],
                "gate_decision": payload["gate"]["decision"],
                "selected_candidate_key": payload["gate"]["selected_candidate_key"],
                "latency_seconds": payload["latency_seconds"],
                "total_cost_usd": payload["total_cost_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
