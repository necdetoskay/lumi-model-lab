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
from src.story_defect_detection import segment_story

PRIMARY_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_SOURCE = Path("data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json")
DEFAULT_APPROVED = Path("data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json")
DEFAULT_GOLD = Path("data/specifications/story_lab/sonnet55_writer_36552606045_human_preaudit.json")
DEFAULT_OUT = Path("runs/sonnet55-primary-audit-age12/result.json")


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
        for anchor in target.get("evidence") or []:
            matches = [str(seg["id"]) for seg in segments if str(anchor) in str(seg["text"])]
            if not matches:
                raise RuntimeError(f"Human pre-audit anchor missing: {target['id']} :: {anchor}")
            ids.extend(matches)
        result[str(target["id"])] = sorted(set(ids))
    return result


def _score(findings: list[dict[str, Any]], targets: list[dict[str, Any]], gold_spans: dict[str, list[str]]) -> dict[str, Any]:
    root_to_finding_indexes = {str(target["id"]): [] for target in targets}
    finding_to_roots: dict[int, list[str]] = {}

    for idx, finding in enumerate(findings):
        fspans = set(str(x) for x in (finding.get("span_ids") or []))
        roots: list[str] = []
        for target in targets:
            rid = str(target["id"])
            if fspans.intersection(gold_spans[rid]):
                root_to_finding_indexes[rid].append(idx)
                roots.append(rid)
        finding_to_roots[idx] = roots

    matched = [rid for rid, rows in root_to_finding_indexes.items() if rows]
    missed = [rid for rid, rows in root_to_finding_indexes.items() if not rows]
    blocking_ids = [str(t["id"]) for t in targets if str(t.get("severity")) in {"serious", "major"}]
    review_ids = [str(t["id"]) for t in targets if str(t.get("severity")) == "review"]
    matched_blocking = [rid for rid in blocking_ids if rid in matched]
    matched_review = [rid for rid in review_ids if rid in matched]
    unmapped = [
        {"finding_index": idx, "finding": findings[idx]}
        for idx, roots in finding_to_roots.items()
        if not roots
    ]

    return {
        "target_count": len(targets),
        "matched_target_count": len(matched),
        "target_recall": round(len(matched) / len(targets), 6) if targets else 1.0,
        "matched_targets": matched,
        "missed_targets": missed,
        "blocking_target_count": len(blocking_ids),
        "matched_blocking_count": len(matched_blocking),
        "blocking_recall": round(len(matched_blocking) / len(blocking_ids), 6) if blocking_ids else 1.0,
        "matched_blocking_targets": matched_blocking,
        "missed_blocking_targets": [rid for rid in blocking_ids if rid not in matched_blocking],
        "review_target_count": len(review_ids),
        "matched_review_count": len(matched_review),
        "root_to_finding_indexes": root_to_finding_indexes,
        "unmapped_finding_count": len(unmapped),
        "unmapped_findings": unmapped,
    }


def run(*, source_path: Path, approved_path: Path, gold_path: Path, out_path: Path, api_key: str | None = None) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read(source_path)
    approved = _read(approved_path)
    gold = _read(gold_path)
    _validate_source(source, approved)
    require_qualification_runtime_profile(PRIMARY_MODEL)

    story = str(source["english_story"]).strip()
    targets = list(gold.get("audit_targets") or [])
    gold_spans = _gold_segment_map(story, targets)

    findings, meta, latency, audit_calls = _audit_once(
        api_key=key,
        stage="sonnet55_primary_audit",
        model=PRIMARY_MODEL,
        story=story,
        approved=approved,
        seed=2026092931,
    )
    score = _score(findings, targets, gold_spans)
    source_calls = list((source.get("source_pipeline_usage_rollup") or {}).get("calls") or [])
    audit_rollup = rollup_model_calls(audit_calls)
    pipeline_rollup = rollup_model_calls(source_calls + audit_calls)

    result = {
        "schema_version": "sonnet55-primary-audit-qualification.v1",
        "status": "completed",
        "experiment": "S55-P3A-PRIMARY-AUDIT",
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "model": PRIMARY_MODEL,
        "blind_to_human_preaudit": True,
        "human_gold_used_only_after_inference": True,
        "gold_segment_map": gold_spans,
        "findings": findings,
        "score": score,
        "audit_meta": meta,
        "audit_usage_rollup": audit_rollup,
        "pipeline_usage_rollup": pipeline_rollup,
        "incremental_audit_cost_usd": audit_rollup["totals"]["cost_usd"],
        "incremental_audit_latency_seconds": audit_rollup["totals"]["latency_seconds"],
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "next_stage_authorized": False,
        "next_stage_note": "No Sol confirmation, repair, re-audit, translation, or fidelity call is authorized by this qualification run.",
    }
    _write(out_path, result)
    print(json.dumps({
        "status": result["status"],
        "finding_count": len(findings),
        "blocking_recall": score["blocking_recall"],
        "matched_blocking_targets": score["matched_blocking_targets"],
        "missed_blocking_targets": score["missed_blocking_targets"],
        "unmapped_finding_count": score["unmapped_finding_count"],
        "incremental_audit_cost_usd": result["incremental_audit_cost_usd"],
        "incremental_audit_latency_seconds": result["incremental_audit_latency_seconds"],
        "next_stage_authorized": False,
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(source_path=args.source, approved_path=args.approved, gold_path=args.gold, out_path=args.out)


if __name__ == "__main__":
    main()
