"""SERA M2 gold-corpus scorer (offline; reports are synthetic, not live models)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import (
    EXTRACTION_SCHEMA, extraction_metrics, prose_hash, reconcile,
    report_signatures,
)

DEFAULT_FIXTURE = Path(__file__).parent / "fixtures/gold_mara_m2_v0.1.json"


def build_report(case: dict, role: str) -> dict:
    """Adapt synthetic fixture annotations to model report format."""
    prose = case["prose"]
    source = case[role.lower()]
    mentions = []
    for ref, kind, quote in source["mentions"]:
        start = prose.index(quote)
        mentions.append({
            "entity_ref": ref, "role": kind,
            "start": start, "end": start + len(quote),
        })
    events = []
    for idx, (kind, args, at, modality, quote) in enumerate(source["events"]):
        start = prose.index(quote)
        events.append({
            "local_id": f"{role.lower()}-{idx}",
            "type": kind, "arguments": args, "at": at,
            "modality": modality,
            "start": start, "end": start + len(quote),
        })
    return {
        "schema": EXTRACTION_SCHEMA, "source_role": role,
        "scene_key": case.get("scene_key", "hook_empty_platform"),
        "entry_revision": case.get("entry_revision", 0),
        "prose_sha256": prose_hash(prose),
        "mentions": mentions, "events": events,
    }


def gold_signatures(case: dict) -> dict:
    return {
        "mentions": {(ref, role) for ref, role in case["gold"]["mentions"]},
        "events": {
            (kind, tuple(sorted(args.items())), at, modality)
            for kind, args, at, modality in case["gold"]["events"]
        },
    }


def score_fixture(path: Path = DEFAULT_FIXTURE) -> dict:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if corpus.get("schema") != "sera.gold.v0.1" or (
        corpus.get("source_type") != "MANUALLY_ADJUDICATED_SYNTHETIC"
    ):
        raise ValueError("GOLD_SOURCE_UNVERIFIED")
    totals = {
        source: {
            group: {"tp": 0, "fp": 0, "fn": 0}
            for group in ("entity_role_mentions", "typed_events")
        }
        for source in ("WRITER", "INDEPENDENT")
    }
    rows = []
    for case in corpus["cases"]:
        reports = {role: build_report(case, role)
                   for role in ("WRITER", "INDEPENDENT")}
        coverage = reconcile(
            prose=case["prose"],
            scene_key=case.get("scene_key", "hook_empty_platform"),
            entry_revision=case.get("entry_revision", 0),
            registry=case["registry"],
            writer=reports["WRITER"], independent=reports["INDEPENDENT"],
        )
        gold = gold_signatures(case)
        scored = {}
        for source, report in reports.items():
            observed = report_signatures(report)
            metric = extraction_metrics(
                expected_mentions=gold["mentions"],
                found_mentions=observed["mentions"],
                expected_events=gold["events"],
                found_events=observed["events"],
            )
            scored[source] = metric
            for dimension, values in metric.items():
                for k in ("tp", "fp", "fn"):
                    totals[source][dimension][k] += values[k]
        rows.append({
            "case_id": case["id"],
            "status": coverage["status"],
            "findings": sorted({f["code"] for f in coverage["findings"]}),
            "gold_scores": scored,
            "commit_authorized": False,
        })

    for source, groups in totals.items():
        for dimension, values in groups.items():
            tp, fp, fn = values["tp"], values["fp"], values["fn"]
            values["precision"] = tp / (tp + fp) if tp + fp else None
            values["recall"] = tp / (tp + fn) if tp + fn else None

    return {
        "protocol": "sera.gold-calibration.m2.v0.1",
        "fixture": path.name,
        "data_identity": "HAND_AUTHORED_SIMULATED_REPORTS_NOT_LIVE_EXTRACTION",
        "case_count": len(rows),
        "rows": rows,
        "aggregate": totals,
        "can_infer_live_model_quality": False,
    }


def cli() -> None:
    parser = argparse.ArgumentParser(description="SERA offline synthetic gold scorer")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    print(json.dumps(score_fixture(args.fixture), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
