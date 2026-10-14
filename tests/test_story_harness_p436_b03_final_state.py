"""P4.36 replay B03 actual Q25 and safely project read-only last state."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p432_b03_quality import (
    SOURCE_SHA, SPINE_SHA, STORY_SHA, FILES, EVIDENCE_DIR, get_original_B03,
)
from src.story_harness_p434_b03_master import (
    AUDIT_PATH, QUALITY_CLAIM, seal_b03_once, load_b03_quality,
)
from src.story_harness_p435_b03_q25 import (
    load_b03_bundle, RUN_NAME as Q25_RUN_NAME,
)
from src.story_harness_p436_b03_final_state import (
    Q25_REFERENCE, Q25_RECEIPT_SHA, OUTPUT_DIR,
    load_original_q25, qualify_q25, project_b03_final_state, freeze_b03_state,
)
from src.story_harness_v1 import HarnessStop

def sources(td):
    root = Path(td)
    producer = root / "producer"
    claim = producer / ("b03-" + SOURCE_SHA[:16] + "-r06")
    claim.mkdir(parents=True)
    quality = root / "quality"
    qa = quality / QUALITY_CLAIM
    qa.mkdir(parents=True)
    master = root / "master"
    master.mkdir()
    q25 = root / "q25"
    q25claim = q25 / Q25_RUN_NAME
    q25claim.mkdir(parents=True)
    final = root / "final"
    final.mkdir()
    for original, frozen in FILES.items():
        (claim / original).write_bytes((Path(EVIDENCE_DIR) / frozen).read_bytes())
    (qa / "01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    source = get_original_B03(".", producer)
    audit = load_b03_quality(".", quality)
    seal_b03_once(source, audit, master)
    (q25claim / "01-q25-evidence.json").write_bytes(Path(Q25_REFERENCE).read_bytes())
    bundle = load_b03_bundle(".", producer, quality, master)
    return root, bundle, q25, final

class P436Tests(unittest.TestCase):
    def test_frozen_real_q25_receipt_is_original_bytes(self):
        original = Path(Q25_REFERENCE).read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), Q25_RECEIPT_SHA)
        record = json.loads(original)
        self.assertEqual(record["case_id"], "B03")
        self.assertEqual(record["provider_reported_cost_usd"], "0.031366")
        self.assertEqual(record["generation_id"], "gen-1791962013-EUhZDIwF6TSPzFoV4B9S")
        self.assertFalse(record["semantic_state_fully_certified"])

    def test_project_real_b03_preserves_open_river_and_unknown_ownership(self):
        with TemporaryDirectory() as td:
            _, bundle, q25, _ = sources(td)
            receipt = load_original_q25(".", q25)
            snapshot = deepcopy(bundle["source"]["pack"]["canonical_state"])
            draft = project_b03_final_state(bundle, receipt)
            self.assertEqual(draft["known_locations_proposal"], ["RIVERBANK", "VILLAGE"])
            self.assertEqual(draft["last_protagonist_location_proposal"]["location_id"], "VILLAGE")
            self.assertEqual([x["status"] for x in draft["open_obligation_outcomes_unapproved"]],
                             ["OPEN", "SATISFIED"])
            self.assertEqual(len(draft["objects_not_admitted_to_canon"]), 3)
            self.assertTrue(all(x["ownership"] == "UNKNOWN"
                                for x in draft["objects_not_admitted_to_canon"]))
            self.assertIsNone(draft["world_time_final"])
            self.assertFalse(draft["canon_commit_authorized"])
            self.assertFalse(draft["production_change"])
            self.assertEqual(draft["model_posts_for_projection"], 0)
            self.assertEqual(bundle["source"]["pack"]["canonical_state"], snapshot)

    def test_freeze_once_does_not_allow_overwrite(self):
        with TemporaryDirectory() as td:
            _, bundle, q25, final = sources(td)
            receipt = load_original_q25(".", q25)
            one = freeze_b03_state(bundle, receipt, final)
            raw = (final / OUTPUT_DIR / "final-state-draft.json").read_bytes()
            self.assertEqual(json.loads(raw), one)
            with self.assertRaises(FileExistsError):
                freeze_b03_state(bundle, receipt, final)
            self.assertEqual((final / OUTPUT_DIR / "final-state-draft.json").read_bytes(), raw)

    def test_tampered_protected_q25_refuses_before_state(self):
        with TemporaryDirectory() as td:
            root, _, q25, final = sources(td)
            path = q25 / Q25_RUN_NAME / "01-q25-evidence.json"
            record = json.loads(path.read_bytes())
            record["provider_reported_cost_usd"] = "0.01"
            path.write_text(json.dumps(record))
            with self.assertRaises(HarnessStop):
                load_original_q25(".", q25)
            self.assertEqual(list(final.iterdir()), [])

    def test_invented_owner_and_changed_obligations_are_denied(self):
        with TemporaryDirectory() as td:
            _, bundle, q25, final = sources(td)
            genuine = load_original_q25(".", q25)
            for alteration in ("owner", "river", "location", "world_time", "cross_story"):
                fake = deepcopy(genuine)
                if alteration == "owner":
                    fake["evidence_proposal"]["object_observations"][0]["ownership"] = "OLD_MAN"
                elif alteration == "river":
                    fake["evidence_proposal"]["open_obligation_outcomes"][0]["status"] = "SATISFIED"
                elif alteration == "location":
                    fake["evidence_proposal"]["final_location"]["location_id"] = "RIVERBANK"
                elif alteration == "world_time":
                    fake["evidence_proposal"]["world_time_delta"] = 42
                else:
                    fake["story_sha256"] = "0" * 64
                with self.subTest(alteration=alteration), self.assertRaises(HarnessStop):
                    project_b03_final_state(bundle, fake)
            self.assertEqual(list(final.iterdir()), [])

if __name__ == "__main__":
    unittest.main()
