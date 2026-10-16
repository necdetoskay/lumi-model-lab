"""SERA v0.6 — scene-assurance entrypoint, findings and bounded repair routes.

Composes existing M2 reconcile with independent lexical/cue surveillance,
full sentence audit, and planned-vs-written alignment. All decisions remain
advisory. No network, model execution, world reduction or SQLite writes.
"""
from __future__ import annotations

from experiments.sera.coverage import CoverageError, prose_hash, reconcile
from experiments.sera.sentence_ledger_v06 import (
    scanner, build_pending_ledger, validate_ledger,
)
from experiments.sera.scene_contract_v06 import align_intents

SCHEMA = "sera.scene-assurance.v0.6"
ROUTES = {
    "LEDGER_SEMANTIC_AMBIGUITY": "REVIEW_SENTENCE",
    "LEDGER_NO_CHANGE_WITH_SIGNIFICANT_CUE": "REVIEW_OMITTED_DELTA",
    "REQUIRED_INTENT_NOT_IN_PROSE": "VERIFY_THEN_WRITER_PATCH",
    "CONTRADICTED_INTENT": "REVIEW_PLOT_CONTRADICTION",
    "INTENT_NEEDS_SEMANTIC_REVIEW": "TARGETED_EVIDENCE_PROBE",
    "UNPLANNED_STATE_CHANGE": "TARGETED_UNPLANNED_DELTA_REVIEW",
    "UNREPORTED_OBJECT_CANDIDATE": "REVIEW_MISSING_OBJECT",
    "UNREPORTED_KNOWN_ENTITY": "REVIEW_MISSING_ENTITY",
    "MENTION_DISAGREEMENT": "TARGETED_ENTITY_CHECK",
    "EVENT_DISAGREEMENT": "TARGETED_EVENT_CHECK",
    "NEW_ENTITY_REQUIRES_AUTHORITY": "REVIEW_ENTITY_INTRODUCTION",
    "ASPECT_NOT_REGISTERED": "REVIEW_ASPECT_SCHEMA",
}
# This is a repair recommendation budget, NOT a model output token limit.
MAX_REPORT_REPAIR_ROUNDS = 2


def classify(finding: str) -> str:
    for prefix, action in ROUTES.items():
        if finding.startswith(prefix):
            return action
    return "HUMAN_REVIEW_UNCLASSIFIED"


def repair_routes(findings: list[str], *, prior_rounds: int = 0) -> list[dict]:
    """No automated content patch is executed. Bounded recommendation only."""
    if type(prior_rounds) is not int or prior_rounds < 0:
        raise CoverageError("REPAIR_ROUNDS_INVALID")
    results = []
    for code in sorted(set(findings)):
        action = classify(code)
        if prior_rounds >= MAX_REPORT_REPAIR_ROUNDS:
            action = "HUMAN_REVIEW_REPAIR_BUDGET_EXHAUSTED"
        results.append({
            "finding": code,
            "suggested_action": action,
            "max_report_repair_rounds": MAX_REPORT_REPAIR_ROUNDS,
            "automatic_state_commit": False,
            "may_invent_new_story_event": False,
        })
    return results


def audit_scene(*, prose: str, scene_key: str, entry_revision: int,
                registry: dict[str, list[str]],
                candidate_lexicon: dict[str, list[str]],
                ledger: dict | None = None,
                evidence_events: list[dict] | None = None,
                contract: dict | None = None,
                alignments: list[dict] | None = None,
                unplanned_changes: list[dict] | None = None,
                writer: dict | None = None,
                independent: dict | None = None,
                prior_repair_rounds: int = 0) -> dict:
    """One conservative offline scene gate, mandatory exact text partitions.

    An unreviewed ledger intentionally produces HOLD, even with perfect
    structural sentence accounting and no known entity omission.
    """
    if not isinstance(scene_key, str) or not scene_key:
        raise CoverageError("ASSURANCE_SCENE_INVALID")
    if type(entry_revision) is not int or entry_revision < 0:
        raise CoverageError("ASSURANCE_REVISION_INVALID")
    scan = scanner(prose=prose, registry=registry,
                   candidate_lexicon=candidate_lexicon)
    current = ledger if ledger is not None else build_pending_ledger(scan)
    checked = validate_ledger(prose=prose, scan=scan, ledger=current,
                              evidence_events=evidence_events or [])
    findings = list(checked["findings"])
    if ledger is None:
        findings.append("LEDGER_ALL_SENTENCES_UNREVIEWED")
    if contract is not None:
        if (contract["scene_key"] != scene_key or
            contract["entry_revision"] != entry_revision):
            raise CoverageError("ASSURANCE_CONTRACT_SCENE_OR_REVISION_MISMATCH")
        if alignments is None or unplanned_changes is None:
            findings.append("SCENE_CONTRACT_NOT_ALIGNED")
            plan = None
        else:
            plan = align_intents(prose=prose, contract=contract,
                                 alignments=alignments,
                                 unplanned_changes=unplanned_changes)
            findings.extend(plan["findings"])
    else:
        if alignments is not None or unplanned_changes is not None:
            raise CoverageError("ASSURANCE_ALIGNMENT_WITHOUT_CONTRACT")
        plan = None
    m2 = None
    if writer is not None or independent is not None:
        if writer is None or independent is None:
            raise CoverageError("ASSURANCE_NEEDS_BOTH_REPORTS")
        m2 = reconcile(
            prose=prose, scene_key=scene_key, entry_revision=entry_revision,
            registry=registry, writer=writer, independent=independent,
            candidate_lexicon=candidate_lexicon,
        )
        if m2["status"] != "RECONCILED_PENDING_SEMANTIC":
            findings.append("M2_EXTRACTION_HOLD")
        findings.extend(x["code"] for x in m2["findings"])
    else:
        findings.append("INDEPENDENT_EXTRACTION_NOT_PERFORMED")

    # T2 sightings are *persistent audit candidates*, not registered entities.
    sightings = [{
        "ref": hint["ref"], "tier": "T2",
        "sentence_id": hint["sentence_id"], "start": hint["start"],
        "end": hint["end"], "quote": hint["quote"],
        "presence": "UNDETERMINED", "canonical_entity_created": False,
    } for hint in scan["hints"] if hint["tier"] == "T2"]

    unique = sorted(set(findings))
    return {
        "schema": SCHEMA,
        "scene_key": scene_key, "entry_revision": entry_revision,
        "prose_sha256": prose_hash(prose),
        "sentence_scan": scan,
        "ledger": current,
        "ledger_validation": checked,
        "t2_sightings": sightings,
        "scene_alignment": plan,
        "m2": m2,
        "findings": unique,
        "repair_suggestions": repair_routes(
            unique, prior_rounds=prior_repair_rounds,
        ),
        "status": "HOLD",
        "hold_reason": "SEMANTIC_COMPLETENESS_AND_CANON_AUTHORITY_NOT_PROVEN",
        "model_calls": 0, "world_db_writes": 0,
        "canonical_commit_authorized": False,
    }
