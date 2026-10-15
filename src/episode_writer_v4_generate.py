from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import OpenRouterCallError, call_openrouter, count_words, parse_cost, parse_usage
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_packet import build_story_authority_packet
from src.story_authority_packet_v2 import build_story_authority_packet_v2


DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_spine_revision_05_approved.json"
)
DEFAULT_PROMPT = Path("prompts/episode_writer_v2.md")
DEFAULT_OUT = Path("runs/episode-writer-v2-age12/result.json")
DEFAULT_STORY_OUT = Path("runs/episode-writer-v2-age12/story.txt")
WRITER_MODEL = "aion-labs/aion-3.5-mini"


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


def _compact_context(approved: dict[str, Any]) -> dict[str, Any]:
    projection = approved["projection"]
    return {
        "reader_profile": projection["reader_profile"],
        "session_target": projection["session_target"],
        "character": projection["character"],
        "world": {
            "world_type": projection["world"]["world_type"],
            "era": projection["world"]["era"],
            "habitat": projection["world"]["habitat"],
            "technology_level": projection["world"]["technology_level"],
            "magic_level": projection["world"]["magic_level"],
            "summary": projection["world"]["summary"],
            "location_access": projection["world"]["location_access"],
            "social_context": projection["world"]["social_context"],
            "known_world_facts": projection["world"]["known_world_facts"],
        },
        "main_saga_public": projection["main_saga_public"],
        "eligible_main_saga_milestones": projection["eligible_main_saga_milestones"],
        "active_side_sagas": projection.get("active_side_sagas", []),
        "recent_episode_summaries": projection.get("recent_episode_summaries", []),
        "creative_permission_envelope": projection["creative_permission_envelope"],
    }


def build_writer_input(
    approved: dict[str, Any],
    *,
    authority_packet_version: str = "v1",
) -> dict[str, Any]:
    spine = approved["episode_spine"]
    if authority_packet_version == "v1":
        authority_packet = build_story_authority_packet(approved)
    elif authority_packet_version == "v2":
        authority_packet = build_story_authority_packet_v2(approved)
    else:
        raise RuntimeError("Unsupported authority packet version.")
    return {
        "task": "write_episode_from_v4_luna_accepted_spine",
        "source_spine_run_id": approved["source_run_id"],
        "model_creative_review": approved["model_creative_review"],
        "approved_premise": approved["approved_premise"]["premise"],
        "context": _compact_context(approved),
        "authority_packet": authority_packet,
        "authority_packet_version": authority_packet_version,
        "episode_spine": spine,
        "hard_rules": {
            "one_writer_call_only": True,
            "editor_call_forbidden": True,
            "judge_call_forbidden": True,
            "repair_call_forbidden": True,
            "translation_call_forbidden": True,
            "writer_must_choose_exactly_one_decision_branch": True,
            "saga_unknowns_must_remain_unresolved": True,
        },
    }


def _validate_source(approved: dict[str, Any]) -> None:
    if approved.get("schema_version") != "episode-spine-v4-model-reviewed.v1":
        raise RuntimeError("V4 writer requires model-reviewed artifact; V3 human approval cannot be impersonated.")
    review=approved.get("model_creative_review") or {}
    if (review.get("model")!="openai/gpt-5.6-luna" or review.get("verdict")!="ACCEPT"
            or review.get("automated") is not True
            or not isinstance(review.get("source_spine_sha256"),str)):
        raise RuntimeError("V4 independent creative approval evidence missing.")
    if (approved.get("human_review") or {}).get("verdict") == "APPROVE":
        raise RuntimeError("Never forge human review for automated V4.")
    if (approved.get("gate") or {}).get("decision") != "ACCEPT":
        raise RuntimeError("Episode Spine gate must be ACCEPT before writer execution.")
    spine = approved.get("episode_spine")
    if not isinstance(spine, dict):
        raise RuntimeError("Approved artifact is missing episode_spine.")
    if int(spine.get("target_words_min") or 0) <= 0:
        raise RuntimeError("Invalid target_words_min.")
    if int(spine.get("target_words_max") or 0) < int(spine["target_words_min"]):
        raise RuntimeError("Invalid target word range.")


def _combined_rollup(
    approved: dict[str, Any],
    writer_call: dict[str, Any],
) -> dict[str, Any]:
    source = approved.get("source_usage_rollup") or {}
    calls = list(source.get("calls") or [])
    calls.append(writer_call)
    return rollup_model_calls(calls)


