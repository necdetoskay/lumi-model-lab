from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.deterministic_story_authority_guards import run_deterministic_authority_guards
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_findings import normalize_authority_findings
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_defect_detection import segment_story
from src.story_stage_common import extract_story, read_json, source_calls, write_json
from src.storyforge.runtime import _structured_call

DEFAULT_PROMPT = Path("prompts/story_compact_authority_gate_v4_generic.md")
DEFAULT_MODEL = "openai/gpt-5.6-luna"


def run(
    *,
    source_path: Path,
    approved_path: Path,
    out_path: Path,
    prompt_path: Path = DEFAULT_PROMPT,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    source = read_json(source_path)
    approved = read_json(approved_path)
    story = extract_story(source)
    packet = build_story_authority_packet_v2(approved)

    hard = run_deterministic_authority_guards(story, packet)
    base_calls = source_calls(source)
    if hard:
        rollup = rollup_model_calls(base_calls)
        result = {
            "schema_version": "episode-authority-gate.v1",
            "status": "hard_findings_confirmed",
            "story": story,
            "authority_packet": packet,
            "hard_findings": hard,
            "semantic_findings": [],
            "confirmed_findings": hard,
            "semantic_adjudication_required": False,
            "model_called": False,
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
            "next_stage": "BOUNDED_REPAIR",
            "next_stage_authorized": False,
        }
        write_json(out_path, result)
        return result

    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    started = time.perf_counter()
    payload, meta = _structured_call(
        api_key=key,
        model=model,
        system=prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "authority_packet": packet,
            "story_segments": segment_story(story),
        },
        seed=2026093002,
        request_class="defect_locator",
        max_tokens=1800,
    )
    latency = round(time.perf_counter() - started, 3)
    findings = normalize_authority_findings(payload, story)

    call = normalize_model_call(
        stage="semantic_authority_gate",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup = rollup_model_calls(base_calls + [call])
    clean = not findings

    result = {
        "schema_version": "episode-authority-gate.v1",
        "status": "clean" if clean else "semantic_findings_need_adjudication",
        "story": story,
        "authority_packet": packet,
        "hard_findings": [],
        "semantic_findings": findings,
        "confirmed_findings": [],
        "semantic_adjudication_required": not clean,
        "model_called": True,
        "semantic_gate_model": model,
        "semantic_gate_meta": meta,
        "pipeline_usage_rollup": rollup,
        "total_cost_usd": rollup["totals"]["cost_usd"],
        "next_stage": "TRANSLATION" if clean else "SEMANTIC_ADJUDICATION",
        "next_stage_authorized": False,
    }
    write_json(out_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    result = run(
        source_path=args.source,
        approved_path=args.approved,
        out_path=args.out,
        prompt_path=args.prompt,
        model=args.model,
    )
    print(json.dumps({
        "status": result["status"],
        "hard_findings": len(result["hard_findings"]),
        "semantic_findings": len(result["semantic_findings"]),
        "model_called": result["model_called"],
        "next_stage": result["next_stage"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
