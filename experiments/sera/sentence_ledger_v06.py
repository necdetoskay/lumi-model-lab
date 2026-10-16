"""SERA v0.6 — evidence-led sentence ledger and independent candidate scanner.

Purpose: make every *sentence* reviewable and detectable entity/action hints
auditable. It does not prove semantic completeness, identify all implicit
entities, or authorize any world/event-state commit.

The scanner is heuristic/advisory. It NEVER registers T2 sightings as physical
world entities, assigns object attributes, or promotes a claim to a world fact.
"""
from __future__ import annotations

from hashlib import sha256
import re

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.sentence-ledger.v0.6"
ROLES = frozenset({"REGISTERED", "CANDIDATE_T2"})
DISPOSITIONS = frozenset({
    "STATE_EVENT", "KNOWLEDGE_EVENT", "CLAIM_ONLY", "NO_TRACKED_CHANGE",
    "TEXTURE", "AMBIGUOUS",
})
EVENT_DISPOSITIONS = frozenset({"STATE_EVENT", "KNOWLEDGE_EVENT"})
NO_EVENT_DISPOSITIONS = DISPOSITIONS - EVENT_DISPOSITIONS

# Multiword cues before single words. These are *hints*, not recognized events.
CUES = {
    "PHYSICAL_CHANGE": (r"\bclosed\b", r"\bopened\b", r"\bbroke\b",
        r"\bpainted\b", r"\bchanged\b", r"\bplaced\b", r"\bdropped\b",
        r"\bhanded\b", r"\bgave\b", r"\btook\b", r"\bmoved\b",
        r"\bturned\b", r"\bshut\b", r"\bclosed the case\b"),
    "DOCUMENT_CHANGE": (r"\bwrote\b", r"\badded\b", r"\bnoted\b",
        r"\bmarked\b", r"\brecorded\b", r"\btraced\b"),
    "EPISTEMIC": (r"\bsaid\b", r"\btold\b", r"\bclaimed\b",
        r"\breported\b", r"\basked\b", r"\banswered\b", r"\bread\b",
        r"\breminded\b", r"\bsaw\b", r"\bwatched\b", r"\bshows\b"),
    "PHYSICAL_INTERACTION": (r"\bheld\b", r"\bexamined\b", r"\bglanced\b",
        r"\btouched\b", r"\blooked\b", r"\bopened\b", r"\bclosed\b"),
}
TIME_PATTERN = re.compile(r"(?<!\d)\b(?:[01]?\d|2[0-3]):[0-5]\d\b(?!\d)")
PRONOUN_PATTERN = re.compile(
    r"\b(?:he|she|they|it|his|her|their|its|him|them|this|that)\b",
    re.IGNORECASE,
)
ABBREVIATIONS = frozenset({"mr", "mrs", "ms", "dr", "prof", "st", "vs", "etc"})


def check(condition, code):
    if not condition:
        raise CoverageError(code)


def _quoted_spans(prose: str, entries: list[dict]) -> bool:
    for e in entries:
        if (type(e.get("start")) is not int or type(e.get("end")) is not int
            or not 0 <= e["start"] < e["end"] <= len(prose)
            or e.get("quote") != prose[e["start"]:e["end"]]):
            return False
    return True


def sentences(prose: str) -> list[dict]:
    """Exact, non-overlapping source spans, with conservative punctuation split.

    A terminal punctuation mark is a boundary only when followed by quote
    closers and then whitespace/end. Supports multiple sentences on one line,
    nested dialogue and multi-line paragraphs; unknown segmentation quality
    remains a separate semantic concern.
    """
    check(isinstance(prose, str) and prose.strip(), "LEDGER_PROSE_REQUIRED")
    result = []
    start = 0
    i = 0
    end_quotes = '"”’\')]}'
    while i < len(prose):
        ch = prose[i]
        if ch in ".!?":
            if ch == ".":
                word = re.search(r"([A-Za-z]+)$", prose[start:i])
                if word and word.group(1).casefold() in ABBREVIATIONS:
                    i += 1
                    continue
                if i > 0 and i+1 < len(prose) and (
                    prose[i-1].isdigit() and prose[i+1].isdigit()
                ):
                    i += 1
                    continue
            j = i+1
            while j < len(prose) and prose[j] in end_quotes:
                j += 1
            if j == len(prose) or prose[j].isspace():
                left, right = start, j
                while left < right and prose[left].isspace():
                    left += 1
                while right > left and prose[right-1].isspace():
                    right -= 1
                if left < right:
                    result.append({
                        "id": f"s{len(result)+1:03d}",
                        "start": left, "end": right,
                        "quote": prose[left:right],
                    })
                start = j
                i = j
                continue
        i += 1
    left, right = start, len(prose)
    while left < right and prose[left].isspace():
        left += 1
    while right > left and prose[right-1].isspace():
        right -= 1
    if left < right:
        result.append({
            "id": f"s{len(result)+1:03d}", "start": left, "end": right,
            "quote": prose[left:right],
        })
    check(bool(result) and _quoted_spans(prose, result),
          "LEDGER_SENTENCE_SEGMENTATION_FAILED")
    # Verify even whitespace between segments contains no discarded prose.
    cursor = 0
    for item in result:
        check(not prose[cursor:item["start"]].strip(),
              "LEDGER_UNPARTITIONED_TEXT")
        cursor = item["end"]
    check(not prose[cursor:].strip(), "LEDGER_UNPARTITIONED_TEXT")
    return result


