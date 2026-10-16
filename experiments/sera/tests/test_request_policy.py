"""Regression: user forbids application-defined output token ceilings.

Tests mock provider request and offline scan of direct SERA clients.
"""
from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from experiments.sera.request_policy import (
    CLIENTS, UserOutputLimitPolicyError,
    enforce_no_output_token_limit, verify_current_sera_clients,
)


class OutputTokenLimitPolicyTests(unittest.TestCase):
    def test_no_output_cap_payload_passes_unchanged(self):
        payload = {"model": "example", "messages": [],
                   "response_format": {"type": "json_schema"}}
        self.assertIs(enforce_no_output_token_limit(payload), payload)

    def test_forbid_all_known_output_cap_fields(self):
        for field in (
            "max_tokens", "max_completion_tokens", "max_output_tokens",
            "max_generation_tokens", "max_new_tokens", "num_predict",
            "n_predict",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    UserOutputLimitPolicyError,
                    "USER_OUTPUT_TOKEN_LIMIT_FORBIDDEN"
                ):
                    enforce_no_output_token_limit({
                        "model": "example", field: 4096,
                    })

    def test_nested_cap_is_also_forbidden(self):
        with self.assertRaisesRegex(
            UserOutputLimitPolicyError,
            "USER_OUTPUT_TOKEN_LIMIT_FORBIDDEN",
        ):
            enforce_no_output_token_limit({
                "provider": {"options": [{"max_tokens": 1000}]},
            })

    def test_current_live_clients_have_gate_and_no_literal_ceiling(self):
        self.assertEqual(
            verify_current_sera_clients(), list(CLIENTS),
        )

    def test_ci_scan_rejects_new_literal_cap(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            for filename in CLIENTS:
                (root / filename).write_text(
                    "from experiments.sera.request_policy import "
                    "enforce_no_output_token_limit\n"
                    "enforce_no_output_token_limit({})\n",
                    encoding="utf-8"
                )
            (root / CLIENTS[0]).write_text(
                "enforce_no_output_token_limit({'max_tokens': 1000})\n",
                encoding="utf-8"
            )
            with self.assertRaisesRegex(
                UserOutputLimitPolicyError,
                "OUTPUT_LIMIT_LITERAL_IN_PROVIDER_CLIENT",
            ):
                verify_current_sera_clients(root)

    def test_ci_scan_rejects_missing_guard(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            for filename in CLIENTS:
                (root / filename).write_text(
                    "enforce_no_output_token_limit({})\n", encoding="utf-8",
                )
            (root / CLIENTS[-1]).write_text(
                "payload = {'messages': []}\n", encoding="utf-8",
            )
            with self.assertRaisesRegex(
                UserOutputLimitPolicyError,
                "PROVIDER_CLIENT_MISSING_OUTPUT_POLICY",
            ):
                verify_current_sera_clients(root)


if __name__ == "__main__":
    unittest.main()
