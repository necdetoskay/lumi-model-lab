"""SERA M3.4: strict event bridge, per-claim JEV binding, time uncertainty.

All test JEV verdicts are SIMULATED, not authenticated provider decisions.
The bridge issues NO state/database authorization, even in its green branch.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from experiments.sera.coverage import (
    CoverageError, EXTRACTION_SCHEMA, prose_hash, reconcile,
)
from experiments.sera.jev_verifier import build_atomic_questions, adjudicate
from experiments.sera.typed_event_bridge_v04 import (
    canonicalize_event, normalize_report, resolve_time, SCHEMA,
)
from experiments.sera.m3_event_graph_bridge_v04 import (
    draft_graph, inspect_scene, verify_verdict, shadow_reduce,
)
from experiments.sera.tests.test_world_state_v02 import base
from experiments.sera.world_state_v02 import canonical
from experiments.sera.event_graph_v03 import EventGraphStore, WorldStateError

PROSE = "Vane looked at his pocket watch."
SCENE = "hook_empty_platform"
REGISTRY = {"vane": ["Vane"], "vane_watch": ["pocket watch"]}
ARGS = {"actor_id": "vane", "object_id": "vane_watch",
        "interaction": "LOOK_AT"}


def report(role, prose=PROSE, typ="INTERACT_OBJECT", args=None,
           at=140, modality="ASSERTED", include=True):
    state = base()
    return {
        "schema": EXTRACTION_SCHEMA,
        "source_role": role,
        "scene_key": SCENE,
        "entry_revision": state["revision"],
        "prose_sha256": prose_hash(prose),
        "mentions": [
            {"entity_ref": "vane", "role": "PRESENT",
             "start": 0, "end": 4},
            {"entity_ref": "vane_watch", "role": "INTERACTED",
             "start": prose.index("pocket watch"),
             "end": prose.index("pocket watch") + len("pocket watch")},
        ],
        "events": ([{
            "local_id": "one",
            "type": typ,
            "arguments": deepcopy(ARGS if args is None else args),
            "at": at, "modality": modality,
            "start": 0, "end": len(prose),
        }] if include else []),
    }


def bundle_and_verdict(writer=None, independent=None, prose=PROSE,
                       registry=REGISTRY, answer="SUPPORTED"):
    writer = writer if writer is not None else report("WRITER", prose=prose)
    independent = independent if independent is not None else report(
        "INDEPENDENT", prose=prose)
    coverage = reconcile(
        prose=prose, scene_key=SCENE, entry_revision=0,
        registry=registry, writer=writer, independent=independent,
    )
    bundle = build_atomic_questions(
        prose=prose, scene_key=SCENE, entry_revision=0,
        coverage=coverage, registry=registry,
        writer=writer, independent=independent,
    )
    verdict = adjudicate(
        bundle=bundle, answers={qid: {"choice": answer, "confidence": 0.9}
                               for qid in bundle["questions"]},
    )
    return writer, independent, bundle, verdict


class TypedEventBridgeTests(unittest.TestCase):
    def test_aligned_full_typed_event_is_advisory_never_world_commit(self):
        w, i, bundle, verdict = bundle_and_verdict()
        actual = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=base(),
            registry=REGISTRY, writer=w, independent=i,
            verdict=verdict,
        )
        self.assertEqual(actual["status"], "PENDING_TRUSTED_HUMAN_AND_APP_REVIEW")
        self.assertFalse(actual["commit_authorized"])
        self.assertFalse(actual["application_review_issued"])
        self.assertEqual(actual["typed_disagreements"], [])
        self.assertEqual(actual["flags"], [])
        candidate = actual["writer"][0]
        self.assertEqual(candidate["world_type"], "INTERACT_ENTITY")
        self.assertEqual(candidate["payload"], {
            "actor_id": "vane", "entity_id": "vane_watch",
            "interaction": "LOOK_AT",
        })
        graph = actual["proposals"][0]
        self.assertEqual(graph["epistemic"], "OBSERVED_ACTION")
        self.assertEqual(graph["objects"][0]["id"], "vane_watch")
        self.assertFalse(graph["commit_authorized"])
        self.assertEqual(graph["world_event"]["at_minute"], 140)
        with EventGraphStore() as store:
            store.create("demo", base())
            with self.assertRaises(WorldStateError):
                store.commit(
                    stream_id="demo", proposal=graph, prose=PROSE,
                    review={}, approved_world_events={}, expected_revision=0,
                )
            self.assertEqual(store.head("demo")["revision"], 0)

    def test_empty_gemini_arguments_are_held_not_autofilled(self):
        w = report("WRITER")
        i = report("INDEPENDENT", args={})
        _, _, _, verdict = bundle_and_verdict(w, i)
        out = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
            writer=w, independent=i, verdict=verdict,
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("EVENT_V04_REQUIRED_ARGUMENTS:INTERACT_OBJECT",
                      out["independent"][0]["blockers"])
        self.assertTrue(out["typed_disagreements"])
        self.assertFalse(out["commit_authorized"])

    def test_required_keys_do_not_allow_unknown_writer_freeform_fields(self):
        s = base()
        e = report("WRITER", args={
            "actor_id": "vane", "object_id": "vane_watch",
            "interaction": "LOOK_AT", "description": "looks",
        })["events"][0]
        with self.assertRaisesRegex(CoverageError,
                                    "EVENT_V04_REQUIRED_ARGUMENTS"):
            canonicalize_event(e, entry=s)

    def test_unregistered_object_fails_before_semantics(self):
        e = report("WRITER", args={
            "actor_id": "vane", "object_id": "new:bench",
            "interaction": "LOOK_AT",
        })["events"][0]
        with self.assertRaisesRegex(CoverageError, "EVENT_V04_OBJECT_UNKNOWN"):
            canonicalize_event(e, entry=base())

    def test_direct_unknown_fact_cannot_be_world_truth(self):
        e = report("WRITER", typ="LEARN_FACT", args={
            "character_id": "vane", "fact_id": "train_physically_arrived",
        })["events"][0]
        with self.assertRaisesRegex(CoverageError, "EVENT_V04_UNATTRIBUTED_FACT"):
            canonicalize_event(e, entry=base())

    def test_reported_claim_requires_known_source_and_is_attributed(self):
        s = base()
        s["entities"]["vane"]["knowledge"].append("claim:vane_0207")
        e = report("WRITER", typ="TELL_FACT", args={
            "from_id": "vane", "to_id": "mara",
            "fact_id": "claim:vane_0207",
        })["events"][0]
        normalized = canonicalize_event(e, entry=s)
        self.assertEqual(normalized["world_type"], "LEARN_FACT")
        self.assertEqual(normalized["payload"]["character_id"], "mara")
        row = normalize_report(
            report=report("WRITER", typ="TELL_FACT", args=e["arguments"]),
            role="WRITER", prose=PROSE, scene_key=SCENE, entry=s,
        )[0]
        graph = draft_graph(row, entry=s, scene_key=SCENE)
        self.assertEqual(graph["event_type"], "TESTIMONY")
        self.assertEqual(graph["epistemic"], "REPORTED_CLAIM")
        self.assertEqual(
            [p["role"] for p in graph["participants"]],
            ["SPEAKER", "LISTENER"],
        )
        without = base()
        with self.assertRaisesRegex(CoverageError,
                                    "EVENT_V04_SPEAKER_DOES_NOT_KNOW_CLAIM"):
            canonicalize_event(e, entry=without)

    def test_movement_graph_includes_all_carried_and_worn_items(self):
        entry = base()
        e = report("WRITER", typ="MOVE_CHARACTER",
                   args={"character_id": "mara", "to": "archive"})["events"][0]
        typed = canonicalize_event(e, entry=entry)
        self.assertEqual(typed["world_type"], "MOVE_CHARACTER")
        row = normalize_report(
            report=report("WRITER", typ="MOVE_CHARACTER",
                          args={"character_id": "mara", "to": "archive"}),
            role="WRITER", prose=PROSE, scene_key=SCENE, entry=entry,
        )[0]
        graph = draft_graph(row, entry=entry, scene_key=SCENE)
        self.assertEqual({x["id"] for x in graph["objects"]},
                         {"mara_notebook", "mara_coat"})
        self.assertEqual(graph["participants"][0]["id"], "mara")

    def test_unknown_time_remains_null_even_after_application_cursor(self):
        w = report("WRITER", at=None)
        rows = normalize_report(
            report=w, role="WRITER", prose=PROSE,
            scene_key=SCENE, entry=base(),
        )
        row = rows[0]
        self.assertIn("EVENT_V04_RELATIVE_TIME_UNRESOLVED", row["blockers"])
        window = {"scene_key": SCENE, "earliest_minute": 135,
                  "latest_minute": 175, "entry_revision": 0}
        resolution = {
            "candidate_id": row["id"],
            "authority": "APPLICATION",
            "resolved_world_cursor": 140,
            "basis": "Ordered index within approved scene window",
            "scene_window_sha256": sha256(canonical(window).encode()).hexdigest(),
        }
        bound = resolve_time(
            row=row, scene_window=window, previous_cursor=135,
            resolution=resolution,
        )
        self.assertIsNone(bound["time"]["exact_minute"])
        self.assertEqual(bound["time"]["resolved_world_cursor"], 140)
        self.assertEqual(bound["time"]["time_resolution"],
                         "APPLICATION_CURSOR_NOT_NARRATIVE_FACT")
        self.assertFalse(bound["blockers"])
        graph = draft_graph(bound, entry=base(), scene_key=SCENE)
        self.assertIsNone(graph["time"]["exact_minute"])
        self.assertEqual(graph["world_event"]["at_minute"], 140)
        bad = dict(resolution, resolved_world_cursor=180)
        with self.assertRaisesRegex(CoverageError, "EVENT_V04_CURSOR_OUT_OF_WINDOW"):
            resolve_time(row=row, scene_window=window, previous_cursor=135,
                         resolution=bad)
        bad = dict(resolution, authority="MODEL")
        with self.assertRaisesRegex(CoverageError, "EVENT_V04_TIME_AUTHORITY_INVALID"):
            resolve_time(row=row, scene_window=window, previous_cursor=135,
                         resolution=bad)

    def test_exact_time_conflict_and_regressive_time_are_rejected(self):
        row = normalize_report(
            report=report("WRITER"), role="WRITER", prose=PROSE,
            scene_key=SCENE, entry=base(),
        )[0]
        window = {"scene_key": SCENE, "earliest_minute": 135,
                  "latest_minute": 175, "entry_revision": 0}
        shared = {
            "candidate_id": row["id"], "authority": "APPLICATION",
            "resolved_world_cursor": 141,
            "basis": "Explicit application decision",
            "scene_window_sha256": sha256(canonical(window).encode()).hexdigest(),
        }
        with self.assertRaisesRegex(CoverageError, "EVENT_V04_EXACT_TIME_CONFLICT"):
            resolve_time(row=row, scene_window=window,
                         previous_cursor=135, resolution=shared)
        with self.assertRaisesRegex(CoverageError, "EVENT_V04_CURSOR_OUT_OF_WINDOW"):
            resolve_time(row=row, scene_window=window,
                         previous_cursor=144, resolution=dict(shared,
                                                               resolved_world_cursor=140))

    def test_missing_jev_does_not_promote_aligned_events(self):
        w, i, _, _ = bundle_and_verdict()
        out = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=base(),
            registry=REGISTRY, writer=w, independent=i,
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("JEV_NOT_CLEARED", out["flags"])

    def test_jev_unknown_claim_and_forged_pass_do_not_clear(self):
        w, i, bundle, verdict = bundle_and_verdict()
        tampered = deepcopy(verdict)
        tampered["next_action"] = "PENDING_DETERMINISTIC_AND_COMPLETENESS_REVIEW"
        tampered["commit_authorized"] = True
        with self.assertRaisesRegex(CoverageError, "BRIDGE_JEV_VERDICT_TAMPERED"):
            verify_verdict(bundle=bundle, verdict=tampered)
        tampered = deepcopy(verdict)
        tampered["judgments"][0]["claim_id"] = "unknown_jev_claim"
        with self.assertRaisesRegex(CoverageError, "BRIDGE_JEV_CLAIM_UNKNOWN"):
            verify_verdict(bundle=bundle, verdict=tampered)

    def test_explicit_insufficient_jev_routes_hold(self):
        w, i, _, verdict = bundle_and_verdict(answer="INSUFFICIENT_EVIDENCE")
        out = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=base(),
            registry=REGISTRY, writer=w, independent=i,
            verdict=verdict,
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertEqual(out["jev_action"], "ESCALATE")

    def test_reported_event_modality_not_promoted_as_physical_fact(self):
        w = report("WRITER", modality="REPORTED")
        i = report("INDEPENDENT", modality="REPORTED")
        _, _, _, verdict = bundle_and_verdict(w, i)
        out = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=base(),
            registry=REGISTRY, writer=w, independent=i, verdict=verdict,
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("EVENT_V04_NON_ASSERTED_MODALITY",
                      out["writer"][0]["blockers"])

    def test_unsupported_record_fact_and_new_object_stay_hold(self):
        e = report("WRITER", typ="RECORD_FACT", args={
            "character_id": "mara", "object_id": "mara_notebook",
            "fact_id": "claim:watch",
        })
        out = normalize_report(
            report=e, role="WRITER", prose=PROSE,
            scene_key=SCENE, entry=base(),
        )
        self.assertIn("EVENT_V04_UNSUPPORTED:RECORD_FACT", out[0]["blockers"])

    def test_writer_and_independent_different_event_payload_stay_hold(self):
        w = report("WRITER")
        i = report("INDEPENDENT", args=dict(ARGS, interaction="TOUCH"))
        _, _, _, verdict = bundle_and_verdict(w, i)
        out = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=base(),
            registry=REGISTRY, writer=w, independent=i, verdict=verdict,
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertTrue(out["typed_disagreements"])

    def test_physical_shadow_stays_noncanonical_and_does_not_mutate_entry(self):
        w, i, _, verdict = bundle_and_verdict()
        entry = base()
        before = deepcopy(entry)
        out = inspect_scene(
            prose=PROSE, scene_key=SCENE, entry=entry,
            registry=REGISTRY, writer=w, independent=i,
            verdict=verdict,
        )
        shadow = shadow_reduce(
            graph_draft=out["proposals"][0], entry=entry, travel_minutes={},
        )
        self.assertEqual(shadow["status"],
                         "PHYSICAL_SHADOW_VALID_NOT_STORY_ACCEPTED")
        self.assertEqual(shadow["effects"], [])
        self.assertFalse(shadow["commit_authorized"])
        self.assertEqual(shadow["db_writes"], 0)
        self.assertEqual(entry, before)

    def test_physical_shadow_rejects_impossible_travel(self):
        entry = base()
        row = normalize_report(
            report=report("WRITER", typ="MOVE_CHARACTER",
                          args={"character_id": "mara", "to": "archive"},
                          at=138),
            role="WRITER", prose=PROSE, scene_key=SCENE, entry=entry,
        )[0]
        graph = draft_graph(row, entry=entry, scene_key=SCENE)
        result = shadow_reduce(
            graph_draft=graph, entry=entry,
            travel_minutes={"station->archive": 10},
        )
        self.assertEqual(result["status"], "HOLD_PHYSICAL_INVARIANT")
        self.assertEqual(result["error_code"], "MOVE_TRAVEL_TOO_FAST")
        self.assertEqual(entry["entities"]["mara"]["location"], "station")

    def test_physical_shadow_records_all_affected_equipment(self):
        entry = base()
        row = normalize_report(
            report=report("WRITER", typ="MOVE_CHARACTER",
                          args={"character_id": "mara", "to": "archive"},
                          at=150),
            role="WRITER", prose=PROSE, scene_key=SCENE, entry=entry,
        )[0]
        draft = draft_graph(row, entry=entry, scene_key=SCENE)
        result = shadow_reduce(
            graph_draft=draft, entry=entry,
            travel_minutes={"station->archive": 10},
        )
        self.assertEqual(result["status"],
                         "PHYSICAL_SHADOW_VALID_NOT_STORY_ACCEPTED")
        ids = {effect["id"] for effect in result["effects"]}
        self.assertEqual(ids, {"mara", "mara_coat", "mara_notebook"})
        self.assertEqual(entry["entities"]["mara_coat"]["location"], "station")
        self.assertFalse(result["commit_authorized"])

    def test_extracted_bench_missing_from_both_lists_not_auto_committed(self):
        prose = "Vane looked at his pocket watch near the bench."
        w = report("WRITER", prose=prose, at=140)
        i = report("INDEPENDENT", prose=prose, at=140)
        # Note: model events carry source spans; this tests the independent
        # lexicon catches an object both models omitted.
        w["events"][0]["end"] = len(prose)
        i["events"][0]["end"] = len(prose)
        obj = inspect_scene(
            prose=prose, scene_key=SCENE, entry=base(),
            registry=REGISTRY, writer=w, independent=i,
            candidate_lexicon={"candidate:bench": ["bench"]},
        )
        self.assertEqual(obj["status"], "HOLD")
        self.assertIn("M2_UNRESOLVED", obj["flags"])
        self.assertIn("UNREPORTED_OBJECT_CANDIDATE",
                      {finding["code"] for finding in obj["m2_findings"]})
        self.assertFalse(obj["commit_authorized"])


if __name__ == "__main__":
    unittest.main()
