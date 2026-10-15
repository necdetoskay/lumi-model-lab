"""P4.2 standalone redacted final-audit diagnostics & frozen v21.4 replay."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

import src.story_harness_p42 as p42
import src.story_harness_p42_diagnostics as diag
from src.story_harness_v1 import HarnessStop, load_json, secure_artifact

ROOT=Path(__file__).resolve().parents[1]


def pinned():
    path=os.environ.get("STORY_HARNESS_PINNED_P42_ROOT")
    return Path(path).resolve(strict=True) if path else None


@unittest.skipUnless(os.environ.get("STORY_HARNESS_PINNED_P42_ROOT"),
                     "Genuine immutable v21 source is required")
class P42FrozenDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe=p42.run_original_diagnostics(repo_root=ROOT,pinned_source_root=pinned())
        cls.p40=load_json(secure_artifact(ROOT,
           "evidence/story_harness_p40/pinned-v21-producer-preflight.json"))
        cls.p41=load_json(secure_artifact(ROOT,
           "evidence/story_harness_p41/pinned-synthetic-seal-contract-receipt.json"))

    def test_actual_v21_4_failed_final_diagnostics_all_seven_cases(self):
        rows=p42._validate_rows(self.probe,self.p40,self.p41)
        self.assertEqual([r["case"] for r in rows],list(p42.CASES))
        self.assertEqual(len(rows),7)
        self.assertEqual([r["phase"] for r in rows],[
           "response_validation","response_validation","response_validation",
           "structured_parse","transport","usage_validation","usage_validation"])
        self.assertEqual([r["error_category"] for r in rows],[
           "UNEXPECTED_FIELD","MISSING_FIELD","INVALID_TYPE",
           "UNSPECIFIED","UNSPECIFIED","INVALID_USAGE","INVALID_USAGE"])
        for r in rows:
            self.assertEqual(r["quality_status"],"REJECT_PROVIDER_FAILURE")
            self.assertEqual(r["model_call_attempts"],3)
            self.assertEqual(r["failed_stage"],"FINAL_AUDIT")
            self.assertTrue(r["immutable_record_preserved"])
            self.assertTrue(r["no_secrets_persisted"])
            self.assertTrue(r["provider_evidence_is_redacted"])

    def test_live_original_v21_retry_and_persist_controls(self):
        first=self.probe["cases"][0]
        self.assertEqual(first["model_call_attempts"],3)
        self.assertEqual(first["accounted_model_calls"],3)
        self.assertTrue(first["usage_accounting_complete"])
        self.assertEqual(first["source_story_sha256"],
                         self.p41["synthetic_previews"][1]["validation"]["preview_story_sha256"])

    def test_report_stays_a_stop_no_story_accept(self):
        r=p42.qualify(repo_root=ROOT,pinned_source_root=pinned())
        self.assertEqual(r["stop_reason"],"REAL_QUALITY_NOT_ACCEPTED_DIAGNOSTIC_READY")
        self.assertTrue(r["original_v21_4_adapter_and_runtime_exercised"])
        self.assertFalse(r["frozen_v21_4_source_modified"])
        self.assertFalse(r["historical_v21_3_failed_provider_response_recovered"])
        self.assertTrue(r["real_paid_history_preserved_as_rejected"])
        self.assertEqual(r["last_quality_status"],"REJECT_PROVIDER_FAILURE")
        self.assertEqual(r["diagnostic_case_count"],7)
        self.assertEqual(r["provider_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")
        for key in ("raw_provider_payload_or_secret_persisted",
                    "provider_failure_auto_retried","old_unbounded_repair_loop_restored",
                    "real_story_quality_accepted","english_master_seal_authorized",
                    "q25_extraction_authorized","state_commit_authorized",
                    "production_write_performed"):
            self.assertFalse(r[key])

    def test_forged_success_or_skipped_stage_rejected(self):
        candidates=[
            lambda a:a["cases"][0].update(quality_status="ACCEPT"),
            lambda a:a["cases"][0].update(model_call_attempts=4),
            lambda a:a["cases"][0].update(failed_stage="INITIAL_AUDIT"),
            lambda a:a["cases"][1].update(phase="transport"),
            lambda a:a["cases"][3].update(error_category="ACCEPT"),
            lambda a:a["cases"][4].update(no_secrets_persisted=False),
            lambda a:a["cases"][5].update(usage_accounting_complete=True),
            lambda a:a["cases"][2].update(source_story_sha256="f"*64),
            lambda a:a["cases"].pop(),
        ]
        for i,mutation in enumerate(candidates):
            data=copy.deepcopy(self.probe)
            mutation(data)
            with self.subTest(index=i),self.assertRaises(HarnessStop):
                p42._validate_rows(data,self.p40,self.p41)

    def test_untrusted_freeform_provider_response_redacted(self):
        private="Bearer sk-original-secret_AaA0123456789"
        obj={
           "phase":"response_validation",
           "parsed_response":{"findings":[{"family":private,"reason":private}],
                              "summary":private,"malicious_extra_field":private},
           "provider_response":{"choices":[{"message":{"content":private}}],
                                "headers":{"authorization":private}},
           "wire_payload":{"full_story":private},
           "parsed_response_sha256":"0"*64,
           "provider_response_sha256":"1"*64,
           "wire_payload_sha256":"2"*64,
        }
        exc=types.SimpleNamespace(
            provider_evidence=obj,usage={"api_calls":1,"input_tokens":100,
                 "output_tokens":20,"total_tokens":120,"reasoning_tokens":0,
                 "cost_usd":0.011,"latency_seconds":0.2},
            diagnostic_message="$.findings[0].family: Invalid response enum "+private)
        record=diag.describe_failure(exc,stage="FINAL_AUDIT",input_sha256="3"*64,
             source_story_sha256="4"*64,run_id="mock")
        raw=json.dumps(record)
        self.assertNotIn(private,raw)
        self.assertNotIn("malicious_extra_field",raw)
        self.assertNotIn("full_story",raw)
        self.assertEqual(record["validation_diagnostic"]["category"],"INVALID_ENUM")
        self.assertEqual(record["validation_diagnostic"]["schema_path"],"$.findings[0].family")
        self.assertTrue(record["raw_response_redacted"])
        self.assertEqual(record["usage"]["values"]["cost_usd"],0.011)

    def test_atomic_write_permissions_and_forbidden_replay(self):
        exc=types.SimpleNamespace(
            provider_evidence={"phase":"response_validation",
              "parsed_response":{"findings":[],"summary":"secret phrase 123"}},
            usage={"api_calls":1,"input_tokens":1,"output_tokens":1,
                   "total_tokens":2,"reasoning_tokens":0,"cost_usd":0.001,
                   "latency_seconds":0.001},
            diagnostic_message="$: Unexpected response field")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"diagnostics"
            expected=diag.persist_failure(exc,stage="FINAL_AUDIT",
                input_sha256="a"*64,source_story_sha256="b"*64,
                run_id="fake",output_dir=p)
            f=p/"targeted-final-audit-diagnostic.json"
            first=f.read_bytes()
            self.assertEqual(json.loads(first),expected)
            self.assertEqual(f.stat().st_mode & 0o777,0o600)
            with self.assertRaises(FileExistsError):
                diag.persist_failure(exc,stage="FINAL_AUDIT",
                    input_sha256="c"*64,source_story_sha256="d"*64,
                    run_id="fake",output_dir=p)
            self.assertEqual(f.read_bytes(),first)
            self.assertNotIn("secret phrase 123",first.decode())

    def test_symlinked_diagnostic_directory_forbidden(self):
        exc=types.SimpleNamespace(provider_evidence={},usage=None,
                                  diagnostic_message="secret")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            target=root/"real";target.mkdir()
            link=root/"symlink";link.symlink_to(target,target_is_directory=True)
            with self.assertRaises(RuntimeError):
                diag.persist_failure(exc,stage="FINAL_AUDIT",
                  input_sha256="a"*64,source_story_sha256="b"*64,
                  run_id="x",output_dir=link)

    def test_unknown_usage_is_not_claimed_as_zero(self):
        for malformed in (
           None,{},{"api_calls":1,"input_tokens":2},
           {"api_calls":1,"input_tokens":10,"output_tokens":1,
            "total_tokens":11,"reasoning_tokens":0,"cost_usd":float("nan"),
            "latency_seconds":1},
        ):
            u=diag._usage(malformed)
            self.assertFalse(u["accounting_complete"])
            self.assertIn("cost_usd",u["missing_fields"])
            self.assertIsNone(u["values"].get("cost_usd") if u["values"] else None)

    def test_forged_adapter_evidence_not_forwarded_to_runtime(self):
        exc=types.SimpleNamespace(
            provider_evidence={"parsed_response":{"secret":"sk-secret-here"}},
            usage=None,
            diagnostic_message="Bearer sk-never-echo")
        record=diag.describe_failure(exc,stage="FINAL_AUDIT",
              input_sha256="0"*64,source_story_sha256="1"*64,run_id="negative")
        forwarded=diag.RedactedProviderFailure(exc,record)
        self.assertIsNone(forwarded.usage)
        self.assertNotIn("sk-never-echo",str(forwarded))
        self.assertNotIn("sk-secret-here",json.dumps(forwarded.provider_evidence))
        self.assertFalse(forwarded.provider_evidence["raw_sensitive_text_stored"])

    def test_forged_stored_receipt_rejected(self):
        original=p42.qualify(repo_root=ROOT,pinned_source_root=pinned())
        stored=load_json(secure_artifact(ROOT,
            "evidence/story_harness_p42/pinned-targeted-audit-diagnostics.json"))
        self.assertEqual(original,stored)
        forged=copy.deepcopy(stored)
        forged["real_story_quality_accepted"]=True
        self.assertNotEqual(original,forged)
        with self.assertRaises(HarnessStop):
            p42._must(forged==original,"receipt changed")

    def test_source_root_wrong_fails_closed(self):
        with self.assertRaises(HarnessStop):
            p42.qualify(repo_root=ROOT,pinned_source_root=ROOT)


if __name__=="__main__":unittest.main()

