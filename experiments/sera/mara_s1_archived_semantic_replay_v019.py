"""SERA v0.19 actual Mara paid-evidence replay — ZERO NEW provider calls.

Consumes the original 28-sentence/25-event Gemini archive and the three
already-paid, independently source-checked Haiku advisories from v0.12.
Both are historical noncanonical artifacts; they never authorize a World
State or EventGraph commit, or constitute human gold.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.event_candidate_projection_v019 import project
from experiments.sera.mara_s1_candidate_corrections_v012 import (
    evidence_bundle_from_last_artifact, validate_model_bundle,
)
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.semantic_risks_v011 import audit_risks
from experiments.sera.world_state_v02 import canonical

EXPECTED_EVENTS = {
    "batch_004:s014:e1": ("MOVE", "OBSERVE"),
    "batch_006:s021:e1": ("COMMUNICATE", "WRITE"),
}


def _require(ok, code):
    if not ok:
        raise CoverageError(code)


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(*, full_report, last_haiku_archive):
    source = _load(PATH)
    prose = source["prose"]
    _require(prose_hash(prose) == EXPECTED_SHA and
             source.get("source_prose_sha256") == EXPECTED_SHA,
             "V019_REAL_MARA_SOURCE_CHANGED")
    _require(isinstance(full_report, dict) and
             full_report.get("schema") == "sera.blind-sweep-bound.v0.10" and
             full_report.get("source_prose_sha256") == EXPECTED_SHA and
             full_report.get("sentences_accounted_for") == 28 and
             len(full_report.get("candidate_events", [])) == 25 and
             full_report.get("canonical_commit_authorized") is False and
             full_report.get("world_state_writes") == 0,
             "V019_REAL_MARA_ORIGINAL_REPORT_INVALID")
    original_sha = sha256(canonical(full_report).encode("utf-8")).hexdigest()
    bundle = evidence_bundle_from_last_artifact(
        last_artifact=last_haiku_archive,
    )
    validate_model_bundle(bundle=bundle, prose=prose)
    audit = audit_risks(prose=prose, report=full_report)
    tasks = audit["targeted_tasks"]
    _require(len(tasks) == 3 and
             [x["task_id"] for x in tasks] ==
             ["task_001", "task_002", "task_003"],
             "V019_REAL_MARA_TASKS_MISMATCH")

    # Import pre-bound historical model evidence, DO NOT CALL a provider.
    advisories = [bundle[t["task_id"]]["bound_advisory"] for t in tasks]
    summary = {
        "schema": "sera.unattended-semantic-recovery.v0.18",
        "status": "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL",
        "source_prose_sha256": EXPECTED_SHA,
        "semantic_risk_count": 3,
        "independent_advisories": advisories,
        "advisory_sha256": sha256(
            canonical(advisories).encode("utf-8")
        ).hexdigest(),
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }
    projected = project(
        prose=prose, extraction_report=full_report,
        semantic_summary=summary,
    )
    _require({
        x["event_id"]: (x["original_candidate"]["kind"],
                        x["proposed_candidate"]["kind"])
        for x in projected["reclassification_proposals"]
    } == EXPECTED_EVENTS, "V019_REAL_MARA_EVENT_PROPOSAL_DRIFT")
    _require(sha256(canonical(full_report).encode("utf-8")).hexdigest()
             == original_sha,
             "V019_REAL_MARA_ORIGINAL_MUTATED")
    _require(projected["canonical_commit_authorized"] is False and
             projected["world_db_writes"] == 0 and
             projected["auto_entity_creations"] == 0 and
             projected["requires_manual_intervention"] is False and
             projected["status"] ==
             "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL",
             "V019_REAL_MARA_CANON_BOUNDARY_BROKEN")
    return {
        "schema": "sera.mara-actual-provider-replay.v0.19",
        "source_prose_sha256": EXPECTED_SHA,
        "original_event_count": len(full_report["candidate_events"]),
        "source_sentence_count": 28,
        "actual_haiku_task_count": len(advisories),
        "historical_provider_answer_reused": True,
        "new_provider_calls": 0,
        "new_provider_spend_usd": "0",
        "event_reclassifications": projected["reclassification_proposals"],
        "remaining_semantic_task_codes":
            projected["remaining_semantic_task_codes"],
        "unresolved_aspects": projected["unsupported_semantic_tasks"],
        "next_automatic_action": projected["next_automatic_action"],
        "original_report_sha256": original_sha,
        "projected_report_sha256": projected["projected_report_sha256"],
        "status": projected["status"],
        "human_gold_qualified": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-report", required=True, type=Path)
    parser.add_argument("--haiku-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    names = (
        "manifest.json",
        "reused-task-001.json",
        "reused-task-002.json",
        "task_003.json",
    )
    archive = {name: _load(args.haiku_directory / name) for name in names}
    result = run(
        full_report=_load(args.full_report),
        last_haiku_archive=archive,
    )
    if args.output.exists():
        raise CoverageError("V019_REAL_MARA_OUTPUT_EXISTS")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "actual_event_corrections":
            len(result["event_reclassifications"]),
        "remaining_semantic_tasks":
            len(result["remaining_semantic_task_codes"]),
        "new_provider_calls": 0, "world_db_writes": 0,
        "canonical_commit_authorized": False,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
