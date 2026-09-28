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
from src.episode_spine_v2_contract import EpisodeSpineGateV2, EpisodeSpineV2
from src.generate import parse_cost, parse_usage
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.premise_architect_v2_contract import (
    PremiseLabStateV1,
    build_reveal_safe_premise_projection,
)
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2


DEFAULT_SPINE = Path(
    "data/specifications/saga_lab/age12_shattered_meridian_gate_b_approved_v1.json"
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
DEFAULT_PREMISE = Path(
    "data/specifications/story_lab/age12_shattered_meridian_episode1_premise_approved_v1.json"
)
DEFAULT_ARCHITECT_PROMPT = Path("prompts/episode_spine_architect_v2.md")
DEFAULT_GATE_PROMPT = Path("prompts/episode_spine_gate_v2.md")
DEFAULT_OUT = Path("runs/episode-spine-v2-age12/result.json")


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


def _provider_block_reason(exc: Exception) -> str | None:
    trace = getattr(exc, "trace", None)
    if not isinstance(trace, dict):
        return None

    status_code = trace.get("status_code")
    error_body = trace.get("error_body") or {}
    message = str(error_body.get("error", {}).get("message", ""))
    code = error_body.get("error", {}).get("code")

    if status_code == 403 and (
        "monthly limit" in message.lower()
        or "key limit exceeded" in message.lower()
    ):
        return "OPENROUTER_KEY_MONTHLY_LIMIT_EXCEEDED"
    return None


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


def _resolve_model(override: str | None, env_name: str, default: str) -> str:
    return override or os.getenv(env_name) or default


def generate(
    *,
    spine_path: Path,
    reader_path: Path,
    fixture_path: Path,
    state_path: Path,
    premise_path: Path,
    architect_prompt_path: Path,
    gate_prompt_path: Path,
    out_path: Path,
    architect_model_override: str | None = None,
    gate_model_override: str | None = None,
    api_key: str | None = None,
    revision_feedback_path: Path | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    architect_model = _resolve_model(
        architect_model_override,
        "EPISODE_SPINE_ARCHITECT_MODEL",
        "anthropic/claude-sonnet-5",
    )
    gate_model = _resolve_model(
        gate_model_override,
        "EPISODE_SPINE_GATE_MODEL",
        "openai/gpt-5.6-luna",
    )
    require_qualification_runtime_profile(architect_model)
    require_qualification_runtime_profile(gate_model)

    saga = CharacterSagaSpineV2.model_validate(_read_json(spine_path))
    reader = ReaderDevelopmentProfileV2.model_validate(_read_json(reader_path))
    fixture = NarrativeFixture.model_validate(_read_json(fixture_path))
    state = PremiseLabStateV1.model_validate(_read_json(state_path))
    premise_artifact = _read_json(premise_path)
    premise = premise_artifact["premise"]

    projection = build_reveal_safe_premise_projection(
        spine=saga,
        reader=reader,
        fixture=fixture,
        state=state,
    )

    eligible_main = {
        row["key"] for row in projection["eligible_main_saga_milestones"]
    }
    intended_milestones = sorted(set(premise["target_refs"]) & eligible_main)

    session = projection["session_target"]
    allowed_locations = set(premise["location_refs"])
    accessible_locations = {
        row["key"]
        for row in projection["world"]["location_access"]
        if row["status"] == "AVAILABLE" and row["premise_usage"] == "FULL"
    }
    if not allowed_locations.issubset(accessible_locations):
        raise RuntimeError(
            "approved premise contains currently inaccessible locations: "
            + ", ".join(sorted(allowed_locations - accessible_locations))
        )

    revision_feedback = (
        _read_json(revision_feedback_path)
        if revision_feedback_path is not None
        else None
    )

    architect_input = {
        "task": (
            "revise_episode_spine_from_independent_feedback"
            if revision_feedback is not None
            else "build_episode_spine_from_approved_premise"
        ),
        "approved_premise": premise,
        "revision_feedback": revision_feedback,
        "premise_context": projection,
        "required_intended_milestone_keys": intended_milestones,
        "allowed_location_refs": sorted(allowed_locations),
        "required_session": {
            "name": session["name"],
            "target_words_min": session["target_words_min"],
            "target_words_max": session["target_words_max"],
        },
        "output_contract": EpisodeSpineV2.model_json_schema(by_alias=True),
        "hard_rules": {
            "prose_generation_forbidden": True,
            "approved_premise_must_remain_intact": True,
            "future_choice_precommitment_forbidden": True,
            "milestone_commit_forbidden": True,
            "hidden_truth_inference_forbidden": True,
            "human_review_required": True,
        },
    }

    started = time.perf_counter()
    started_at = _now_iso()
    architect_prompt = architect_prompt_path.read_text(encoding="utf-8").strip()
    gate_prompt = gate_prompt_path.read_text(encoding="utf-8").strip()

    try:
        raw, body, request, parse_failures = call_structured_json_with_retry(
            api_key=key,
            model=architect_model,
            system_prompt=architect_prompt,
            user_prompt=json.dumps(architect_input, ensure_ascii=False),
            temperature=0.35,
            max_tokens=12000,
            seed=2026092807,
            request_class="saga_architect",
            max_parse_attempts=2,
        )
    except Exception as exc:
        provider_block_reason = _provider_block_reason(exc)
        evidence = {
            "schema_version": "episode-spine-v2-evidence.v1",
            "status": "provider_limit_blocked" if provider_block_reason else "architect_failure",
            "episode_writer_authorized": False,
            "started_at": started_at,
            "completed_at": _now_iso(),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "architect_model": architect_model,
            "gate_model": gate_model,
            "architect_input": architect_input,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "trace": getattr(exc, "trace", None),
            },
        }
        if provider_block_reason:
            evidence["provider_block_reason"] = provider_block_reason
        _write_json(out_path, evidence)
        raise

    evidence: dict[str, Any] = {
        "schema_version": "episode-spine-v2-evidence.v1",
        "status": "architect_generated",
        "episode_writer_authorized": False,
        "human_creative_review_required": True,
        "started_at": started_at,
        "architect_model": architect_model,
        "gate_model": gate_model,
        "architect_runtime_identity": runtime_profile_identity(architect_model),
        "gate_runtime_identity": runtime_profile_identity(gate_model),
        "approved_premise": premise_artifact,
        "projection": projection,
        "architect_raw_payload": raw,
        "architect_parse_failures": parse_failures,
        "architect_call": _model_call_evidence(body, request),
    }

    try:
        episode_spine = EpisodeSpineV2.model_validate(raw)
        if episode_spine.premise_key != premise["key"]:
            raise ValueError("Episode Spine premise_key mismatch")
        if episode_spine.exact_age != reader.exact_age:
            raise ValueError("Episode Spine exact_age mismatch")
        if episode_spine.session != session["name"]:
            raise ValueError("Episode Spine session mismatch")
        if episode_spine.target_words_min != session["target_words_min"]:
            raise ValueError("Episode Spine target_words_min mismatch")
        if episode_spine.target_words_max != session["target_words_max"]:
            raise ValueError("Episode Spine target_words_max mismatch")

        used_locations = {beat.location_ref for beat in episode_spine.beats}
        if not used_locations.issubset(allowed_locations):
            raise ValueError(
                "Episode Spine uses location outside approved premise: "
                + ", ".join(sorted(used_locations - allowed_locations))
            )

        actual_intended = set(
            episode_spine.saga_progression.intended_milestone_keys
        )
        if actual_intended != set(intended_milestones):
            raise ValueError(
                "Episode Spine intended Saga milestones differ from approved premise context"
            )

        if intended_milestones and episode_spine.episode_role not in {
            "MAIN_SAGA_ENTRY",
            "MAIN_SAGA_PROGRESS",
            "MIXED",
        }:
            raise ValueError(
                "Episode Spine targeting Main Saga milestone needs Main Saga episode role"
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
        raise RuntimeError("Episode Spine Architect failed contract validation.") from exc

    gate_input = {
        "task": "evaluate_episode_spine",
        "approved_premise": premise,
        "premise_context": projection,
        "episode_spine": episode_spine.model_dump(mode="json", by_alias=True),
        "output_contract": EpisodeSpineGateV2.model_json_schema(by_alias=True),
        "decision_rule": "ACCEPT only if writer execution is justified; otherwise REPLAN.",
    }

    try:
        gate_raw, gate_body, gate_request, gate_parse_failures = (
            call_structured_json_with_retry(
                api_key=key,
                model=gate_model,
                system_prompt=gate_prompt,
                user_prompt=json.dumps(gate_input, ensure_ascii=False),
                temperature=0.10,
                max_tokens=6000,
                seed=2026092808,
                request_class="editorial_audit",
                max_parse_attempts=2,
            )
        )
    except Exception as exc:
        evidence["status"] = "gate_failure"
        evidence["episode_spine"] = episode_spine.model_dump(
            mode="json", by_alias=True
        )
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
        gate = EpisodeSpineGateV2.model_validate(gate_raw)
    except ValidationError as exc:
        evidence["status"] = "gate_contract_rejected"
        evidence["episode_spine"] = episode_spine.model_dump(
            mode="json", by_alias=True
        )
        evidence["contract_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "details": exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            ),
        }
        evidence["completed_at"] = _now_iso()
        evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
        _write_json(out_path, evidence)
        raise RuntimeError("Episode Spine Gate failed contract validation.") from exc

    evidence["status"] = "awaiting_human_review"
    evidence["episode_spine"] = episode_spine.model_dump(
        mode="json", by_alias=True
    )
    evidence["gate"] = gate.model_dump(mode="json", by_alias=True)
    evidence["total_cost_usd"] = round(
        float(evidence["architect_call"]["cost"]["usd"] or 0.0)
        + float(evidence["gate_call"]["cost"]["usd"] or 0.0),
        9,
    )
    evidence["completed_at"] = _now_iso()
    evidence["latency_seconds"] = round(time.perf_counter() - started, 3)
    evidence["human_review"] = {
        "verdict": None,
        "allowed_values": ["APPROVE", "REVISE", "REJECT"],
        "assistant_independent_assessment": None,
        "episode_writer_authorized": False,
    }
    _write_json(out_path, evidence)
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and gate one Episode Spine v2 from an approved premise."
    )
    parser.add_argument("--spine", type=Path, default=DEFAULT_SPINE)
    parser.add_argument("--reader", type=Path, default=DEFAULT_READER)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--premise", type=Path, default=DEFAULT_PREMISE)
    parser.add_argument(
        "--architect-prompt",
        type=Path,
        default=DEFAULT_ARCHITECT_PROMPT,
    )
    parser.add_argument("--gate-prompt", type=Path, default=DEFAULT_GATE_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--architect-model")
    parser.add_argument("--gate-model")
    parser.add_argument("--revision-feedback", type=Path)
    args = parser.parse_args()

    payload = generate(
        spine_path=args.spine,
        reader_path=args.reader,
        fixture_path=args.fixture,
        state_path=args.state,
        premise_path=args.premise,
        architect_prompt_path=args.architect_prompt,
        gate_prompt_path=args.gate_prompt,
        out_path=args.out,
        architect_model_override=args.architect_model,
        gate_model_override=args.gate_model,
        revision_feedback_path=args.revision_feedback,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "architect_model": payload["architect_model"],
                "gate_model": payload["gate_model"],
                "gate_decision": payload["gate"]["decision"],
                "latency_seconds": payload["latency_seconds"],
                "total_cost_usd": payload["total_cost_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
