"""Isolated key preflight is always read-only and cannot authorize a POST."""
from datetime import datetime, timezone
from unittest.mock import Mock
import copy
import unittest

from src.story_harness_cohort_provider_observe_v1 import (
    analyze_isolated_key, observe_provider_read_only, offline_status, KEY_ENV
)
from src.story_harness_v1 import HarnessStop

NOW=datetime(2026,10,14,20,0,tzinfo=timezone.utc)
def key(**overrides):
    row={
        "is_management_key":False,"is_provisioning_key":False,
        "is_free_tier":False,"include_byok_in_limit":True,
        "limit_reset":None,"limit":4.4,"limit_remaining":4.4,
        "usage":0,"byok_usage":0,"expires_at":None,
        "label":"NEVER_LOG_PRIVATE_KEY_LABEL",
        "hash":"NEVER_LOG_PRIVATE_KEY_IDENTIFIER",
    }
    row.update(overrides)
    return {"data":row}
def catalog():
    return {"data":{
        "id":"anthropic/claude-sonnet-5.5",
        "endpoints":[{
            "provider_name":"Anthropic","tag":"anthropic",
            "model_id":"anthropic/claude-sonnet-5.5","status":0,
            "supported_parameters":[
                "temperature","max_tokens","response_format","structured_outputs"
            ],
            "pricing":{"prompt":"0.000002","completion":"0.00001"},
            "context_length":200000,"max_completion_tokens":16000,
        }],
    }}

class IsolatedReadOnlyKeyTests(unittest.TestCase):
    def test_key_metadata_not_external_attestation(self):
        r=analyze_isolated_key(key(),now=NOW)
        self.assertEqual(r["configured_limit_usd"],"4.4")
        self.assertFalse(r["real_live_key_provenance"])
        self.assertFalse(r["provider_dispatch_authorized"])
        self.assertNotIn("NEVER_LOG_PRIVATE_KEY_LABEL",str(r))
        self.assertNotIn("NEVER_LOG_PRIVATE_KEY_IDENTIFIER",str(r))
    def test_shared_used_or_recharging_key_rejected(self):
        for k, val in [
            ("limit",20),("limit_remaining",3.9),("usage",0.01),
            ("byok_usage",0.01),("limit_reset","daily"),
            ("include_byok_in_limit",False),("is_management_key",True),
            ("is_provisioning_key",True),("is_free_tier",True),
        ]:
            with self.subTest(field=k),self.assertRaises(HarnessStop):
                analyze_isolated_key(key(**{k:val}),now=NOW)
    def test_no_login_and_no_post_with_fake_get(self):
        calls={"key":0,"catalog":0}
        def getter(*,api_key):
            self.assertEqual(api_key,"sk-or-offline-unique-isolated-test")
            calls["key"]+=1
            return key()
        def model_catalog():
            calls["catalog"]+=1
            return catalog()
        r=observe_provider_read_only(
            api_key="sk-or-offline-unique-isolated-test",
            key_fetch=getter,catalog_fetch=model_catalog,now=NOW)
        self.assertEqual(calls,{"key":1,"catalog":1})
        self.assertTrue(r["key_get_attempted"])
        self.assertFalse(r["real_live_key_provenance"])
        self.assertFalse(r["provider_dispatch_authorized"])
    def test_catalog_provider_or_schema_unavailable_rejected(self):
        def fake_get(*,api_key):return key()
        for mutation in ("provider","model","unsupported","price"):
            x=catalog()
            e=x["data"]["endpoints"][0]
            if mutation=="provider":e["provider_name"]="Other"
            if mutation=="model":x["data"]["id"]="other/model"
            if mutation=="unsupported":e["supported_parameters"]=[]
            if mutation=="price":e["pricing"]["completion"]="0.0001"
            with self.subTest(case=mutation),self.assertRaises(HarnessStop):
                observe_provider_read_only(
                    api_key="sk-or-offline-unique-isolated-test",
                    key_fetch=fake_get,catalog_fetch=lambda:x,now=NOW)
    def test_script_default_does_not_read_credentials(self):
        r=offline_status()
        self.assertEqual(r["required_secret_name"],KEY_ENV)
        self.assertEqual(r["paid_model_calls"],0)
        self.assertFalse(r["live_key_observed"])
