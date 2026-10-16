"""SERA v0.7: bind blind extractor reports to the complete sentence ledger.

This consumes a previously generated report; it NEVER calls a model. Each
event quote is anchored to every sentence it overlaps, including
multi-sentence witness statements. The bindings are candidate evidence,
not human review and never an authority to apply reducer events.
"""
from __future__ import annotations

from experiments.sera.coverage import (
    CoverageError, prose_hash, validate_report,
)
from experiments.sera.sentence_ledger_v06 import (
    scanner, build_pending_ledger, validate_ledger,
)
from experiments.sera.scene_assurance_v06 import audit_scene

SCHEMA = "sera.independent-ledger-binding.v0.7"


def bind_independent_to_ledger(*, prose: str, scene_key: str,
                               entry_revision: int,
                               registry: dict[str, list[str]],
                               candidate_lexicon: dict[str, list[str]],
                               report: dict) -> dict:
    """Attach a STRICT INDEPENDENT report without asserting semantic truth."""
    validated = validate_report(
        report, role="INDEPENDENT", prose=prose,
        scene_key=scene_key, entry_revision=entry_revision,
    )
    scan = scanner(
        prose=prose, registry=registry,
        candidate_lexicon=candidate_lexicon,
    )
    ledger = build_pending_ledger(scan)
    events = []
    links = []
    for raw in validated["events"]:
        eid = "independent:" + raw["local_id"]
        s, e = raw["start"], raw["end"]
        related = []
        for sentence in scan["sentences"]:
            a, b = max(s, sentence["start"]), min(e, sentence["end"])
            while a < b and prose[a].isspace():
                a += 1
            while b > a and prose[b-1].isspace():
                b -= 1
            if a >= b:
                continue
            related.append(sentence["id"])
            events.append({
                "event_id": eid, "sentence_id": sentence["id"],
                "start": a, "end": b, "quote": prose[a:b],
            })
        if not related:
            raise CoverageError("INDEPENDENT_EVENT_HAS_NO_SENTENCE_EVIDENCE")
        links.append({
            "event_id": eid,
            "local_id": raw["local_id"],
            "type": raw["type"], "modality": raw["modality"],
            "argument_shape_is_unadjudicated": True,
            "sentence_ids": related,
            "reported_event_at": raw["at"],
            "time_is_independently_grounded": False,
        })
        for row in ledger["rows"]:
            if row["sentence_id"] in related and eid not in row["event_ids"]:
                row["event_ids"].append(eid)
                row["reason"] = (
                    "UNREVIEWED: independent model event overlaps this "
                    "sentence; semantic classification is not confirmed"
                )
    # Keep every disposition AMBIGUOUS. The model has not qualified the
    # sentence as NO_CHANGE, CLAIM or PHYSICAL_EVENT by independent review.
    checked = validate_ledger(
        prose=prose, scan=scan, ledger=ledger, evidence_events=events,
    )
    reported_refs = {row["entity_ref"] for row in validated["mentions"]}
    findings = []
    for hint in scan["hints"]:
        expected_ref = hint["ref"]
        if expected_ref.startswith("candidate:"):
            expected_ref = "new:" + expected_ref.split(":", 1)[1]
        if expected_ref not in reported_refs:
            findings.append(
                "INDEPENDENT_UNREPORTED_SCAN_HINT:"
                + hint["sentence_id"] + ":" + hint["ref"]
            )
    # A reported *new* entity outside the lexicon is still a legitimate
    # candidate, not a confirmed error. It needs independent noun evidence.
    scanned_new = {
        "new:" + h["ref"].split(":", 1)[1]
        for h in scan["hints"] if h["tier"] == "T2"
    }
    for mention in validated["mentions"]:
        if (mention["entity_ref"].startswith("new:") and
            mention["entity_ref"] not in scanned_new):
            findings.append("INDEPENDENT_OPEN_WORLD_ENTITY_REVIEW:"
                            + mention["entity_ref"])
    out = audit_scene(
        prose=prose, scene_key=scene_key, entry_revision=entry_revision,
        registry=registry, candidate_lexicon=candidate_lexicon,
        ledger=ledger, evidence_events=events,
        independent_only=report,
    )
    return {
        "schema": SCHEMA,
        "scene_key": scene_key, "prose_sha256": prose_hash(prose),
        "entry_revision": entry_revision,
        "source_role": "INDEPENDENT",
        "source_report_sha256": __import__("hashlib").sha256(
            __import__("experiments.sera.world_state_v02",
                       fromlist=["canonical"]).canonical(report).encode("utf-8")
        ).hexdigest(),
        "event_links": links,
        "ledger_validation": checked,
        "scan_findings": sorted(set(findings)),
        "assurance": out,
        "status": "HOLD",
        "human_adjudicated": False,
        "semantic_recall_proven": False,
        "canonical_commit_authorized": False,
        "model_calls_during_binding": 0,
        "world_db_writes": 0,
    }
