"""SERA v0.6 — plan-first scene contract and evidence-only intent alignment.

Planned events are intent, NOT events that happened. An UNPLANNED tracked
change is not automatically rejected or silently committed: it enters review.
Requires independently supplied evidence links; byte/codepoint matching is
deterministic but semantic entailment still needs external adjudication.
"""
from __future__ import annotations

from experiments.sera.coverage import CoverageError, prose_hash

SCHEMA = "sera.scene-contract.v0.6"
INTENT_KEYS = frozenset({
    "intent_id", "kind", "actor_ids", "object_refs", "required_in_prose",
    "epistemic", "notes",
})
ALIGNMENT_KEYS = frozenset({
    "intent_id", "status", "evidence", "reason",
})
MATCH = frozenset({"MATCHED", "MISSING", "CONTRADICTED", "UNCERTAIN"})
EVIDENCE_KEYS = frozenset({"start", "end", "quote"})
EPISTEMIC = frozenset({
    "OBSERVED_ACTION", "REPORTED_CLAIM", "HYPOTHESIS", "NARRATOR_FACT",
})
KINDS = frozenset({
    "OBSERVE", "COMMUNICATE", "WRITE", "OPEN", "CLOSE", "MOVE",
    "TRANSFER", "DISCOVER", "CHANGE_STATE", "KNOW", "WORLD_CHANGE",
    "FREEFORM_REVIEW_REQUIRED",
})


def check(flag, code):
    if not flag:
        raise CoverageError(code)


def make_contract(*, scene_key: str, entry_revision: int,
                  intents: list[dict], tracked_refs: list[str],
                  texture_freedom: str) -> dict:
    """Produce an app-supplied, reviewable contract before prose exists."""
    check(isinstance(scene_key, str) and scene_key and
          type(entry_revision) is int and entry_revision >= 0,
          "SCENE_CONTRACT_HEADER_INVALID")
    check(isinstance(intents, list) and isinstance(tracked_refs, list) and
          len(tracked_refs) == len(set(tracked_refs)) and
          all(isinstance(x, str) and x for x in tracked_refs) and
          isinstance(texture_freedom, str) and texture_freedom.strip(),
          "SCENE_CONTRACT_VALUES_INVALID")
    known = set(tracked_refs)
    seen = set()
    for intent in intents:
        check(isinstance(intent, dict) and set(intent) == INTENT_KEYS,
              "SCENE_INTENT_SCHEMA_INVALID")
        iid = intent["intent_id"]
        check(isinstance(iid, str) and iid and iid not in seen and
              intent["kind"] in KINDS and
              type(intent["required_in_prose"]) is bool and
              intent["epistemic"] in EPISTEMIC and
              isinstance(intent["notes"], str) and intent["notes"].strip() and
              all(isinstance(intent[field], list) and
                  all(isinstance(x, str) and x in known
                      for x in intent[field])
                  for field in ("actor_ids", "object_refs")),
              "SCENE_INTENT_INVALID")
        seen.add(iid)
    return {
        "schema": SCHEMA, "scene_key": scene_key,
        "entry_revision": entry_revision,
        "tracked_refs": tracked_refs,
        "texture_freedom": texture_freedom,
        "intents": intents,
        "planned_events_are_canon": False,
    }


def align_intents(*, prose: str, contract: dict, alignments: list[dict],
                  unplanned_changes: list[dict]) -> dict:
    """Check evidence spans and plan completeness; never decide actual truth."""
    check(isinstance(contract, dict) and contract.get("schema") == SCHEMA and
          contract.get("planned_events_are_canon") is False,
          "SCENE_CONTRACT_VERSION_INVALID")
    check(isinstance(alignments, list) and
          isinstance(unplanned_changes, list),
          "ALIGNMENT_INPUT_INVALID")
    intents = {x["intent_id"]: x for x in contract["intents"]}
    ids = [r.get("intent_id") for r in alignments if isinstance(r, dict)]
    check(len(ids) == len(intents) and set(ids) == set(intents) and
          len(ids) == len(set(ids)),
          "ALIGNMENT_INTENT_COVERAGE_INVALID")
    findings = []
    for row in alignments:
        check(isinstance(row, dict) and set(row) == ALIGNMENT_KEYS,
              "ALIGNMENT_FIELDS_INVALID")
        status = row["status"]
        check(status in MATCH and isinstance(row["reason"], str) and
              row["reason"].strip(), "ALIGNMENT_VALUES_INVALID")
        evidence = row["evidence"]
        if status == "MATCHED":
            check(isinstance(evidence, list) and len(evidence) > 0,
                  "ALIGNMENT_MATCH_MISSING_EVIDENCE")
            for e in evidence:
                check(isinstance(e, dict) and set(e) == EVIDENCE_KEYS and
                      type(e["start"]) is int and type(e["end"]) is int and
                      0 <= e["start"] < e["end"] <= len(prose) and
                      e["quote"] == prose[e["start"]:e["end"]],
                      "ALIGNMENT_EVIDENCE_NOT_IN_PROSE")
        else:
            check(evidence == [], "ALIGNMENT_NONMATCH_CANNOT_HAVE_EVIDENCE")
            if status == "MISSING" and intents[row["intent_id"]]["required_in_prose"]:
                findings.append(f"REQUIRED_INTENT_NOT_IN_PROSE:{row['intent_id']}")
            elif status == "CONTRADICTED":
                findings.append(f"CONTRADICTED_INTENT:{row['intent_id']}")
            elif status == "UNCERTAIN":
                findings.append(f"INTENT_NEEDS_SEMANTIC_REVIEW:{row['intent_id']}")
    for x in unplanned_changes:
        check(isinstance(x, dict) and set(x) == {
            "event_candidate_id", "start", "end", "quote", "reason",
        } and isinstance(x["event_candidate_id"], str) and
              x["event_candidate_id"] and
              isinstance(x["reason"], str) and x["reason"].strip() and
              type(x["start"]) is int and type(x["end"]) is int and
              0 <= x["start"] < x["end"] <= len(prose) and
              x["quote"] == prose[x["start"]:x["end"]],
              "ALIGNMENT_UNPLANNED_EVIDENCE_INVALID")
        findings.append(f"UNPLANNED_STATE_CHANGE:{x['event_candidate_id']}")
    return {
        "schema": "sera.scene-intent-alignment.v0.6",
        "scene_key": contract["scene_key"],
        "prose_sha256": prose_hash(prose),
        "alignments": alignments,
        "unplanned_changes": unplanned_changes,
        "findings": findings,
        "status": "HOLD" if findings else "STRUCTURAL_PASS_SEMANTIC_UNVERIFIED",
        "planned_events_committed": 0,
        "canonical_commit_authorized": False,
    }
