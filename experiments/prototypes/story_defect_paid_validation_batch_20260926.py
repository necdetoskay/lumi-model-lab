from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.story_defect_synthetic_corpus import load_synthetic_corpus

TRIGGER = Path("experiments/triggers/story-defect-paid-validation-batch.txt")
OUT = Path("runs/story-defect-paid-validation-batch/result.json")

PRIMARY_MODEL = "anthropic/claude-sonnet-5"
ADJUDICATOR_MODEL = "anthropic/claude-haiku-4.5"

SYSTEM = r"""
You are an independent publication-defect verifier for one finished Turkish children's story.
Reader: exact age 4, adult read-aloud.

You are BLIND to benchmark mutations and expected labels. Audit the current story on its own.

Report ONLY serious or critical semantic defects in:
physical_feasibility, causal_logic, state_continuity, epistemic_order,
spatial_consistency, temporal_consistency, response_causality,
closure_integrity, canon_integrity.

Do not report style, grammar, length, repetition, optional polish, or ordinary fantasy that is internally consistent.
Do not invent hidden constraints.
A solved problem may continue into harmless play without becoming a closure defect.
Use exact supplied sentence IDs. Do not rewrite.

JSON only:
{"findings":[{"family":"...","severity":"serious|critical","span_ids":["S001"],"reason":"..."}]}
""".strip()


def batch_index() -> int:
    text = TRIGGER.read_text(encoding="utf-8")
    match = re.search(r"batch_index\s*=\s*(\d+)", text)
    if not match:
        raise RuntimeError("batch_index_missing")
    value = int(match.group(1))
    if not 0 <= value <= 6:
        raise RuntimeError(f"batch_index_out_of_range:{value}")
    return value


def select_batch(corpus: dict[str, Any], index: int) -> list[dict[str, Any]]:
    by_recipe: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in corpus["cases"]:
        by_recipe[case["mutation"]["recipe_id"]].append(case)

    selected: list[dict[str, Any]] = []
    for recipe_id in sorted(by_recipe):
        rows = sorted(by_recipe[recipe_id], key=lambda row: row["case_id"])
        start = index * 2
        chunk = rows[start:start + 2]
        if len(chunk) != 2:
            raise RuntimeError(f"batch_recipe_count_mismatch:{index}:{recipe_id}:{len(chunk)}")
        selected.extend(chunk)

    if len(selected) != 30:
        raise RuntimeError(f"batch_case_count_mismatch:{index}:{len(selected)}")
    return selected


