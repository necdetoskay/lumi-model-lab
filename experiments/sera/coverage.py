"""SERA M2: model-agnostic, fail-closed coverage reconciliation.

Independent extraction is provided as a report, not run here. Agreement between
models is NOT semantic proof or permission to commit state. All offsets are
Python string codepoint offsets into the exact frozen prose.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any

from experiments.sera.state_engine import EVENT_TYPES

EXTRACTION_SCHEMA = "sera.extraction.v0.1"
SUPPORTED_ROLES = frozenset({"MENTIONED", "PRESENT", "INTERACTED", "REPORTED_ONLY"})
SUPPORTED_MODALITIES = frozenset({
    "ASSERTED", "REPORTED", "HYPOTHETICAL", "NEGATED", "UNCERTAIN",
})
# M2 records these explicitly even though the M1 reducer does not implement them.
DISCOVERY_TYPES = EVENT_TYPES | {"MOVE_OBJECT", "UNMAPPED_STATE_CHANGE"}
REDUCER_ELIGIBLE = EVENT_TYPES
SOURCE_ROLES = frozenset({"WRITER", "INDEPENDENT"})

MENTION_FIELDS = frozenset({"entity_ref", "role", "start", "end"})
EVENT_FIELDS = frozenset({
    "local_id", "type", "arguments", "at", "modality", "start", "end",
})
REPORT_FIELDS = frozenset({
    "schema", "source_role", "scene_key", "entry_revision", "prose_sha256",
    "mentions", "events",
})


class CoverageError(ValueError):
    """Invalid extraction input, distinct from a model's semantic disagreement."""
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require(check: bool, code: str) -> None:
    if not check:
        raise CoverageError(code)


def prose_hash(prose: str) -> str:
    return sha256(prose.encode("utf-8")).hexdigest()


def _only_keys(item: dict, keys: frozenset[str], label: str) -> None:
    require(isinstance(item, dict) and set(item) == keys, f"{label}_SCHEMA_INVALID")


def _span(prose: str, start: Any, end: Any, code: str) -> str:
    require(type(start) is int and type(end) is int and
            0 <= start < end <= len(prose), f"{code}_OFFSET_INVALID")
    quote = prose[start:end]
    require(quote.strip() != "", f"{code}_EMPTY_SPAN")
    return quote


def _is_primitive(value: Any) -> bool:
    # Typed event arguments must be stable, JSON-compatible primitives.
    # Lists/objects are disallowed to prevent unstable canonical matching.
    return value is None or type(value) in (str, int, float, bool)


def validate_report(report: dict, *, role: str, prose: str,
                    scene_key: str, entry_revision: int) -> dict:
    """Validate the exact independent or writer extraction contract.

    The independent report receives prose, registry and permitted event taxonomy
    but not the writer report. This function cannot prove actual blinding.
    """
    _only_keys(report, REPORT_FIELDS, "REPORT")
    require(role in SOURCE_ROLES and report["source_role"] == role,
            "SOURCE_ROLE_INVALID")
    require(report["schema"] == EXTRACTION_SCHEMA, "REPORT_VERSION_INVALID")
    require(isinstance(scene_key, str) and scene_key and
            report["scene_key"] == scene_key, "SCENE_KEY_MISMATCH")
    require(type(entry_revision) is int and
            type(report["entry_revision"]) is int and
            entry_revision == report["entry_revision"], "ENTRY_REVISION_MISMATCH")
    require(report["prose_sha256"] == prose_hash(prose),
            "PROSE_FINGERPRINT_MISMATCH")
    require(isinstance(report["mentions"], list), "MENTIONS_NOT_LIST")
    require(isinstance(report["events"], list), "EVENTS_NOT_LIST")

    mentions = []
    seen_mentions = set()
    for mention in report["mentions"]:
        _only_keys(mention, MENTION_FIELDS, "MENTION")
        entity_ref = mention["entity_ref"]
        require(isinstance(entity_ref, str) and entity_ref and
                not entity_ref.isspace(), "MENTION_ENTITY_INVALID")
        require(mention["role"] in SUPPORTED_ROLES, "MENTION_ROLE_INVALID")
        _span(prose, mention["start"], mention["end"], "MENTION")
        identity = (entity_ref, mention["role"], mention["start"], mention["end"])
        require(identity not in seen_mentions, "DUPLICATE_MENTION")
        seen_mentions.add(identity)
        mentions.append(mention)

    seen_ids = set()
    events = []
    for event in report["events"]:
        _only_keys(event, EVENT_FIELDS, "EVENT")
        eid = event["local_id"]
        require(isinstance(eid, str) and eid, "EVENT_LOCAL_ID_INVALID")
        require(eid not in seen_ids, "DUPLICATE_EVENT_LOCAL_ID")
        seen_ids.add(eid)
        require(event["type"] in DISCOVERY_TYPES, "EVENT_TYPE_INVALID")
        require(event["modality"] in SUPPORTED_MODALITIES,
                "EVENT_MODALITY_INVALID")
        require(event["at"] is None or
                (type(event["at"]) is int and event["at"] >= 0),
                "EVENT_TIME_INVALID")
        args = event["arguments"]
        require(isinstance(args, dict) and all(
            isinstance(k, str) and k and _is_primitive(v)
            for k, v in args.items()
        ), "EVENT_ARGUMENTS_INVALID")
        _span(prose, event["start"], event["end"], "EVENT")
        events.append(event)

    return {"mentions": mentions, "events": events}


