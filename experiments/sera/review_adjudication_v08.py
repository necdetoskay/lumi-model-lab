"""SERA v0.8 — blind human-review staging and non-authorizing disagreement queue.

Two independent reviews can document sentence-level facts without exposing
the original nine analyst suggestions to either reviewer. Full structural
validation requires an answer (including explicit no-event classifications)
for EVERY source sentence and EVERY lexical entity hint. Agreement is only
advisory, not authenticated gold, not event approval or WorldStore authority.

No API calls, state commits, provider-specific options, or token limits.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256

from experiments.sera.coverage import CoverageError
from experiments.sera.sentence_review_packet_v07 import SCHEMA as PACKET_SCHEMA
from experiments.sera.sentence_ledger_v06 import DISPOSITIONS
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.human-annotation.v0.8"
ENTITY_DECISIONS = frozenset({
    "PHYSICALLY_PRESENT", "MENTIONED_ONLY", "REPORTED_ONLY",
    "NOT_ENTITY", "AMBIGUOUS",
})
EVENT_TYPES = frozenset({
    "OBSERVE", "DISCOVER", "COMMUNICATE", "WRITE", "OPEN", "CLOSE",
    "MOVE", "TRANSFER", "CHANGE_STATE", "KNOWLEDGE_UPDATE",
    "CLAIM_MENTION", "UNMAPPED",
})
EPISTEMIC = frozenset({
    "OBSERVED_ACTION", "REPORTED_CLAIM", "NARRATOR_ASSERTION",
    "HYPOTHESIS", "NEGATED", "UNCERTAIN",
})
EFFECTS = frozenset({
    "NONE", "OBJECT", "DOCUMENT", "CHARACTER_KNOWLEDGE",
    "WORLD", "UNKNOWN",
})
EVENT_LABELED = frozenset({"STATE_EVENT", "KNOWLEDGE_EVENT", "CLAIM_ONLY"})
HIGH_RISK_CUES = frozenset({
    "PHYSICAL_CHANGE", "DOCUMENT_CHANGE", "EPISTEMIC",
})
HIGH_RISK_WORDS = frozenset({
    "candidate:bench", "candidate:pencil",
})


def require(value, code):
    if not value:
        raise CoverageError(code)


def _span_in_sentence(row: dict, span: dict) -> bool:
    return (
        type(span.get("start")) is int and type(span.get("end")) is int
        and row["start"] <= span["start"] < span["end"] <= row["end"]
        and isinstance(span.get("quote"), str)
        and row["quote"][span["start"]-row["start"]:
                         span["end"]-row["start"]] == span["quote"]
    )


def blank_annotation(packet: dict, *, reviewer_alias: str) -> dict:
    """Blind review form: NO previous analyst event suggestions or answers."""
    require(isinstance(packet, dict) and packet.get("schema") == PACKET_SCHEMA
            and packet.get("review_status") == "UNREVIEWED"
            and packet.get("adjudicated_gold") is False
            and packet.get("canonical_commit_authorized") is False,
            "ANNOTATION_PACKET_NOT_UNREVIEWED")
    require(isinstance(reviewer_alias, str) and reviewer_alias.strip(),
            "ANNOTATION_REVIEWER_REQUIRED")
    rows = []
    for source in packet["sentences"]:
        rows.append({
            "sentence_id": source["sentence_id"],
            "start": source["start"], "end": source["end"],
            "quote": source["quote"],
            "disposition": "UNREVIEWED",
            "entity_decisions": [{
                "ref": hint["ref"], "start": hint["start"],
                "end": hint["end"], "quote": hint["quote"],
                "decision": "UNREVIEWED", "reason": "",
            } for hint in source["entity_hints"]],
            "events": [],
            "notes": "",
        })
    return {
        "schema": SCHEMA,
        "scene_key": packet["scene_key"],
        "prose_sha256": packet["prose_sha256"],
        "source_packet_sha256": packet["packet_sha256"],
        "reviewer_alias": reviewer_alias,
        "review_source": "CLAIMED_HUMAN_UNATTESTED",
        "rows": rows,
        "status": "IN_PROGRESS",
        "gold_status": "NOT_GOLD",
        "canonical_commit_authorized": False,
    }


def validate_annotation(*, packet: dict, annotation: dict,
                        require_complete: bool = False) -> dict:
    """Strict, source-bound and coverage-preserving review validator.

    Reviewer alias and packet hash are NOT identity authentication. A fully
    marked form is still 'human review CLAIMED', pending real attestation.
    """
    require(isinstance(annotation, dict) and set(annotation) == {
        "schema", "scene_key", "prose_sha256", "source_packet_sha256",
        "reviewer_alias", "review_source", "rows", "status", "gold_status",
        "canonical_commit_authorized",
    }, "ANNOTATION_SCHEMA_INVALID")
    require(annotation["schema"] == SCHEMA
            and annotation["scene_key"] == packet["scene_key"]
            and annotation["prose_sha256"] == packet["prose_sha256"]
            and annotation["source_packet_sha256"] == packet["packet_sha256"]
            and isinstance(annotation["reviewer_alias"], str)
            and annotation["reviewer_alias"].strip()
            and annotation["review_source"] == "CLAIMED_HUMAN_UNATTESTED"
            and annotation["status"] == "IN_PROGRESS"
            and annotation["gold_status"] == "NOT_GOLD"
            and annotation["canonical_commit_authorized"] is False,
            "ANNOTATION_SOURCE_OR_AUTHORITY_INVALID")
    rows = annotation["rows"]
    source = packet["sentences"]
    require(isinstance(rows, list) and len(rows) == len(source),
            "ANNOTATION_SENTENCE_COUNT_INVALID")
    all_events = {}
    missing = []
    risk = []
    event_count = 0
    for row, original in zip(rows, source):
        require(isinstance(row, dict) and set(row) == {
            "sentence_id", "start", "end", "quote", "disposition",
            "entity_decisions", "events", "notes",
        } and all(row[k] == original[k] for k in (
            "sentence_id", "start", "end", "quote"
        )), "ANNOTATION_SENTENCE_SOURCE_MISMATCH")
        sid = row["sentence_id"]
        require(row["disposition"] == "UNREVIEWED" or
                row["disposition"] in DISPOSITIONS,
                "ANNOTATION_DISPOSITION_INVALID")
        require(isinstance(row["notes"], str)
                and isinstance(row["entity_decisions"], list)
                and isinstance(row["events"], list)
                and len(row["entity_decisions"]) ==
                len(original["entity_hints"]),
                "ANNOTATION_ROW_VALUES_INVALID")
        for mention, hint in zip(row["entity_decisions"],
                                 original["entity_hints"]):
            require(isinstance(mention, dict) and set(mention) == {
                "ref", "start", "end", "quote", "decision", "reason",
            } and all(mention[k] == hint[k] for k in (
                "ref", "start", "end", "quote"
            )), "ANNOTATION_ENTITY_EVIDENCE_MISMATCH")
            require(mention["decision"] == "UNREVIEWED" or
                    mention["decision"] in ENTITY_DECISIONS,
                    "ANNOTATION_ENTITY_DECISION_INVALID")
            require(isinstance(mention["reason"], str),
                    "ANNOTATION_ENTITY_REASON_INVALID")
            if mention["decision"] != "UNREVIEWED":
                require(bool(mention["reason"].strip()),
                        "ANNOTATION_ENTITY_REASON_REQUIRED")
            elif row["disposition"] != "UNREVIEWED":
                risk.append(f"HINT_UNREVIEWED:{sid}:{mention['ref']}")
        local_ids = set()
        for event in row["events"]:
            require(isinstance(event, dict) and set(event) == {
                "event_id", "event_type", "start", "end", "quote",
                "epistemic", "effect", "entity_refs", "reason",
            }, "ANNOTATION_EVENT_SCHEMA_INVALID")
            require(isinstance(event["event_id"], str) and
                    event["event_id"].strip() and
                    event["event_id"] not in local_ids and
                    event["event_type"] in EVENT_TYPES and
                    event["epistemic"] in EPISTEMIC and
                    event["effect"] in EFFECTS and
                    isinstance(event["reason"], str) and
                    event["reason"].strip() and
                    isinstance(event["entity_refs"], list) and
                    all(isinstance(x, str) and x for x in
                        event["entity_refs"]) and
                    len(event["entity_refs"]) ==
                    len(set(event["entity_refs"])) and
                    _span_in_sentence(row, event),
                    "ANNOTATION_EVENT_INVALID")
            local_ids.add(event["event_id"])
            signature = (
                event["event_type"], event["epistemic"],
                event["effect"], tuple(sorted(event["entity_refs"])),
            )
            previous = all_events.setdefault(event["event_id"], signature)
            require(previous == signature,
                    "ANNOTATION_CROSS_SENTENCE_EVENT_CONFLICT")
            event_count += 1
        if row["disposition"] == "UNREVIEWED":
            require(not row["events"] and all(
                e["decision"] == "UNREVIEWED"
                for e in row["entity_decisions"]
            ), "ANNOTATION_PARTIAL_ROW_MISLABELED")
            missing.append(sid)
            continue
        if row["disposition"] in ("STATE_EVENT", "KNOWLEDGE_EVENT"):
            require(bool(row["events"]), "ANNOTATION_EVENT_EXPECTED")
        if row["disposition"] in ("TEXTURE", "NO_TRACKED_CHANGE"):
            require(not row["events"], "ANNOTATION_NO_CHANGE_HAS_EVENT")
        # A sentence may contain a physical action and a reported claim;
        # the single disposition is a summary, not a complete label vector.
        if row["events"] and row["disposition"] not in EVENT_LABELED:
            risk.append(f"ANNOTATION_EVENT_LABEL_DISAGREEMENT:{sid}")
        if row["disposition"] in ("TEXTURE", "NO_TRACKED_CHANGE"):
            if any(c["family"] in HIGH_RISK_CUES
                   for c in original["cue_hints"]):
                risk.append(f"ANNOTATION_POSSIBLE_MISSED_EVENT:{sid}")
        for mention in row["entity_decisions"]:
            if (mention["ref"] in HIGH_RISK_WORDS and
                mention["decision"] in ("NOT_ENTITY", "MENTIONED_ONLY")):
                risk.append(f"ANNOTATION_T2_DOWNGRADED:{sid}:{mention['ref']}")
    if require_complete:
        require(not missing and not any(
            "HINT_UNREVIEWED:" in x for x in risk
        ), "ANNOTATION_NOT_COMPLETE")
    return {
        "schema": "sera.annotation-validation.v0.8",
        "reviewer_alias": annotation["reviewer_alias"],
        "source_packet_sha256": packet["packet_sha256"],
        "sentence_count": len(rows),
        "reviewed_sentence_count": len(rows) - len(missing),
        "unreviewed_sentence_ids": missing,
        "reviewed_event_span_count": event_count,
        "distinct_event_ids": len(all_events),
        "risk_findings": sorted(set(risk)),
        "fully_reviewed_claimed": not missing and
            not any(x.startswith("HINT_UNREVIEWED:") for x in risk),
        "reviewer_identity_authenticated": False,
        "status": "READY_FOR_INDEPENDENT_COMPARISON_UNATTESTED"
            if not missing and not any(
                x.startswith("HINT_UNREVIEWED:") for x in risk
            ) else "PARTIAL_REVIEW_HOLD",
        "gold_qualified": False,
        "canonical_commit_authorized": False,
    }


def compare_annotations(*, packet: dict,
                        reviewer_a: dict, reviewer_b: dict) -> dict:
    """Enumerate exact per-sentence disagreements and high-risk consensus.

    No similarity claim means semantic truth. Even two identical model
    outputs cannot impersonate independent authenticated humans.
    """
    a = validate_annotation(packet=packet, annotation=reviewer_a)
    b = validate_annotation(packet=packet, annotation=reviewer_b)
    require(reviewer_a["reviewer_alias"] != reviewer_b["reviewer_alias"],
            "ADJUDICATION_DUPLICATE_ALIAS")
    differences = []
    agreed = []
    for ar, br in zip(reviewer_a["rows"], reviewer_b["rows"]):
        sid = ar["sentence_id"]
        if (ar["disposition"] == "UNREVIEWED" or
            br["disposition"] == "UNREVIEWED" or
            any(x["decision"] == "UNREVIEWED" for x in
                ar["entity_decisions"] + br["entity_decisions"])):
            differences.append({
                "sentence_id": sid, "category": "INCOMPLETE",
                "reason": "At least one reviewer did not finish",
            })
            continue
        components = []
        if ar["disposition"] != br["disposition"]:
            components.append("DISPOSITION")
        ahints = [(x["ref"], x["start"], x["end"], x["decision"])
                  for x in ar["entity_decisions"]]
        bhints = [(x["ref"], x["start"], x["end"], x["decision"])
                  for x in br["entity_decisions"]]
        if ahints != bhints:
            components.append("ENTITY_PRESENCE")
        def spans(row):
            return sorted((x["event_type"], x["start"], x["end"],
                           x["epistemic"], x["effect"],
                           tuple(sorted(x["entity_refs"])))
                          for x in row["events"])
        if spans(ar) != spans(br):
            components.append("EVENT_EVIDENCE_OR_SEMANTICS")
        if components:
            differences.append({
                "sentence_id": sid, "category": "DISAGREEMENT",
                "components": components,
            })
        else:
            agreed.append(sid)
    review_risk = sorted(set(a["risk_findings"] + b["risk_findings"]))
    requires = sorted(set(
        [x["sentence_id"] for x in differences] +
        [x.split(":")[1] for x in review_risk if len(x.split(":")) >= 2]
    ))
    return {
        "schema": "sera.adjudication-queue.v0.8",
        "scene_key": packet["scene_key"],
        "prose_sha256": packet["prose_sha256"],
        "source_packet_sha256": packet["packet_sha256"],
        "reviewer_aliases": [
            reviewer_a["reviewer_alias"], reviewer_b["reviewer_alias"],
        ],
        "reviewer_identities_authenticated": False,
        "review_summary": [a, b],
        "agreed_sentence_ids": agreed,
        "disagreements": differences,
        "risk_findings": review_risk,
        "priority_sentence_ids": requires,
        "human_adjudication_required_for_gold": True,
        "status": "NOT_GOLD_HUMAN_ADJUDICATION_REQUIRED",
        "canonical_commit_authorized": False,
        "production_db_writes": 0,
    }
