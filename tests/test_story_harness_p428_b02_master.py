"""P4.28 B02 pilot Master reads the real, immutable 5/5 quality artifact."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.story_harness_p427_b02_quality import (
    SOURCE_SHA,SPINE_SHA,STORY_SHA,COPY_FILES,EVIDENCE_DIR,get_b02_original
)
from src.story_harness_p428_b02_master import (
    MASTER_DIR,AUDIT_FILE,load_b02_quality,seal_b02_once
)
from src.story_harness_v1 import HarnessStop


def make_sources(root):
    parent=Path(root)
    source=parent/"producer"
    quality=parent/"audit"
    master=parent/"master"
    (source/("b02-"+SOURCE_SHA[:16]+"-r06")).mkdir(parents=True)
    (quality/("p427-b02-r06-"+STORY_SHA[:12])).mkdir(parents=True)
    master.mkdir()
    for key,item in COPY_FILES.items():
        (source/("b02-"+SOURCE_SHA[:16]+"-r06")/key).write_bytes(
            (Path(".")/EVIDENCE_DIR/item).read_bytes())
    (quality/("p427-b02-r06-"+STORY_SHA[:12])/"01-audit-outcome.json").write_bytes(
        (Path(".")/AUDIT_FILE).read_bytes())
    return source,quality,master


class P428Tests(unittest.TestCase):
    def test_real_original_b02_is_eligible_only_for_pilot_master(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            original=get_b02_original(".",prod)
            audit=load_b02_quality(".",qa)
            manifest=seal_b02_once(original,audit,out)
            self.assertEqual(manifest["case_id"],"B02")
            self.assertEqual(manifest["source_story_sha256"],STORY_SHA)
            self.assertEqual(manifest["approved_spine_sha256"],SPINE_SHA)
            self.assertEqual(manifest["english_master_word_count"],561)
            self.assertEqual(manifest["independent_initial_audit_verdict"],"ACCEPT")
            self.assertEqual(manifest["reader_score"],5)
            self.assertEqual(manifest["audit_cost_usd"],"0.02069")
            self.assertTrue(manifest["q25_read_only_extraction_allowed"])
            self.assertFalse(manifest["production_master_published"])
            self.assertFalse(manifest["production_state_write_authorized"])
            master=(out/MASTER_DIR/"ENGLISH_MASTER.txt").read_bytes()
            self.assertEqual(hashlib.sha256(master).hexdigest(),STORY_SHA)
            self.assertEqual(master,original["story"]["story_text"].encode())
            self.assertEqual(json.loads((out/MASTER_DIR/"master-manifest.json").read_text()),
                             manifest)

    def test_once_only_cannot_write_second_master(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            original=get_b02_original(".",prod)
            audit=load_b02_quality(".",qa)
            seal_b02_once(original,audit,out)
            with self.assertRaises(FileExistsError):
                seal_b02_once(original,audit,out)

    def test_other_case_cannot_inherit_original_B02_quality(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            original=get_b02_original(".",prod)
            audit=load_b02_quality(".",qa)
            original["case_id"]="B01"
            with self.assertRaises(HarnessStop):
                seal_b02_once(original,audit,out)
            self.assertEqual(list(out.iterdir()),[])

    def test_injected_approval_flag_never_makes_qa_authorize_prod(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            original=get_b02_original(".",prod)
            for field in ("production_state_write_authorized",
                          "english_master_authorized","q25_authorized"):
                a=load_b02_quality(".",qa)
                a[field]=True
                with self.subTest(field=field),self.assertRaises(HarnessStop):
                    seal_b02_once(original,a,out)

    def test_quality_REJECT_or_missing_blocker_refuses_master(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            original=get_b02_original(".",prod)
            for name,value in (("quality_initial_verdict","REJECT"),
                               ("quality_initial_audit_accepted",False),
                               ("blocking_findings",[{"family":"canon","quote":"bad","reason":"bad"}]),
                               ("reader_score",3)):
                record=load_b02_quality(".",qa)
                record[name]=value
                with self.subTest(name=name),self.assertRaises(HarnessStop):
                    seal_b02_once(original,record,out)
            self.assertEqual(list(out.iterdir()),[])

    def test_saved_qa_receipt_must_be_real_and_byte_identical(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            q=qa/("p427-b02-r06-"+STORY_SHA[:12])/"01-audit-outcome.json"
            v=json.loads(q.read_text())
            v["reader_score"]=4
            q.write_text(json.dumps(v)+"\n")
            with self.assertRaises(HarnessStop):
                load_b02_quality(".",qa)

    def test_different_original_writer_prose_is_not_sealed(self):
        with TemporaryDirectory() as td:
            prod,qa,out=make_sources(td)
            original=get_b02_original(".",prod)
            audit=load_b02_quality(".",qa)
            original["story"]["story_text"]+=" one invented word"
            with self.assertRaises(HarnessStop):
                seal_b02_once(original,audit,out)
            self.assertEqual(list(out.iterdir()),[])


if __name__=="__main__":
    unittest.main()