def _lexical_matches(prose: str, aliases: dict[str, list[str]]) -> list[dict]:
    matches = []
    for ref, words in aliases.items():
        check(isinstance(ref, str) and ref and isinstance(words, list) and
              bool(words) and all(isinstance(w, str) and w.strip()
                                  for w in words), f"LEDGER_LEXICON_INVALID:{ref}")
        for word in words:
            for m in re.finditer(r"(?<!\w)" + re.escape(word) + r"(?!\w)",
                                 prose, flags=re.IGNORECASE):
                matches.append({"ref": ref, "start": m.start(), "end": m.end(),
                                "quote": prose[m.start():m.end()]})
    # Prefer long composite aliases, then registered IDs as stable tie breaks.
    return sorted(matches, key=lambda x: (x["start"], -(x["end"]-x["start"]),
                                          x["ref"]))


def scanner(*, prose: str, registry: dict[str, list[str]],
            candidate_lexicon: dict[str, list[str]]) -> dict:
    """Find all known alias and candidate-noun occurrences, never guess roles."""
    spans = sentences(prose)
    known = _lexical_matches(prose, registry)
    candidates = _lexical_matches(prose, candidate_lexicon)
    for row in candidates:
        check(row["ref"].startswith("candidate:"),
              "LEDGER_CANDIDATE_ID_INVALID")
    # A known compound match suppresses a candidate only if the candidate's
    # entire occurrence is inside the known alias. E.g. 'platform clock'.
    candidates = [row for row in candidates if not any(
        k["start"] <= row["start"] and row["end"] <= k["end"] for k in known
    )]
    hints = []
    seen = set()
    for source, role in ((known, "REGISTERED"), (candidates, "CANDIDATE_T2")):
        for row in source:
            identity = (row["ref"], row["start"], row["end"], role)
            if identity in seen:
                continue
            seen.add(identity)
            parent = next((s for s in spans
                           if s["start"] <= row["start"] and
                           row["end"] <= s["end"]), None)
            if parent is None:
                # A sentence boundary splitting a known entity is a HOLD,
                # not grounds for discarding it.
                raise CoverageError("LEDGER_ENTITY_CROSSES_SENTENCE")
            hints.append({**row, "tier": "T2" if role == "CANDIDATE_T2" else
                          "REGISTERED", "role": role, "sentence_id": parent["id"],
                          "physical_presence": "UNDETERMINED",
                          "canonical_entity_created": False})
    hints.sort(key=lambda x: (x["start"], x["end"], x["ref"]))
    cue_items = []
    for s in spans:
        cues = []
        for family, expressions in CUES.items():
            for expression in expressions:
                for m in re.finditer(expression, s["quote"], flags=re.IGNORECASE):
                    cues.append({
                        "family": family, "start": s["start"]+m.start(),
                        "end": s["start"]+m.end(),
                        "quote": s["quote"][m.start():m.end()],
                    })
        times = [{
            "start": s["start"]+m.start(),
            "end": s["start"]+m.end(),
            "quote": m.group(0), "narrative_action_time": "NOT_PROVEN",
        } for m in TIME_PATTERN.finditer(s["quote"])]
        pronouns = [{
            "start": s["start"]+m.start(), "end": s["start"]+m.end(),
            "quote": m.group(0), "antecedent": "UNRESOLVED",
        } for m in PRONOUN_PATTERN.finditer(s["quote"])]
        cue_items.append({
            "sentence_id": s["id"], "cues": cues,
            "time_expressions": times, "pronouns": pronouns,
            "object_refs": sorted({h["ref"] for h in hints
                                   if h["sentence_id"] == s["id"]}),
        })
    return {
        "schema": "sera.entity-candidate-scan.v0.6",
        "prose_sha256": prose_hash(prose),
        "sentences": spans, "hints": hints, "sentence_cues": cue_items,
        "canonical_entities_added": 0,
        "semantic_completeness_proven": False,
    }


def build_pending_ledger(scan: dict) -> dict:
    """Create a complete structural ledger with honest UNREVIEWED status."""
    return {
        "schema": SCHEMA, "prose_sha256": scan["prose_sha256"],
        "rows": [{
            "sentence_id": s["id"], "disposition": "AMBIGUOUS",
            "event_ids": [], "candidate_refs": sorted({
                h["ref"] for h in scan["hints"] if h["sentence_id"] == s["id"]
            }), "reason": "UNREVIEWED: independent semantic review required",
        } for s in scan["sentences"]],
        "status": "HOLD_SEMANTIC_UNREVIEWED",
        "canonical_commit_authorized": False,
    }


