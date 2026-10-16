"""SERA v0.19 — source-bound event correction proposals + temporal recheck.

Consumes v0.18 automatically sourced independent model evidence, proposes
narrow corrections to an isolated COPY of uncommitted candidate events,
re-runs the v0.11 risk audit and optional v0.5 trusted temporal constraints.
NEVER alters prose, canonical state, EventGraph, DB, or existing evidence.
Independent model opinions are not gold or machine commit grants.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.semantic_risks_v011 import (
    audit_risks, bind_task_response, make_task_request,
)
from experiments.sera.temporal_domains_v05 import solve_temporal_domains
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.event-candidate-repair.v0.19"


def _check(ok, code):
    if not ok:
        raise CoverageError(code)


def _sha(obj):
    return sha256(canonical(obj).encode("utf-8")).hexdigest()


def _validated_advisory(*, audit, task, advisory):
    _check(isinstance(advisory, dict) and
           advisory.get("task_id") == task["task_id"] and
           advisory.get("source_prose_sha256") ==
           audit["source_prose_sha256"] and
           advisory.get("canonical_commit_authorized") is False and
           advisory.get("prior_candidate_unchanged") is True and
           advisory.get("status") == "HOLD_MODEL_RESPONSE_NOT_AUTHORITY",
           "V019_ADVISORY_SOURCE_OR_AUTHORITY_INVALID")
    spans = advisory.get("possible_source_evidence")
    _check(isinstance(spans, list) and spans and
           isinstance(spans[0], dict) and
           isinstance(spans[0].get("quote"), str),
           "V019_ADVISORY_EVIDENCE_MISSING")
    # Rebind all advisory fields independently to the exact original source.
    supplied = {
        "verdict": advisory.get("verdict_model_proposed"),
        "operation_kind": advisory.get("kind_model_proposed"),
        "effect": advisory.get("effect_model_proposed"),
        "evidence_quote": spans[0]["quote"],
        "reason": advisory.get("reason_model_proposed"),
    }
    rebound = bind_task_response(
        audit=audit,
        request=make_task_request(audit=audit, task_id=task["task_id"]),
        raw=supplied,
    )
    _check(_sha(rebound) == _sha(advisory),
           "V019_ADVISORY_SOURCE_REBIND_MISMATCH")
    return rebound


def _event_for_task(report, task, span):
    code = task["finding_code"]
    matches = [
        event for event in report["candidate_events"]
        if code.endswith(":" + event["event_id"]) and
        (":" + event["sentence_id"] + ":") in code and
        event["start"] < span["end"] and span["start"] < event["end"]
    ]
    return matches[0] if len(matches) == 1 else None


def project(*, prose, extraction_report, semantic_summary,
            temporal_case=None):
    """Produce proposed event corrections, no canonical permission."""
    audit = audit_risks(prose=prose, report=extraction_report)
    tasks = audit["targeted_tasks"]
    expected_status = (
        "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL" if tasks
        else "NO_TARGETED_RISKS_FOUND_NONCANONICAL"
    )
    _check(isinstance(semantic_summary, dict) and
           semantic_summary.get("schema") ==
           "sera.unattended-semantic-recovery.v0.18" and
           semantic_summary.get("status") == expected_status and
           semantic_summary.get("source_prose_sha256") == prose_hash(prose) and
           semantic_summary.get("semantic_risk_count") == len(tasks) and
           semantic_summary.get("canonical_commit_authorized") is False and
           semantic_summary.get("world_db_writes") == 0,
           "V019_SEMANTIC_SOURCE_INVALID")
    supplied = semantic_summary.get("independent_advisories")
    # This digest detects accidental/post-processor modification of the
    # v0.18 summary. It is NOT a production authentication signature.
    _check(semantic_summary.get("advisory_sha256") == _sha(supplied),
           "V019_ADVISORY_HASH_MISMATCH")
    _check(isinstance(supplied, list) and len(supplied) == len(tasks) and
           [x.get("task_id") for x in supplied if isinstance(x, dict)] ==
           [x["task_id"] for x in tasks],
           "V019_SEMANTIC_TASK_COVERAGE_INVALID")

    detached = deepcopy(extraction_report)
    replacements = []
    unresolved = []
    for task, advisory in zip(tasks, supplied):
        rebound = _validated_advisory(
            audit=audit, task=task, advisory=advisory,
        )
        code = task["finding_code"]
        evidence = rebound["possible_source_evidence"][0]
        event = _event_for_task(detached, task, evidence)
        desired = None
        verdict = rebound["verdict_model_proposed"]
        kind = rebound["kind_model_proposed"]
        effect = rebound["effect_model_proposed"]
        if (code.startswith("MOVE_KIND_EFFECT_MISMATCH:") and
            event is not None and event["kind"] == "MOVE" and
            event["effect"] == "CHARACTER_KNOWLEDGE" and
            verdict == "STATE_OBSERVATION" and kind == "OBSERVE" and
            effect == "CHARACTER_KNOWLEDGE"):
            desired = ("OBSERVE", "CHARACTER_KNOWLEDGE")
        elif (code.startswith("DOCUMENT_APPEND_MISREAD_AS_SPEECH:") and
              event is not None and event["kind"] == "COMMUNICATE" and
              event["effect"] == "NONE" and
              verdict == "DOCUMENT_WRITE" and kind == "WRITE" and
              effect == "DOCUMENT"):
            desired = ("WRITE", "DOCUMENT")
        elif (code.startswith("REPORTED_CLAIM_PHYSICAL_PROMOTION:") and
              event is not None and event["kind"] == "CLAIM_MENTION" and
              event["effect"] in ("OBJECT", "WORLD") and
              verdict == "REPORTED_CLAIM" and kind == "CLAIM_MENTION" and
              effect == "NONE"):
            desired = ("CLAIM_MENTION", "NONE")
        if desired is None:
            unresolved.append({
                "task_id": task["task_id"], "finding_code": code,
                "reason": "UNQUALIFIED_TYPED_REPAIR_OR_ASPECT_TRANSITION",
            })
            continue
        before = {"kind": event["kind"], "effect": event["effect"]}
        event["kind"], event["effect"] = desired
        replacements.append({
            "task_id": task["task_id"], "event_id": event["event_id"],
            "original_candidate": before,
            "proposed_candidate": {
                "kind": desired[0], "effect": desired[1],
            },
            "source_quote": event["quote"],
            "independent_evidence": evidence,
            "status": "UNCOMMITTED_PROPOSAL_REQUIRES_REEXTRACTION",
        })

    # Audit the projected (still untrusted!) event candidates once again.
    remaining = audit_risks(prose=prose, report=detached)
    temporal = None
    temporal_failure = None
    if temporal_case is not None:
        _check(isinstance(temporal_case, dict) and set(temporal_case) == {
            "entry", "scene_key", "scene_window", "events",
            "travel_minutes",
        }, "V019_TEMPORAL_INPUT_INVALID")
        try:
            temporal = solve_temporal_domains(
                entry=temporal_case["entry"],
                scene_key=temporal_case["scene_key"],
                scene_window=temporal_case["scene_window"],
                events=temporal_case["events"],
                travel_minutes=temporal_case["travel_minutes"],
            )
        except CoverageError as exc:
            temporal_failure = str(exc)
    blocked = bool(remaining["targeted_tasks"] or unresolved or
                   temporal_failure)
    return {
        "schema": SCHEMA,
        "prose_sha256": prose_hash(prose),
        "original_report_sha256": _sha(extraction_report),
        "projected_report_sha256": _sha(detached),
        "projected_report_noncanonical": detached,
        "reclassification_proposals": replacements,
        "unsupported_semantic_tasks": unresolved,
        "remaining_semantic_task_codes": [
            t["finding_code"] for t in remaining["targeted_tasks"]
        ],
        "temporal_domains": temporal,
        "temporal_failure": temporal_failure,
        "status": ("AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL"
                   if blocked else "CANDIDATES_STRUCTURALLY_CLEAN_NONCANONICAL"),
        "next_automatic_action": ("AUTO_EVENT_REEXTRACTION_OR_REPLAN"
                                  if blocked else "CONTINUE_FULL_SCENE_GATES"),
        "canonical_commit_authorized": False,
        "auto_entity_creations": 0,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }
