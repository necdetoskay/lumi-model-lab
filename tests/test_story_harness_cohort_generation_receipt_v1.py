"""Provider generation GET is always read-only, cost/source-bound."""
import json
import unittest

from src.story_harness_cohort_generation_receipt_v1 import (
    get_generation, validate_generation, read_and_verify_generation, ENDPOINT)
from src.story_harness_v1 import HarnessStop

GID = "gen-ABCDEF123456"
def snapshot(**changes):
    d = {"id":GID,"model":"anthropic/claude-sonnet-5.5",
         "provider_name":"Anthropic","cancelled":False,
         "finish_reason":"stop","is_byok":False,
         "tokens_prompt":220,"tokens_completion":410,
         "total_cost":"0.004540",
         "external_user":"PRIVATE_NEVER_COPY"}
    d.update(changes)
    return {"data":d}

def verify(data, **overrides):
    args = {"generation_id":GID,"stage":"SPINEFORGE",
            "reported_cost_usd":"0.004540",
            "prompt_tokens":220,"completion_tokens":410}
    args.update(overrides)
    return validate_generation(data,**args)

class FakeResponse:
    status=200
    def __init__(self, url, body=None):
        self.url=url
        self.body=json.dumps(body if body is not None else snapshot()).encode()
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,max_bytes):return self.body[:max_bytes]
    def geturl(self):return self.url
class FakeOpener:
    def __init__(self):self.calls=0;self.methods=[]
    def open(self,request,timeout):
        self.calls+=1
        self.methods.append(request.get_method())
        assert timeout==12
        return FakeResponse(request.full_url)
class ReceiptTests(unittest.TestCase):
    def test_mock_proof_is_never_live_provenance(self):
        r=verify(snapshot())
        self.assertEqual(r["provider_generation_cost_usd"],"0.004540")
        self.assertFalse(r["provider_origin_independently_attested"])
        self.assertFalse(r["cohort_paid_dispatch_authorized"])
        self.assertNotIn("PRIVATE_NEVER_COPY",str(r))

    def test_one_exact_get_and_no_post(self):
        fake=FakeOpener()
        r=read_and_verify_generation(
            api_key="sk-or-test-only-0123456789",generation_id=GID,
            stage="SPINEFORGE",reported_cost_usd="0.004540",
            prompt_tokens=220,completion_tokens=410,opener=fake)
        self.assertEqual(fake.calls,1)
        self.assertEqual(fake.methods,["GET"])
        self.assertFalse(r["authenticated_live_metadata_get"])

    def test_bad_generation_id_never_opens_network(self):
        fake=FakeOpener()
        for gid in ("", "../bad", "gen-a&secret=true", "gen-b_abc"):
            with self.subTest(gid=gid),self.assertRaises(HarnessStop):
                get_generation(api_key="sk-or-test-only-0123456789",
                               generation_id=gid,opener=fake)
        self.assertEqual(fake.calls,0)

    def test_strict_billable_contract(self):
        invalid = [
            {"id":"gen-OTHER12345"},
            {"model":"other/model"},
            {"provider_name":"Other"},
            {"cancelled":True},
            {"finish_reason":"length"},
            {"is_byok":True},
            {"tokens_prompt":219},
            {"tokens_completion":409},
            {"total_cost":"0.005"},
            {"total_cost":None},
            {"total_cost":"NaN"},
            {"total_cost":"0"},
            {"total_cost":"0.0000001"},
        ]
        for item in invalid:
            with self.subTest(item=item),self.assertRaises(HarnessStop):
                verify(snapshot(**item))

    def test_stage_budget_and_expected_response_checks(self):
        with self.assertRaises(HarnessStop):
            verify(snapshot(),stage="UNKNOWN")
        with self.assertRaises(HarnessStop):
            verify(snapshot(),stage="Q25",
                   reported_cost_usd="0.200000")
        with self.assertRaises(HarnessStop):
            verify(snapshot(),prompt_tokens=True)
        with self.assertRaises(HarnessStop):
            verify(snapshot(),reported_cost_usd="0.004541")

    def test_no_credentials_or_payload_in_unavailable_response_error(self):
        class FailOpener:
            def open(self,*args,**kwargs):
                raise RuntimeError("PRIVATE secret log should never appear")
        with self.assertRaises(HarnessStop) as err:
            get_generation(api_key="sk-or-test-only-0123456789",
                           generation_id=GID,opener=FailOpener())
        self.assertNotIn("PRIVATE",str(err.exception))
        self.assertNotIn("sk-or-",str(err.exception))