def validate_ledger(*, prose: str, scan: dict, ledger: dict,
                    evidence_events: list[dict]) -> dict:
    """Validate exact once-per-sentence coverage; never assert semantic truth.

    Each event must link to exactly one sentence or explicit multiple sentence
    IDs; it must contain an actual quoted span. Hints must be accounted for
    in the corresponding row even if their meaning remains ambiguous.
    """
    check(isinstance(scan, dict) and scan.get("prose_sha256") == prose_hash(prose),
          "LEDGER_SCAN_SOURCE_MISMATCH")
    check(isinstance(ledger, dict) and set(ledger) == {
        "schema", "prose_sha256", "rows", "status",
        "canonical_commit_authorized",
    }, "LEDGER_SCHEMA_INVALID")
    check(ledger["schema"] == SCHEMA and
          ledger["prose_sha256"] == prose_hash(prose),
          "LEDGER_SOURCE_MISMATCH")
    check(ledger["canonical_commit_authorized"] is False,
          "LEDGER_CANNOT_AUTHORIZE_COMMIT")
    check(isinstance(ledger["rows"], list) and
          isinstance(evidence_events, list), "LEDGER_ROWS_INVALID")
    units = scan["sentences"]
    ids = [s["id"] for s in units]
    rows = ledger["rows"]
    check(len(rows) == len(ids) and
          [r.get("sentence_id") for r in rows if isinstance(r, dict)] == ids,
          "LEDGER_SENTENCE_COVERAGE_GAP_OR_DUPLICATE")
    by_id = {s["id"]: s for s in units}
    events = {}
    for e in evidence_events:
        check(isinstance(e, dict) and set(e) == {
            "event_id", "sentence_id", "start", "end", "quote",
        }, "LEDGER_EVIDENCE_EVENT_SCHEMA_INVALID")
        eid, sid = e["event_id"], e["sentence_id"]
        check(isinstance(eid, str) and eid and eid not in events and
              sid in by_id and _quoted_spans(prose, [e]) and
              by_id[sid]["start"] <= e["start"] and
              e["end"] <= by_id[sid]["end"],
              "LEDGER_EVENT_EVIDENCE_INVALID")
        events[eid] = e
    flags = []
    linked = set()
    for row in rows:
        check(set(row) == {"sentence_id", "disposition", "event_ids",
                           "candidate_refs", "reason"},
              "LEDGER_ROW_SCHEMA_INVALID")
        sid = row["sentence_id"]
        disp = row["disposition"]
        check(disp in DISPOSITIONS and
              isinstance(row["reason"], str) and row["reason"].strip() and
              isinstance(row["event_ids"], list) and
              len(set(row["event_ids"])) == len(row["event_ids"]) and
              all(isinstance(x, str) and x for x in row["event_ids"]) and
              isinstance(row["candidate_refs"], list) and
              len(set(row["candidate_refs"])) == len(row["candidate_refs"]),
              "LEDGER_ROW_VALUES_INVALID")
        if disp in EVENT_DISPOSITIONS:
            check(bool(row["event_ids"]), "LEDGER_EVENT_ROW_MISSING_EVENT")
        elif row["event_ids"]:
            check(disp == "AMBIGUOUS", "LEDGER_NON_EVENT_HAS_EVENTS")
            flags.append("LEDGER_AMBIGUOUS_LINKED_EVENTS")
        for eid in row["event_ids"]:
            check(eid in events and
                  events[eid]["sentence_id"] == sid and eid not in linked,
                  "LEDGER_EVENT_LINK_INVALID")
            linked.add(eid)
        needed = {h["ref"] for h in scan["hints"]
                  if h["sentence_id"] == sid}
        check(set(row["candidate_refs"]) == needed,
              "LEDGER_ENTITY_HINT_UNACCOUNTED")
        cues = next(x for x in scan["sentence_cues"]
                    if x["sentence_id"] == sid)
        if disp in ("TEXTURE", "NO_TRACKED_CHANGE") and (
            cues["cues"] or any(h["tier"] == "T2" for h in scan["hints"]
                               if h["sentence_id"] == sid)):
            flags.append(f"LEDGER_NO_CHANGE_WITH_SIGNIFICANT_CUE:{sid}")
        if disp == "AMBIGUOUS":
            flags.append(f"LEDGER_SEMANTIC_AMBIGUITY:{sid}")
    check(linked == set(events), "LEDGER_UNLINKED_EVENT_EVIDENCE")
    return {
        "schema": "sera.sentence-ledger-validation.v0.6",
        "prose_sha256": prose_hash(prose),
        "total_sentences": len(ids),
        "accounted_sentences": len(rows),
        "event_evidence_count": len(events),
        "candidate_sightings": len(scan["hints"]),
        "findings": sorted(set(flags)),
        "status": "HOLD" if flags else "STRUCTURAL_PASS_SEMANTIC_UNVERIFIED",
        "semantic_completeness_proven": False,
        "canonical_commit_authorized": False,
    }
