"""v0.21 actual SERA source-bound recheck composition; zero provider calls."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.artifact_scene_checker_v021 import build_bundle, create_checker
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.semantic_recovery_v018 import execute as semantic_execute
from experiments.sera.tests.test_semantic_risks_v011 import SOURCE, report
from experiments.sera.tests.test_event_candidate_projection_v019 import model
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.unattended_scene_rewrite_v020 import execute as loop

WORLD=entry_state()

def event(kind,quote,object_id,actor,payload,ident):
    i=SOURCE.index(quote)
    sid=next(x["id"] for x in sentences(SOURCE)
             if x["start"]<=i and i+len(quote)<=x["end"])
    return {"event_id":ident,"type":kind,"actor_id":actor,"object_id":object_id,
            "sentence_id":sid,"evidence":{"start":i,"end":i+len(quote),"quote":quote},
            "payload":payload}

def evidence(root):
    semantic=semantic_execute(prose=SOURCE,extraction_report=report(),
        call_model=model,output_dir=root/"advisories")
    typed=[
        event("OBSERVE_OPENABLE","pocket watch open","vane_watch","vane",
              {"expected":"UNKNOWN","observed":"OPEN"},"open"),
        event("SET_OPENABLE","closed the case","vane_watch","vane",
              {"expected":"OPEN","next":"CLOSED"},"close"),
        event("APPEND_DOCUMENT_ENTRY","Discrepancy unknown.","mara_notebook","mara",
              {"expected_append_count":0,"text":"Discrepancy unknown."},"write"),
    ]
    bundle=build_bundle(prose=SOURCE,world=WORLD,extraction_report=report(),
        semantic_summary=semantic,typed_registry={
            "openables":["vane_watch"],"documents":["mara_notebook"]},
        typed_candidates=typed)
    path=root/"evidence"
    path.mkdir()
    (path/(prose_hash(SOURCE)+".json")).write_text(
        json.dumps(bundle,ensure_ascii=False),encoding="utf-8")
    return path

class SourceEvidenceIntegrationTests(unittest.TestCase):
    def test_actual_v019_and_v020_run_with_source_bound_archives(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            original=deepcopy(WORLD)
            checked=create_checker(evidence_root=evidence(root))(
                prose=SOURCE,world=deepcopy(WORLD))
        self.assertEqual(WORLD,original)
        self.assertEqual(len(checked["projection"]["reclassification_proposals"]),2)
        self.assertEqual(checked["typed"]["typed_preview"]["simulated_revision"],3)
        self.assertEqual(checked["typed"]["typed_preview"]["aspects"]["vane_watch"]
                         ["position"],"CLOSED")
        self.assertEqual(checked["typed"]["status"],
                         "AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL")
        self.assertEqual(checked["typed"]["world_db_writes"],0)
        self.assertFalse(checked["typed"]["canonical_commit_authorized"])

    def test_missing_new_story_artifact_never_reuses_old_semantic_opinion(self):
        with TemporaryDirectory() as d:
            checker=create_checker(evidence_root=evidence(Path(d)))
            with self.assertRaisesRegex(
                CoverageError,"V021_EVIDENCE_FOR_PROSE_NOT_AVAILABLE"):
                checker(prose=SOURCE+" Another scene.",world=deepcopy(WORLD))

    def test_world_revision_change_blocks_stale_receipt_reuse(self):
        with TemporaryDirectory() as d:
            checker=create_checker(evidence_root=evidence(Path(d)))
            changed=deepcopy(WORLD);changed["revision"]+=1
            with self.assertRaisesRegex(
                CoverageError,"V021_EVIDENCE_WORLD_OR_SOURCE_MISMATCH"):
                checker(prose=SOURCE,world=changed)

    def test_forged_event_quote_fails_strict_provenance(self):
        with TemporaryDirectory() as d:
            folder=evidence(Path(d))
            file=folder/(prose_hash(SOURCE)+".json")
            blob=json.loads(file.read_text(encoding="utf-8"))
            blob["extraction_report"]["candidate_events"][0]["quote"]="forgery"
            file.write_text(json.dumps(blob),encoding="utf-8")
            with self.assertRaises(CoverageError):
                create_checker(evidence_root=folder)(
                    prose=SOURCE,world=deepcopy(WORLD))

    def test_live_controller_requests_recheck_but_blocks_unverified_rewrite(self):
        calls=[]
        def writer(*,source,defects):
            calls.append(defects)
            return {"prose":source+" Added uncertainty.",
                    "receipt":{"source_prose_sha256":prose_hash(source),
                               "response_id":"mock", "model":"mock",
                               "finish_reason":"stop","cost_usd":"0.001"}}
        with TemporaryDirectory() as d:
            root=Path(d)
            out=loop(prose=SOURCE,world=deepcopy(WORLD),
                     check_scene=create_checker(evidence_root=evidence(root)),
                     rewrite_scene=writer,output_dir=root/"loop")
        self.assertEqual(len(calls),1)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(out["reason_code"],"V020_SCENE_CHECK_FAILED_SAFE")
        self.assertFalse(out["requires_manual_intervention"])
        self.assertFalse(out["canonical_commit_authorized"])

if __name__=="__main__":
    unittest.main()
