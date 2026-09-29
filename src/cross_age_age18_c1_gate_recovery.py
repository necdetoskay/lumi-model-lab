from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.cross_age_spine_safe_normalize import normalize_logistics_location_sequence
from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_v2_contract import EpisodeSpineGateV2, EpisodeSpineV2
from src.episode_spine_v2_generate import _model_call_evidence
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/"
    "sonnet55_cross_age_age18_c1_recovery_source_36608347735.json"
)
DEFAULT_PROMPT = Path("prompts/episode_spine_gate_v2.md")
DEFAULT_OUT = Path("runs/sonnet55-cross-age-age18-c1-recovery/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _inherited_architect_call(source: dict[str, Any]) -> dict[str, Any]:
    call = source["architect_call"]
    return normalize_model_call(
        stage="episode_spine_architect",
        model=source["architect_model"],
        provider=runtime_profile_identity(source["architect_model"]).get("provider"),
        raw_usage=call.get("raw_usage") or {},
        cost=call.get("cost") or {},
        latency_seconds=call.get("latency_seconds"),
    )


def validate_normalized_candidate(
    source: dict[str, Any],
    raw: dict[str, Any],
) -> EpisodeSpineV2:
    spine = EpisodeSpineV2.model_validate(raw)
    premise = source["approved_premise"]["premise"]
    projection = source["projection"]
    session = projection["session_target"]

    if spine.premise_key != premise["key"]:
        raise RuntimeError("premise_key mismatch")
    if spine.exact_age != 18:
        raise RuntimeError("exact_age must be 18")
    if spine.session != session["name"]:
        raise RuntimeError("session mismatch")
    if spine.target_words_min != session["target_words_min"]:
        raise RuntimeError("target_words_min mismatch")
    if spine.target_words_max != session["target_words_max"]:
        raise RuntimeError("target_words_max mismatch")

    allowed = set(premise["location_refs"])
    used = {beat.location_ref for beat in spine.beats}
    if not used.issubset(allowed):
        raise RuntimeError("candidate uses location outside controlled premise")

    eligible = {
        row["key"] for row in projection["eligible_main_saga_milestones"]
    }
    intended = sorted(set(premise["target_refs"]) & eligible)
    if set(spine.saga_progression.intended_milestone_keys) != set(intended):
        raise RuntimeError("intended milestone mismatch")

    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY",
        "MAIN_SAGA_PROGRESS",
        "MIXED",
    }:
        raise RuntimeError("Main Saga target requires a Main Saga role")

    return spine


def run(
    *,
    source_path: Path,
    prompt_path: Path,
    out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read(source_path)
    if source.get("schema_version") != "sonnet55-cross-age-age18-c1-recovery-source.v1":
        raise RuntimeError("Recovery source schema mismatch.")

    normalized, repairs = normalize_logistics_location_sequence(
        source["architect_raw_payload"]
    )
    if len(repairs) != 3:
        raise RuntimeError(f"Expected exactly 3 safe location repairs, got {len(repairs)}")

    spine = validate_normalized_candidate(source, normalized)
    gate_model = str(source["gate_model"])
    require_qualification_runtime_profile(gate_model)

    gate_input = {
        "task": "evaluate_cross_age_age18_episode_spine",
        "approved_premise": source["approved_premise"]["premise"],
        "premise_context": source["projection"],
        "episode_spine": spine.model_dump(mode="json", by_alias=True),
        "output_contract": EpisodeSpineGateV2.model_json_schema(by_alias=True),
        "decision_rule": (
            "ACCEPT only if this exact-age-18 spine is mature, causally coherent, "
            "professionally consequential, branch-executable, and safe to hand to "
            "the writer; otherwise REPLAN."
        ),
    }

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    started = time.perf_counter()
    gate_raw, gate_body, gate_request, parse_failures = call_structured_json_with_retry(
        api_key=key,
        model=gate_model,
        system_prompt=prompt,
        user_prompt=json.dumps(gate_input, ensure_ascii=False),
        temperature=0.10,
        max_tokens=6000,
        seed=2026092940,
        request_class="editorial_audit",
        max_parse_attempts=2,
    )
    latency = round(time.perf_counter() - started, 3)
    gate = EpisodeSpineGateV2.model_validate(gate_raw)

    gate_call_raw = _model_call_evidence(
        gate_body,
        gate_request,
        latency_seconds=latency,
    )
    gate_call = normalize_model_call(
        stage="episode_spine_gate",
        model=gate_model,
        provider=runtime_profile_identity(gate_model).get("provider"),
        raw_usage=gate_call_raw.get("raw_usage") or {},
        cost=gate_call_raw.get("cost") or {},
        latency_seconds=latency,
    )
    architect_call = _inherited_architect_call(source)
    incremental = rollup_model_calls([gate_call])
    combined = rollup_model_calls([architect_call, gate_call])

    result = {
        "schema_version": "sonnet55-cross-age-age18-c1-recovery-evidence.v1",
        "status": "awaiting_human_review",
        "source_run_id": source["source_run_id"],
        "architect_model": source["architect_model"],
        "gate_model": gate_model,
        "safe_normalization": {
            "applied": True,
            "repairs": repairs,
            "semantic_fields_changed": False,
        },
        "approved_premise": source["approved_premise"],
        "projection": source["projection"],
        "episode_spine": spine.model_dump(mode="json", by_alias=True),
        "gate": gate.model_dump(mode="json", by_alias=True),
        "gate_raw_payload": gate_raw,
        "gate_parse_failures": parse_failures,
        "gate_call": gate_call_raw,
        "incremental_gate_usage_rollup": incremental,
        "candidate_pipeline_usage_rollup": combined,
        "incremental_gate_cost_usd": incremental["totals"]["cost_usd"],
        "candidate_pipeline_cost_usd": combined["totals"]["cost_usd"],
        "human_review": {
            "required": True,
            "verdict": None,
            "episode_writer_authorized": False,
        },
    }
    _write(out_path, result)
    print(json.dumps({
        "status": result["status"],
        "gate_decision": result["gate"]["decision"],
        "incremental_gate_cost_usd": result["incremental_gate_cost_usd"],
        "candidate_pipeline_cost_usd": result["candidate_pipeline_cost_usd"],
        "episode_writer_authorized": False,
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(source_path=args.source, prompt_path=args.prompt, out_path=args.out)


if __name__ == "__main__":
    main()
