"""Frozen Mara S1 identity interpretation hypotheses for generic v0.14 gate.

These are REVIEW PROMPTS, not trusted ontology decisions. Rules use actual
anchored source sentences from the original paid model mention inventory.
Don't generalize literal entity names to other story worlds.
"""
from __future__ import annotations

from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA

SOURCE_SHA=EXPECTED_SHA

def rule(cls, anchor, action, relation="NONE",target=None):
    return {
        "classification":cls,
        "anchor":anchor,
        "relation":relation,
        "relation_target":target,
        "review_action":action,
    }

MARA_RULES={
    "new:archive":rule(
        "ABSTRACT_SOURCE_COLLECTION","archive",
        "ABSTRACT_DISCOURSE_NOT_PHYSICAL"),
    "new:bench":rule(
        "PHYSICAL_OBJECT_CANDIDATE","beside the bench",
        "INDEPENDENT_PHYSICAL_IDENTITY_REVIEW"),
    "new:entry_train_41":rule(
        "DOCUMENT_SUBENTRY_CANDIDATE","entry for train 41",
        "DOCUMENT_STRUCTURE_REVIEW",
        "POTENTIAL_DOCUMENT_ENTRY_OF","new:strike_record"),
    "new:mark":rule(
        "NEGATED_DOCUMENT_MARKER","There was no mark",
        "NEGATED_EVIDENCE_NOT_ENTITY"),
    "new:north_quay_station":rule(
        "REGION_ALIAS_CANDIDATE","At North Quay Station",
        "LOCATION_MAPPING_REVIEW",
        "EXISTING_REGION_NAME_CANDIDATE","north_quay_station"),
    "new:pencil":rule(
        "PHYSICAL_OBJECT_CANDIDATE","pencil move",
        "INDEPENDENT_PHYSICAL_IDENTITY_REVIEW"),
    "new:platform":rule(
        "SUBLOCATION_CANDIDATE","on the platform",
        "LOCATION_MAPPING_REVIEW",
        "POTENTIAL_LOCATION_WITHIN","north_quay_station"),
    "new:platform_record":rule(
        "DOCUMENT_ALIAS_CANDIDATE","platform record",
        "DOCUMENT_STRUCTURE_REVIEW",
        "POTENTIAL_ALIAS_OF","new:strike_record"),
    "new:sources":rule(
        "ABSTRACT_SOURCE_COLLECTION","sources say",
        "ABSTRACT_DISCOURSE_NOT_PHYSICAL"),
    "new:strike_mark":rule(
        "NEGATED_DOCUMENT_MARKER","no corresponding strike",
        "NEGATED_EVIDENCE_NOT_ENTITY"),
    "new:strike_record":rule(
        "DOCUMENT_COMPONENT_CANDIDATE","strike record",
        "DOCUMENT_STRUCTURE_REVIEW",
        "POTENTIAL_PART_OF","platform_clock"),
    "new:train":rule(
        "REPORTED_TOPIC_NONPHYSICAL","saw no train",
        "REPORTED_TOPIC_NOT_WORLD_TRUTH"),
    "new:train_41":rule(
        "REPORTED_TOPIC_NONPHYSICAL","train 41",
        "REPORTED_TOPIC_NOT_WORLD_TRUTH"),
    "new:vane_thumb":rule(
        "ANATOMICAL_PART_CANDIDATE","with his thumb",
        "ANATOMICAL_NOT_INVENTORY",
        "POTENTIAL_ANATOMICAL_PART_OF","vane"),
    "new:watch_case":rule(
        "OBJECT_COMPONENT_CANDIDATE","closed the case",
        "PART_OF_RELATION_REVIEW",
        "POTENTIAL_PART_OF","vane_watch"),
    "new:watch_hands":rule(
        "OBJECT_COMPONENT_CANDIDATE","Its hands remained at 02:07",
        "PART_OF_RELATION_REVIEW",
        "POTENTIAL_PART_OF","vane_watch"),
}