def _mention_key(mention: dict) -> tuple:
    # Presence qualification is part of identity; it cannot silently upgrade
    # a reported statement into physical presence.
    return (mention["entity_ref"], mention["role"])


def _event_key(event: dict) -> tuple:
    # Include time/modality; a conflicting time or epistemic class must fail.
    return (
        event["type"],
        tuple(sorted(event["arguments"].items())),
        event["at"],
        event["modality"],
    )


def _serialize_key(key: tuple) -> str:
    import json
    return json.dumps(key, ensure_ascii=False, separators=(",", ":"))


def _find_lexical_refs(prose: str, registry: dict[str, list[str]]) -> set[str]:
    """Cheap supplementary detector, not complete coreference resolution."""
    found: set[str] = set()
    for entity_ref, aliases in registry.items():
        require(isinstance(entity_ref, str) and entity_ref and
                isinstance(aliases, list) and
                bool(aliases) and
                all(isinstance(a, str) and a.strip() for a in aliases),
                f"REGISTRY_INVALID:{entity_ref}")
        for alias in aliases:
            # \w boundaries also work for accented letters under Python Unicode.
            if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)",
                         prose, re.IGNORECASE):
                found.add(entity_ref)
                break
    return found


def _find_object_candidate_spans(
    prose: str, registry: dict[str, list[str]],
    candidate_lexicon: dict[str, list[str]],
    reported_entity_refs: set[str],
) -> list[dict]:
    """Conservative noun candidate scan; never promotes text into state.

    Matches known registry aliases first so a 'clock' inside 'platform clock'
    is not falsely treated as an additional object. A lexicon is an advisory
    coverage aid, not a guarantee of open-world entity completeness.
    """
    protected: list[tuple[int, int]] = []
    for aliases in registry.values():
        for alias in aliases:
            for match in re.finditer(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)", prose, re.IGNORECASE
            ):
                protected.append(match.span())
    findings = []
    for candidate_id, aliases in candidate_lexicon.items():
        require(isinstance(candidate_id, str) and candidate_id.startswith("candidate:"),
                "OBJECT_CANDIDATE_ID_INVALID")
        require(isinstance(aliases, list) and bool(aliases) and
                all(isinstance(alias, str) and alias.strip() for alias in aliases),
                f"OBJECT_CANDIDATE_ALIASES_INVALID:{candidate_id}")
        # If a model discovered the new entity, it enters the ordinary
        # authority-controlled new-entity reconciliation path instead.
        promoted_proposal_id = "new:" + candidate_id.split(":", 1)[1]
        if promoted_proposal_id in reported_entity_refs:
            continue
        seen_positions = set()
        for alias in aliases:
            for match in re.finditer(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)", prose, re.IGNORECASE
            ):
                start, end = match.span()
                if any(pstart <= start and end <= pend
                       for pstart, pend in protected):
                    continue
                if (start, end) in seen_positions:
                    continue
                seen_positions.add((start, end))
                findings.append({
                    "code": "UNREPORTED_OBJECT_CANDIDATE",
                    "candidate_ref": candidate_id,
                    "start": start, "end": end,
                    "evidence_quote": prose[start:end],
                })
    return sorted(findings, key=lambda x: (x["start"], x["end"]))


