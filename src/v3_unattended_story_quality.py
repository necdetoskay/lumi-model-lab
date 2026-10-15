"""Automatic model-audit -> bounded model-repair -> model-recheck.

No story-specific edits, no manual approval, no provider access directly.
Live callbacks must be executed under separately authorized one-call guards.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable

from src.deterministic_story_authority_guards import run_deterministic_authority_guards
from src.generate import count_words
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.storyforge.runtime import _apply_local_repairs, _normalize_audit

AUDIT_MODEL = "openai/gpt-5.6-luna"
REPAIR_MODEL = "openai/gpt-5.6-sol"
AUDIT_INSTRUCTIONS = (
    "Audit story coherency not prose length. Compare numerical claims "
    "about counts of observations, measurements and actions against "
    "the actually narrated events. Check negation before treating "
    "uncertainty as a claim. Cover all nine defect families and "
    "return serious/critical exact-quote grounded findings."
)
MAX_REPAIRS = 3


class QualityStop(RuntimeError):
    pass


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_hard(story, authority_packet):
    by_id = {s["id"]:s["text"] for s in segment_story(story)}
    active, negated = [], []
    for finding in run_deterministic_authority_guards(story, authority_packet):
        quote = finding.get("exact_quote", "")
        is_negated = False
        if finding["guard_id"] == "unresolved_cause_overclaim":
            for sid in finding.get("span_ids", []):
                text = by_id.get(sid, "")
                # Only a locally negated matched phrase, not an unrelated
                # negation elsewhere, can suppress this regex false positive.
                for match in re.finditer(re.escape(quote), text, re.I):
                    before = text[max(0, match.start()-42):match.start()]
                    # The regex quote itself begins with "established:"
                    # in the confirmed false-positive pattern. The adjacent
                    # negation is directly before that word.
                    if (
                        quote.lower().startswith("established:")
                        and re.search(r"\bnot\s+$", before, re.I)
                    ):
                        is_negated = True
        if is_negated:
            negated.append(finding)
        else:
            active.append(finding)
    return active, negated


def _semantic_audit(story, packet, audit):
    payload = audit(
        story=story, authority_packet=packet,
        families=list(DEFECT_FAMILIES),
        audit_policy=AUDIT_INSTRUCTIONS,
    )
    if not isinstance(payload, dict):
        raise QualityStop("INVALID_AUDIT_RESPONSE")
    try:
        return _normalize_audit(payload, segment_story(story))
    except (ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise QualityStop("INVALID_AUDIT_CONTRACT") from exc


def qualify(*, story: str, writer_result: dict, approved: dict,
            audit: Callable, repair: Callable) -> dict:
    if not story.strip() or writer_result.get("story", "").strip() != story.strip():
        raise QualityStop("STORY_SOURCE_MISMATCH")
    if writer_result.get("writer_model") != "aion-labs/aion-3.5-mini":
        raise QualityStop("WRONG_WRITER_MODEL")
    if writer_result.get("source_spine_run_id") != approved.get("source_run_id"):
        raise QualityStop("SPINE_PROVENANCE_MISMATCH")
    if (approved.get("human_review") or {}).get("verdict") != "APPROVE":
        raise QualityStop("MISSING_APPROVED_SPINE")
    if (approved.get("gate") or {}).get("decision") != "ACCEPT":
        raise QualityStop("SPINE_GATE_NOT_ACCEPTED")
    if writer_result.get("status") not in (
        "writer_generated", "writer_generated_deterministic_check_failed",
    ):
        raise QualityStop("ORIGINAL_WRITER_STATUS_INVALID")
    checks = writer_result.get("deterministic_checks") or {}
    if checks.get("non_empty") is not True or checks.get("title_present") is not True:
        raise QualityStop("ORIGINAL_STORY_STRUCTURE_INVALID")
    if writer_result.get("next_stage_authorized") is not False:
        raise QualityStop("WRITER_AUTHORITY_DRIFT")
    original_hash = fingerprint(story)
    packet = build_story_authority_packet_v2(approved)
    hard, dismissed_negations = _safe_hard(story, packet)
    first = _semantic_audit(story, packet, audit)
    findings = hard + first
    accepted = story
    patches = []
    if findings:
        if len(findings) > MAX_REPAIRS:
            raise QualityStop("TOO_MANY_BLOCKING_FINDINGS")
        if any(f.get("repair_scope") != "local" for f in findings):
            raise QualityStop("NONLOCAL_DEFECT_REQUIRES_REPLAN")
        proposal = repair(
            story=story, authority_packet=packet,
            confirmed_local_defects=findings,
            policy={"minimal_exact_replacements_only":True,
                    "no_other_event_change":True,
                    "length_is_nonblocking":True},
        )
        rows = proposal.get("repairs") if isinstance(proposal, dict) else None
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_REPAIRS:
            raise QualityStop("INVALID_REPAIR_MODEL_OUTPUT")
        by_id = {s["id"]:s["text"] for s in segment_story(story)}
        for row in rows:
            old, new = row.get("old"), row.get("new")
            if not isinstance(old,str) or not isinstance(new,str):
                raise QualityStop("BAD_MODEL_REPLACEMENT")
            if max(len(old), len(new)) > 250 or abs(count_words(new)-count_words(old)) > 25:
                raise QualityStop("MODEL_REPAIR_EXCEEDS_BOUNDS")
            if not any(old in by_id.get(sid, "")
                       for f in findings for sid in f.get("span_ids", [])):
                raise QualityStop("MODEL_REPAIR_NOT_IN_FLAGGED_SPAN")
        try:
            accepted, patches = _apply_local_repairs(story, proposal)
        except RuntimeError as exc:
            raise QualityStop("UNSAFE_MODEL_REPLACEMENT") from exc
        post_hard, _ = _safe_hard(accepted, packet)
        if post_hard:
            raise QualityStop("POST_REPAIR_HARD_FINDINGS")
        if _semantic_audit(accepted, packet, audit):
            raise QualityStop("POST_REPAIR_SEMANTIC_FINDINGS")
    words = count_words(accepted)
    lo, hi = (int(approved["episode_spine"][field])
              for field in ("target_words_min", "target_words_max"))
    return {
        "status":"AUTOMATED_ENGLISH_COHERENCE_ACCEPTED",
        "accepted_english_story":accepted,
        "original_writer_status_unchanged":writer_result["status"],
        "source_story_sha256":original_hash,
        "accepted_story_sha256":fingerprint(accepted),
        "audit_model":AUDIT_MODEL,
        "repair_model":REPAIR_MODEL if patches else None,
        "confirmed_findings":len(findings),
        "false_positive_negations":len(dismissed_negations),
        "model_generated_repairs":patches,
        "word_count":words,
        "length_warning":not lo <= words <= hi,
        "length_blocking":False,
        "translation_authorized":False,
        "world_state_commit_authorized":False,
    }
