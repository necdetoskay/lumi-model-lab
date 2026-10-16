"""v0.40.1: strict no-charge real provider receipt replay tests."""
import tempfile
from pathlib import Path
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.real_blind_receipt_replay_v0401 import (
    SHA256_RAW_FILES, file_proof,
)


class RealBlindReceiptReplayV0401Tests(unittest.TestCase):
    def test_existing_strict_recovery_accepts_complete_json_fence_only(self):
        data='{"rows":[]}'
        fence=chr(96)*3
        v, envelope = parse_json_model_reply(data)
        self.assertEqual(v, {"rows":[]})
        self.assertEqual(envelope,"RAW_JSON")
        v, envelope = parse_json_model_reply(
            fence+"json\n"+data+"\n"+fence
        )
        self.assertEqual(v, {"rows":[]})
        self.assertEqual(envelope,"FULL_JSON_CODE_FENCE")
        for unsafe in (
            "Please see below\n"+fence+"json\n"+data+"\n"+fence,
            fence+"json\n"+data+"\n"+fence+"\nextra interpretation",
            fence+"json\n"+data,
        ):
            with self.assertRaises(CoverageError):
                parse_json_model_reply(unsafe)

    def test_mutated_receipt_refused_before_json_parsing_or_any_replay(self):
        with tempfile.TemporaryDirectory() as d:
            for name in SHA256_RAW_FILES:
                (Path(d)/name).write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(CoverageError,
                       "V0401_REAL_PAID_EVIDENCE_HASH_MISMATCH"):
                file_proof(d)

    def test_replay_has_no_network_provider_client_and_expected_three_receipts(self):
        self.assertEqual(set(SHA256_RAW_FILES),{
            "result.json","provider_reply_1.json","provider_reply_2.json",
        })
        module=(Path(__file__).resolve().parents[1]/
                "real_blind_receipt_replay_v0401.py").read_text(encoding="utf-8")
        self.assertNotIn("one_provider_call(",module)
        self.assertNotIn("urlopen(",module)
        self.assertNotIn("max_tokens",module)
        self.assertNotIn("max_output_tokens",module)


if __name__ == "__main__":
    unittest.main()