def reconcile(*, prose: str, scene_key: str, entry_revision: int,
              registry: dict[str, list[str]],
              writer: dict, independent: dict,
              candidate_lexicon: dict[str, list[str]] | None = None) -> dict:
    """Compare reports; fail closed without ever mutating canonical state."""
    require(isinstance(prose, str) and prose.strip(), "PROSE_REQUIRED")
    w = validate_report(writer, role="WRITER", prose=prose,
                        scene_key=scene_key, entry_revision=entry_revision)
    i = validate_report(independent, role="INDEPENDENT", prose=prose,
                        scene_key=scene_key, entry_revision=entry_revision)
    lexical = _find_lexical_refs(prose, registry)
    findings: list[dict] = []

    wm = {_mention_key(x) for x in w["mentions"]}
    im = {_mention_key(x) for x in i["mentions"]}
    registered_mentions = {key[0] for key in wm | im}
    if candidate_lexicon:
        findings.extend(_find_object_candidate_spans(
            prose, registry, candidate_lexicon, registered_mentions,
        ))
    for entity_ref in sorted(lexical - registered_mentions):
        findings.append({"code": "UNREPORTED_KNOWN_ENTITY",
                         "entity_ref": entity_ref})
    for source_name, extras in (("WRITER", wm-im), ("INDEPENDENT", im-wm)):
        for entity_ref, role in sorted(extras):
            findings.append({"code": "MENTION_DISAGREEMENT", "only_in": source_name,
                             "entity_ref": entity_ref, "role": role})
    for entity_ref, role in sorted(wm | im):
        if entity_ref.startswith("new:"):
            findings.append({"code": "NEW_ENTITY_REQUIRES_AUTHORITY",
                             "entity_ref": entity_ref, "role": role})
        elif entity_ref not in registry:
            findings.append({"code": "UNREGISTERED_ENTITY_REF",
                             "entity_ref": entity_ref, "role": role})

    we = Counter(_event_key(x) for x in w["events"])
    ie = Counter(_event_key(x) for x in i["events"])
    for key in sorted(set(we) | set(ie), key=_serialize_key):
        w_count, i_count = we[key], ie[key]
        if w_count != i_count:
            findings.append({"code": "EVENT_DISAGREEMENT",
                             "signature": _serialize_key(key),
                             "writer_count": w_count, "independent_count": i_count})
        typ, _, at, modality = key
        if typ not in REDUCER_ELIGIBLE:
            findings.append({"code": "UNSUPPORTED_REDUCER_EVENT",
                             "signature": _serialize_key(key)})
        if at is None:
            findings.append({"code": "EVENT_TIME_NOT_GROUNDED",
                             "signature": _serialize_key(key)})
        if modality != "ASSERTED":
            findings.append({"code": "EVENT_NOT_ASSERTED_AS_FACT",
                             "signature": _serialize_key(key)})

    # Even perfect matching means only structural reconciliation, NOT truth.
    status = "HOLD" if findings else "RECONCILED_PENDING_SEMANTIC"
    return {
        "schema": "sera.coverage.v0.1",
        "scene_key": scene_key,
        "entry_revision": entry_revision,
        "prose_sha256": prose_hash(prose),
        "status": status,
        "semantic_verification": "NOT_RUN",
        "commit_authorized": False,
        "writer_mention_count": len(w["mentions"]),
        "independent_mention_count": len(i["mentions"]),
        "writer_event_count": len(w["events"]),
        "independent_event_count": len(i["events"]),
        "matched_event_count": sum((we & ie).values()),
        "lexical_known_entities": sorted(lexical),
        "findings": findings,
    }


def extraction_metrics(*, expected_mentions: set[tuple],
                       found_mentions: set[tuple],
                       expected_events: set[tuple],
                       found_events: set[tuple]) -> dict:
    """Measure against manually adjudicated GOLD, not against another model."""
    def score(expected: set, found: set) -> dict:
        tp = len(expected & found)
        fp = len(found - expected)
        fn = len(expected - found)
        # 0/0 has no evidential coverage: report null rather than fictitious 1.0.
        p = tp / (tp + fp) if tp + fp else None
        r = tp / (tp + fn) if tp + fn else None
        return {"tp": tp, "fp": fp, "fn": fn,
                "precision": p, "recall": r}

    return {
        "entity_role_mentions": score(expected_mentions, found_mentions),
        "typed_events": score(expected_events, found_events),
    }


def report_signatures(report: dict) -> dict:
    return {
        "mentions": {_mention_key(x) for x in report["mentions"]},
        "events": {_event_key(x) for x in report["events"]},
    }
