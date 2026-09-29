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
DEFAULT_PROMPT = Path("prompts/story_canon_authority_gate_v1.md")
DEFAULT_OUT = Path("runs/story-canon-authority-qualification/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _gold_segment_map(story: str, targets: list[dict[str, Any]]) -> dict[str, list[str]]:
    segments = segment_story(story)
    result: dict[str, list[str]] = {}
    for target in targets:
        ids: list[str] = []
        for anchor in target.get("anchors") or []:
            matches = [str(seg["id"]) for seg in segments if str(anchor) in str(seg["text"])]
            if not matches:
                raise RuntimeError(f"Canon gold anchor missing: {target['id']} :: {anchor}")
            ids.extend(matches)
        result[str(target["id"])] = sorted(set(ids))
    return result


def _normalize_findings(payload: dict[str, Any], story: str) -> list[dict[str, Any]]:
    segments = segment_story(story)
    by_id = {str(seg["id"]): str(seg["text"]) for seg in segments}
    findings: list[dict[str, Any]] = []
    for row in payload.get("findings") or []:
        span_ids = [str(x) for x in (row.get("span_ids") or [])]
        quote = str(row.get("exact_quote") or "").strip()
        if not span_ids or not quote:
            continue
        if not any(quote in by_id.get(span_id, "") for span_id in span_ids):
            raise RuntimeError(f"Finding exact_quote not found in cited spans: {quote}")
        severity = str(row.get("severity") or "").lower()
        if severity not in {"serious", "critical"}:
            continue
        scope = str(row.get("repair_scope") or "").lower()
        if scope not in {"local", "structural", "replan"}:
            scope = "local"
        findings.append(
            {
                "family": str(row.get("family") or "canon_integrity"),
                "severity": severity,
                "repair_scope": scope,
                "span_ids": span_ids,
                "exact_quote": quote,
                "reason": str(row.get("reason") or "").strip(),
            }
        )
    return findings


def _score(
    findings: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    gold_spans: dict[str, list[str]],
) -> dict[str, Any]:
    root_to_findings = {str(target["id"]): [] for target in targets}
    finding_to_roots: dict[int, list[str]] = {}

    for idx, finding in enumerate(findings):
        spans = set(finding["span_ids"])
        roots: list[str] = []
        for target in targets:
            rid = str(target["id"])
            if spans.intersection(gold_spans[rid]):
                root_to_findings[rid].append(idx)
                roots.append(rid)
        finding_to_roots[idx] = roots

    matched = [rid for rid, rows in root_to_findings.items() if rows]
    missed = [rid for rid, rows in root_to_findings.items() if not rows]
    unmapped = [
        {"finding_index": idx, "finding": findings[idx]}
        for idx, roots in finding_to_roots.items()
        if not roots
    ]

    return {
        "target_count": len(targets),
        "matched_target_count": len(matched),
        "recall": round(len(matched) / len(targets), 6) if targets else 1.0,
        "matched_targets": matched,
        "missed_targets": missed,
        "unmapped_finding_count": len(unmapped),
        "unmapped_findings": unmapped,
        "root_to_finding_indexes": root_to_findings,
    }


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
    targets = list(gold.get("targets") or [])
    gold_spans = _gold_segment_map(story, targets)

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    started = time.perf_counter()
    payload, meta = _structured_call(
        api_key=key,
        model=MODEL,
        system=prompt,
        payload={
            "authority": {
                "approved_premise": approved["approved_premise"]["premise"],
                "context_packet": approved["projection"],
                "validated_spine": approved["episode_spine"],
                "hard_constraints": _hard_constraints(approved["episode_spine"]),
            },
            "story_segments": segments,
        },
        seed=2026092932,
        request_class="defect_locator",
        max_tokens=1800,
    )
    latency = round(time.perf_counter() - started, 3)
    findings = _normalize_findings(payload, story)
    score = _score(findings, targets, gold_spans)

    audit_call = normalize_model_call(
        stage="targeted_canon_authority_gate",
        model=MODEL,
        provider=runtime_profile_identity(MODEL).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    audit_rollup = rollup_model_calls([audit_call])
    source_calls = list((source.get("source_pipeline_usage_rollup") or {}).get("calls") or [])
    pipeline_rollup = rollup_model_calls(source_calls + [audit_call])

    result = {
        "schema_version": "story-canon-authority-qualification.v1",
        "status": "completed",
        "experiment": "P3B_TARGETED_CANON_AUTHORITY_GATE",
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
        "next_stage_note": "No repair, Sol, translation, or fidelity call is authorized by this run.",
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
