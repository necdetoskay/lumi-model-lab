from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_defect_detection import segment_story
from src.storyforge.runtime import AUDIT_SYSTEM, _normalize_audit, _structured_call

MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_SOURCE = Path("data/specifications/story_lab/age12_episode1_writer_run_36526379349.json")
DEFAULT_SPINE = Path("data/specifications/story_lab/age12_episode1_spine_revision_05_approved.json")
DEFAULT_GOLD = Path("data/specifications/story_lab/sonnet55_audit_gold_age12.json")
DEFAULT_OUT = Path("runs/sonnet55-audit-ab/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hard_constraints(spine: dict[str, Any]) -> list[str]:
    rows = list(spine.get("writer_rules") or [])
    reversal = spine.get("reversal") or {}
    if reversal.get("inference_ceiling"):
        rows.append("INFERENCE CEILING: " + str(reversal["inference_ceiling"]))
    if reversal.get("unresolved_after_reversal"):
        rows.append("MUST REMAIN UNRESOLVED: " + str(reversal["unresolved_after_reversal"]))
    return rows


def _anchor_segment_ids(story: str, roots: list[dict[str, Any]]) -> dict[str, list[str]]:
    segments = segment_story(story)
    result: dict[str, list[str]] = {}
    for root in roots:
        ids: list[str] = []
        for anchor in root.get("anchors") or []:
            matches = [str(seg["id"]) for seg in segments if str(anchor) in str(seg["text"])]
            if not matches:
                raise RuntimeError(f"Gold anchor missing from raw story: {root['id']} :: {anchor}")
            ids.extend(matches)
        result[str(root["id"])] = sorted(set(ids))
    return result


def _score(findings: list[dict[str, Any]], roots: list[dict[str, Any]], gold_spans: dict[str, list[str]]) -> dict[str, Any]:
    matches: dict[str, list[int]] = {str(root["id"]): [] for root in roots}
    finding_to_roots: dict[int, list[str]] = {}
    for idx, finding in enumerate(findings):
        fspans = set(str(x) for x in (finding.get("span_ids") or []))
        matched: list[str] = []
        for root in roots:
            rid = str(root["id"])
            if fspans.intersection(gold_spans[rid]):
                matches[rid].append(idx)
                matched.append(rid)
        finding_to_roots[idx] = matched

    matched_roots = [rid for rid, idxs in matches.items() if idxs]
    missed_roots = [rid for rid, idxs in matches.items() if not idxs]
    unmapped = [
        {"finding_index": idx, "finding": findings[idx]}
        for idx, roots_for_finding in finding_to_roots.items()
        if not roots_for_finding
    ]
    return {
        "root_count": len(roots),
        "matched_root_count": len(matched_roots),
        "root_recall": round(len(matched_roots) / len(roots), 6) if roots else 1.0,
        "matched_roots": matched_roots,
        "missed_roots": missed_roots,
        "root_to_finding_indexes": matches,
        "unmapped_findings": unmapped,
        "unmapped_finding_count": len(unmapped),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved-spine", type=Path, default=DEFAULT_SPINE)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    load_dotenv()
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    require_qualification_runtime_profile(MODEL)

    source = _read(args.source)
    approved = _read(args.approved_spine)
    gold = _read(args.gold)
    story = str(source["english_story"]).strip()
    spine = approved["episode_spine"]
    roots = list(gold["roots"])
    segments = segment_story(story)
    gold_spans = _anchor_segment_ids(story, roots)

    started = time.perf_counter()
    payload, meta = _structured_call(
        api_key=key,
        model=MODEL,
        system=AUDIT_SYSTEM,
        payload={
            "story_intent": approved["approved_premise"]["premise"],
            "hard_constraints": _hard_constraints(spine),
            "context_packet": approved["projection"],
            "validated_spine": spine,
            "story_segments": segments,
        },
        seed=2026092955,
        request_class="editorial_audit",
        max_tokens=2800,
    )
    latency = round(time.perf_counter() - started, 3)
    findings = _normalize_audit(payload, segments)
    score = _score(findings, roots, gold_spans)

    call = normalize_model_call(
        stage="sonnet55_primary_audit",
        model=MODEL,
        provider=runtime_profile_identity(MODEL).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup = rollup_model_calls([call])
    baseline = gold["baseline_primary"]
    candidate_cost = float(rollup["totals"]["cost_usd"])
    candidate_latency = float(rollup["totals"]["latency_seconds"])
    baseline_cost = float(baseline["cost_usd"])
    baseline_latency = float(baseline["latency_seconds"])

    result = {
        "schema_version": "sonnet55-audit-ab-evidence.v1",
        "status": "completed",
        "experiment": "S55-P1-AUDIT-AB",
        "source_writer_run_id": gold["source_writer_run_id"],
        "source_postprocess_run_id": gold["source_postprocess_run_id"],
        "model": MODEL,
        "runtime_identity": runtime_profile_identity(MODEL),
        "gold_root_spans": gold_spans,
        "findings": findings,
        "score": score,
        "baseline_sonnet5": baseline,
        "candidate_sonnet55": {
            "finding_count": len(findings),
            "cost_usd": candidate_cost,
            "latency_seconds": candidate_latency,
            "usage": rollup["totals"],
            "meta": meta
        },
        "comparison": {
            "cost_delta_usd": round(candidate_cost - baseline_cost, 9),
            "cost_ratio_vs_sonnet5": round(candidate_cost / baseline_cost, 6) if baseline_cost else None,
            "latency_delta_seconds": round(candidate_latency - baseline_latency, 3),
            "latency_ratio_vs_sonnet5": round(candidate_latency / baseline_latency, 6) if baseline_latency else None
        },
        "usage_rollup": rollup,
        "promotion_decision": "HUMAN_REVIEW_REQUIRED"
    }
    _write(args.out, result)
    print(json.dumps({
        "status": result["status"],
        "root_recall": score["root_recall"],
        "matched_roots": score["matched_roots"],
        "missed_roots": score["missed_roots"],
        "unmapped_finding_count": score["unmapped_finding_count"],
        "cost_usd": candidate_cost,
        "latency_seconds": candidate_latency,
        "cost_ratio_vs_sonnet5": result["comparison"]["cost_ratio_vs_sonnet5"],
        "latency_ratio_vs_sonnet5": result["comparison"]["latency_ratio_vs_sonnet5"]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
