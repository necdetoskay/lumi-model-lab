"""SERA v0.15 one-call live adapter tests; no actual provider calls."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from unittest.mock import patch

from experiments.sera.tests.test_identity_resolution_v014 import (
    synthetic_mention_census,
)
from experiments.sera.tests.test_blind_identity_v015 import (
    synthetic_model_rows,
)
from experiments.sera.mara_s1_blind_identity_pilot_v015 import run,MODEL

def preflight_module():
    m=ModuleType("src.openrouter_preflight")
    m.fetch_key_status=lambda key:{"synthetic":True}
    m.enforce_key_access=lambda data,min_remaining:None
    return m

class BlindIdentityPilotV015Tests(unittest.TestCase):
    def test_one_source_only_provider_call_full_result_no_authority(self):
        raw=json.dumps(synthetic_model_rows())
        provider={"error":None,"raw":{
            "id":"synthetic-reviewed-identity","model":MODEL,
            "usage":{"cost":0.0075},
            "choices":[{
                "finish_reason":"stop","message":{"content":raw},
            }],
        }}
        with TemporaryDirectory() as td:
            dest=Path(td)/"pilot.json"
            with patch.dict(sys.modules,{
                "src.openrouter_preflight":preflight_module(),
            }),patch(
                "experiments.sera.mara_s1_blind_identity_pilot_v015.one_provider_call",
                return_value=provider,
            ) as caller:
                res=run(mentions=synthetic_mention_census(),output=dest,
                        launch_id="synthetic-only",key="fake")
                caller.assert_called_once()
                self.assertEqual(caller.call_args.kwargs["model"],MODEL)
                sent=caller.call_args.kwargs["prepared"]["request"]
                self.assertNotIn("max_tokens",str(sent))
                self.assertNotIn("max_output_tokens",str(sent))
            self.assertEqual(res["status"],
                             "ALL_IDENTITY_MODEL_OPINIONS_BOUND_NONCANONICAL_HOLD")
            self.assertEqual(res["provider_attempts"],1)
            self.assertEqual(res["bound_advisory"]["proposed_count"],16)
            self.assertEqual(res["raw_provider_content"],raw)
            self.assertEqual(res["provider_reported_cost"],0.0075)
            self.assertFalse(res["canonical_commit_authorized"])
            self.assertFalse(res["output_token_limit_configured"])
            self.assertEqual(res["world_db_writes"],0)
            self.assertEqual(res["new_entities_created"],0)
            self.assertEqual(res["new_relationship_links"],0)
            self.assertEqual(json.loads(dest.read_text())["status"],res["status"])

    def test_source_unbound_reply_is_preserved_but_rejected(self):
        forged=synthetic_model_rows()
        forged["rows"][0]["support_quote"]="a fictional invisible object"
        provider={"error":None,"raw":{
            "id":"synthetic-corrupt","model":MODEL,
            "usage":{"cost":0.009},"choices":[{
                "finish_reason":"stop","message":{"content":json.dumps(forged)},
            }],
        }}
        with TemporaryDirectory() as td:
            dest=Path(td)/"evidence.json"
            with patch.dict(sys.modules,{
                "src.openrouter_preflight":preflight_module(),
            }),patch(
                "experiments.sera.mara_s1_blind_identity_pilot_v015.one_provider_call",
                return_value=provider,
            ) as caller:
                res=run(mentions=synthetic_mention_census(),output=dest,
                        launch_id="synthetic-invalid",key="fake")
                caller.assert_called_once()
            self.assertEqual(res["status"],"IDENTITY_PROVIDER_OR_CONTRACT_HOLD")
            self.assertEqual(res["provider_reported_cost"],0.009)
            self.assertIsNone(res["bound_advisory"])
            self.assertIn("V015_SOURCE_QUOTE_NOT_EXACT",res["error_code"])
            self.assertEqual(
                json.loads(dest.read_text())["raw_provider_content"],
                json.dumps(forged))
            self.assertFalse(res["canonical_commit_authorized"])

    def test_http_failure_does_not_retry_or_fallback(self):
        with TemporaryDirectory() as td:
            with patch.dict(sys.modules,{
                "src.openrouter_preflight":preflight_module(),
            }),patch(
                "experiments.sera.mara_s1_blind_identity_pilot_v015.one_provider_call",
                return_value={"error":"HTTP_400",
                              "provider_detail":"synthetic invalid JSON schema"},
            ) as caller:
                res=run(mentions=synthetic_mention_census(),
                        output=Path(td)/"evidence.json",
                        launch_id="synthetic-400",key="fake")
                caller.assert_called_once()
            self.assertEqual(res["status"],"PROVIDER_ERROR_HOLD")
            self.assertEqual(res["error_code"],"HTTP_400")
            self.assertEqual(res["provider_attempts"],1)

    def test_missing_key_means_zero_calls(self):
        with TemporaryDirectory() as td:
            res=run(mentions=synthetic_mention_census(),
                    output=Path(td)/"no-key.json",
                    launch_id="synthetic-missing-key",key="")
            self.assertEqual(res["status"],"IDENTITY_PROVIDER_OR_CONTRACT_HOLD")
            self.assertEqual(res["error_code"],"V015_OPENROUTER_KEY_MISSING")
            self.assertEqual(res["provider_attempts"],0)

if __name__=="__main__":
    unittest.main()
