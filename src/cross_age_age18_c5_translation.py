from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_openrouter
from src.episode_postprocess_v2 import _hard_constraints
from src.generate import count_words
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.openrouter_usage import parse_cost
from src.storyforge.runtime import TRANSLATION_SYSTEM

TRANSLATOR_MODEL = "google/gemini-3.8-flash"

DEFAULT_ENGLISH = Path(
    "data/specifications/story_lab/age18_cross_age_c41_deterministic_recovered_story.txt"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age18_cross_age_c11_approved.json"
)
DEFAULT_C4 = Path(
    "data/specifications/story_lab/age18_cross_age_c4_run_36618878723.json"
)
DEFAULT_C41 = Path(
    "data/specifications/story_lab/age18_cross_age_c41_deterministic_recovery_evidence.json"
)
DEFAULT_OUT = Path("runs/sonnet55-cross-age-age18-c5/result.json")
DEFAULT_TR_OUT = Path("runs/sonnet55-cross-age-age18-c5/story_tr.txt")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    *,
    english_path: Path,
    approved_path: Path,
    c4_path: Path,
    c41_path: Path,
    out_path: Path,
    tr_out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    approved = _read(approved_path)
    c4 = _read(c4_path)
    c41 = _read(c41_path)
    english = english_path.read_text(encoding="utf-8").strip()

    if c41.get("status") != "GREEN":
        raise RuntimeError("C4.1 deterministic recovery must be GREEN.")
    if c41.get("post_recovery_findings"):
        raise RuntimeError("C4.1 still contains authority findings.")
    if not bool(c41.get("length_pass")):
        raise RuntimeError("C4.1 English master is outside the approved word range.")

    spine = approved["episode_spine"]
    if int(spine["exact_age"]) != 18:
        raise RuntimeError("Age18 C5 requires exact_age=18.")

    require_qualification_runtime_profile(TRANSLATOR_MODEL)

    translation_input = {
        "exact_age": 18,
        "hard_constraints": _hard_constraints(spine),
        "accepted_english_master": english,
    }
    started = time.perf_counter()
    translation, body, request = call_openrouter(
        api_key=key,
        model=TRANSLATOR_MODEL,
        system_prompt=TRANSLATION_SYSTEM,
        user_prompt=json.dumps(translation_input, ensure_ascii=False),
        temperature=0.2,
        max_tokens=8000,
        seed=2026092944,
        request_class="translation",
        structured_output=False,
    )
    latency = round(time.perf_counter() - started, 3)

    tr_call = normalize_model_call(
        stage="age18_c5_translation",
        model=TRANSLATOR_MODEL,
        provider=runtime_profile_identity(TRANSLATOR_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    delivery_rollup = rollup_model_calls([tr_call])
    source_calls = list((c4.get("pipeline_usage_rollup") or {}).get("calls") or [])
    pipeline_rollup = rollup_model_calls(source_calls + [tr_call])

    result = {
        "schema_version": "cross-age-age18-c5-translation.v1",
        "status": "translated_awaiting_fidelity",
        "source_c4_run_id": 36618878723,
        "translator_model": TRANSLATOR_MODEL,
        "accepted_english_master": english,
        "english_word_count": count_words(english),
        "turkish_delivery": translation,
        "turkish_word_count": count_words(translation),
        "translation_request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
        },
        "translation_usage_rollup": delivery_rollup,
        "pipeline_usage_rollup": pipeline_rollup,
        "incremental_cost_usd": delivery_rollup["totals"]["cost_usd"],
        "incremental_latency_seconds": delivery_rollup["totals"]["latency_seconds"],
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "next_stage_authorized": False,
        "next_stage": "AGE18_C6_LUNA_FIDELITY_ONLY",
    }
    _write(out_path, result)
    tr_out_path.parent.mkdir(parents=True, exist_ok=True)
    tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "english_word_count": result["english_word_count"],
        "turkish_word_count": result["turkish_word_count"],
        "incremental_cost_usd": result["incremental_cost_usd"],
        "incremental_latency_seconds": result["incremental_latency_seconds"],
        "pipeline_cost_usd": result["pipeline_cost_usd"],
        "next_stage_authorized": False,
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--english", type=Path, default=DEFAULT_ENGLISH)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--c4", type=Path, default=DEFAULT_C4)
    parser.add_argument("--c41", type=Path, default=DEFAULT_C41)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--tr-out", type=Path, default=DEFAULT_TR_OUT)
    args = parser.parse_args()
    run(
        english_path=args.english,
        approved_path=args.approved,
        c4_path=args.c4,
        c41_path=args.c41,
        out_path=args.out,
        tr_out_path=args.tr_out,
    )


if __name__ == "__main__":
    main()
