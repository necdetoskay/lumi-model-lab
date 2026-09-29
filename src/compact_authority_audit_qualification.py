from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.episode_postprocess_v2 import _validate_source
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_packet import build_story_authority_packet
from src.story_canon_authority_qualification import (
    _gold_segment_map,
    _normalize_findings,
    _score,
)
from src.story_defect_detection import segment_story
from src.storyforge.runtime import _structured_call

MODEL = "openai/gpt-5.6-luna"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
DEFAULT_GOLD = Path(
    "data/specifications/story_lab/sonnet55_writer_36552606045_confirmed_canon_gold.json"
)
DEFAULT_PROMPT = Path("prompts/story_compact_authority_gate_v2.md")
DEFAULT_OUT = Path("runs/compact-authority-audit-qualification/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    *,
    source_path: Path,
    approved_path: Path,
    gold_path: Path,
    prompt_path: Path,
    out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read(source_path)
    approved = _read(approved_path)
    gold = _read(gold_path)
    _validate_source(source, approved)
    require_qualification_runtime_profile(MODEL)

    story = str(source["english_story"]).strip()
    segments = segment_story(story)
    authority_packet = build_story_authority_packet(approved)
    targets = list(gold.get("targets") or [])
    gold_spans = _gold_segment_map(story, targets)

    started = time.perf_counter()
    payload, meta = _structured_call(
        api_key=key,
        model=MODEL,
        system=prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "authority_packet": authority_packet,
            "story_segments": segments,
        },
        seed=2026092934,
        request_class="defect_locator",
        max_tokens=1800,
    )
    latency = round(time.perf_counter() - started, 3)

    audit_call = normalize_model_call(
        stage="compact_authority_audit",
        model=MODEL,
        provider=runtime_profile_identity(MODEL).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    audit_rollup = rollup_model_calls([audit_call])
    source_calls = list(
        (source.get("source_pipeline_usage_rollup") or {}).get("calls") or []
    )
    pipeline_rollup = rollup_model_calls(source_calls + [audit_call])

    try:
        findings = _normalize_findings(payload, story)
        score = _score(findings, targets, gold_spans)
    except Exception as exc:
        failure_result = {
            "schema_version": "compact-authority-audit-qualification.v1",
            "status": "post_inference_normalization_failure",
            "experiment": "P3D_COMPACT_TYPED_AUTHORITY",
            "source_writer_run_id": source["source_writer_run_id"],
            "source_spine_run_id": source["source_spine_run_id"],
            "model": MODEL,
            "blind_to_gold": True,
            "gold_used_only_after_inference": True,
            "authority_packet": authority_packet,
            "raw_model_payload": payload,
            "normalization_error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "audit_meta": meta,
            "audit_usage_rollup": audit_rollup,
            "pipeline_usage_rollup": pipeline_rollup,
            "incremental_cost_usd": audit_rollup["totals"]["cost_usd"],
            "incremental_latency_seconds": audit_rollup["totals"]["latency_seconds"],
            "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
            "next_stage_authorized": False,
            "next_stage_note": (
                "Post-inference normalization failed; raw model payload and usage were "
                "persisted. No further model call is authorized."
            ),
        }
        _write(out_path, failure_result)
        raise

    result = {
        "schema_version": "compact-authority-audit-qualification.v1",
        "status": "completed",
        "experiment": "P3D_COMPACT_TYPED_AUTHORITY",
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "model": MODEL,
        "blind_to_gold": True,
        "gold_used_only_after_inference": True,
        "authority_packet": authority_packet,
        "findings": findings,
        "score": score,
        "audit_meta": meta,
        "audit_usage_rollup": audit_rollup,
        "pipeline_usage_rollup": pipeline_rollup,
        "incremental_cost_usd": audit_rollup["totals"]["cost_usd"],
        "incremental_latency_seconds": audit_rollup["totals"]["latency_seconds"],
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "next_stage_authorized": False,
        "next_stage_note": (
            "No repair, Sol, re-audit, translation, fidelity, or writer regeneration "
            "is authorized by this proof."
        ),
    }
    _write(out_path, result)
    print(json.dumps({
        "status": result["status"],
        "finding_count": len(findings),
        "recall": score["recall"],
        "matched_targets": score["matched_targets"],
        "missed_targets": score["missed_targets"],
        "unmapped_finding_count": score["unmapped_finding_count"],
        "incremental_cost_usd": result["incremental_cost_usd"],
        "incremental_latency_seconds": result["incremental_latency_seconds"],
        "next_stage_authorized": False,
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        approved_path=args.approved,
        gold_path=args.gold,
        prompt_path=args.prompt,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
