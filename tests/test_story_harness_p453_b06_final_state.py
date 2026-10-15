"""P4.53: original paid Q25 v02 evidence -> immutable zero-cost B06 state draft."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p449_b06_quality import CLAIM_NAME,AUDIT_DIR,SOURCE_SHA,STORY_SHA
from src.story_harness_p450_b06_master import (
    AUDIT_PATH,SOURCE_FILES,seal_or_verify,original_b06,load_b06_quality,
)
from src.story_harness_p452_b06_q25 import load_b06_bundle,RUN_NAME as Q25_RUN_NAME
from src.story_harness_p453_b06_final_state import (
    Q25_REFERENCE,Q25_RECEIPT_SHA,Q25_INTENT_REFERENCE,Q25_INTENT_SHA,
    MASTER_REFERENCE,MASTER_RECEIPT_SHA,OUTPUT_DIR,
    original_b06_q25,verify_original_master_receipt,
    qualify_b06_q25,project_b06_final_state,freeze_or_verify,
)
from src.story_harness_v1 import HarnessStop

def fixture(td):
    root=Path(td)
    source=root/"producer";c=source/CLAIM_NAME;c.mkdir(parents=True)
    qa=root/"quality";aud=qa/AUDIT_DIR;aud.mkdir(parents=True)
    master=root/"master";master.mkdir()
    q25=root/"q25";claim=q25/Q25_RUN_NAME;claim.mkdir(parents=True)
    final=root/"final";final.mkdir()
    for name,saved in SOURCE_FILES.items():
        (c/name).write_bytes((Path("evidence/story_harness_p448")/saved).read_bytes())
    (aud/"01-audit-outcome.json").write_bytes(Path(AUDIT_PATH).read_bytes())
    seal_or_verify(original_b06(".",source),load_b06_quality(".",qa),master)
    (claim/"00-intent.json").write_bytes(Path(Q25_INTENT_REFERENCE).read_bytes())
    (claim/"01-q25-evidence.json").write_bytes(Path(Q25_REFERENCE).read_bytes())
    bundle=load_b06_bundle(".",source,qa,master)
    return bundle,q25,master,final

class P453Tests(unittest.TestCase):
    def test_original_real_q25_and_master_digest_are_pinned(self):
        for ref,sha in ((Q25_REFERENCE,Q25_RECEIPT_SHA),
                        (Q25_INTENT_REFERENCE,Q25_INTENT_SHA),
                        (MASTER_REFERENCE,MASTER_RECEIPT_SHA)):
            self.assertEqual(hashlib.sha256(Path(ref).read_bytes()).hexdigest(),sha)
        original=json.loads(Path(Q25_REFERENCE).read_bytes())
        self.assertEqual(original["generation_id"],"gen-1791994391-Nq4NFlp6dwA6ZLmm01MP")
        self.assertEqual(original["provider_reported_cost_usd"],"0.029742")
        self.assertFalse(original["final_story_state_committed"])

    def test_original_quote_replay_and_read_only_final_state(self):
        with TemporaryDirectory() as td:
            bundle,q25,master,final=fixture(td)
            verify_original_master_receipt(".",master,bundle)
            receipt=original_b06_q25(".",q25)
            result=project_b06_final_state(bundle,receipt)
            self.assertEqual(result["case_id"],"B06")
            self.assertEqual(result["last_protagonist_location_proposal"]["location_id"],"LIBRARY")
            self.assertEqual([p["location_id"] for p in result["new_discoveries_with_evidence"]],["TOWER"])
            self.assertEqual(result["known_locations_proposal"],["LIBRARY","TOWER"])
            self.assertEqual(result["original_open_obligations_unchanged"],
                             ["Sözleşme kapanmamıştır","Atlasın sahibi bilinmemektedir"])
            self.assertEqual([x["status"] for x in result["open_obligation_outcomes_unapproved"]],["OPEN","OPEN"])
            self.assertEqual(result["objects_not_admitted_to_canon"],[])
            self.assertEqual(result["unknown_facts_retained"],["unobserved_owners","unobserved_locations"])
            self.assertIsNone(result["world_time_final"])
            self.assertFalse(result["canon_commit_authorized"])
            self.assertFalse(result["production_change"])
            self.assertFalse(result["final_story_state_committed"])
            self.assertEqual(result["model_posts_for_projection"],0)

    def test_freeze_once_and_replay_no_overwrite(self):
        with TemporaryDirectory() as td:
            bundle,q25,master,final=fixture(td)
            receipt=original_b06_q25(".",q25)
            first,new=freeze_or_verify(bundle,receipt,final)
            self.assertTrue(new)
            p=final/OUTPUT_DIR/"final-state-draft.json"
            raw=p.read_bytes()
            second,new=freeze_or_verify(bundle,receipt,final)
            self.assertFalse(new)
            self.assertEqual(first,second)
            self.assertEqual(p.read_bytes(),raw)
            p.write_bytes(raw+b"edited")
            with self.assertRaises(HarnessStop):
                freeze_or_verify(bundle,receipt,final)

    def test_tampered_provider_receipt_is_blocked(self):
        with TemporaryDirectory() as td:
            bundle,q25,master,final=fixture(td)
            p=q25/Q25_RUN_NAME/"01-q25-evidence.json"
            p.write_bytes(p.read_bytes()+b" ")
            with self.assertRaises(HarnessStop):
                original_b06_q25(".",q25)
            self.assertFalse(list(final.iterdir()))

    def test_changing_master_is_denied(self):
        with TemporaryDirectory() as td:
            bundle,q25,master,final=fixture(td)
            p=next(master.glob("*/ENGLISH_MASTER.txt"))
            p.write_bytes(p.read_bytes()+b"spoof")
            with self.assertRaises(HarnessStop):
                load_b06_bundle(".",Path(td)/"producer",Path(td)/"quality",master)

    def test_unknown_owner_false_obligation_wrong_time_and_cross_story_stopped(self):
        with TemporaryDirectory() as td:
            bundle,q25,master,final=fixture(td)
            original=original_b06_q25(".",q25)
            for defect in ("owner","location","obligation","time","story","cost"):
                counterfeit=deepcopy(original)
                obs=counterfeit["evidence_proposal"]
                if defect=="owner":
                    obs["object_observations"]=[{"object_name":"atlas",
                        "last_seen_relation":"AT_LIBRARY","ownership":"YASMIN",
                        "quote":"The atlas's owner was unknown."}]
                elif defect=="location":obs["final_location"]["location_id"]="TOWER"
                elif defect=="obligation":obs["open_obligation_outcomes"][0]["status"]="SATISFIED"
                elif defect=="time":obs["world_time_delta"]=1
                elif defect=="story":counterfeit["story_sha256"]="f"*64
                elif defect=="cost":counterfeit["provider_reported_cost_usd"]="0.001"
                with self.subTest(defect=defect),self.assertRaises(HarnessStop):
                    project_b06_final_state(bundle,counterfeit)
            self.assertFalse(list(final.iterdir()))
if __name__=="__main__":
    unittest.main()
