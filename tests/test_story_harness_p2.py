"""P2: locally executed *integrity* gate; historical author verdicts stay untrusted."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.story_harness_p2 import (
    GateReceipt, StageInput, StageResult, generate_receipts, verify_report,
)
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "configs/story_harness_p1_frozen_import.json"


def source():
    return json.loads((ROOT / MANIFEST).read_text(encoding="utf8"))


class P2RealIntegrityGate(unittest.TestCase):
    def test_typed_schema_is_frozen_and_offline_only(self):
        self.assertTrue(all(obj.__dataclass_params__.frozen
            for obj in (GateReceipt, StageInput, StageResult)))
        r=generate_receipts(manifest=source(),repo_root=ROOT)
        self.assertEqual(r["schema"],"lumi.story-harness-p2-result-bundle.v1")
        self.assertEqual(r["mode"],"LOCAL_ARCHIVE_VERIFICATION_ONLY")
        self.assertEqual(r["case_count"],4)
        self.assertEqual(r["actual_local_integrity_checks_executed"],4)
        self.assertFalse(r["original_spine_or_q25_gates_reexecuted"])
        self.assertFalse(r["original_human_review_authenticated"])
        self.assertFalse(r["semantic_support_certified"])
        self.assertFalse(r["full_story_state_qualified"])
        self.assertFalse(r["state_commit_authorized"])
        self.assertFalse(r["production_write_performed"])
        self.assertFalse(r["model_execution_performed"])
        self.assertEqual(r["provider_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")
        self.assertEqual(r["downstream_stage_executions_authorized"],0)
        self.assertTrue(r["independent_case_records_only"])

    def test_original_rejections_and_source_candidate_limited_are_preserved(self):
        r=generate_receipts(manifest=source(),repo_root=ROOT)
        self.assertEqual(
            [s["original_historical_outcome"] for s in r["stage_results"]],
            ["ACCEPT","FAIL_KNOWN_DEFECT_MISSED",
             "SOURCE_BOUND_CANDIDATES_ONLY","REJECTED_BY_OFFLINE_GATE"])
        self.assertEqual([s["stop_reason"] for s in r["stage_results"]], [
            "HISTORICAL_APPROVAL_UNAUTHENTICATED",
            "HISTORICAL_QUALITY_GATE_FAILED",
            "STATE_CANDIDATES_AWAIT_SEMANTIC_REVIEW",
            "HISTORICAL_EXTRACTOR_GATE_REJECTED"])
        for s in r["stage_results"]:
            self.assertEqual(s["state"],"STOPPED_PENDING_UNVERIFIED_GATE")
            self.assertFalse(s["downstream_execution_authorized"])
            self.assertFalse(s["semantic_support_certified"])
            self.assertFalse(s["canonical_state_commit_authorized"])
            self.assertEqual(s["provider_calls_this_run"],0)
            self.assertEqual(s["provider_cost_usd_this_run"],"0")

    def test_gate_receipts_verify_only_local_archive_checks_not_people(self):
        r=generate_receipts(manifest=source(),repo_root=ROOT)
        for inp,rec,out in zip(
                r["stage_inputs"],r["gate_receipts"],r["stage_results"]):
            self.assertEqual(inp["source_commit"],r["source_commit"])
            self.assertTrue(inp["independent_case_only"])
            self.assertEqual(rec["gate_id"],"p2.local-frozen-integrity-gate.v1")
            self.assertEqual(rec["locally_verified_scope"],"FROZEN_ARCHIVE_BYTES_AND_SCHEMA_ONLY")
            self.assertEqual(rec["local_integrity_result"],"PASS")
            self.assertTrue(rec["check_executed"])
            self.assertFalse(rec["original_historical_gate_reexecuted"])
            self.assertFalse(rec["original_human_reviewer_authenticated"])
            self.assertFalse(rec["semantic_validity_certified"])
            self.assertFalse(rec["stage_execution_authorized"])
            self.assertEqual(rec["input_sha256"],digest(canonical_bytes(inp)))
            self.assertEqual(out["input_sha256"],rec["input_sha256"])
            self.assertEqual(out["gate_receipt_sha256"],digest(canonical_bytes(rec)))
            self.assertEqual(rec["artifact_set_sha256"],
                digest(canonical_bytes(inp["archived_artifact_sha256_by_role"])))
            self.assertEqual(rec["verifier_source_sha256"],
                hashlib.sha256((ROOT/"src/story_harness_p1.py").read_bytes()).hexdigest())

    def test_original_report_deterministic_reverified_and_cannot_be_promoted(self):
        manifest=source(); before=copy.deepcopy(manifest)
        one=generate_receipts(manifest=manifest,repo_root=ROOT)
        self.assertEqual(one,generate_receipts(manifest=manifest,repo_root=ROOT))
        self.assertTrue(verify_report(one,manifest=manifest,repo_root=ROOT))
        self.assertEqual(manifest,before)
        for mutation in [
            ("stage_result","original_historical_outcome","SOURCE_BOUND_CANDIDATES_ONLY"),
            ("stage_result","state","GATE_ACCEPTED"),
            ("stage_result","downstream_execution_authorized",True),
            ("stage_result","stop_reason","READY_TO_WRITE"),
            ("receipt","original_human_reviewer_authenticated",True),
            ("receipt","original_historical_gate_reexecuted",True),
            ("receipt","semantic_validity_certified",True),
            ("receipt","check_executed",False),
            ("receipt","gate_id","fake-verified-judge.v1"),
            ("input","source_commit","0"*40),
            ("root","state_commit_authorized",True),
            ("root","provider_calls",1),
        ]:
            with self.subTest(mutation=mutation):
                kind,key,value=mutation
                forged=copy.deepcopy(one)
                field=(forged["stage_results"][3] if kind=="stage_result"
                    else forged["gate_receipts"][1] if kind=="receipt"
                    else forged["stage_inputs"][2] if kind=="input"
                    else forged)
                field[key]=value
                with self.assertRaises(HarnessStop):
                    verify_report(forged,manifest=manifest,repo_root=ROOT)

    def test_historical_paid_run_cannot_be_transformed_into_source_pass(self):
        m=source()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"src").mkdir()
            (root/"src/story_harness_p1.py").write_bytes(
                (ROOT/"src/story_harness_p1.py").read_bytes())
            for case in m["cases"]:
                for f in case["files"]:
                    p=root/f["archive"]
                    p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes((ROOT/f["archive"]).read_bytes())
            case=m["cases"][3]
            ledger=root/case["files"][0]["archive"]
            x=json.loads(ledger.read_text("utf8"))
            x["outcome"]="SOURCE_BOUND_CANDIDATES_ONLY"
            ledger.write_text(json.dumps(x,ensure_ascii=False)+"\n",encoding="utf8")
            with self.assertRaises(HarnessStop):
                generate_receipts(manifest=m,repo_root=root)

    def test_report_is_not_a_cross_story_chain(self):
        r=generate_receipts(manifest=source(),repo_root=ROOT)
        self.assertEqual(
            len({s["case_id"] for s in r["stage_results"]}),4)
        self.assertEqual(
            len({s["input_sha256"] for s in r["stage_results"]}),4)
        self.assertFalse(any(s["downstream_execution_authorized"]
                             for s in r["stage_results"]))

    def test_unknown_or_changed_source_manifest_fails_closed(self):
        for change in ["commit","wrong_path","swap_raw","extra_case","paid_mode"]:
            with self.subTest(change=change):
                m=source()
                if change=="commit":m["source_commit"]="0"*40
                elif change=="wrong_path":m["cases"][0]["files"][0]["source_path"]="evidence/q25/fake.json"
                elif change=="swap_raw":m["cases"][2]["files"][1]["sha256"]="0"*64
                elif change=="extra_case":m["cases"].append(copy.deepcopy(m["cases"][0]))
                elif change=="paid_mode":m["mode"]="EXECUTE_PAID"
                with self.assertRaises(HarnessStop):
                    generate_receipts(manifest=m,repo_root=ROOT)

    def test_frozen_real_stage_receipts_match_recomputation_exactly(self):
        archived_path = ROOT / "evidence/story_harness_p2/pinned-local-integrity-receipts.json"
        original = archived_path.read_bytes()
        saved = json.loads(original.decode("utf8"))
        computed = generate_receipts(manifest=source(),repo_root=ROOT)
        self.assertEqual(saved, computed)
        self.assertTrue(verify_report(saved, manifest=source(), repo_root=ROOT))
        self.assertEqual(original, archived_path.read_bytes())
        self.assertEqual(saved["provider_calls"],0)
        self.assertFalse(saved["original_spine_or_q25_gates_reexecuted"])
        self.assertFalse(saved["state_commit_authorized"])

    def test_cli_verifies_frozen_report_but_does_not_promote(self):
        command=[sys.executable,"-m","src.story_harness_p2",
                 "--manifest",MANIFEST,
                 "--verify-report","evidence/story_harness_p2/pinned-local-integrity-receipts.json",
                 "--repo-root",str(ROOT)]
        output=subprocess.check_output(command,text=True,encoding="utf8",cwd=ROOT)
        report=json.loads(output)
        self.assertEqual(report,generate_receipts(manifest=source(),repo_root=ROOT))
        self.assertEqual(report["downstream_stage_executions_authorized"],0)
        self.assertEqual(report["provider_cost_usd"],"0")

    def test_cli_twice_same_bytes(self):
        cmd=[sys.executable,"-m","src.story_harness_p2",
             "--manifest",MANIFEST,"--repo-root",str(ROOT)]
        a=subprocess.check_output(cmd,text=True,encoding="utf8",cwd=ROOT)
        b=subprocess.check_output(cmd,text=True,encoding="utf8",cwd=ROOT)
        self.assertEqual(a,b)
        self.assertEqual(json.loads(a),
                         generate_receipts(manifest=source(),repo_root=ROOT))


if __name__=="__main__":
    unittest.main()
