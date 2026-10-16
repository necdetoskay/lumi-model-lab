"""SERA v0.25 source-based possession and verified knowledge, zero model cost."""
from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.relation_knowledge_preview_v025 import preview
from experiments.sera.tests.test_world_state_v02 import base
from experiments.sera.world_state_v02 import entity_template, validate

SOURCE = ("Vane handed the watch to Mara. "
          "Mara learned the station clock stopped.")
ALIASES = {
    "vane": ["Vane"], "mara": ["Mara"],
    "vane_watch": ["watch"],
}
FACTS = {"station_clock_stopped": {
    "truth_status": "VERIFIED", "source_phrase": "station clock stopped",
}}


def row(eid, kind, start, text, refs):
    return {"event_id": eid, "kind": kind,
            "effect": ("CHARACTER_KNOWLEDGE" if kind == "LEARN_FACT" else
                       "WORLD"),
            "epistemic": "OBSERVED_ACTION", "sentence_id": eid,
            "start": start, "end": start+len(text), "quote": text,
            "entity_refs": refs}


def report():
    first = "Vane handed the watch to Mara"
    second = "Mara learned the station clock stopped"
    return {"source_prose_sha256": prose_hash(SOURCE),
            "candidate_events": [
                row("handoff", "TRANSFER", SOURCE.index(first), first,
                    ["vane", "vane_watch", "mara"]),
                row("learning", "LEARN_FACT", SOURCE.index(second), second,
                    ["mara"]),
            ]}


def case(world):
    return {"entry": deepcopy(world), "policy_id": "trusted-lexicon-1",
            "registered_aliases": deepcopy(ALIASES),
            "verified_fact_registry": deepcopy(FACTS),
            "transitions": [
                {"source_event_id": "handoff",
                 "operation": "TRANSFER_HOLDER", "object_id": "vane_watch",
                 "from_id": "vane", "to_id": "mara", "fact_id": None},
                {"source_event_id": "learning", "operation": "LEARN_FACT",
                 "object_id": None, "from_id": None, "to_id": "mara",
                 "fact_id": "station_clock_stopped"},
            ]}


def check(*, world=None, proof=None, policy=None):
    w = world or base()
    return preview(prose=SOURCE, world=w, extraction_report=proof or report(),
                   relation_case=policy or case(w))


