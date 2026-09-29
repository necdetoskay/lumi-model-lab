from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.episode_postprocess_v2 import _audit_once, _validate_source
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_packet import build_story_authority_packet
from src.story_canon_authority_qualification import _normalize_findings
from src.story_defect_detection import segment_story
from src.storyforge.runtime import _structured_call

COMPACT_MODEL = "openai/gpt-5.6-luna"
GENERAL_MODEL = "anthropic/claude-sonnet-5.5"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_repaired_postprocess_source.json"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
DEFAULT_COMPACT_PROMPT = Path("prompts/story_compact_authority_gate_v2.md")
DEFAULT_OUT = Path("runs/post-repair-publication-audit-v1/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    *,
    source_path: Path,
    approved_path: Path,
    compact_prompt_path: Path,
    out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read(source_path)
    approved = _read(approved_path)
    _validate_source(source, approved)
    require_qualification_runtime_profile(COMPACT_MODEL)
    require_qualification_runtime_profile(GENERAL_MODEL)

    story = str(source["english_story"]).strip()
    authority_packet = build_story_authority_packet(approved)
    segments = segment_story(story)

    # 1) Compact typed-authority gate.
    started = time.perf_counter()
    compact_payload, compact_meta = _structured_call(
        api_key=key,
        model=COMPACT_MODEL,
        system=compact_prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "authority_packet": authority_packet,
            "story_segments": segments,
        },
        seed=2026092936,
        request_class="defect_locator",
        max_tokens=1800,
    )
    compact_latency = round(time.perf_counter() - started, 3)
    compact_findings = _normalize_findings(compact_payload, story)
    compact_call = normalize_model_call(
        stage="post_repair_compact_authority_audit",
        model=COMPACT_MODEL,
        provider=runtime_profile_identity(COMPACT_MODEL).get("provider"),
        raw_usage=compact_meta.get("raw_usage") or {},
        cost=compact_meta.get("cost") or {},
        latency_seconds=compact_latency,
    )

    # 2) Broad publication-blocker audit.
    general_findings, general_meta, general_latency, general_calls = _audit_once(
        api_key=key,
        stage="post_repair_sonnet55_audit",
        model=GENERAL_MODEL,
        story=story,
        approved=approved,
        seed=2026092937,
    )

    new_calls = [compact_call] + general_calls
    audit_rollup = rollup_model_calls(new_calls)
    source_calls = list(
        (source.get("source_pipeline_usage_rollup") or {}).get("calls") or []
    )
    pipeline_rollup = rollup_model_calls(source_calls + new_calls)

    risky_phrases = [
        "Serel",
        "older than any chart in the harbor archive",
        "the old builders had known things about tides",
        "Last spring I had an apprentice bring me an odd reading",
        "Two other pilots, Deniz had overheard",
        "The pilots would be talking soon.",
        "the logbook left this ridge empty",
    ]
    residual_risky = [phrase for phrase in risky_phrases if phrase in story]

    result = {
        "schema_version": "post-repair-publication-audit-v1",
        "status": "completed",
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "compact_model": COMPACT_MODEL,
        "general_model": GENERAL_MODEL,
        "compact_findings": compact_findings,
        "compact_meta": compact_meta,
        "general_findings": general_findings,
        "general_meta": general_meta,
        "residual_known_risky_phrases": residual_risky,
        "audit_usage_rollup": audit_rollup,
        "pipeline_usage_rollup": pipeline_rollup,
        "incremental_audit_cost_usd": audit_rollup["totals"]["cost_usd"],
        "incremental_audit_latency_seconds": audit_rollup["totals"]["latency_seconds"],
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "english_gate_clean": (
            not compact_findings
            and not general_findings
            and not residual_risky
        ),
        "human_adjudication_required": bool(general_findings),
        "next_stage": "translation" if (
            not compact_findings and not general_findings and not residual_risky
        ) else "adjudicate_or_repair",
    }
    _write(out_path, result)
    print(json.dumps({
        "status": result["status"],
        "compact_findings": len(compact_findings),
        "general_findings": len(general_findings),
        "residual_known_risky_phrases": residual_risky,
        "english_gate_clean": result["english_gate_clean"],
        "incremental_audit_cost_usd": result["incremental_audit_cost_usd"],
        "incremental_audit_latency_seconds": result["incremental_audit_latency_seconds"],
        "pipeline_cost_usd": result["pipeline_cost_usd"],
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--compact-prompt", type=Path, default=DEFAULT_COMPACT_PROMPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        approved_path=args.approved,
        compact_prompt_path=args.compact_prompt,
        out_path=args.out,
    )


if __name__ == "__main__":
    main()
