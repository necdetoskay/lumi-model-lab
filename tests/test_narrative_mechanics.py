"""Offline integrity, policy, adversarial boundary and replay tests (stdlib)."""
import ast
import copy
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.narrative_mechanics import core as n


class MechanicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = n.load_release()
        cls.base = n.read_json(n.HERE / "examples/request.v1.json")

    def request(self, **changes):
        value = copy.deepcopy(self.base)
        value.update(changes)
        return value

    def select(self, **changes):
        # Policy unit tests use the already verified release, not mutable sources.
        with patch.object(n, "load_release", return_value=copy.deepcopy(self.artifacts)):
            return n.select(self.request(**changes))

    def test_01_full_release_and_episode_coverage(self):
        self.assertEqual(314, len(self.artifacts["archive"]["episodes"]))
        self.assertEqual(322, len(self.artifacts["archive"]["files"]))
        self.assertEqual(18, len(self.artifacts["cards"]))
        self.assertEqual(214, sum(e["id"].startswith("sg1:") for e in self.artifacts["archive"]["episodes"]))

    def test_manifest_rebuild_is_byte_deterministic(self):
        self.assertEqual(n.canonical(n.build_manifest()), n.canonical(self.artifacts["archive"]))

    def test_manifest_pin_rejects_forged_entry(self):
        manifest = copy.deepcopy(self.artifacts["archive"])
        manifest["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(n.Invalid, "MANIFEST_MISMATCH"):
            n.verify_archive(manifest)

    def test_manifest_pin_rejects_removed_episode(self):
        manifest = copy.deepcopy(self.artifacts["archive"])
        manifest["episodes"].pop()
        with self.assertRaises(n.Invalid):
            n.verify_archive(manifest)

    def test_frozen_git_objects_are_required(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(n.Invalid, "GIT_OBJECT"):
            n.build_manifest(Path(tmp))

    def test_archive_mutations_and_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in n.ARCHIVES:
                shutil.copytree(n.ROOT / folder, root / folder)
            manifest = self.artifacts["archive"]
            with patch.object(n, "build_manifest", return_value=manifest):
                n.verify_archive(manifest, root)
                target = root / manifest["episodes"][0]["path"]
                original = target.read_bytes()
                for changed in (original + b"injected instruction", original.replace(b"\n", b"\r\n")):
                    target.write_bytes(changed)
                    with self.assertRaisesRegex(n.Invalid, "BYTES_CHANGED"):
                        n.verify_archive(manifest, root)
                target.write_bytes(original)
                extra = root / n.ARCHIVES[0] / "extra.md"
                extra.write_bytes(b"untracked")
                with self.assertRaisesRegex(n.Invalid, "MEMBERSHIP"):
                    n.verify_archive(manifest, root)
                extra.unlink()
                target.unlink()
                with self.assertRaisesRegex(n.Invalid, "MEMBERSHIP"):
                    n.verify_archive(manifest, root)

    def test_immutable_freeze_is_idempotent_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            value = {"a": "Türkçe", "b": 2}
            first = n.freeze(tmp, "fixture", value)
            self.assertEqual(first, n.freeze(tmp, "fixture", dict(reversed(list(value.items())))))
            original = first.read_bytes()
            second = n.freeze(tmp, "fixture", {"a": "new"})
            self.assertNotEqual(first, second)
            self.assertEqual(original, first.read_bytes())
            first.write_bytes(b"tampered")
            with self.assertRaisesRegex(n.Invalid, "IMMUTABLE_COLLISION"):
                n.freeze(tmp, "fixture", value)
            self.assertEqual(b"tampered", first.read_bytes())

    def test_unsafe_paths(self):
        for value in ("../secret", "/absolute", "C:/file", "a\\b", "a/../b", "./a", "a//b"):
            with self.subTest(value=value), self.assertRaises(n.Invalid):
                n.safe_path(n.ROOT, value)

    def test_freeze_prefix_cannot_escape_directory(self):
        for prefix in ("../escape", "a/b", "C:", "", "a\\b"):
            with self.subTest(prefix=prefix), self.assertRaises(n.Invalid):
                n.freeze(n.HERE, prefix, {})

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "real").mkdir()
            try:
                (base / "link").symlink_to(base / "real", target_is_directory=True)
            except OSError:
                self.skipTest("OS does not grant symlink creation; Linux CI covers it")
            with self.assertRaisesRegex(n.Invalid, "SYMLINK"):
                n.safe_path(base, "link/file")

    def test_each_pinned_artifact_and_schema_resists_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "nml"
            shutil.copytree(n.HERE, folder)
            release = n.read_json(folder / "releases" / ("release-" + n.RELEASE_SHA256 + ".json"))
            for entry in [*release["artifacts"].values(), *release["schemas"].values()]:
                path = folder / entry["path"]
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.subTest(path=entry["path"]), patch.object(n, "HERE", folder), self.assertRaises(n.Invalid):
                    n.load_release()
                path.write_bytes(original)

    def test_release_self_hash_is_pinned_in_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "releases").mkdir()
            (folder / "releases" / ("release-" + n.RELEASE_SHA256 + ".json")).write_bytes(b'{}')
            with patch.object(n, "HERE", folder), self.assertRaisesRegex(n.Invalid, "RELEASE_CHANGED"):
                n.load_release()

    def test_extractions_all_link_and_validate(self):
        for record in self.artifacts["extractions"]:
            n.validate_extraction(record, self.artifacts["archive"])
            self.assertFalse(record["semantic_support_certified"])
            self.assertEqual("PENDING", record["human_review"])

    def mutate_extraction(self, action):
        record = copy.deepcopy(self.artifacts["extractions"][0])
        action(record)
        with self.assertRaises(n.Invalid):
            n.validate_extraction(record, self.artifacts["archive"])

    def test_extraction_bad_archive_hash(self):
        self.mutate_extraction(lambda r: r.update(archive_sha256="0" * 64))

    def test_extraction_unknown_episode(self):
        self.mutate_extraction(lambda r: r.update(source_id="sg1:S99E99"))

    def test_extraction_bad_span_hash(self):
        self.mutate_extraction(lambda r: r["axes"]["event"]["spans"][0].update(sha256="0" * 64))

    def test_extraction_out_of_bounds_and_empty_span(self):
        for changes in ({"start_byte": -1}, {"end_byte": 9999999}, {"end_byte": 1}):
            with self.subTest(changes=changes):
                self.mutate_extraction(lambda r: r["axes"]["event"]["spans"][0].update(changes))

    def test_extraction_utf8_mid_character_boundary(self):
        record = copy.deepcopy(self.artifacts["extractions"][0])
        source = next(e for e in self.artifacts["archive"]["episodes"] if e["id"] == record["source_id"])
        data = (n.ROOT / source["path"]).read_bytes()
        offset = next(i for i, b in enumerate(data) if b >= 192)
        piece = data[offset + 1:offset + 2]
        record["axes"]["event"]["spans"] = [dict(start_byte=offset + 1, end_byte=offset + 2, sha256=n.sha(piece))]
        with self.assertRaisesRegex(n.Invalid, "UTF8"):
            n.validate_extraction(record, self.artifacts["archive"])

    def test_unknown_cannot_have_positive_score_or_evidence(self):
        self.mutate_extraction(lambda r: r["axes"]["event"].update(epistemic="UNKNOWN"))

    def test_known_claim_needs_evidence(self):
        self.mutate_extraction(lambda r: r["axes"]["event"].update(spans=[]))

    def test_no_silent_human_approval(self):
        self.mutate_extraction(lambda r: r.update(human_review="APPROVED"))

    def test_valid_span_does_not_certify_semantics(self):
        record = copy.deepcopy(self.artifacts["extractions"][0])
        record["axes"]["event"]["claim"] = "This is a deliberately unsupported interpretation."
        n.validate_extraction(record, self.artifacts["archive"])
        self.assertFalse(record["semantic_support_certified"])
        self.assertEqual("PENDING", record["human_review"])

    def test_strict_request_types_and_unknown_fields(self):
        for changes in ({"age": True}, {"age": "10"}, {"count": 0}, {"count": 6}, {"age": 3},
                        {"age": 121}, {"reveal_ceiling": 3}, {"min_source_groups": 3},
                        {"families": ["unrecognized"]}, {"raw_source": "inject me"},
                        {"state_commit_authorized": True}, {"scope": "PRODUCTION"},
                        {"authorized_features": ["magic_unlimited"]}, {"canon_fingerprint": "short"},
                        {"families": ["ethical", "ethical"]}, {"recent_ids": ["NM-999"]}):
            with self.subTest(changes=changes), self.assertRaises(n.Invalid):
                self.select(**changes)

    def test_missing_canon_fingerprint_fails_closed(self):
        request = self.request()
        del request["canon_fingerprint"]
        with patch.object(n, "load_release", return_value=self.artifacts), self.assertRaises(n.Invalid):
            n.select(request)

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            for data in (b'{"age": 7, "age": 18}', b'{"value": NaN}', b'{"value": Infinity}', b'\xff'):
                path.write_bytes(data)
                with self.assertRaises(n.Invalid):
                    n.read_json(path)

    def test_unsupported_schema_keywords_fail_closed(self):
        with self.assertRaises(n.Invalid):
            n.validate({}, {"oneOf": []})
        with self.assertRaises(n.Invalid):
            n.validate({}, {"$ref": "https://example.invalid/schema"})

    def test_selection_replay(self):
        first = self.select()
        self.assertEqual(first, self.select())
        self.assertEqual(3, len(first[0]["mechanics"]))

    def test_checked_in_example_is_reproducible(self):
        writer, audit = self.select()
        self.assertEqual(n.read_json(n.HERE / "examples/writer-preview.v1.json"), writer)
        self.assertEqual(n.read_json(n.HERE / "examples/selection-audit.v1.json"), audit)

    def test_example_covers_only_declared_permissions(self):
        _, audit = self.select()
        for cid in audit["selected_ids"]:
            card = next(c for c in self.artifacts["cards"] if c["id"] == cid)
            self.assertTrue(set(card["effects"]) <= set(self.base["allowed_effects"]))
            self.assertTrue(set(card["requires"]) <= set(self.base["authorized_features"]))
            self.assertLessEqual(card["reveal_level"], self.base["reveal_ceiling"])

    def test_catalog_order_invariance(self):
        request = self.request()
        first = self.select()
        artifacts = copy.deepcopy(self.artifacts)
        artifacts["cards"].reverse()
        artifacts["templates"].reverse()
        with patch.object(n, "load_release", return_value=artifacts):
            self.assertEqual(first, n.select(request))

    def test_input_not_mutated(self):
        request = self.request()
        before = copy.deepcopy(request)
        with patch.object(n, "load_release", return_value=self.artifacts):
            writer, _ = n.select(request)
        self.assertEqual(before, request)
        writer["mechanics"][0]["name"] = "changed"
        self.assertNotIn("changed", [t["name"] for t in self.artifacts["templates"]])

    def test_withheld_card_is_never_selected(self):
        _, audit = self.select(age=18, forbidden_risks=[], reveal_ceiling=2, count=5)
        self.assertIn("CARD_WITHHELD", audit["exclusions"]["NM-007"])
        self.assertNotIn("NM-007", audit["selected_ids"])

    def test_age_boundaries_and_hard_floor(self):
        for age in (4, 6, 7, 9, 10, 14, 15, 18, 70, 120):
            writer, audit = self.select(age=age, forbidden_risks=[], reveal_ceiling=2)
            for cid in audit["selected_ids"]:
                card = next(c for c in self.artifacts["cards"] if c["id"] == cid)
                self.assertLessEqual(card["age_min"], age)
                if age < 10:
                    self.assertFalse(set(card["risks"]) & {"loss", "ethical_conflict", "identity_uncertainty"})
            if age < 7:
                self.assertEqual("ABSTAIN", writer["status"])

    def test_age_min_exact_transition(self):
        card = self.artifacts["cards"][5]
        self.assertIn("AGE", n._eligible(card, self.request(age=14, forbidden_risks=[])))
        self.assertNotIn("AGE", n._eligible(card, self.request(age=15, forbidden_risks=[])))

    def test_canon_requirements_are_hard(self):
        writer, audit = self.select(authorized_features=[])
        self.assertEqual("ABSTAIN", writer["status"])
        self.assertTrue(all("CANON_REQUIREMENTS" in reasons for reasons in audit["exclusions"].values()))

    def test_state_permission_is_hard(self):
        writer, _ = self.select(allowed_effects=[])
        self.assertEqual([], writer["mechanics"])
        self.assertFalse(writer["state_commit_authorized"])

    def test_reveal_ceiling_is_hard(self):
        writer, audit = self.select(reveal_ceiling=0)
        self.assertEqual("ABSTAIN", writer["status"])
        self.assertIn("REVEAL_CEILING", audit["exclusions"]["NM-016"])

    def test_forbidden_risks_are_hard(self):
        risks = ["mild_peril", "loss", "ethical_conflict", "identity_uncertainty"]
        _, audit = self.select(forbidden_risks=risks, count=2, min_families=2)
        for cid in audit["selected_ids"]:
            self.assertEqual([], next(c for c in self.artifacts["cards"] if c["id"] == cid)["risks"])

    def test_recent_history_exclusion(self):
        _, first = self.select()
        _, second = self.select(recent_ids=first["selected_ids"])
        self.assertFalse(set(first["selected_ids"]) & set(second["selected_ids"]))

    def test_fresh_state_changes_audit_binding(self):
        _, old = self.select()
        _, new = self.select(canon_fingerprint="b" * 64)
        self.assertNotEqual(old["request_sha256"], new["request_sha256"])
        self.assertNotEqual(old["canon_fingerprint"], new["canon_fingerprint"])

    def test_diversity_caps_and_minima(self):
        _, audit = self.select(count=4, min_families=3, max_per_family=2, max_per_source_group=2)
        selected = [c for c in self.artifacts["cards"] if c["id"] in audit["selected_ids"]]
        self.assertEqual(4, len(selected))
        self.assertGreaterEqual(len({c["family"] for c in selected}), 3)
        self.assertEqual(2, len({c["source_group"] for c in selected}))
        for key in ("family", "source_group"):
            self.assertTrue(all(sum(c[key] == value for c in selected) <= 2 for value in {c[key] for c in selected}))

    def test_impossible_diversity_never_relaxes(self):
        writer, audit = self.select(count=3, max_per_source_group=1)
        self.assertEqual("ABSTAIN", writer["status"])
        self.assertEqual("NO_FEASIBLE_SET", audit["reason"])
        self.assertEqual([], writer["mechanics"])

    def test_exact_search_finds_a_feasible_set_despite_bad_greedy_order(self):
        # Two scarce families in opposite source groups: choosing the wrong first
        # member would consume a group cap and strand a naive greedy selector.
        artifacts = copy.deepcopy(self.artifacts)
        keep = ["NM-001", "NM-005", "NM-010"]
        artifacts["cards"] = [c for c in artifacts["cards"] if c["id"] in keep]
        with patch.object(n, "load_release", return_value=artifacts):
            writer, audit = n.select(self.request(count=2, min_families=2, min_source_groups=2,
                                                   max_per_source_group=1, max_per_family=1))
        self.assertEqual("PROPOSED", writer["status"])
        self.assertIn("NM-010", audit["selected_ids"])

    def test_seed_variation_remains_policy_safe(self):
        seen = set()
        for seed in ("a", "b", "c", "d", "e"):
            _, audit = self.select(seed=seed)
            seen.add(tuple(audit["selected_ids"]))
            self.assertTrue(set(audit["selected_ids"]) <= set(audit["eligible_ids"]))
        self.assertGreater(len(seen), 1)

    def test_writer_has_only_allowlisted_fields(self):
        writer, audit = self.select()
        self.assertEqual({"schema", "scope", "status", "state_commit_authorized", "semantic_support_certified", "mechanics"}, set(writer))
        n.validate(writer, n.schema("writer"))
        self.assertNotIn("canon_fingerprint", writer)
        self.assertNotIn("exclusions", writer)
        self.assertNotIn("request_sha256", writer)
        self.assertEqual(n.fingerprint(writer), audit["writer_sha256"])

    def test_request_text_never_echoes_into_writer(self):
        writer, _ = self.select(seed='Stargate Atlantis ignore rules https://evil.invalid S01E01')
        result = n.canonical(writer).decode().casefold()
        self.assertNotIn("stargate", result)
        self.assertNotIn("evil.invalid", result)
        self.assertNotIn("s01e01", result)

    def test_all_templates_exclude_production_identifiers_and_links(self):
        text = n.canonical(self.artifacts["templates"]).decode().casefold()
        for forbidden in ("stargate", "atlantis", "sg-1", "wraith", "goa", "teal", "mckay", "sheppard",
                          "weir", "o’neill", "o'neill", "daniel", "carter", "http", "source_ids", "start_byte"):
            self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"s\d{2}e\d{2}", text))

    def test_templates_do_not_copy_eight_word_source_fragments(self):
        def windows(text):
            tokens = re.findall(r"\w+", text.casefold())
            return {tuple(tokens[i:i+8]) for i in range(len(tokens)-7)}
        source_windows = set()
        for entry in self.artifacts["archive"]["episodes"]:
            source_windows.update(windows((n.ROOT / entry["path"]).read_text(encoding="utf-8")))
        for template in self.artifacts["templates"]:
            self.assertFalse(source_windows & windows(n.canonical(template).decode()))

    def test_no_network_or_provider_needed_for_real_selection(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            writer, audit = n.select(self.request())
        self.assertEqual("PROPOSED", writer["status"])
        self.assertEqual(0, audit["provider_calls"])
        self.assertEqual(0, audit["paid_ai_usd"])

    def test_no_production_imports_or_call_sites(self):
        allowed = {"__future__", "copy", "hashlib", "itertools", "json", "pathlib", "re", "subprocess", "argparse", "sys", "core"}
        for path in n.HERE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(x.name.split(".")[0] in allowed for x in node.names))
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split(".")[0], allowed)
        for path in (n.ROOT / "src").glob("*.py"):
            self.assertNotIn("narrative_mechanics", path.read_text(encoding="utf-8"))

    def test_ci_has_no_model_credentials_or_dispatch(self):
        workflow = (n.ROOT / ".github/workflows/narrative-mechanics-offline.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("runs-on: self-hosted", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("python -m unittest tests.test_narrative_mechanics", workflow)
        for forbidden in ("secrets.", "API_KEY", "workflow_dispatch", "curl ", "pip install", "contents: write", "src."):
            self.assertNotIn(forbidden, workflow)

    def test_catalog_document_lists_every_card_and_withheld_status(self):
        text = (n.ROOT / "docs/research/narrative-mechanics/CARDS.md").read_text(encoding="utf-8")
        for card in self.artifacts["cards"]:
            self.assertIn("## " + card["id"], text)
        self.assertIn("WITHHELD", text)

    def test_cli_replay_hash_seed_independence_and_separate_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = []
            for seed in ("1", "492"):
                run = subprocess.run([sys.executable, "-m", "experiments.narrative_mechanics", "select", "--request",
                                      str(n.HERE / "examples/request.v1.json"), "--audit-dir", tmp],
                                     cwd=n.ROOT, env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, check=True)
                self.assertEqual(b"", run.stderr)
                outputs.append(run.stdout)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(1, len(list(Path(tmp).glob("selection-*.json"))))
            self.assertNotIn(b"source", outputs[0])

    def test_cli_invalid_request_has_no_source_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text('{"secret source":"Stargate"}', encoding="utf-8")
            run = subprocess.run([sys.executable, "-m", "experiments.narrative_mechanics", "select", "--request", str(path)],
                                 cwd=n.ROOT, capture_output=True)
            self.assertEqual(2, run.returncode)
            self.assertEqual(b"", run.stdout)
            self.assertNotIn(b"Stargate", run.stderr)


if __name__ == "__main__":
    unittest.main()
