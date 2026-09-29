from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_v2_contract import EpisodeSpineGateV2, EpisodeSpineV2
from src.episode_spine_v2_generate import _model_call_evidence
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.sonnet55_spine_safe_normalize import normalize_reversal_support_refs

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/sonnet55_p25_recovery_source_36541988910.json"
)
DEFAULT_AUTHORITY = Path(
    "data/specifications/story_lab/sonnet55_revision05_qualification_authority.json"
)
DEFAULT_GATE_PROMPT = Path(
    "prompts/episode_spine_gate_sonnet55_qualification.md"
)
DEFAULT_OUT = Path("runs/sonnet55-spine-p27-authority-gate/result.json")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _architect_inherited_call(source: dict[str, Any]) -> dict[str, Any]:
    call = source["architect_call"]
    return normalize_model_call(
        stage="episode_spine_architect",
        model=source["architect_model"],
        provider=runtime_profile_identity(source["architect_model"]).get("provider"),
        raw_usage=call.get("raw_usage") or {},
        cost=call.get("cost") or {},
        latency_seconds=call.get("latency_seconds"),
    )


def build_gate_input(
    *,
    source: dict[str, Any],
    authority: dict[str, Any],
    episode_spine: EpisodeSpineV2,
) -> dict[str, Any]:
    if authority.get("schema_version") != "sonnet55-qualification-authority.v1":
        raise RuntimeError("Qualification authority schema mismatch.")
    if (authority.get("human_review") or {}).get("verdict") != "APPROVE":
        raise RuntimeError("Qualification authority is not human-approved.")
    if int(authority.get("source_run_id") or 0) != 36520646579:
        raise RuntimeError("Qualification authority must point to frozen Revision-05.")

    premise = source["approved_premise"]["premise"]
    projection = source["projection"]
    return {
        "task": "evaluate_episode_spine_with_frozen_human_authority",
        "approved_premise": premise,
        "premise_context": projection,
        "qualification_authority": authority,
        "episode_spine": episode_spine.model_dump(mode="json", by_alias=True),
        "output_contract": EpisodeSpineGateV2.model_json_schema(by_alias=True),
        "decision_rule": (
            "ACCEPT only if writer execution is justified under the explicit authority "
            "hierarchy; otherwise REPLAN."
        ),
    }


def run(
    *,
    source_path: Path,
    authority_path: Path,
    gate_prompt_path: Path,
    out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read_json(source_path)
    if source.get("schema_version") != "sonnet55-p25-recovery-source.v1":
        raise RuntimeError("Recovery source schema mismatch.")
    authority = _read_json(authority_path)

    gate_model = str(source["gate_model"])
    require_qualification_runtime_profile(gate_model)

    normalized, normalization_repairs = normalize_reversal_support_refs(
        source["architect_raw_payload"]
    )
    if len(normalization_repairs) != 1:
        raise RuntimeError(
            f"Expected exactly one safe normalization repair, got {len(normalization_repairs)}"
        )

    episode_spine = EpisodeSpineV2.model_validate(normalized)
    gate_input = build_gate_input(
        source=source,
        authority=authority,
        episode_spine=episode_spine,
    )

    gate_prompt = gate_prompt_path.read_text(encoding="utf-8").strip()
    started = time.perf_counter()
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
    gate_latency = round(time.perf_counter() - started, 3)
    gate = EpisodeSpineGateV2.model_validate(gate_raw)

    gate_call = _model_call_evidence(
        gate_body,
        gate_request,
        latency_seconds=gate_latency,
    )
    recovery_gate_call = normalize_model_call(
        stage="episode_spine_authority_gate_recovery",
        model=gate_model,
        provider=runtime_profile_identity(gate_model).get("provider"),
        raw_usage=gate_call.get("raw_usage") or {},
        cost=gate_call.get("cost") or {},
        latency_seconds=gate_latency,
    )
    inherited_architect_call = _architect_inherited_call(source)

    recovery_rollup = rollup_model_calls([recovery_gate_call])
    candidate_rollup = rollup_model_calls(
        [inherited_architect_call, recovery_gate_call]
    )

    result = {
        "schema_version": "sonnet55-p27-authority-gate-evidence.v1",
        "status": "awaiting_human_review",
        "source_run_id": source["source_run_id"],
        "authority_source_run_id": authority["source_run_id"],
        "authority_human_verdict": authority["human_review"]["verdict"],
        "architect_model": source["architect_model"],
        "gate_model": gate_model,
        "safe_normalization": {
            "applied": True,
            "repairs": normalization_repairs,
            "semantic_fields_changed": False,
        },
        "authority_input": authority,
        "episode_spine": episode_spine.model_dump(mode="json", by_alias=True),
        "gate": gate.model_dump(mode="json", by_alias=True),
        "gate_raw_payload": gate_raw,
        "gate_parse_failures": gate_parse_failures,
        "gate_call": gate_call,
        "recovery_usage_rollup": recovery_rollup,
        "candidate_pipeline_usage_rollup": candidate_rollup,
        "incremental_recovery_cost_usd": recovery_rollup["totals"]["cost_usd"],
        "candidate_pipeline_cost_usd": candidate_rollup["totals"]["cost_usd"],
        "human_review": {
            "required": True,
            "verdict": None,
            "episode_writer_authorized": False,
        },
    }
    _write_json(out_path, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "gate_decision": result["gate"]["decision"],
                "authority_source_run_id": result["authority_source_run_id"],
                "incremental_recovery_cost_usd": result["incremental_recovery_cost_usd"],
                "candidate_pipeline_cost_usd": result["candidate_pipeline_cost_usd"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--gate-prompt", type=Path, default=DEFAULT_GATE_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        authority_path=args.authority,
        gate_prompt_path=args.gate_prompt,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
