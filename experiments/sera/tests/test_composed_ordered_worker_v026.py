"""v0.26: actual composed SERA worker with independently prompted fake provider.

No paid provider calls. The trusted policies carry app-scoped identities,
route minimums and verified facts. No canon authorizations or token caps.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.composed_scene_runner_v023 import run
from experiments.sera.coverage import prose_hash
from experiments.sera.tests.test_ordered_causal_preview_v026 import (
    SOURCE, SCENE,
)
from experiments.sera.tests.test_relation_knowledge_v025 import (
    ALIASES, FACTS,
)
from experiments.sera.tests.test_world_state_v02 import base

ROUTES = {"station->archive": 10}
REGISTRY = {"vane": ["Vane"], "mara": ["Mara"],
            "vane_watch": ["watch"]}


def mock_provider(calls, *, claim=False):
    def call(*, key, model, prepared):
        req = prepared["request"]
        for forbidden in (
            "max_tokens", "max_output_tokens", "max_completion_tokens",
            "max_new_tokens", "max_generation_tokens",
        ):
            assert forbidden not in json.dumps(req)
        packet = json.loads(req["messages"][1]["content"])
        calls.append(model)
        if "target_sentences" in packet:
            rows = []
            for sentence in packet["target_sentences"]:
                quote = sentence["quote"]
                if "walked" in quote:
                    name = "Vane" if quote.startswith("Vane") else "Mara"
                    actor = name.lower()
                    kind, effect = "MOVE", "WORLD"
                    evidence = "walked to archive"
                    refs = [actor]
                    names = [(actor, name)]
                elif "handed" in quote:
                    kind, effect = "TRANSFER", "OBJECT"
                    evidence = "Vane handed the watch to Mara"
                    refs = ["vane", "mara", "vane_watch"]
                    names = [
                        ("vane", "Vane"), ("mara", "Mara"),
                        ("vane_watch", "watch"),
                    ]
                else:
                    kind, effect = ("KNOWLEDGE_UPDATE",
                                    "CHARACTER_KNOWLEDGE")
                    evidence = "Mara learned the station clock stopped"
                    refs = ["mara"]
                    names = [("mara", "Mara")]
                rows.append({
                    "sentence_id": sentence["id"],
                    "disposition": "STATE_EVENT",
                    "reason": "Complete independent source extraction",
                    "mentions": [
                        {"entity_ref": ident, "role": "PRESENT",
                         "evidence_quote": name, "occurrence": 0}
                        for ident, name in names
                    ],
                    "events": [{
                        "kind": kind, "epistemic": (
                            "REPORTED_CLAIM" if claim and
                            kind == "TRANSFER" else "OBSERVED_ACTION"
                        ),
                        "effect": effect, "evidence_quote": evidence,
                        "occurrence": 0, "entity_refs": refs,
                        "reason": "Source-anchored candidate",
                    }],
                })
            result = {"rows": rows}
        elif "original_prose" in packet:
            result = {"typed_candidates": []}
        else:
            # No previous model decision is used as a source of truth.
            lines = packet.get("exact_chronological_sentences") or []
            result = {
                "verdict": "STATE_OBSERVATION", "operation_kind": "OBSERVE",
                "effect": "UNKNOWN",
                "evidence_quote": lines[0]["quote"] if lines else SOURCE[:4],
                "reason": "Conservative independent model uncertainty",
            }
        return {"error": None, "raw": {
            "id": "synthetic-v026-" + str(len(calls)), "model": model,
            "usage": {"cost": "0.001"},
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(result)},
            }],
        }}
    return call


def temporal_builder(*, prose, world, extraction_report, **unused):
    rows = sorted(extraction_report["candidate_events"],
                  key=lambda e: e["start"])
    return {
        "entry": deepcopy(world), "scene_key": SCENE,
        "scene_window": {
            "scene_key": SCENE, "entry_revision": world["revision"],
            "earliest_minute": 135, "latest_minute": 175,
        },
        "travel_minutes": deepcopy(ROUTES),
        "events": [{
            "event_id": row["event_id"], "ordinal": idx+1,
            "actor_id": (
                "vane" if row["kind"] == "TRANSFER"
                else "mara" if row["kind"] == "KNOWLEDGE_UPDATE"
                else "vane" if row["quote"].startswith("Vane")
                else "mara"
            ),
            "kind": ("MOVEMENT" if row["kind"] == "MOVE" else "ACTION"),
            "to_location": ("archive" if row["kind"] == "MOVE"
                            else None),
            "earliest_minute": None, "latest_minute": None,
            "exact_minute": None, "depends_on": [],
        } for idx, row in enumerate(rows)],
    }


def relation_builder(*, prose, world, extraction_report,
                     facts=None, **unused):
    rows = sorted(extraction_report["candidate_events"],
                  key=lambda e: e["start"])
    transitions = []
    for event in rows:
        if event["kind"] == "TRANSFER":
            transitions.append({
                "source_event_id": event["event_id"],
                "operation": "TRANSFER_HOLDER",
                "object_id": "vane_watch", "from_id": "vane",
                "to_id": "mara", "fact_id": None,
            })
        if event["kind"] == "KNOWLEDGE_UPDATE":
            transitions.append({
                "source_event_id": event["event_id"],
                "operation": "LEARN_FACT", "object_id": None,
                "from_id": None, "to_id": "mara",
                "fact_id": "station_clock_stopped",
            })
    return {
        "entry": deepcopy(world), "policy_id": "registered-facts-v1",
        "registered_aliases": deepcopy(ALIASES),
        "verified_fact_registry": deepcopy(FACTS if facts is None else facts),
        "transitions": transitions,
    }


def invoke(root, provider, *, facts=None, temporal=None):
    def policy(**kwargs):
        return relation_builder(**kwargs, facts=facts)
    return run(
        prose=SOURCE, world=base(), scene_key=SCENE, work_root=root,
        api_key="fake-key", registry=REGISTRY, candidate_lexicon={},
        typed_registry={"openables": [], "documents": []},
        writer_model="synthetic/unused-writer",
        sweep_model="synthetic/independent-extractor",
        semantic_model="synthetic/independent-semantic",
        facet_model="synthetic/independent-typed",
        provider_call=provider, max_rewrites=0,
        trusted_temporal_builder=temporal or temporal_builder,
        temporal_policy_id="registered-station-archive-routes-v1",
        trusted_relation_builder=policy,
        relation_policy_id="registered-facts-v1",
    )


class ComposedOrderedCausalWorkerV026Tests(unittest.TestCase):
    def test_single_worker_runs_all_real_sweeps_and_joint_state_replay(self):
        calls = []
        with TemporaryDirectory() as d:
            root = Path(d)/"job"
            result = invoke(root, mock_provider(calls))
            archived = list((root/"evidence").glob("*.json"))
            again = invoke(root, lambda **kw: self.fail(
                "Completed paid model reply re-sent"
            ))
        self.assertEqual(result, again)
        self.assertEqual(result["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(result["rewrite_count"], 0)
        self.assertEqual(len(archived), 1)
        self.assertGreaterEqual(len(calls), 2)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_rumored_fact_is_not_bypassed_by_independent_models(self):
        facts = deepcopy(FACTS)
        facts["station_clock_stopped"]["truth_status"] = "RUMORED"
        with TemporaryDirectory() as d:
            out = invoke(Path(d)/"job", mock_provider([]), facts=facts)
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(out["world_db_writes"], 0)
        self.assertFalse(out["requires_manual_intervention"])

    def test_malformed_registered_route_does_not_create_new_world_truth(self):
        def incorrect(**kwargs):
            answer = temporal_builder(**kwargs)
            answer["travel_minutes"] = {}
            return answer
        with TemporaryDirectory() as d:
            out = invoke(
                Path(d)/"job", mock_provider([]), temporal=incorrect,
            )
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertFalse(out["canonical_commit_authorized"])


if __name__ == "__main__":
    unittest.main()
