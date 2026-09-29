from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.episode_postprocess_v2 import _audit_once, _validate_source
from src.model_registry import require_qualification_runtime_profile
from src.model_usage_rollup import rollup_model_calls
from src.story_canon_authority_qualification import _gold_segment_map, _score

MODEL = "openai/gpt-5.6-sol"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
DEFAULT_GOLD = Path(
    "data/specifications/story_lab/sonnet55_writer_36552606045_confirmed_canon_gold.json"
)
DEFAULT_OUT = Path("runs/sol-secondary-audit-qualification/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    *,
    source_path: Path,
    approved_path: Path,
    gold_path: Path,
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
    targets = list(gold.get("targets") or [])
    gold_spans = _gold_segment_map(story, targets)

    findings, meta, latency, audit_calls = _audit_once(
        api_key=key,
        stage="sol_secondary_audit_qualification",
        model=MODEL,
        story=story,
        approved=approved,
        seed=2026092933,
    )
    score = _score(findings, targets, gold_spans)

    audit_rollup = rollup_model_calls(audit_calls)
    source_calls = list(
        (source.get("source_pipeline_usage_rollup") or {}).get("calls") or []
    )
    pipeline_rollup = rollup_model_calls(source_calls + audit_calls)

    result = {
        "schema_version": "sol-secondary-audit-qualification.v1",
        "status": "completed",
        "experiment": "P3C_SOL_SECONDARY_AUDIT_PROOF",
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "model": MODEL,
        "blind_to_gold": True,
        "gold_used_only_after_inference": True,
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
            "No repair, re-audit, translation, fidelity, or further model call "
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
        "next_stage_authorized": False
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        approved_path=args.approved,
        gold_path=args.gold,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
