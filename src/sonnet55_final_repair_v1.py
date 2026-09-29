from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.episode_postprocess_v2 import _hard_constraints, _validate_source
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_packet import build_story_authority_packet
from src.storyforge.runtime import REPAIR_SYSTEM, _apply_local_repairs, _structured_call
from src.generate import count_words

REPAIR_MODEL = "openai/gpt-5.6-sol"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
DEFAULT_P3D1 = Path(
    "data/specifications/story_lab/sonnet55_p3d1_compact_authority_result.json"
)
DEFAULT_OUT = Path("runs/sonnet55-final-repair-v1/result.json")
DEFAULT_STORY_OUT = Path("runs/sonnet55-final-repair-v1/repaired_story.txt")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _manual_authority_cleanups(story: str) -> list[dict[str, Any]]:
    cleanups: list[dict[str, Any]] = []
    if "Master Serel" in story or "Serel" in story:
        cleanups.append(
            {
                "family": "canon_integrity",
                "severity": "serious",
                "repair_scope": "local",
                "span_ids": [],
                "exact_quote": "Master Serel was already there",
                "reason": (
                    "The validated spine supplies only a mentor role and no durable proper "
                    "name or gender. Remove the invented recurring name Serel throughout the "
                    "story and use role-based wording / neutral reference without changing "
                    "the mentor's actions or dialogue."
                ),
            }
        )
    if "Last spring I had an apprentice bring me an odd reading" in story:
        cleanups.append(
            {
                "family": "canon_integrity",
                "severity": "serious",
                "repair_scope": "local",
                "span_ids": [],
                "exact_quote": "Last spring I had an apprentice bring me an odd reading",
                "reason": (
                    "This invents durable mentor history and a prior apprentice incident. "
                    "Replace only this anecdotal history with present-tense methodological "
                    "advice that preserves the dialogue purpose."
                ),
            }
        )
    return cleanups


def run(
    *,
    source_path: Path,
    approved_path: Path,
    p3d1_path: Path,
    out_path: Path,
    story_out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read(source_path)
    approved = _read(approved_path)
    p3d1 = _read(p3d1_path)
    _validate_source(source, approved)
    require_qualification_runtime_profile(REPAIR_MODEL)

    if p3d1.get("status") != "completed":
        raise RuntimeError("P3-D.1 source is not completed.")
    if float((p3d1.get("score") or {}).get("recall") or 0) != 1.0:
        raise RuntimeError("P3-D.1 must have 100% target recall before final repair.")

    story = str(source["english_story"]).strip()
    confirmed = list(p3d1.get("findings") or [])
    confirmed.extend(_manual_authority_cleanups(story))

    authority_packet = build_story_authority_packet(approved)
    payload = {
        "story": story,
        "validated_spine": approved["episode_spine"],
        "authority_packet": authority_packet,
        "hard_constraints": _hard_constraints(approved["episode_spine"]),
        "confirmed_local_defects": confirmed,
        "repair_policy": {
            "minimal_exact_replacements_only": True,
            "do_not_rewrite_unaffected_prose": True,
            "remove_all_unauthorized_serel_name_references": True,
            "preserve_report_now_branch": True,
            "preserve_five_reading_evidence_series": True,
            "preserve_provisional_entry_outcome": True,
        },
    }

    started = time.perf_counter()
    repair_payload, meta = _structured_call(
        api_key=key,
        model=REPAIR_MODEL,
        system=REPAIR_SYSTEM,
        payload=payload,
        seed=2026092935,
        request_class="editorial_audit",
        max_tokens=3200,
    )
    latency = round(time.perf_counter() - started, 3)

    repair_call = normalize_model_call(
        stage="final_english_repair",
        model=REPAIR_MODEL,
        provider=runtime_profile_identity(REPAIR_MODEL).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    repair_rollup = rollup_model_calls([repair_call])

    result_base = {
        "schema_version": "sonnet55-final-repair-v1.evidence.v1",
        "status": "repair_model_returned",
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "model": REPAIR_MODEL,
        "confirmed_defects": confirmed,
        "authority_packet": authority_packet,
        "repair_payload": repair_payload,
        "repair_meta": meta,
        "repair_usage_rollup": repair_rollup,
        "incremental_cost_usd": repair_rollup["totals"]["cost_usd"],
        "incremental_latency_seconds": repair_rollup["totals"]["latency_seconds"],
    }
    _write(out_path, result_base)

    repaired_story, applied = _apply_local_repairs(story, repair_payload)
    words = count_words(repaired_story)
    target_min = int(approved["episode_spine"]["target_words_min"])
    target_max = int(approved["episode_spine"]["target_words_max"])

    source_calls = list(
        (source.get("source_pipeline_usage_rollup") or {}).get("calls") or []
    )
    pipeline_rollup = rollup_model_calls(source_calls + [repair_call])

    result = {
        **result_base,
        "status": "repaired",
        "original_word_count": count_words(story),
        "repaired_word_count": words,
        "length_pass": target_min <= words <= target_max,
        "applied_repairs": applied,
        "original_story": story,
        "repaired_story": repaired_story,
        "pipeline_usage_rollup": pipeline_rollup,
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "next_stage": "post_repair_reaudit",
    }
    _write(out_path, result)
    story_out_path.parent.mkdir(parents=True, exist_ok=True)
    story_out_path.write_text(repaired_story.rstrip() + "\n", encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "repairs": len(applied),
        "repaired_word_count": words,
        "length_pass": result["length_pass"],
        "incremental_cost_usd": result["incremental_cost_usd"],
        "incremental_latency_seconds": result["incremental_latency_seconds"],
        "pipeline_cost_usd": result["pipeline_cost_usd"],
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--p3d1", type=Path, default=DEFAULT_P3D1)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--story-out", type=Path, default=DEFAULT_STORY_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        approved_path=args.approved,
        p3d1_path=args.p3d1,
        out_path=args.out,
        story_out_path=args.story_out,
    )


if __name__ == "__main__":
    main()
