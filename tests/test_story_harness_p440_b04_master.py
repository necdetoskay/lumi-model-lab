"""P4.40 real B04 Master seal and source/adversary regression gates."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p439_b04_quality import CLAIM_NAME, AUDIT_DIR, STORY_SHA, SOURCE_SHA
from src.story_harness_p440_b04_master import (
    AUDIT_PATH, AUDIT_SHA, MASTER_DIR, SOURCE_FILES, original_b04,
    load_b04_quality, manifest_for, seal_or_verify,
)
from src.story_harness_v1 import HarnessStop

def fixture(tmp):
    root=Path(tmp)
    producer=root/"producer"; claim=producer/CLAIM_NAME; claim.mkdir(parents=True)
    quality=root/"quality"; qa=quality/AUDIT_DIR; qa.mkdir(parents=True)
    master=root/"master"; master.mkdir()
    for name,frozen in SOURCE_FILES.items():
        (claim/name).write_bytes((Path("evidence/story_harness_p438")/frozen).read_bytes())
    (qa/"01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    return root,producer,quality,master,claim,qa

class P440Tests(unittest.TestCase):
    def test_genuine_frozen_provider_quality_sha(self):
        raw=Path(AUDIT_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),AUDIT_SHA)
        a=json.loads(raw)
        self.assertEqual(a["quality_initial_verdict"],"ACCEPT")
        self.assertEqual(a["auditor_reported_cost_usd"],"0.02468")
        self.assertEqual(a["blocking_findings"],[])
        self.assertEqual(a["reader_score"],4)

    def test_original_b04_master_sealed_and_idempotent_verification(self):
        with TemporaryDirectory() as tmp:
            _,pr,qr,mr,_,_=fixture(tmp)
            src=original_b04(".",pr); qa=load_b04_quality(".",qr)
            m,created=seal_or_verify(src,qa,mr)
            self.assertTrue(created)
            self.assertEqual(m["accepted_story_sha256"],STORY_SHA)
            self.assertEqual(m["english_master_word_count"],1277)
            self.assertEqual(m["audit_cost_usd"],"0.02468")
            self.assertEqual(m["source_pack_sha256"],SOURCE_SHA)
            self.assertFalse(m["production_state_write_authorized"])
            raw=(mr/MASTER_DIR/"ENGLISH_MASTER.txt").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),STORY_SHA)
            original=(mr/MASTER_DIR/"master-manifest.json").read_bytes()
            again,new=seal_or_verify(src,qa,mr)
            self.assertFalse(new)
            self.assertEqual(m,again)
            self.assertEqual(original,(mr/MASTER_DIR/"master-manifest.json").read_bytes())

    def test_modified_producer_claim_cannot_seal(self):
        with TemporaryDirectory() as tmp:
            _,pr,qr,mr,claim,_=fixture(tmp)
            p=claim/"story-draft.json"
            p.write_bytes(p.read_bytes()+b" ")
            with self.assertRaises(HarnessStop):
                original_b04(".",pr)
            self.assertFalse((mr/MASTER_DIR).exists())

    def test_modified_original_audit_denied(self):
        with TemporaryDirectory() as tmp:
            _,pr,qr,mr,_,qa=fixture(tmp)
            p=qa/"01-audit-outcome.json"
            q=json.loads(p.read_bytes())
            q["reader_score"]=5
            p.write_text(json.dumps(q))
            with self.assertRaises(HarnessStop):
                load_b04_quality(".",qr)
            self.assertFalse((mr/MASTER_DIR).exists())

    def test_replaced_auditor_and_fabricated_prose_denied(self):
        with TemporaryDirectory() as tmp:
            _,pr,qr,mr,_,_=fixture(tmp)
            src=original_b04(".",pr); qa=load_b04_quality(".",qr)
            fake=deepcopy(qa); fake["auditor_generation_id"]="gen-replaced"
            with self.assertRaises(HarnessStop):
                manifest_for(src,fake)
            fake=deepcopy(src);fake["story"]["story_text"] += " Forged."
            with self.assertRaises(HarnessStop):
                manifest_for(fake,qa)
            self.assertFalse((mr/MASTER_DIR).exists())

    def test_existing_master_tampering_refused_without_repair(self):
        with TemporaryDirectory() as tmp:
            _,pr,qr,mr,_,_=fixture(tmp)
            src=original_b04(".",pr);qa=load_b04_quality(".",qr)
            seal_or_verify(src,qa,mr)
            path=mr/MASTER_DIR/"ENGLISH_MASTER.txt"
            path.write_bytes(path.read_bytes()+b" edited")
            with self.assertRaises(HarnessStop):
                seal_or_verify(src,qa,mr)
            self.assertTrue(path.read_bytes().endswith(b" edited"))

if __name__=="__main__":
    unittest.main()
