"""Adversarial offline tests. Synthetic ballots test mechanics, never quality."""
import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from experiments.narrative_mechanics import core as nml
from experiments.nova import evaluate as ev, source_review, trial, vault
from experiments.nova.match import match
from experiments.nova.__main__ import main


class NovaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.state, cls.briefs, cls.release = ev.load_inputs()
        cls.requests, cls.allocation = ev.prepare(cls.rows, cls.state, cls.briefs, 1701)
        cls.packet = ev.blind_packet([{"sample_id": r["sample_id"], "text": ev.fixture_story(r)} for r in cls.requests], cls.allocation)

    def ballots(self, packet=None, human=False):
        return [{"schema": "nova.ballot.v1", "sample_id": s["sample_id"], "story_sha256": s["story_sha256"],
                 "reviewer": reviewer, "kind": "HUMAN" if human else "SYNTHETIC", "independent": True,
                 "saw_allocation": False, "is_story_author": False,
                 "scores": {d: 3 for d in ev.DIMENSIONS}, "gates": {g: True for g in ev.GATES}, "notes": "test only"}
                for s in (packet or self.packet) for reviewer in ("test-1", "test-2")]

    def test_release_cardinality_and_withheld(self):
        self.assertEqual(len(self.rows), 18)
        self.assertEqual(sum(r["status"] == "PROPOSED_LAB" for r in self.rows), 17)
        self.assertEqual(sum(len(r["profiles"]) == 2 for r in self.rows), 5)
        self.assertFalse(vault.duplicate_report(self.rows)["exact"])

    def test_all_16_balanced_briefs_select_two_source_groups(self):
        for brief in self.briefs:
            advice, audit = match(brief, self.state, self.rows)
            self.assertEqual(advice["status"], "PROPOSED", brief["id"])
            self.assertEqual(len(advice["advice"]), 2)
            self.assertEqual(audit["source_groups"], ["atlantis", "sg1"])
            self.assertNotIn("NOVA-007", audit["selected_ids"])

    def test_selection_order_invariance(self):
        self.assertEqual(match(self.briefs[0], self.state, self.rows),
                         match(self.briefs[0], self.state, list(reversed(self.rows))))

    def test_state_fingerprint_mismatch(self):
        state = copy.deepcopy(self.state)
        state["facts"].append("New power")
        with self.assertRaisesRegex(nml.Invalid, "STATE_MISMATCH"):
            match(self.briefs[0], state, self.rows)

    def test_missing_canon_field(self):
        state = copy.deepcopy(self.state)
        del state["allowed_effects"]
        with self.assertRaises(nml.Invalid):
            match(self.briefs[0], state, self.rows)

    def test_unknown_age_and_extra_brief_field(self):
        for field, value in (("age", 5), ("untrusted_override", True)):
            brief = {**self.briefs[0], field: value}
            with self.assertRaises(nml.Invalid):
                match(brief, self.state, self.rows)

    def test_fail_closed_canon_and_state_permission(self):
        for key in ("authorized_features", "allowed_effects"):
            state = {**self.state, key: ["unrelated"]}
            brief = {**self.briefs[0], "state_sha256": nml.fingerprint(state)}
            projection, _ = match(brief, state, self.rows)
            self.assertEqual(projection["status"], "ABSTAIN")

    def test_reveal_ceiling(self):
        state = {**self.state, "reveal_ceiling": 0}
        brief = {**self.briefs[0], "state_sha256": nml.fingerprint(state)}
        self.assertEqual(match(brief, state, self.rows)[0]["status"], "ABSTAIN")

    def test_age_floor_cannot_be_overridden(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            for p in row["profiles"]:
                if p["profile"] == "GENTLE_LAB":
                    p["risks"] = ["loss"]
        brief = {**self.briefs[0], "forbidden_risks": []}
        self.assertEqual(match(brief, self.state, rows)[0]["status"], "ABSTAIN")

    def test_recent_usage_and_family_originality(self):
        brief = self.briefs[0]
        _, audit = match(brief, self.state, self.rows)
        history = [{"schema": "nova.usage.v1", "id": mid, "ordinal": brief["ordinal"]-1,
                    "state_sha256": brief["state_sha256"], "selection_sha256": nml.fingerprint(audit)}
                   for mid in audit["selected_ids"]]
        _, second = match(brief, self.state, self.rows, history)
        self.assertFalse(set(second["selected_ids"]) & set(audit["selected_ids"]))
        for mid in audit["selected_ids"]:
            self.assertIn("RECENT_ID", second["exclusions"][mid])
            self.assertIn("RECENT_FAMILY", second["exclusions"][mid])
        for event in history:
            event["ordinal"] -= 5
        self.assertEqual(match(brief, self.state, self.rows, history), match(brief, self.state, self.rows))

    def test_bad_usage_rejected(self):
        event = {"schema": "nova.usage.v1", "id": "NOVA-001", "ordinal": 999,
                 "state_sha256": "a"*64, "selection_sha256": "a"*64}
        with self.assertRaisesRegex(nml.Invalid, "FUTURE_USAGE"):
            match(self.briefs[0], self.state, self.rows, [event])
        event.update(id="unknown", ordinal=0)
        with self.assertRaisesRegex(nml.Invalid, "UNKNOWN_USAGE"):
            match(self.briefs[0], self.state, self.rows, [event])

    def test_immutable_usage_roundtrip(self):
        _, audit = match(self.briefs[0], self.state, self.rows)
        with tempfile.TemporaryDirectory() as td:
            path = vault.record_usage(td, audit, self.briefs[0])
            self.assertEqual(path, vault.record_usage(td, audit, self.briefs[0]))
            history = vault.load_usage(td)
            self.assertEqual(len(history), 2)
            self.assertEqual(match(self.briefs[0], self.state, self.rows, history)[0]["status"], "ABSTAIN")
            path.write_bytes(b"[]\n")
            with self.assertRaisesRegex(nml.Invalid, "USAGE_ARTIFACT_CHANGED"):
                vault.load_usage(td)

    def test_sanitized_advice_has_no_private_fields(self):
        for brief in self.briefs:
            projection, _ = match({**brief, "seed": "https://evil.example/Stargate"}, self.state, self.rows)
            serialized = nml.canonical(projection).decode()
            for forbidden in ("source_id", "sha256", "sg1:", "atlantis:", "NOVA-", "https:"):
                self.assertNotIn(forbidden, serialized)
            self.assertFalse(ev.lexical_gates(serialized, self.state))

    def test_exact_duplicate_detection(self):
        rows = copy.deepcopy(self.rows[:2])
        rows[1]["abstract"] = rows[0]["abstract"].upper() + " !!!"
        self.assertEqual(len(vault.duplicate_report(rows)["exact"]), 1)

    def test_near_duplicate_review(self):
        rows = copy.deepcopy(self.rows[:2])
        rows[1]["abstract"] = rows[0]["abstract"] + " extra"
        self.assertEqual(len(vault.duplicate_report(rows)["near_review_required"]), 1)

    def test_sqlite_index_roundtrip_and_drift(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "index.sqlite"
            vault.build_index(path, self.rows, self.release)
            vault.verify_index(path, self.rows, self.release)
            with self.assertRaises(FileExistsError):
                vault.build_index(path, self.rows, self.release)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE mechanics SET status='ACCEPTED' WHERE id='NOVA-001'")
            with self.assertRaisesRegex(nml.Invalid, "INDEX_DRIFT"):
                vault.verify_index(path, self.rows, self.release)

    def test_sqlite_stale_release(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "index.sqlite"
            vault.build_index(path, self.rows, self.release)
            with self.assertRaisesRegex(nml.Invalid, "STALE_INDEX"):
                vault.verify_index(path, self.rows, {"different": True})

    def test_modified_release_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "release.v1.json").write_text("{}")
            with patch.object(vault, "DATA", path), patch.object(nml, "load_release", return_value={}):
                with self.assertRaisesRegex(nml.Invalid, "NOVA_RELEASE_CHANGED"):
                    vault.load()

    def test_all_records_have_multisource_evidence_and_unknown_arc(self):
        for row in self.rows:
            self.assertEqual(len(row["source_ids"]), 2)
            self.assertEqual(set(row["analysis"]), set(vault.AXES))
            self.assertEqual(row["analysis"]["series_arc"]["epistemic"], "UNKNOWN")
            self.assertFalse(row["semantic_support_certified"])

    def test_deterministic_balanced_blinding(self):
        self.assertEqual((self.requests, self.allocation), ev.prepare(self.rows, self.state, self.briefs, 1701))
        for age in (4, 10, 25, 40):
            on_a = [a for a in self.allocation if a["age"] == age and a["sample_id"].endswith("A") and a["arm"] == "ON"]
            self.assertEqual(len(on_a), 2)
        for pair in {a["pair_id"] for a in self.allocation}:
            hashes = {a["common_sha256"] for a in self.allocation if a["pair_id"] == pair}
            self.assertEqual(len(hashes), 1)

    def test_blind_packet_no_allocation(self):
        for item in self.packet:
            self.assertEqual(set(item), {"sample_id", "text", "story_sha256"})

    def test_generation_requests_are_source_free(self):
        for request in self.requests:
            text = nml.canonical(request).decode()
            self.assertFalse(ev.lexical_gates(text, self.state))
            for private in ("source_ids", "source_path", "fixture_beats", "span_sha256", "NM-", "NOVA-"):
                self.assertNotIn(private, text)

    def test_missing_or_duplicate_story(self):
        for stories in (self.packet[:-1], self.packet[:-1]+self.packet[:1]):
            with self.assertRaises(nml.Invalid):
                ev.blind_packet(stories, self.allocation)

    def test_no_evidence_of_quality_from_fixture_scores(self):
        report = ev.score(self.packet, self.allocation, self.ballots(), fixture=True)
        self.assertEqual(report["quality_status"], "NOT_ESTABLISHED_FIXTURE")
        self.assertEqual(report["ties"], 16)
        self.assertFalse(report["integration_authorized"])

    def test_missing_duplicate_and_self_judged_ballots(self):
        for mode in ("missing", "duplicate", "author", "unblinded", "nonindependent", "unknown_sample", "bad_score", "boolean_score"):
            ballots = self.ballots()
            if mode == "missing":
                ballots.pop()
            elif mode == "duplicate":
                ballots.append(ballots[0])
            elif mode == "author":
                ballots[0]["is_story_author"] = True
            elif mode == "unblinded":
                ballots[0]["saw_allocation"] = True
            elif mode == "nonindependent":
                ballots[0]["independent"] = False
            elif mode == "unknown_sample":
                ballots[0]["sample_id"] = "unknown"
            else:
                ballots[0]["scores"]["interest"] = 6 if mode == "bad_score" else True
            with self.subTest(mode=mode), self.assertRaises(nml.Invalid):
                ev.score(self.packet, self.allocation, ballots, fixture=True)

    def test_fixture_cannot_be_counted_as_human(self):
        with self.assertRaisesRegex(nml.Invalid, "INDEPENDENT_REVIEW"):
            ev.score(self.packet, self.allocation, self.ballots(), fixture=False)

    def test_tampered_story_hash(self):
        packet = copy.deepcopy(self.packet)
        packet[0]["text"] += " extra"
        with self.assertRaisesRegex(nml.Invalid, "STORY_HASH"):
            ev.score(packet, self.allocation, self.ballots(), fixture=True)

    def test_each_red_gate_blocks(self):
        for gate in ev.GATES:
            ballots = self.ballots(human=True)
            ballots[0]["gates"][gate] = False
            report = ev.score(self.packet, self.allocation, ballots, fixture=False)
            self.assertEqual(report["quality_status"], "NOT_ESTABLISHED")
            self.assertEqual(report["red_gate_failures"][0]["gate"], gate)

    def test_disagreement_requires_adjudication(self):
        ballots = self.ballots()
        ballots[0]["scores"]["interest"] = 1
        report = ev.score(self.packet, self.allocation, ballots, fixture=True)
        self.assertEqual(len(report["adjudication_required"]), 1)

    def test_context_change_between_arms(self):
        allocation = copy.deepcopy(self.allocation)
        allocation[0]["common_sha256"] = "a"*64
        with self.assertRaisesRegex(nml.Invalid, "UNPAIRED_CONTEXT"):
            ev.score(self.packet, allocation, self.ballots(), fixture=True)

    def test_fake_sample_size_and_wrong_age_blocked(self):
        allocation = copy.deepcopy(self.allocation)
        allocation[0]["age"] = 40
        with self.assertRaisesRegex(nml.Invalid, "BRIEF_BINDING"):
            ev.score(self.packet, allocation, self.ballots(), fixture=True)

    def test_positive_48_pair_math_still_never_authorizes_integration(self):
        requests, allocation = ev.prepare(self.rows, self.state, self.briefs, 23, repeats=3)
        packet = ev.blind_packet([{"sample_id": r["sample_id"], "text": ev.fixture_story(r)} for r in requests], allocation)
        ballots = self.ballots(packet, human=True)  # Deliberately fake attestations: arithmetic test only.
        arms = {a["sample_id"]: a["arm"] for a in allocation}
        for b in ballots:
            b["scores"] = {d: 4 if arms[b["sample_id"]] == "ON" else 3 for d in ev.DIMENSIONS}
        report = ev.score(packet, allocation, ballots, fixture=False)
        self.assertEqual(report["quality_status"], "PILOT_THRESHOLD_MET")
        self.assertFalse(report["integration_authorized"])
        self.assertGreater(report["win_rate_ci95"][0], 0.5)

    def test_lexical_copy_and_named_entity_gates(self):
        self.assertIn("SOURCE_COPY", ev.lexical_gates("one two three four five six seven eight nine", self.state,
                                                     ["zero one two three four five six seven eight nine"]))
        self.assertIn("FORBIDDEN_TERM", ev.lexical_gates("Sheppard geldi", self.state))
        self.assertFalse(ev.lexical_gates("O bir oyun oynadı.", self.state))

    def test_paid_dispatch_blocked(self):
        self.assertEqual(main(["generate"]), 2)

    def test_output_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(nml.Invalid, "OUTPUT_EXISTS"):
                ev.dry_run(td)

    def test_trial_prepare_reconstruct_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trial"
            with patch.object(ev, "load_inputs", return_value=(self.rows, self.state, self.briefs, self.release)):
                manifest = trial.prepare_trial(path, repeats=1)
                self.assertFalse(manifest["paid_dispatch_authorized"])
                requests, allocation, _ = trial.load_trial(path)
                self.assertEqual(len(requests), 32)
                allocation[0]["arm"] = "OFF" if allocation[0]["arm"] == "ON" else "ON"
                (path / "private/allocation.json").write_bytes(nml.canonical(allocation))
                with self.assertRaisesRegex(nml.Invalid, "TRIAL_BINDING"):
                    trial.load_trial(path)

    def bundle(self):
        return {"schema": "nova.story-bundle.v1", "mode": "HUMAN_MANUAL", "generator": "manual-author",
                "authorization_reference": "", "approved_budget_microusd": 0, "actual_cost_microusd": 0,
                "stories": [{"sample_id": r["sample_id"], "text": ev.fixture_story(r) + " Bu metin yalnız ithalat testinin sentetik verisidir."} for r in self.requests]}

    def test_external_metadata_costs_and_modes_fail_closed(self):
        for kind in ("fixture", "overbudget", "negative", "boolean", "missing_auth", "manual_cost", "empty_author", "extra"):
            bundle = self.bundle()
            if kind == "fixture":
                bundle["mode"] = "FIXTURE"
            elif kind == "overbudget":
                bundle["actual_cost_microusd"] = 1
            elif kind == "negative":
                bundle["actual_cost_microusd"] = -1
            elif kind == "boolean":
                bundle["approved_budget_microusd"] = True
            elif kind == "missing_auth":
                bundle["mode"] = "EXTERNAL_AUTHORIZED_MODEL"
            elif kind == "manual_cost":
                bundle["actual_cost_microusd"] = bundle["approved_budget_microusd"] = 1
            elif kind == "empty_author":
                bundle["generator"] = ""
            else:
                bundle["override"] = True
            with patch.object(trial, "load_trial", return_value=(self.requests, self.allocation, self.state)):
                with self.subTest(kind=kind), self.assertRaises(nml.Invalid):
                    trial.import_stories("unused", bundle)

    def test_import_short_copied_and_named_story_rejected(self):
        for text in ("too short", "Sheppard " * 40):
            bundle = self.bundle()
            bundle["stories"][0]["text"] = text
            with patch.object(trial, "load_trial", return_value=(self.requests, self.allocation, self.state)):
                with self.assertRaises(nml.Invalid):
                    trial.import_stories("unused", bundle)

    def test_external_import_and_review_pipeline_synthetic_plumbing_only(self):
        # Deliberately simulated operator attestations; never saved as research quality evidence.
        with tempfile.TemporaryDirectory() as td:
            with patch.object(trial, "load_trial", return_value=(self.requests, self.allocation, self.state)):
                result = trial.import_stories(td, self.bundle())
                self.assertEqual(result["stories"], 32)
                self.assertFalse((Path(td)/"review/allocation.json").exists())
                packet = nml.read_json(Path(td)/"review/blind-packet.json")
                report = trial.score_trial(td, self.ballots(packet, human=True))
                self.assertEqual(report["overall_maturity"], "NOT_ESTABLISHED")
                ballots = self.ballots(packet, human=True)
                ballots[0]["reviewer"] = "manual-author"
                with self.assertRaisesRegex(nml.Invalid, "GENERATOR_CANNOT_SCORE"):
                    trial.score_trial(td, ballots)
                (Path(td)/"private/import-receipt.json").write_text("{}")
                with self.assertRaisesRegex(nml.Invalid, "IMPORT_RECEIPT_CHANGED"):
                    trial.score_trial(td, self.ballots(packet, human=True))

    def test_known_fixture_relabeling_is_rejected(self):
        bundle = self.bundle()
        bundle["stories"][0]["text"] = ev.fixture_story(self.requests[0])
        with patch.object(trial, "load_trial", return_value=(self.requests, self.allocation, self.state)):
            with self.assertRaisesRegex(nml.Invalid, "KNOWN_FIXTURE_NOT_REAL"):
                trial.import_stories("unused", bundle)

    def test_reviewer_context_change_invalidates_ratings(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(trial, "load_trial", return_value=(self.requests, self.allocation, self.state)):
                trial.import_stories(td, self.bundle())
                context_path = Path(td)/"review/context.json"
                context = nml.read_json(context_path)
                context["briefs"][0]["age"] = 40
                context_path.write_bytes(nml.canonical(context))
                with self.assertRaisesRegex(nml.Invalid, "IMPORT_RECEIPT_CHANGED"):
                    trial.score_trial(td, self.ballots(human=True))

    def test_source_review_unique_utf8_anchor(self):
        data = "Önce. Gözlem açık. Sonra.".encode()
        span = source_review.anchor(data, "Gözlem açık.")
        self.assertEqual(data[span["start_byte"]:span["end_byte"]].decode(), "Gözlem açık.")
        for data, quote in ((b"twice twice", "twice"), (b"absent", "missing"), (b"value", "")):
            with self.assertRaisesRegex(nml.Invalid, "ANCHOR_NOT_UNIQUE"):
                source_review.anchor(data, quote)

    def test_source_review_keeps_adaptation_distinct_and_no_promotion(self):
        upstream = nml.load_release()
        before = nml.fingerprint(self.rows)
        report = source_review.audit(self.rows, upstream)
        self.assertEqual(report["mechanics_audited"], 18)
        self.assertEqual(report["narrowed_mechanics"], 3)
        self.assertEqual(len(report["narrow_proposals"]), 9)
        self.assertEqual(nml.fingerprint(self.rows), before)
        self.assertFalse(report["semantic_support_certified"])
        self.assertFalse(report["active_vault_changed"])
        decision = next(p for p in report["narrow_proposals"] if p["mechanic_id"] == "NOVA-018" and p["axis"] == "decision")
        self.assertEqual(decision["relation"], "ADAPTATION_NOT_OBSERVED_CHOICE")
        self.assertTrue(all(p["evidence"]["end_byte"]-p["evidence"]["start_byte"] < 800 for p in report["narrow_proposals"]))

    def test_end_to_end_fixture_replay(self):
        with tempfile.TemporaryDirectory() as td:
            # Only one expensive archive load is needed; pinned boundary tested separately.
            with patch.object(ev, "load_inputs", return_value=(self.rows, self.state, self.briefs, self.release)):
                first = ev.dry_run(Path(td) / "first")
                second = ev.dry_run(Path(td) / "second")
            self.assertEqual(first, second)
            self.assertEqual(first["engineering_status"], "PASS")
            self.assertEqual(first["provider_calls"], 0)
            for name in ("blind-packet.json", "allocation.private.json", "report.json", "artifact-hashes.json"):
                self.assertEqual((Path(td)/"first"/name).read_bytes(), (Path(td)/"second"/name).read_bytes())


if __name__ == "__main__":
    unittest.main()
