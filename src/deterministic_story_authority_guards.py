from __future__ import annotations

import re
from typing import Any

from src.story_defect_detection import segment_story


_FORMAL_COMMIT_PATTERNS = [
    re.compile(
        r"\b(?:provisional\s+|formal\s+|official\s+)?(?:record|entry|log)"
        r"\s+(?:has\s+been\s+|is\s+|was\s+)?(?:filed|accepted|approved|registered)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:filed|accepted|approved|registered)\s+"
        r"(?:the\s+)?(?:provisional\s+|formal\s+|official\s+)?(?:record|entry|log)\b",
        re.IGNORECASE,
    ),
]

_FORMAL_ACCEPT_PATTERNS = [
    re.compile(
        r"\b(?:reviewer|supervisor|mentor|officer|registrar)\b.{0,120}"
        r"\b(?:signed|accepted|approved)\b.{0,80}\b(?:entry|record|log)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:signed|accepted|approved)\s+(?:the\s+)?(?:entry|record|log)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:entry|record|log)\b.{0,80}\b(?:signed|accepted|approved)\b",
        re.IGNORECASE,
    ),
]

_RAW_OBSERVATION_PATTERNS = [
    re.compile(r"\b(?:readings?|measurements?|observations?)\b.{0,80}\b(?:logged|recorded|written|entered|timestamped)\b", re.IGNORECASE),
    re.compile(r"\b(?:logged|recorded|wrote|written)\b.{0,80}\b(?:readings?|measurements?|observations?|time|tide|temperature)\b", re.IGNORECASE),
    re.compile(r"\b(?:logbook|field\s+sheet|field\s+notes?)\b", re.IGNORECASE),
    re.compile(r"\b(?:five|four|three|two)\s+readings?\b", re.IGNORECASE),
]

_RAW_ERASURE_PATTERNS = [
    re.compile(r"\bblank\s+page\b", re.IGNORECASE),
    re.compile(r"\bnothing\s+(?:was\s+)?(?:recorded|logged|written)\b", re.IGNORECASE),
    re.compile(r"\bno\s+(?:raw\s+)?(?:notes?|readings?|measurements?|observations?)\b", re.IGNORECASE),
]

_FORMAL_QUALIFIERS = re.compile(
    r"\b(?:formal|reviewed|official|accepted|approved)\b",
    re.IGNORECASE,
)

_SETUP_HARD_OVERCLAIM_PATTERNS = [
    re.compile(
        r"\b(?:it|this|that|the\s+anomaly|the\s+offset)\s+"
        r"(?:is|was)\s+not\s+(?:a\s+|an\s+)?(?:single\s+)?(?:bad\s+)?"
        r"(?:setup|instrument(?:\s+error)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:setup|instrument(?:\s+error)?|instrumental\s+error)"
        r"\s+(?:is|was|has\s+been)\s+(?:ruled\s+out|excluded|impossible)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bsetup[-\s]independent\b", re.IGNORECASE),
    re.compile(
        r"\b(?:rules?\s+out|excludes?|eliminates?)\b.{0,80}"
        r"\b(?:setup|instrument(?:\s+error)?)\b",
        re.IGNORECASE,
    ),
]

_CAUSE_HARD_OVERCLAIM_PATTERNS = [
    re.compile(
        r"\b(?:proves?|proved|confirms?|confirmed|establishes?|established)\b"
        r".{0,80}\b(?:cause|caused|because|physical\s+cause)\b",
        re.IGNORECASE,
    ),
]

_RECURRENCE_HARD_OVERCLAIM_PATTERNS = [
    re.compile(
        r"\b(?:the\s+anomaly|the\s+offset|this\s+problem)\b.{0,80}"
        r"\b(?:always|recurs?|repeats?\s+every|happens?\s+every)\b",
        re.IGNORECASE,
    ),
]

_OTHER_BEACON_HARD_OVERCLAIM_PATTERNS = [
    re.compile(
        r"\b(?:other|all|multiple)\s+beacons?\b.{0,100}"
        r"\b(?:same\s+(?:problem|anomaly|offset)|share|show|have)\b",
        re.IGNORECASE,
    ),
]


def _smallest_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def _requires_reviewed_formal_state(authority_packet: dict[str, Any]) -> bool:
    rules = authority_packet.get("record_state_rules") or {}
    if not rules.get("chosen_branch_controls_formal_entry_state"):
        return False
    text = str(rules.get("branch_contracts") or {}).lower()
    return any(token in text for token in ("reviewed", "accepted", "formal entry", "formal record"))


