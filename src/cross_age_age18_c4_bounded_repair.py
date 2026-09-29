from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.deterministic_story_authority_guards import run_deterministic_authority_guards
from src.episode_postprocess_v2 import _hard_constraints, _validate_source
from src.generate import count_words
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.storyforge.runtime import REPAIR_SYSTEM, _apply_local_repairs, _structured_call

REPAIR_MODEL = "openai/gpt-5.6-sol"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age18_cross_age_c2_postprocess_source_36612862926.json"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age18_cross_age_c11_approved.json"
)
DEFAULT_GUARD = Path(
    "data/specifications/story_lab/age18_cross_age_c32_deterministic_guard_evidence.json"
)
DEFAULT_OUT = Path("runs/sonnet55-cross-age-age18-c4/result.json")
DEFAULT_STORY_OUT = Path("runs/sonnet55-cross-age-age18-c4/repaired_story.txt")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    *,
    source_path: Path,
    approved_path: Path,
    guard_path: Path,
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
    guard = _read(guard_path)
    _validate_source(source, approved)
    require_qualification_runtime_profile(REPAIR_MODEL)

    if guard.get("status") != "PASS":
        raise RuntimeError("C3.2 deterministic guard evidence must PASS before repair.")
    score = ((guard.get("age18") or {}).get("score") or {})
    if float(score.get("recall") or 0) != 1.0:
        raise RuntimeError("C3.2 must have 100% confirmed-root recall.")
    if int(score.get("unmapped_finding_count") or 0) != 0:
        raise RuntimeError("C3.2 cannot contain unmapped findings.")

    story = str(source["english_story"]).strip()
    authority_packet = build_story_authority_packet_v2(approved)
    confirmed = list((guard.get("age18") or {}).get("findings") or [])
    if len(confirmed) != 3:
        raise RuntimeError(f"Expected exactly 3 deterministic confirmed defects, got {len(confirmed)}")

    payload = {
        "story": story,
        "validated_spine": approved["episode_spine"],
        "authority_packet": authority_packet,
        "hard_constraints": _hard_constraints(approved["episode_spine"]),
        "confirmed_local_defects": confirmed,
        "repair_policy": {
            "minimal_exact_replacements_only": True,
            "do_not_rewrite_unaffected_prose": True,
            "do_not_change_branch_choice": True,
            "preserve_provisional_record_branch": True,
            "preserve_five_reading_series": True,
            "preserve_no_advisory_outcome": True,
            "fix_only_confirmed_defects": True,
        },
    }

    started = time.perf_counter()
    repair_payload, meta = _structured_call(
        api_key=key,
        model=REPAIR_MODEL,
        system=REPAIR_SYSTEM,
        payload=payload,
        seed=2026092943,
        request_class="editorial_audit",
        max_tokens=2400,
    )
    latency = round(time.perf_counter() - started, 3)

    repair_call = normalize_model_call(
        stage="age18_c4_bounded_repair",
        model=REPAIR_MODEL,
        provider=runtime_profile_identity(REPAIR_MODEL).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    repair_rollup = rollup_model_calls([repair_call])

    result_base = {
        "schema_version": "cross-age-age18-c4-bounded-repair.v1",
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
    if len(applied) > 6:
        raise RuntimeError(f"Repair model returned too many local replacements: {len(applied)}")

    post_guard = run_deterministic_authority_guards(repaired_story, authority_packet)
    words = count_words(repaired_story)
    target_min = int(approved["episode_spine"]["target_words_min"])
    target_max = int(approved["episode_spine"]["target_words_max"])

    source_calls = list((source.get("source_pipeline_usage_rollup") or {}).get("calls") or [])
    pipeline_rollup = rollup_model_calls(source_calls + [repair_call])

    result = {
        **result_base,
        "status": "repaired_guard_clean" if not post_guard else "repaired_guard_blocked",
        "original_word_count": count_words(story),
        "repaired_word_count": words,
        "length_pass": target_min <= words <= target_max,
        "applied_repairs": applied,
        "post_repair_deterministic_findings": post_guard,
        "original_story": story,
        "repaired_story": repaired_story,
        "pipeline_usage_rollup": pipeline_rollup,
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "next_stage_authorized": False,
        "next_stage": "AGE18_C5_TRANSLATION_ONLY_IF_HUMAN_ACCEPTS_C4",
    }
    _write(out_path, result)
    story_out_path.parent.mkdir(parents=True, exist_ok=True)
    story_out_path.write_text(repaired_story.rstrip() + "\n", encoding="utf-8")

    print(json.dumps({
        "status": result["status"],
        "repairs": len(applied),
        "post_repair_guard_findings": len(post_guard),
        "repaired_word_count": words,
        "length_pass": result["length_pass"],
        "incremental_cost_usd": result["incremental_cost_usd"],
        "incremental_latency_seconds": result["incremental_latency_seconds"],
        "pipeline_cost_usd": result["pipeline_cost_usd"],
        "next_stage_authorized": False,
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--guard", type=Path, default=DEFAULT_GUARD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--story-out", type=Path, default=DEFAULT_STORY_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        approved_path=args.approved,
        guard_path=args.guard,
        out_path=args.out,
        story_out_path=args.story_out,
    )


if __name__ == "__main__":
    main()