def generate(
    *,
    approved_path: Path,
    prompt_path: Path,
    out_path: Path,
    story_out_path: Path,
    api_key: str | None = None,
    authority_packet_version: str = "v1",
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    approved = _read_json(approved_path)
    _validate_source(approved)

    # Intentional hard boundary for this proof: one writer model, one paid generation call.
    writer_model = WRITER_MODEL
    require_qualification_runtime_profile(writer_model)

    spine = approved["episode_spine"]
    writer_input = build_writer_input(
        approved, authority_packet_version=authority_packet_version
    )

    system_prompt = prompt_path.read_text(encoding="utf-8").strip()
    started = time.perf_counter()
    started_at = _now_iso()
    call_started = time.perf_counter()

    try:
        story, body, request = call_openrouter(
            api_key=key,
            model=writer_model,
            system_prompt=system_prompt,
            user_prompt=json.dumps(writer_input, ensure_ascii=False),
            temperature=0.72,
            max_tokens=None,
            seed=2026092901,
            request_class="teacher_story_medium_reasoning",
            structured_output=False,
        )
    except OpenRouterCallError as exc:
        writer_latency = round(time.perf_counter() - call_started, 3)
        trace = getattr(exc, "trace", None) or {}
        raw_usage = trace.get("raw_usage") or {}
        cost = trace.get("cost") or {}
        usage = trace.get("usage") or {}
        failure_call = normalize_model_call(
            stage="episode_writer",
            model=writer_model,
            provider=runtime_profile_identity(writer_model).get("provider"),
            raw_usage=raw_usage,
            cost=cost,
            latency_seconds=writer_latency,
            status="failed",
        )
        writer_rollup = rollup_model_calls([failure_call])
        pipeline_rollup = _combined_rollup(approved, failure_call)
        evidence = {
            "schema_version": "episode-writer-v2-evidence.v1",
            "status": "writer_provider_failure",
            "source_spine_run_id": approved["source_run_id"],
            "model_creative_review": approved["model_creative_review"],
            "writer_model": writer_model,
            "writer_runtime_identity": runtime_profile_identity(writer_model),
            "started_at": started_at,
            "completed_at": _now_iso(),
            "latency_seconds": round(time.perf_counter() - started, 3),
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "stage": trace.get("stage"),
                "finish_reason": trace.get("finish_reason"),
                "generation_id": (trace.get("body") or {}).get("id"),
            },
            "writer_call": {
                "raw_usage": raw_usage,
                "usage": usage,
                "cost": cost,
                "latency_seconds": writer_latency,
            },
            "writer_usage_rollup": writer_rollup,
            "pipeline_usage_rollup": pipeline_rollup,
            "writer_cost_usd": writer_rollup["totals"]["cost_usd"],
            "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
            "next_stage_authorized": False,
            "next_stage_note": "Writer failed; no editor, judge, repair, or translation call was made.",
        }
        _write_json(out_path, evidence)
        raise

    writer_latency = round(time.perf_counter() - call_started, 3)
    words = count_words(story)
    title = next((line.strip() for line in story.splitlines() if line.strip()), "")
    min_words = int(spine["target_words_min"])
    max_words = int(spine["target_words_max"])

    writer_call = normalize_model_call(
        stage="episode_writer",
        model=writer_model,
        provider=runtime_profile_identity(writer_model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=writer_latency,
    )
    writer_rollup = rollup_model_calls([writer_call])
    pipeline_rollup = _combined_rollup(approved, writer_call)

    deterministic_checks = {
        "non_empty": bool(story.strip()),
        "title_present": bool(title),
        "word_count": words,
        "target_words_min": min_words,
        "target_words_max": max_words,
        "length_pass": min_words <= words <= max_words,
    }

    evidence = {
        "schema_version": "episode-writer-v2-evidence.v1",
        "status": (
            "writer_generated"
            if all(
                [
                    deterministic_checks["non_empty"],
                    deterministic_checks["title_present"],
                    deterministic_checks["length_pass"],
                ]
            )
            else "writer_generated_deterministic_check_failed"
        ),
        "source_spine_run_id": approved["source_run_id"],
        "model_creative_review": approved["model_creative_review"],
        "writer_model": writer_model,
        "writer_runtime_identity": runtime_profile_identity(writer_model),
        "started_at": started_at,
        "completed_at": _now_iso(),
        "latency_seconds": round(time.perf_counter() - started, 3),
        "deterministic_checks": deterministic_checks,
        "story": story,
        "writer_call": {
            "raw_usage": body.get("usage") or {},
            "usage": parse_usage(body).model_dump(mode="json"),
            "cost": parse_cost(body).model_dump(mode="json"),
            "latency_seconds": writer_latency,
            "request": {
                "temperature": request.get("temperature"),
                "max_tokens": request.get("max_tokens"),
                "reasoning": request.get("reasoning"),
                "response_format": request.get("response_format"),
            },
        },
        "writer_usage_rollup": writer_rollup,
        "pipeline_usage_rollup": pipeline_rollup,
        "writer_cost_usd": writer_rollup["totals"]["cost_usd"],
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "next_stage_authorized": False,
        "next_stage_note": "No editor, judge, repair, or translation call was authorized in this run.",
    }

    _write_json(out_path, evidence)
    story_out_path.parent.mkdir(parents=True, exist_ok=True)
    story_out_path.write_text(story.rstrip() + "\n", encoding="utf-8")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write one V4 episode from independently Luna-reviewed Episode Spine."
    )
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--story-out", type=Path, default=DEFAULT_STORY_OUT)
    parser.add_argument("--authority-packet-version", choices=["v1", "v2"], default="v1")
    args = parser.parse_args()

    result = generate(
        approved_path=args.approved,
        prompt_path=args.prompt,
        out_path=args.out,
        story_out_path=args.story_out,
        authority_packet_version=args.authority_packet_version,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "writer_model": result["writer_model"],
                "word_count": result["deterministic_checks"]["word_count"],
                "length_pass": result["deterministic_checks"]["length_pass"],
                "writer_usage": result["writer_usage_rollup"]["totals"],
                "pipeline_usage": result["pipeline_usage_rollup"]["totals"],
                "next_stage_authorized": result["next_stage_authorized"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
