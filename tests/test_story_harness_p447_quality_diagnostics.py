"""P4.47 sanitizes future quality failures without any provider contact."""
import unittest

from src.story_harness_p417_live_pilot import ProviderTransportFault
from src.story_harness_v1 import HarnessStop
from src.story_harness_p447_quality_diagnostics import (
    sanitized_failure_receipt, MESSAGES
)

SHA="342dff8084787c0f42f036ab34d973741aed55cecaef40a4e734ca242f9465c0"

class QualityDiagnosticTests(unittest.TestCase):
    def stop(self,error,response=None):
        return sanitized_failure_receipt(error,response,case_id="B06",story_sha256=SHA)

    def test_prepaid_cap_does_not_mask_actual_reported_overage(self):
        result=self.stop(HarnessStop("Original 0.040 initial-audit cost cap exceeded"),{
            "id":"gen-AnAuthenticAudit123",
            "usage":{"cost":"0.051234","prompt_tokens":8000,"completion_tokens":2400},
            "choices":[{"message":{"content":"PRIVATE STORY API KEY"}}],
        })
        self.assertEqual(result["sanitized_failure_code"],"AUDITOR_RETURNED_COST_OVER_CAP")
        self.assertEqual(result["auditor_reported_cost_usd"],"0.051234")
        self.assertEqual(result["provider_generation_id"],"gen-AnAuthenticAudit123")
        self.assertEqual(result["auditor_usage"],{"prompt_tokens":8000,"completion_tokens":2400})
        self.assertNotIn("PRIVATE",str(result))
        self.assertEqual(result["quality_initial_verdict"],"STOP_UNKNOWN_OR_INVALID")
        self.assertFalse(result["retry_allowed"])
        self.assertFalse(result["english_master_authorized"])

    def test_transport_failure_safe_enum_not_private_error(self):
        error=ProviderTransportFault("HTTP_429","MODEL_UNAVAILABLE")
        result=self.stop(error)
        self.assertEqual(result["sanitized_failure_code"],"PROVIDER_HTTP_429")
        self.assertEqual(result["safe_transport_hint"],"MODEL_UNAVAILABLE")
        self.assertIsNone(result["provider_generation_id"])
        self.assertIsNone(result["auditor_reported_cost_usd"])
        self.assertTrue(result["model_attempt_consumed"])

    def test_literal_validator_categories_only(self):
        for original,safe in MESSAGES.items():
            with self.subTest(message=original):
                receipt=self.stop(HarnessStop(original))
                self.assertEqual(receipt["sanitized_failure_code"],safe)
                self.assertNotIn("safe_transport_hint",receipt)
                self.assertFalse(receipt["production_state_write_authorized"])

    def test_unknown_exception_no_prompt_or_secrets(self):
        key="SECRET_BEARER_123456"
        result=self.stop(RuntimeError("crash "+key),{"id":"not-an-id","usage":{"cost":key}})
        self.assertEqual(result["sanitized_failure_code"],"AUDITOR_UNHANDLED_EXCEPTION_STOP")
        self.assertIsNone(result["provider_generation_id"])
        self.assertIsNone(result["auditor_reported_cost_usd"])
        self.assertNotIn(key,str(result))

    def test_bad_response_usage_does_not_fabricate_invoice(self):
        cases=[
            {"id":"gen-invalid!", "usage":{"cost":"NaN","prompt_tokens":1}},
            {"id":"gen-Qwerty567890","usage":{"cost":-1,"prompt_tokens":1}},
            {"id":"gen-Qwerty567890","usage":{"cost":100.5,"prompt_tokens":1}},
            "NOT_OBJECT",
            None
        ]
        for response in cases:
            with self.subTest(response=repr(response)):
                result=self.stop(HarnessStop("Audit incomplete/truncated"),response)
                self.assertIsNone(result["auditor_reported_cost_usd"])
                self.assertIsNone(result["auditor_usage"])
                self.assertEqual(result["quality_initial_verdict"],"STOP_UNKNOWN_OR_INVALID")

if __name__=="__main__":
    unittest.main()
