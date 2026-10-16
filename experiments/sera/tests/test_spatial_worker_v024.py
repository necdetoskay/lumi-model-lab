"""SERA v0.24: pure movement scene through real v0.22/23 worker seams."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.composed_scene_runner_v023 import run
from experiments.sera.coverage import prose_hash
from experiments.sera.tests.test_world_state_v02 import base

PROSE = "Mara walked to archive."
SCENE = "movement-only-trusted-route"
ROUTES = {"station->archive": 10}


def provider_fixture(calls, *, epistemic="OBSERVED_ACTION"):
    def call(*, key, model, prepared):
        request = prepared["request"]
        for cap in ("max_tokens", "max_output_tokens",
                    "max_completion_tokens", "max_new_tokens"):
            assert cap not in json.dumps(request)
        packet = json.loads(request["messages"][1]["content"])
        calls.append((model, deepcopy(packet)))
        if "target_sentences" in packet:
            rows = []
            for sentence in packet["target_sentences"]:
                rows.append({
                    "sentence_id": sentence["id"],
                    "disposition": "STATE_EVENT",
                    "reason": "Independent synthetic source-backed movement",
                    "mentions": [{
                        "entity_ref": "mara", "role": "PRESENT",
                        "evidence_quote": "Mara", "occurrence": 0,
                    }],
                    "events": [{
                        "kind": "MOVE", "epistemic": epistemic,
                        "effect": "WORLD",
                        "evidence_quote": "walked to archive",
                        "occurrence": 0, "entity_refs": ["mara"],
                        "reason": "Synthetic registered movement event",
                    }],
                })
            body = {"rows": rows}
        elif "original_prose" in packet:
            body = {"typed_candidates": []}
        else:
            context = packet.get("exact_chronological_sentences")
            assert context, "unexpected semantic model request"
            body = {
                "verdict": "STATE_OBSERVATION", "operation_kind": "OBSERVE",
                "effect": "UNKNOWN", "evidence_quote": context[0]["quote"],
                "reason": "Synthetic conservative finding",
            }
        return {"error": None, "raw": {
            "id": "mock-v024-" + str(len(calls)),
            "model": model,
            "usage": {"cost": "0.001"},
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(body)},
            }],
        }}
    return call


def route_builder(*, prose, world, extraction_report, destination="archive",
                  routes=None, exact_minute=None):
    events = extraction_report["candidate_events"]
    assert len(events) == 1
    return {
        "entry": deepcopy(world),
        "scene_key": SCENE,
        "scene_window": {
            "scene_key": SCENE,
            "entry_revision": world["revision"],
            "earliest_minute": 135,
            "latest_minute": 175,
        },
        "travel_minutes": ROUTES if routes is None else routes,
        "events": [{
            "event_id": events[0]["event_id"],
            "ordinal": 1,
            "actor_id": "mara",
            "kind": "MOVEMENT",
            "to_location": destination,
            "earliest_minute": None, "latest_minute": None,
            "exact_minute": exact_minute, "depends_on": [],
        }],
    }


def execute(root, call, *, builder=None, temporal_policy_id=None):
    return run(
        prose=PROSE, world=base(), scene_key=SCENE, work_root=root,
        api_key="synthetic",
        registry={"mara": ["Mara"]}, candidate_lexicon={},
        typed_registry={"openables": [], "documents": []},
        writer_model="synthetic/unused-writer",
        sweep_model="synthetic/independent-sweep",
        semantic_model="synthetic/independent-semantic",
        facet_model="synthetic/independent-facet",
        provider_call=call, max_rewrites=0,
        trusted_temporal_builder=builder, temporal_policy_id=temporal_policy_id,
    )


class MovementOnlyComposedWorkerV024Tests(unittest.TestCase):
    def test_real_worker_supports_pure_movement_without_fabricating_objects(self):
        calls = []
        with TemporaryDirectory() as d:
            root = Path(d)
            result = execute(
                root, provider_fixture(calls),
                builder=route_builder, temporal_policy_id="registered-routes-v1",
            )
            bundle = json.loads(
                (root/"evidence"/(prose_hash(PROSE)+".json"))
                .read_text(encoding="utf-8")
            )
            again = execute(
                root, lambda **kw: self.fail("no repeat provider"),
                builder=route_builder, temporal_policy_id="registered-routes-v1",
            )
        self.assertEqual(result, again)
        self.assertEqual(result["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(result["rewrite_count"], 0)
        self.assertEqual(len(bundle["typed_candidates"]), 0)
        self.assertEqual(bundle["typed_registry"],
                         {"openables": [], "documents": []})
        self.assertEqual(len(bundle["extraction_report"]["candidate_events"]), 1)
        self.assertGreaterEqual(len(calls), 2)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_without_governed_temporal_route_movement_fails_safely(self):
        with TemporaryDirectory() as d:
            result = execute(Path(d), provider_fixture([]))
        self.assertEqual(result["status"], "FAILED_SAFE_FINAL")
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)

    def test_impossible_registered_route_time_replans_without_manual_input(self):
        def bad(**kwargs):
            return route_builder(**kwargs, exact_minute=139)
        with TemporaryDirectory() as d:
            out=execute(
                Path(d), provider_fixture([]),
                builder=bad, temporal_policy_id="impossible-time-v1",
            )
        self.assertEqual(out["status"], "FAILED_SAFE_FINAL")
        self.assertFalse(out["requires_manual_intervention"])
        self.assertEqual(out["world_db_writes"], 0)

    def test_wrong_narrative_knowledge_cannot_authorize_world_movement(self):
        with TemporaryDirectory() as d:
            result=execute(
                Path(d),
                provider_fixture([], epistemic="REPORTED_CLAIM"),
                builder=route_builder, temporal_policy_id="registered-routes-v1",
            )
        self.assertEqual(result["status"], "FAILED_SAFE_FINAL")
        self.assertFalse(result["canonical_commit_authorized"])


if __name__ == "__main__":
    unittest.main()
