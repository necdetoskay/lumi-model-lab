"""SERA v0.25 — source-bound holder transfer and verified knowledge preview.

Only application-owned identity aliases and verified facts can qualify a
noncanonical simulation. Reported/negated/uncertain propositions never become
objective world facts. Changing HOLDER never silently changes OWNER.
No invented time, new entity, canonical event or production write.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import re
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.relation-knowledge-preview.v0.25"
KINDS = {"TRANSFER_HOLDER": "TRANSFER", "LEARN_FACT": "LEARN_FACT"}


def require(condition, error):
    if not condition:
        raise CoverageError(error)


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def source_mentions(phrase, aliases):
    return isinstance(aliases, list) and any(
        isinstance(s, str) and s.strip() and
        re.search(r"(?<!\w)" + re.escape(s) + r"(?!\w)",
                  phrase, re.IGNORECASE) is not None for s in aliases
    )


def preview(*, prose, world, extraction_report, relation_case):
    validate_world(world)
    original_sha = digest(world)
    require(isinstance(prose, str) and prose.strip() and
            isinstance(extraction_report, dict) and
            extraction_report.get("source_prose_sha256") ==
                prose_hash(prose) and
            isinstance(extraction_report.get("candidate_events"), list),
            "V025_SOURCE_REPORT_INVALID")
    require(isinstance(relation_case, dict) and
            set(relation_case) == {
                "entry", "registered_aliases", "verified_fact_registry",
                "transitions", "policy_id",
            } and relation_case["entry"] == world and
            isinstance(relation_case["registered_aliases"], dict) and
            isinstance(relation_case["verified_fact_registry"], dict) and
            isinstance(relation_case["transitions"], list) and
            isinstance(relation_case["policy_id"], str) and
            relation_case["policy_id"].strip(),
            "V025_TRUSTED_RELATION_POLICY_INVALID")
    sourced = [e for e in extraction_report["candidate_events"]
               if isinstance(e, dict) and e.get("kind") in (
                   "TRANSFER", "LEARN_FACT", "KNOWLEDGE_UPDATE",
               ) and e.get("effect") in (
                   "WORLD", "OBJECT", "CHARACTER_KNOWLEDGE",
               )]
    specs = relation_case["transitions"]
    require(len(specs) == len(sourced) and bool(sourced) and all(
        isinstance(t, dict) and set(t) == {
            "source_event_id", "operation", "object_id",
            "from_id", "to_id", "fact_id",
        } and t["operation"] in KINDS for t in specs
    ), "V025_SOURCE_TRANSITION_COVERAGE_INVALID")
    ids = {e.get("event_id"): e for e in sourced}
    require(len(ids) == len(sourced) and all(
        isinstance(k, str) and k for k in ids
    ) and len({t["source_event_id"] for t in specs}) == len(specs) and
            {t["source_event_id"] for t in specs} == set(ids),
            "V025_EVENT_BINDING_INVALID")
    chronological = sorted(sourced, key=lambda e: e["start"])
    require([t["source_event_id"] for t in specs] ==
            [e["event_id"] for e in chronological],
            "V025_SOURCE_ORDER_INVALID")
    projected = deepcopy(world)
    history = []

    def active(key, kind=None):
        value = projected["entities"].get(key)
        require(isinstance(value, dict) and value["lifecycle"] == "ACTIVE"
                and (kind is None or value["kind"] == kind),
                "V025_ACTIVE_ENTITY_MISSING")
        return value

    def named(key, quote):
        require(source_mentions(quote,
                relation_case["registered_aliases"].get(key)),
                "V025_ENTITY_NOT_NAMED_IN_SOURCE")

    for t in specs:
        ev = ids[t["source_event_id"]]
        quote = ev.get("quote")
        require(type(ev.get("start")) is int and
                type(ev.get("end")) is int and
                0 <= ev["start"] < ev["end"] <= len(prose) and
                prose[ev["start"]:ev["end"]] == quote and
                ev.get("epistemic") == "OBSERVED_ACTION" and
                isinstance(ev.get("entity_refs"), list),
                "V025_NONOBJECTIVE_OR_UNSOURCED_EVENT")
        if t["operation"] == "TRANSFER_HOLDER":
            require(ev["kind"] == "TRANSFER" and
                    ev.get("effect") in ("WORLD", "OBJECT") and
                    t["fact_id"] is None,
                    "V025_TRANSFER_OPERATION_MISMATCH")
            item_id, old, new = t["object_id"], t["from_id"], t["to_id"]
            require(all(isinstance(v, str) and v for v in (
                item_id, old, new,
            )) and old != new, "V025_TRANSFER_IDS_INVALID")
            obj, sender, recipient = (
                active(item_id), active(old, "CHARACTER"),
                active(new, "CHARACTER"),
            )
            require(obj["kind"] != "CHARACTER" and obj["holder"] == old
                    and obj["worn_by"] is None and
                    obj["location"] == sender["location"] ==
                        recipient["location"],
                    "V025_HOLDER_CAS_OR_COLOCATION_FAILED")
            require({item_id, old, new}.issubset(set(ev["entity_refs"])),
                    "V025_TRANSFER_SOURCE_REFS_MISSING")
            for key in (item_id, old, new):
                named(key, quote)
            require(not any(e["parent_id"] == item_id
                            for e in projected["entities"].values()),
                    "V025_NESTED_TRANSFER_GRAPH_UNQUALIFIED")
            obj["holder"] = new
            history.append({
                "event_id": ev["event_id"], "operation": "TRANSFER_HOLDER",
                "object_id": item_id, "old_holder": old,
                "new_holder": new, "owner_unchanged": True,
            })
        else:
            require(ev["kind"] in ("LEARN_FACT", "KNOWLEDGE_UPDATE") and
                    ev.get("effect") == "CHARACTER_KNOWLEDGE" and
                    t["object_id"] is None and t["from_id"] is None,
                    "V025_LEARNING_OPERATION_MISMATCH")
            actor_id, fact_id = t["to_id"], t["fact_id"]
            require(isinstance(actor_id, str) and
                    isinstance(fact_id, str) and fact_id and
                    actor_id in ev["entity_refs"],
                    "V025_LEARNING_SOURCE_ACTOR_MISSING")
            person = active(actor_id, "CHARACTER")
            named(actor_id, quote)
            fact = relation_case["verified_fact_registry"].get(fact_id)
            require(isinstance(fact, dict) and set(fact) == {
                "truth_status", "source_phrase",
            } and fact["truth_status"] == "VERIFIED" and
                    source_mentions(quote, [fact["source_phrase"]]),
                    "V025_FACT_UNVERIFIED_OR_UNGROUNDED")
            require(fact_id not in person["knowledge"],
                    "V025_FACT_ALREADY_KNOWN")
            person["knowledge"].append(fact_id)
            history.append({
                "event_id": ev["event_id"], "operation": "LEARN_FACT",
                "character_id": actor_id, "fact_id": fact_id,
                "model_supplied_truth": False,
            })
    validate_world(projected)
    require(digest(world) == original_sha, "V025_WORLD_MUTATED")
    return {
        "schema": SCHEMA, "status": "RELATIONS_FEASIBLE_NONCANONICAL",
        "prose_sha256": prose_hash(prose), "world_sha256": original_sha,
        "source_report_sha256": digest(extraction_report),
        "relation_policy_sha256": digest(relation_case),
        "transition_count": len(history), "transitions": history,
        "isolated_preview_state": projected,
        "semantic_truth_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0, "requires_manual_intervention": False,
    }
