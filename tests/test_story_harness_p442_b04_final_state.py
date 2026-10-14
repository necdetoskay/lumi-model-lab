"""P4.42 genuine B04 Q25 quote replay -> immutable read-only final state."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p439_b04_quality import CLAIM_NAME,AUDIT_DIR,SOURCE_SHA,STORY_SHA
from src.story_harness_p440_b04_master import AUDIT_PATH,SOURCE_FILES,seal_or_verify,original_b04,load_b04_quality
from src.story_harness_p441_b04_q25 import load_b04_bundle,RUN_NAME as Q25_RUN_NAME
from src.story_harness_p442_b04_final_state import (
    Q25_REFERENCE,Q25_RECEIPT_SHA,MASTER_REFERENCE,MASTER_RECEIPT_SHA,
    OUTPUT_DIR,original_b04_q25,verify_original_master_receipt,
    qualify_b04_q25,project_b04_final_state,freeze_or_verify
)
from src.story_harness_v1 import HarnessStop

def fixture(td):
    root=Path(td)
    pr=root/"producer";claim=pr/CLAIM_NAME;claim.mkdir(parents=True)
    qr=root/"quality"; qa=qr/AUDIT_DIR;qa.mkdir(parents=True)
    mr=root/"master";mr.mkdir()
    q25=root/"q25";(q25/Q25_RUN_NAME).mkdir(parents=True)
    final=root/"final";final.mkdir()
    for name,frozen in SOURCE_FILES.items():
        (claim/name).write_bytes((Path("evidence/story_harness_p438")/frozen).read_bytes())
    (qa/"01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    src=original_b04(".",pr);aud=load_b04_quality(".",qr)
    seal_or_verify(src,aud,mr)
    (q25/Q25_RUN_NAME/"01-q25-evidence.json").write_bytes(Path(Q25_REFERENCE).read_bytes())
    bundle=load_b04_bundle(".",pr,qr,mr)
    return root,bundle,q25,mr,final

class P442Tests(unittest.TestCase):
    def test_frozen_real_final_state_byte_replay_without_inference(self):
        original=Path("evidence/story_harness_p442/b04-r06-real-read-only-final-state-draft.json")
        raw=original.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "e85296ebc76b1278a6ee05a12015cc2516ec3ef03a247f9fd14ede0ab12ab978")
        with TemporaryDirectory() as td:
            _,bundle,q25,master,_=fixture(td)
            record=original_b04_q25(".",q25)
            calculated=project_b04_final_state(bundle,record)
            self.assertEqual(json.loads(raw),calculated)

    def test_actual_q25_and_master_hashes(self):
        a=Path(Q25_REFERENCE).read_bytes()
        m=Path(MASTER_REFERENCE).read_bytes()
        self.assertEqual(hashlib.sha256(a).hexdigest(),Q25_RECEIPT_SHA)
        self.assertEqual(hashlib.sha256(m).hexdigest(),MASTER_RECEIPT_SHA)
        real=json.loads(a)
        self.assertEqual(real["case_id"],"B04")
        self.assertEqual(real["generation_id"],"gen-1791967013-OBmyunMTruhDSL9mkOYD")
        self.assertEqual(real["provider_reported_cost_usd"],"0.0452")
        self.assertFalse(real["final_story_state_committed"])

    def test_replay_real_original_quotes_studio_and_unresolved_obligations(self):
        with TemporaryDirectory() as td:
            _,b,q25,mr,_=fixture(td)
            verify_original_master_receipt(".",mr,b)
            actual=original_b04_q25(".",q25)
            projection=project_b04_final_state(b,actual)
            self.assertEqual(projection["known_locations_proposal"],["MARKET","STUDIO"])
            self.assertEqual(projection["last_protagonist_location_proposal"]["location_id"],"STUDIO")
            self.assertEqual([x["status"] for x in projection["open_obligation_outcomes_unapproved"]],
                             ["OPEN","OPEN"])
            self.assertEqual(len(projection["objects_not_admitted_to_canon"]),4)
            self.assertTrue(all(x["ownership"]=="UNKNOWN" for x in projection["objects_not_admitted_to_canon"]))
            self.assertEqual(projection["unknown_facts_retained"],["unobserved_owners","unobserved_locations"])
            self.assertIsNone(projection["world_time_final"])
            self.assertFalse(projection["canon_commit_authorized"])
            self.assertFalse(projection["production_change"])
            self.assertEqual(projection["model_posts_for_projection"],0)

    def test_sealed_once_rechecked_without_mutation(self):
        with TemporaryDirectory() as td:
            _,b,q25,mr,final=fixture(td)
            actual=original_b04_q25(".",q25)
            first,created=freeze_or_verify(b,actual,final)
            self.assertTrue(created)
            path=final/OUTPUT_DIR/"final-state-draft.json"
            sealed=path.read_bytes()
            second,created=freeze_or_verify(b,actual,final)
            self.assertFalse(created)
            self.assertEqual(first,second)
            self.assertEqual(path.read_bytes(),sealed)
            path.write_bytes(path.read_bytes()+b"tampered")
            with self.assertRaises(HarnessStop):
                freeze_or_verify(b,actual,final)

    def test_edited_original_q25_receipt_is_denied(self):
        with TemporaryDirectory() as td:
            _,b,q25,mr,final=fixture(td)
            receipt=q25/Q25_RUN_NAME/"01-q25-evidence.json"
            changed=json.loads(receipt.read_bytes())
            changed["provider_reported_cost_usd"]="0.010"
            receipt.write_text(json.dumps(changed))
            with self.assertRaises(HarnessStop):
                original_b04_q25(".",q25)
            self.assertEqual(list(final.iterdir()),[])

    def test_synthetic_owner_or_satisfied_map_denied(self):
        with TemporaryDirectory() as td:
            _,b,q25,mr,final=fixture(td)
            original=original_b04_q25(".",q25)
            for defect in ["owner","location","obligation","time","cross_story"]:
                fake=deepcopy(original)
                if defect=="owner":
                    fake["evidence_proposal"]["object_observations"][0]["ownership"]="EMIR"
                elif defect=="location":
                    fake["evidence_proposal"]["final_location"]["location_id"]="MARKET"
                elif defect=="obligation":
                    fake["evidence_proposal"]["open_obligation_outcomes"][1]["status"]="SATISFIED"
                elif defect=="time":
                    fake["evidence_proposal"]["world_time_delta"]=1
                else:
                    fake["story_sha256"]="f"*64
                with self.subTest(defect=defect),self.assertRaises(HarnessStop):
                    project_b04_final_state(b,fake)
            self.assertEqual(list(final.iterdir()),[])

if __name__=="__main__":
    unittest.main()
