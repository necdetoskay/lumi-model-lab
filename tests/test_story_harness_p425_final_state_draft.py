"""P4.25 actual B01-r06 Q25 receipt → read-only state projection tests."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case
from src.story_harness_p425_final_state_draft import (
    SCHEMA, DRAFT_DIR, EXPECTED_Q25_RECEIPT_SHA, REFERENCE,
    load_original_q25, qualify_q25, project_proposed_state,
    freeze_state_draft,
)
from src.story_harness_v1 import HarnessStop


def actual_source():
    repo=Path(".")
    p=compile_case(next(c for c in load_plan(repo)["cases"] if c["id"]=="B01"))
    spine=json.loads((repo/"evidence/story_harness_p421/b01-r06-original-spine-plan.json").read_text())
    story=json.loads((repo/"evidence/story_harness_p421/b01-r06-original-writer-draft.json").read_text())
    text=(repo/"evidence/story_harness_p423/b01-r06-pilot-english-master.txt").read_text()
    assert text==story["story_text"]
    q25=json.loads((repo/REFERENCE).read_text())
    return {"source":{"pack":p,"spine":spine,"story":story},
            "english_master_text":text},q25


class P425Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle,cls.q25=actual_source()

    def test_real_original_provider_q25_is_accepted_as_evidence_only(self):
        data,charge=qualify_q25(self.bundle,self.q25)
        self.assertEqual(data["final_location"]["location_id"],"HOME")
        self.assertEqual(data["discovered_locations"][0]["location_id"],"MEADOW")
        self.assertEqual(str(charge),"0.026022")
        self.assertEqual(len(data["object_observations"]),2)
        self.assertTrue(all(o["ownership"]=="UNKNOWN"
                            for o in data["object_observations"]))

    def test_real_projection_does_not_commit_canon_or_invent_time(self):
        b=deepcopy(self.bundle)
        r=project_proposed_state(b,self.q25)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["final_protagonist_location_proposal"]["location_id"],"HOME")
        self.assertEqual(r["known_locations_proposal"],["HOME","MEADOW"])
        self.assertEqual(r["world_time_initial_snapshot"],0)
        self.assertIsNone(r["world_time_final"])
        self.assertFalse(r["state_commit_authorized"])
        self.assertFalse(r["independent_state_semantic_validator_passed"])
        self.assertFalse(r["original_v21_4_full_final_quality_audit_passed"])
        self.assertEqual(r["original_canonical_objects_unchanged"],[])
        self.assertEqual(r["open_canonical_obligations_unchanged"],
                         b["source"]["pack"]["open_obligations"])
        self.assertEqual(r["manual_prose_edits"],0)
        self.assertEqual(r["model_calls_for_projection"],0)
        self.assertEqual(b,self.bundle)

    def test_only_same_story_spine_and_q25_model_generation_admitted(self):
        for key,bad in (("story_sha256","f"*64),("spine_sha256","f"*64),
                        ("source_pack_sha256","f"*64),
                        ("generation_id","synthetic-no-generation")):
            q=deepcopy(self.q25)
            q[key]=bad
            with self.subTest(key=key),self.assertRaises(HarnessStop):
                project_proposed_state(self.bundle,q)

    def test_untrusted_source_forgery_cannot_turn_evidence_into_certified_state(self):
        for key in ("semantic_state_fully_certified","final_story_state_committed",
                    "production_state_write_authorized"):
            q=deepcopy(self.q25)
            q[key]=True
            with self.subTest(key=key),self.assertRaises(HarnessStop):
                project_proposed_state(self.bundle,q)

    def test_object_ownership_fabrication_and_worldtime_forgery_denied(self):
        for field,value in (("ownership","Mira"),("world_time_delta",3)):
            q=deepcopy(self.q25)
            if field=="ownership":
                q["evidence_proposal"]["object_observations"][0]["ownership"]=value
            else:
                q["evidence_proposal"][field]=value
            with self.subTest(field=field),self.assertRaises(HarnessStop):
                project_proposed_state(self.bundle,q)

    def test_original_q25_receipt_and_frozen_github_reference_exact_bytes(self):
        raw=(Path(".")/REFERENCE).read_bytes()
        with TemporaryDirectory() as td:
            claim=Path(td)/"p424-b01-r06-q25-evidence-v02"
            claim.mkdir()
            (claim/"01-q25-proposal.json").write_bytes(raw)
            loaded=load_original_q25(".",td)
            self.assertEqual(loaded,self.q25)
            (claim/"01-q25-proposal.json").write_bytes(raw+b"\n")
            with self.assertRaises(HarnessStop):
                load_original_q25(".",td)

    def test_original_provider_receipt_digest_not_self_attesting(self):
        raw=(Path(".")/REFERENCE).read_bytes()
        with TemporaryDirectory() as td:
            root=Path(td)
            claim=root/"p424-b01-r06-q25-evidence-v02"
            claim.mkdir()
            (claim/"01-q25-proposal.json").write_bytes(raw)
            with patch("src.story_harness_p425_final_state_draft.EXPECTED_Q25_RECEIPT_SHA",
                       "0"*64):
                with self.assertRaises(HarnessStop):
                    load_original_q25(".",root)

    def test_read_only_final_draft_immutable_one_use(self):
        with TemporaryDirectory() as td:
            r=freeze_state_draft(self.bundle,self.q25,td)
            self.assertEqual(r["artifact_classification"],
                             "READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON")
            folder=Path(td)/DRAFT_DIR
            original=json.loads((folder/"final-state-draft.json").read_text())
            self.assertEqual(original,r)
            with self.assertRaises(FileExistsError):
                freeze_state_draft(self.bundle,self.q25,td)
            self.assertEqual(len(list(folder.iterdir())),1)

    def test_cannot_drop_unresolved_canon_obligations_based_on_model_status(self):
        r=project_proposed_state(self.bundle,self.q25)
        expected=self.bundle["source"]["pack"]["open_obligations"]
        self.assertEqual(r["open_canonical_obligations_unchanged"],expected)
        self.assertEqual([x["status"] for x in r["obligation_closure_evidence_not_yet_approved"]],
                         ["SATISFIED","SATISFIED"])
        self.assertIs(r["state_commit_authorized"],False)


if __name__=="__main__":
    unittest.main()