def _ceiling_text(authority_packet: dict[str, Any]) -> str:
    unresolved = authority_packet.get("must_remain_unresolved") or {}
    return " ".join(
        str(unresolved.get(key) or "")
        for key in ("inference_ceiling", "unresolved_after_reversal")
    ).lower()


def run_deterministic_authority_guards(
    story: str,
    authority_packet: dict[str, Any],
) -> list[dict[str, Any]]:
    segments = segment_story(story)
    findings: list[dict[str, Any]] = []

    # Guard 1: formal reviewed state cannot be committed before review acceptance.
    if _requires_reviewed_formal_state(authority_packet):
        accepted = False
        for seg in segments:
            text = str(seg["text"])
            if any(p.search(text) for p in _FORMAL_ACCEPT_PATTERNS):
                accepted = True

            if not accepted:
                for pattern in _FORMAL_COMMIT_PATTERNS:
                    quote = _smallest_match(pattern, text)
                    if quote:
                        findings.append({
                            "guard_id": "formal_record_ordering",
                            "family": "record_state",
                            "severity": "serious",
                            "repair_scope": "local",
                            "span_ids": [str(seg["id"])],
                            "exact_quote": quote,
                            "reason": (
                                "Formal reviewed record state is asserted before "
                                "the required review/acceptance checkpoint is earned."
                            ),
                        })
                        break

    # Guard 2: raw observations cannot later be erased as a blank/no-notes state.
    raw_observations_exist = False
    for seg in segments:
        text = str(seg["text"])
        if any(p.search(text) for p in _RAW_OBSERVATION_PATTERNS):
            raw_observations_exist = True

        if raw_observations_exist and not _FORMAL_QUALIFIERS.search(text):
            for pattern in _RAW_ERASURE_PATTERNS:
                quote = _smallest_match(pattern, text)
                if quote:
                    findings.append({
                        "guard_id": "raw_observation_erasure",
                        "family": "record_state",
                        "severity": "major",
                        "repair_scope": "local",
                        "span_ids": [str(seg["id"])],
                        "exact_quote": quote,
                        "reason": (
                            "Raw observations already exist, so prose cannot "
                            "erase them as a blank/no-notes state. Only absence "
                            "of a reviewed formal record may remain true."
                        ),
                    })
                    break

    # Guard 3: only high-confidence definitive claims cross explicit inference ceilings.
    ceiling = _ceiling_text(authority_packet)
    hard_groups: list[tuple[str, list[re.Pattern[str]], str]] = []

    if "setup-independence" in ceiling or "setup" in ceiling or "instrument" in ceiling:
        hard_groups.append((
            "unresolved_setup_overclaim",
            _SETUP_HARD_OVERCLAIM_PATTERNS,
            "Setup/instrument explanations are explicitly unresolved, but the prose definitively excludes them.",
        ))
    if "physical cause" in ceiling or "cause" in ceiling:
        hard_groups.append((
            "unresolved_cause_overclaim",
            _CAUSE_HARD_OVERCLAIM_PATTERNS,
            "Physical cause is explicitly unresolved, but the prose states it as established.",
        ))
    if "recurrence" in ceiling:
        hard_groups.append((
            "unresolved_recurrence_overclaim",
            _RECURRENCE_HARD_OVERCLAIM_PATTERNS,
            "Recurrence is explicitly unresolved, but the prose states a recurring pattern as established.",
        ))
    if "other beacons" in ceiling or "other-beacon" in ceiling:
        hard_groups.append((
            "unresolved_scope_overclaim",
            _OTHER_BEACON_HARD_OVERCLAIM_PATTERNS,
            "Other-beacon anomaly scope is explicitly unresolved, but prose promotes it to fact.",
        ))

    seen: set[tuple[str, str]] = set()
    for seg in segments:
        text = str(seg["text"])
        for guard_id, patterns, reason in hard_groups:
            for pattern in patterns:
                quote = _smallest_match(pattern, text)
                if not quote:
                    continue
                key = (guard_id, str(seg["id"]))
                if key in seen:
                    break
                seen.add(key)
                findings.append({
                    "guard_id": guard_id,
                    "family": "epistemic_order",
                    "severity": "serious",
                    "repair_scope": "local",
                    "span_ids": [str(seg["id"])],
                    "exact_quote": quote,
                    "reason": reason,
                })
                break

    return findings