class RelationKnowledgeV025Tests(unittest.TestCase):
    def test_actual_holder_switch_does_not_switch_legal_owner(self):
        w = base()
        copy = deepcopy(w)
        result = check(world=w)
        self.assertEqual(result["status"], "RELATIONS_FEASIBLE_NONCANONICAL")
        self.assertEqual(w, copy)
        watch = result["isolated_preview_state"]["entities"]["vane_watch"]
        self.assertEqual(watch["holder"], "mara")
        self.assertEqual(watch["owner"], "vane")
        self.assertEqual(result["transition_count"], 2)
        self.assertTrue(result["transitions"][0]["owner_unchanged"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_verified_fact_is_character_knowledge_not_global_truth_mutation(self):
        w = base()
        out = check(world=w)
        self.assertIn(
            "station_clock_stopped",
            out["isolated_preview_state"]["entities"]["mara"]["knowledge"],
        )
        self.assertNotIn("station_clock_stopped",
                         w["entities"]["mara"]["knowledge"])
        self.assertFalse(out["semantic_truth_proven"])

    def test_reported_claim_cannot_transfer_watch(self):
        proof = report()
        proof["candidate_events"][0]["epistemic"] = "REPORTED_CLAIM"
        with self.assertRaisesRegex(
            CoverageError, "V025_NONOBJECTIVE_OR_UNSOURCED_EVENT"
        ):
            check(proof=proof)

    def test_unverified_rumor_cannot_become_known_fact(self):
        w = base()
        policy = case(w)
        policy["verified_fact_registry"]["station_clock_stopped"][
            "truth_status"] = "RUMORED"
        with self.assertRaisesRegex(CoverageError,
                                    "V025_FACT_UNVERIFIED_OR_UNGROUNDED"):
            check(world=w, policy=policy)

    def test_model_invents_unknown_fact_id(self):
        w = base()
        policy = case(w)
        policy["transitions"][1]["fact_id"] = "new:secret_truth"
        with self.assertRaisesRegex(
            CoverageError, "V025_FACT_UNVERIFIED_OR_UNGROUNDED"
        ):
            check(world=w, policy=policy)

    def test_source_does_not_name_recipient(self):
        w = base()
        policy = case(w)
        policy["registered_aliases"]["mara"] = ["Marius"]
        with self.assertRaisesRegex(
            CoverageError, "V025_ENTITY_NOT_NAMED_IN_SOURCE"
        ):
            check(world=w, policy=policy)

    def test_duplicate_preknown_fact_does_not_append_again(self):
        w = base()
        w["entities"]["mara"]["knowledge"].append("station_clock_stopped")
        validate(w)
        with self.assertRaisesRegex(
            CoverageError, "V025_FACT_ALREADY_KNOWN"
        ):
            check(world=w)

    def test_sender_holder_cas_prevents_fabricated_handoff(self):
        w = base()
        w["entities"]["vane_watch"]["holder"] = "mara"
        validate(w)
        with self.assertRaisesRegex(
            CoverageError, "V025_HOLDER_CAS_OR_COLOCATION_FAILED"
        ):
            check(world=w)

    def test_not_colocated_recipient_cannot_teleport_object(self):
        w = base()
        w["entities"]["mara"]["location"] = "archive"
        for item in w["entities"].values():
            if item["holder"] == "mara" or item["worn_by"] == "mara":
                item["location"] = "archive"
        validate(w)
        with self.assertRaisesRegex(
            CoverageError, "V025_HOLDER_CAS_OR_COLOCATION_FAILED"
        ):
            check(world=w)

    def test_unmentioned_extra_change_or_absent_sweep_prohibited(self):
        w = base()
        policy = case(w)
        policy["transitions"].append(deepcopy(policy["transitions"][0]))
        with self.assertRaisesRegex(
            CoverageError, "V025_SOURCE_TRANSITION_COVERAGE_INVALID"
        ):
            check(world=w, policy=policy)
        proof = report()
        proof["candidate_events"].pop()
        with self.assertRaisesRegex(
            CoverageError, "V025_SOURCE_TRANSITION_COVERAGE_INVALID"
        ):
            check(world=w, proof=proof)

    def test_transition_chronology_cannot_reverse_handoff_and_learning(self):
        w = base()
        policy = case(w)
        policy["transitions"].reverse()
        with self.assertRaisesRegex(
            CoverageError, "V025_SOURCE_ORDER_INVALID"
        ):
            check(world=w, policy=policy)

    def test_nested_contained_object_blocks_partial_transfer(self):
        w = base()
        w["entities"]["watch_piece"] = entity_template(
            "watch_piece", "OBJECT", "station", parent_id="vane_watch",
        )
        validate(w)
        original = deepcopy(w)
        with self.assertRaisesRegex(
            CoverageError, "V025_NESTED_TRANSFER_GRAPH_UNQUALIFIED"
        ):
            check(world=w)
        self.assertEqual(w, original)

    def test_old_world_fingerprint_rejected(self):
        w = base()
        policy = case(w)
        policy["entry"]["revision"] += 1
        with self.assertRaisesRegex(
            CoverageError, "V025_TRUSTED_RELATION_POLICY_INVALID"
        ):
            check(world=w, policy=policy)

    def test_source_quote_forgery_cannot_change_holder(self):
        proof = report()
        proof["candidate_events"][0]["quote"] = "fake quote"
        with self.assertRaisesRegex(
            CoverageError, "V025_NONOBJECTIVE_OR_UNSOURCED_EVENT"
        ):
            check(proof=proof)


if __name__ == "__main__":
    unittest.main()
