"""P4.34 B03 genuine initial ACCEPT -> immutable pilot English Master."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p432_b03_quality import (
    FILES, EVIDENCE_DIR, SOURCE_SHA, SPINE_SHA, STORY_SHA, get_original_B03,
)
from src.story_harness_p434_b03_master import (
    AUDIT_PATH, AUDIT_RECEIPT_SHA256, QUALITY_CLAIM, MASTER_DIR,
    load_b03_quality, seal_b03_once,
)
from src.story_harness_v1 import HarnessStop

def sources(tmp):
    root = Path(tmp)
    prod = root / "producer"
    quality = root / "quality"
    master = root / "master"
    claim = prod / ("b03-" + SOURCE_SHA[:16] + "-r06")
    claim.mkdir(parents=True)
    qa = quality / QUALITY_CLAIM
    qa.mkdir(parents=True)
    master.mkdir()
    for original, frozen in FILES.items():
        (claim / original).write_bytes((Path(EVIDENCE_DIR) / frozen).read_bytes())
    (qa / "01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    return prod, quality, master, qa

class P434Tests(unittest.TestCase):
    def test_p433_original_receipt_sha(self):
        receipt = Path(AUDIT_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(receipt).hexdigest(), AUDIT_RECEIPT_SHA256)
        audit = json.loads(receipt)
        self.assertEqual(audit["case_id"], "B03")
        self.assertTrue(audit["quality_initial_audit_accepted"])
        self.assertEqual(audit["reader_score"], 4)
        self.assertEqual(audit["blocking_findings"], [])

    def test_real_original_b03_master_seals_exact_text(self):
        with TemporaryDirectory() as td:
            prod, quality, out, _ = sources(td)
            original = get_original_B03(".", prod)
            audit = load_b03_quality(".", quality)
            result = seal_b03_once(original, audit, out)
            self.assertEqual(result["case_id"], "B03")
            self.assertEqual(result["approved_spine_sha256"], SPINE_SHA)
            self.assertEqual(result["accepted_story_sha256"], STORY_SHA)
            self.assertEqual(result["english_master_word_count"], 1300)
            self.assertEqual(result["audit_cost_usd"], "0.027522")
            self.assertFalse(result["production_master_published"])
            self.assertFalse(result["production_state_write_authorized"])
            text = (out / MASTER_DIR / "ENGLISH_MASTER.txt").read_bytes()
            self.assertEqual(hashlib.sha256(text).hexdigest(), STORY_SHA)
            self.assertEqual(text, original["story"]["story_text"].encode())
            self.assertEqual(json.loads((out / MASTER_DIR / "master-manifest.json").read_bytes()), result)
            with self.assertRaises(FileExistsError):
                seal_b03_once(original, audit, out)

    def test_tampered_receipt_does_not_seal(self):
        with TemporaryDirectory() as td:
            prod, quality, out, qa = sources(td)
            a = json.loads((qa / "01-audit-outcome.json").read_bytes())
            a["reader_score"] = 5
            (qa / "01-audit-outcome.json").write_text(json.dumps(a))
            with self.assertRaises(HarnessStop):
                load_b03_quality(".", quality)
            self.assertEqual(list(out.iterdir()), [])

    def test_bad_verdict_and_cross_story_denied(self):
        with TemporaryDirectory() as td:
            prod, quality, out, _ = sources(td)
            original = get_original_B03(".", prod)
            audit = load_b03_quality(".", quality)
            for key, bad in [("quality_initial_verdict", "REJECT"),
                             ("blocking_findings", [{"family":"canon","quote":"x","reason":"x"}]),
                             ("reader_score", 3),
                             ("auditor_generation_id", "gen-fake"),
                             ("q25_authorized", True)]:
                corrupted = dict(audit)
                corrupted[key] = bad
                with self.subTest(key=key), self.assertRaises(HarnessStop):
                    seal_b03_once(original, corrupted, out)
            cross = dict(original)
            cross["case_id"] = "B02"
            with self.assertRaises(HarnessStop):
                seal_b03_once(cross, audit, out)
            self.assertEqual(list(out.iterdir()), [])

    def test_mutated_original_draft_denied(self):
        with TemporaryDirectory() as td:
            prod, quality, out, _ = sources(td)
            original = get_original_B03(".", prod)
            audit = load_b03_quality(".", quality)
            original["story"]["story_text"] += " fabrication"
            with self.assertRaises(HarnessStop):
                seal_b03_once(original, audit, out)
            self.assertEqual(list(out.iterdir()), [])

if __name__ == "__main__":
    unittest.main()
