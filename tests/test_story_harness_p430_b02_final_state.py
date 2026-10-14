"""P4.30: actual model B02 Q25 receipt yields non-committing Final StoryState draft."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.story_harness_p430_b02_final_state import (
    SCHEMA,DIR,Q25_REFERENCE,load_original_q25,
    qualify_source_and_evidence,project_b02_final_state,freeze_b02_state
)
from src.story_harness_p429_b02_q25 import load_b02_bundle
from src.story_harness_v1 import HarnessStop
from test_story_harness_p428_b02_master import make_sources
from src.story_harness_p428_b02_master import seal_b02_once,load_b02_quality
from src.story_harness_p427_b02_quality import get_b02_original


class P430Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p,q,m=make_sources(self.temp.name)
        original=get_b02_original(".",p)
        audit=load_b02_quality(".",q)
        seal_b02_once(original,audit,m)
        self.bundle=load_b02_bundle(".",p,q,m)
        self.q25=json.loads((Path(".")/Q25_REFERENCE).read_bytes())

    def test_original_B02_Q25_yields_read_only_not_canon(self):
        r=project_b02_final_state(self.bundle,self.q25)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["case_id"],"B02")
        self.assertEqual(r["known_locations_proposal"],["GARDEN","COMMONS"])
        self.assertEqual(r["last_protagonist_location_proposal"]["location_id"],"GARDEN")
        self.assertEqual([x["status"] for x in r["open_obligation_outcomes_unapproved"]],
                         ["SATISFIED","OPEN"])
        self.assertEqual(r["original_open_obligations_unchanged"],
                         self.bundle["source"]["pack"]["open_obligations"])
        self.assertIsNone(r["world_time_final"])
        self.assertEqual(r["world_time_initial_snapshot"],0)
        self.assertEqual(r["unknown_facts_retained"],
                         ["unobserved_owners","unobserved_locations"])
        self.assertEqual(r["model_posts_for_projection"],0)
        self.assertFalse(r["canon_commit_authorized"])
        self.assertFalse(r["production_change"])
        self.assertFalse(r["independent_final_state_semantic_certification"])
        self.assertEqual(r["original_q25_reported_cost_usd"],"0.021746")

    def test_original_protected_receipt_matches_bit_for_bit_frozen_GitHub(self):
        from src.story_harness_p429_b02_q25 import Q25_RUN_NAME
        with TemporaryDirectory() as td:
            p=Path(td)/Q25_RUN_NAME
            p.mkdir()
            original=(Path(".")/Q25_REFERENCE).read_bytes()
            (p/"01-b02-q25-evidence.json").write_bytes(original)
            self.assertEqual(load_original_q25(".",td),self.q25)
            (p/"01-b02-q25-evidence.json").write_bytes(original+b" ")
            with self.assertRaises(HarnessStop):
                load_original_q25(".",td)

    def test_false_satisfied_status_cannot_close_original_OPEN_obligation(self):
        q=deepcopy(self.q25)
        q["evidence_proposal"]["open_obligation_outcomes"][1]["status"]="SATISFIED"
        with self.assertRaises(HarnessStop):
            project_b02_final_state(self.bundle,q)

    def test_forged_time_owner_or_quote_is_denied(self):
        tests=("world_time","ownership","quote")
        for action in tests:
            q=deepcopy(self.q25)
            obs=q["evidence_proposal"]
            if action=="world_time":
                obs["world_time_delta"]=7
            elif action=="ownership":
                obs["object_observations"].append({
                    "object_name":"Cloud","last_seen_relation":"AT_GARDEN",
                    "ownership":"Aren","quote":"Then Cloud sang."})
            else:
                obs["final_location"]["quote"]="No such place in source"
            with self.subTest(action=action),self.assertRaises(HarnessStop):
                project_b02_final_state(self.bundle,q)

    def test_wrong_story_spine_canon_and_quality_flags_refused(self):
        for field in ("story_sha256","spine_sha256","source_pack_sha256",
                      "generation_id","semantic_state_fully_certified",
                      "production_state_write_authorized"):
            q=deepcopy(self.q25)
            q[field]="0"*64 if field.endswith("sha256") else (
                "fake" if field=="generation_id" else True)
            with self.subTest(field=field),self.assertRaises(HarnessStop):
                project_b02_final_state(self.bundle,q)

    def test_frozen_read_only_state_can_be_written_once_only(self):
        with TemporaryDirectory() as td:
            out=freeze_b02_state(self.bundle,self.q25,td)
            file=Path(td)/DIR/"final-state-draft.json"
            self.assertTrue(file.is_file())
            self.assertEqual(json.loads(file.read_bytes()),out)
            with self.assertRaises(FileExistsError):
                freeze_b02_state(self.bundle,self.q25,td)

    def test_replay_does_not_modify_B02_source_or_master(self):
        b=deepcopy(self.bundle)
        a=deepcopy(self.q25)
        project_b02_final_state(self.bundle,self.q25)
        self.assertEqual(b,self.bundle)
        self.assertEqual(a,self.q25)


if __name__=="__main__":
    unittest.main()