def validate_payload(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("findings_missing")
    out = []
    for idx, finding in enumerate(findings):
        family = finding.get("family")
        severity = finding.get("severity")
        spans = finding.get("span_ids")
        reason = str(finding.get("reason") or "").strip()
        reason_missing = not bool(reason)
        if reason_missing:
            reason = "[validator omitted reason]"
        if family not in DEFECT_FAMILIES:
            raise RuntimeError(f"finding_{idx}_family_invalid:{family}")
        if severity not in {"serious", "critical"}:
            raise RuntimeError(f"finding_{idx}_severity_invalid:{severity}")
        if not isinstance(spans, list) or not spans or not set(spans).issubset(valid_ids):
            raise RuntimeError(f"finding_{idx}_span_invalid:{spans}")
        out.append({
            "family": family,
            "severity": severity,
            "span_ids": spans,
            "reason": reason,
            "reason_missing": reason_missing,
        })
    return out


def inspect_findings(case: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    expected_family = case["gold"]["family"]
    expected_spans = set(case["gold"]["span_ids"])
    intended = [
        f for f in findings
        if f["family"] == expected_family and expected_spans.intersection(f["span_ids"])
    ]
    overlap_other = [
        f for f in findings
        if f["family"] != expected_family and expected_spans.intersection(f["span_ids"])
    ]
    second = [
        f for f in findings
        if not expected_spans.intersection(f["span_ids"])
    ]
    return {
        "intended": intended,
        "overlap_other": overlap_other,
        "second": second,
    }


def extra_confirmed(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    confirmed = []
    for p in primary:
        p_spans = set(p["span_ids"])
        if any(s["family"] == p["family"] and p_spans.intersection(s["span_ids"]) for s in secondary):
            confirmed.append(p)
    return confirmed


def call_validator(
    *,
    key: str,
    model: str,
    request_class: str,
    max_tokens: int,
    seed: int,
    case: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], float]:
    segments = segment_story(case["text"])
    parsed, meta = structured_call(
        api_key=key,
        model=model,
        system=SYSTEM,
        payload={
            "case_id": case["case_id"],
            "story_family": case["family"],
            "story_segments": segments,
        },
        seed=seed,
        max_tokens=max_tokens,
        request_class=request_class,
    )
    findings = validate_payload(parsed, {row["id"] for row in segments})
    cost = float(((meta.get("cost") or {}).get("usd")) or 0.0)
    return findings, meta, cost


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    index = batch_index()
    corpus = load_synthetic_corpus()
    cases = select_batch(corpus, index)

    rows = []
    total_cost = 0.0
    primary_calls = 0
    adjudicator_calls = 0
    started = time.perf_counter()

    for i, case in enumerate(cases):
        primary_findings: list[dict[str, Any]] = []
        primary_meta: dict[str, Any] | None = None
        primary_cost = 0.0
        primary_error: str | None = None

        try:
            primary_findings, primary_meta, primary_cost = call_validator(
                key=key,
                model=PRIMARY_MODEL,
                request_class="editorial_audit",
                max_tokens=2200,
                seed=2026100000 + index * 100 + i,
                case=case,
            )
            primary_calls += 1
            total_cost += primary_cost
            p = inspect_findings(case, primary_findings)
        except Exception as exc:
            primary_error = f"{type(exc).__name__}: {exc}"
            p = {"intended": [], "overlap_other": [], "second": []}

        needs_adjudication = (
            primary_error is not None
            or not p["intended"]
            or bool(p["overlap_other"])
            or bool(p["second"])
        )

        adjudicator_findings: list[dict[str, Any]] = []
        adjudicator_meta: dict[str, Any] | None = None
        adjudicator_cost = 0.0
        adjudicator_error: str | None = None
        a = {"intended": [], "overlap_other": [], "second": []}

        if needs_adjudication:
            try:
                adjudicator_findings, adjudicator_meta, adjudicator_cost = call_validator(
                    key=key,
                    model=ADJUDICATOR_MODEL,
                    request_class="judge",
                    max_tokens=1800,
                    seed=2026105000 + index * 100 + i,
                    case=case,
                )
                adjudicator_calls += 1
                total_cost += adjudicator_cost
                a = inspect_findings(case, adjudicator_findings)
            except Exception as exc:
                adjudicator_error = f"{type(exc).__name__}: {exc}"

        intended_confirmed = bool(p["intended"]) or bool(a["intended"])
        taxonomy_unresolved = bool(p["overlap_other"]) and bool(a["overlap_other"])
        confirmed_extra = (
            extra_confirmed(p["second"], a["second"])
            if needs_adjudication and adjudicator_error is None
            else []
        )

        if primary_error is not None and adjudicator_error is not None:
            final_status = "RUNTIME_ERROR"
        elif intended_confirmed and not taxonomy_unresolved and not confirmed_extra:
            final_status = "VALIDATED_GOLD"
        else:
            final_status = "NEEDS_MANUAL_ADJUDICATION"

        rows.append({
            "case_id": case["case_id"],
            "source_id": case["source_id"],
            "recipe_id": case["mutation"]["recipe_id"],
            "dataset_split": case["dataset_split"],
            "expected": {
                "family": case["gold"]["family"],
                "severity": case["gold"]["severity"],
                "span_ids": case["gold"]["span_ids"],
                "repair_scope": case["gold"]["repair_scope"],
            },
            "primary": {
                "model": PRIMARY_MODEL,
                "findings": primary_findings,
                "intended_confirmed": bool(p["intended"]),
                "overlap_family_disagreements": p["overlap_other"],
                "second_blocking_findings": p["second"],
                "cost_usd": primary_cost,
                "meta": primary_meta,
                "error": primary_error,
            },
            "adjudication": None if not needs_adjudication else {
                "model": ADJUDICATOR_MODEL,
                "findings": adjudicator_findings,
                "intended_confirmed": bool(a["intended"]),
                "overlap_family_disagreements": a["overlap_other"],
                "second_blocking_findings": a["second"],
                "cost_usd": adjudicator_cost,
                "meta": adjudicator_meta,
                "error": adjudicator_error,
            },
            "final": {
                "status": final_status,
                "intended_confirmed": intended_confirmed,
                "taxonomy_unresolved": taxonomy_unresolved,
                "confirmed_extra_blocking_findings": confirmed_extra,
            },
        })

        OUT.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "schema_version": "story-defect-paid-validation-batch.v1",
            "status": "IN_PROGRESS",
            "batch_index": index,
            "completed_cases": len(rows),
            "results": rows,
            "total_cost_usd": round(total_cost, 6),
        }
        OUT.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validated = sum(1 for row in rows if row["final"]["status"] == "VALIDATED_GOLD")
    manual = len(rows) - validated
    output = {
        "schema_version": "story-defect-paid-validation-batch.v1",
        "status": "COMPLETE",
        "batch_index": index,
        "batch_count": 7,
        "case_count": len(rows),
        "selection": "2 cases per each of 15 recipes; 7 batches cover all 210 cases exactly once",
        "models": {
            "primary": PRIMARY_MODEL,
            "adjudicator": ADJUDICATOR_MODEL,
        },
        "summary": {
            "validated_gold": validated,
            "needs_manual_adjudication": manual,
            "primary_calls": primary_calls,
            "adjudicator_calls": adjudicator_calls,
            "validation_rate": validated / len(rows),
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": rows,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "batch_index": index,
        "summary": output["summary"],
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
