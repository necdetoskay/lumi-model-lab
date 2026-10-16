"""SERA v0.6 — controlled aspects and epistemic claims, advisory-only.

Unknown properties are not model-selected JSON keys. A registered aspect may
define explicitly typed booleans or document append operations. This module
produces reviews/proposals only; existing v0.2 reducer has not been extended
and the proposals cannot be used as an application approval or DB event.
"""
from __future__ import annotations

from experiments.sera.coverage import CoverageError

ASPECTS = {
    "openable.case_open": {
        "entity_kind": "OBJECT",
        "type": "bool", "operation": "SET_KNOWN_VALUE",
    },
    "writable.entries": {
        "entity_kind": "OBJECT",
        "type": "list_of_proposition_ids", "operation": "APPEND",
    },
    "mechanical.functional": {
        "entity_kind": "OBJECT",
        "type": "enum", "operation": "SET_KNOWN_VALUE",
        "values": ("UNKNOWN", "WORKING", "STOPPED", "BROKEN"),
    },
}
ORIGINS = frozenset({"DIALOGUE", "DOCUMENT", "DIRECT_OBSERVATION",
                     "NARRATOR", "THOUGHT"})
TRUTH = frozenset({"UNVERIFIED", "VERIFIED", "DISPROVED", "UNKNOWN"})
STANCES = frozenset({"HEARD", "OBSERVED", "BELIEVES", "DOUBTS", "DENIES",
                     "KNOWS_CLAIM_EXISTS"})
TIERS = frozenset({"T0", "T1", "T2"})


def require(flag, code):
    if not flag:
        raise CoverageError(code)


def review_aspect_change(*, entity_id: str, entity_kind: str, aspect_id: str,
                         before, after, evidence_ref: str, entity_tier="T1") -> dict:
    """Build a typed proposal; keep source of truth untouched."""
    require(isinstance(entity_id, str) and entity_id and
            aspect_id in ASPECTS, "ASPECT_NOT_REGISTERED")
    spec = ASPECTS[aspect_id]
    require(entity_kind == spec["entity_kind"] and entity_tier in TIERS,
            "ASPECT_ENTITY_NOT_COMPATIBLE")
    require(isinstance(evidence_ref, str) and evidence_ref.strip(),
            "ASPECT_EVIDENCE_REQUIRED")
    typ = spec["type"]
    if typ == "bool":
        require(before is None or type(before) is bool,
                "ASPECT_OLD_VALUE_INVALID")
        require(type(after) is bool, "ASPECT_NEW_VALUE_INVALID")
    elif typ == "list_of_proposition_ids":
        require(isinstance(before, list) and
                all(isinstance(x, str) and x for x in before) and
                isinstance(after, list) and
                len(after) == len(before)+1 and
                after[:-1] == before and
                isinstance(after[-1], str) and after[-1] and
                after[-1] not in before,
                "ASPECT_APPEND_CONTRACT_INVALID")
    else:
        require((before is None or before in spec["values"]) and
                after in spec["values"], "ASPECT_ENUM_INVALID")
    require(before != after, "ASPECT_NO_OP")
    return {
        "schema": "sera.aspect-change-proposal.v0.6",
        "entity_id": entity_id, "entity_tier": entity_tier,
        "aspect_id": aspect_id, "old": before, "proposed": after,
        "evidence_ref": evidence_ref,
        "status": "PENDING_SCHEMA_AND_SEMANTIC_REVIEW",
        "existing_world_reducer_updated": False,
        "canonical_commit_authorized": False,
    }


def proposition(*, proposition_id: str, text: str, origin: str,
                source_entity_id: str, evidence_ref: str,
                truth: str = "UNVERIFIED") -> dict:
    require(all(isinstance(x, str) and x.strip() for x in (
        proposition_id, text, source_entity_id, evidence_ref
    )), "PROPOSITION_VALUES_INVALID")
    require(origin in ORIGINS and truth in TRUTH, "PROPOSITION_CATEGORY_INVALID")
    if truth == "VERIFIED":
        if origin in ("DIALOGUE", "DOCUMENT", "THOUGHT"):
            raise CoverageError("PROPOSITION_CLAIM_NOT_OBJECTIVE_FACT")
        # Neither narration nor observation supplied by an LLM is a trusted
        # objective-truth attestation. Keep the pilot uniformly provisional.
        raise CoverageError("PROPOSITION_TRUSTED_VERIFICATION_NOT_IMPLEMENTED")
    return {
        "schema": "sera.proposition.v0.6",
        "proposition_id": proposition_id, "text": text,
        "origin": origin, "source_entity_id": source_entity_id,
        "evidence_ref": evidence_ref, "truth": truth,
        "canonical_objective_fact": False,
        "approval_status": "PENDING_TRUSTED_REVIEW",
    }


def character_stance(*, character_id: str, proposition_record: dict,
                     stance: str, evidence_ref: str) -> dict:
    require(isinstance(character_id, str) and character_id and
            isinstance(proposition_record, dict) and
            proposition_record.get("schema") == "sera.proposition.v0.6" and
            stance in STANCES and
            isinstance(evidence_ref, str) and evidence_ref.strip(),
            "STANCE_VALUES_INVALID")
    return {
        "schema": "sera.character-stance.v0.6",
        "character_id": character_id,
        "proposition_id": proposition_record["proposition_id"],
        "stance": stance,
        "heard_or_believed_is_objective_fact": False,
        "evidence_ref": evidence_ref,
        "canonical_commit_authorized": False,
    }
