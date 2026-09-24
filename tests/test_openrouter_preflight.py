from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from src.openrouter_preflight import (
    OPENROUTER_KEY_URL,
    OpenRouterKeyStatus,
    ProviderAccessBlocked,
    ProviderPreflightError,
    enforce_key_access,
    fetch_key_status,
    parse_key_status,
)


class OpenRouterPreflightTests(unittest.TestCase):
    def test_parse_key_status_with_monthly_limit(self) -> None:
        status = parse_key_status(
            {
                "data": {
                    "limit": 100,
                    "limit_remaining": 74.5,
                    "limit_reset": "monthly",
                    "usage_monthly": 25.5,
                    "is_free_tier": False,
                    "label": "must-not-be-exposed",
                }
            }
        )
        self.assertEqual(status.limit, 100.0)
        self.assertEqual(status.limit_remaining, 74.5)
        self.assertEqual(status.limit_reset, "monthly")
        self.assertEqual(status.usage_monthly, 25.5)
        self.assertTrue(status.access_available)
        self.assertNotIn("label", status.safe_payload())

    def test_unlimited_key_passes(self) -> None:
        status = OpenRouterKeyStatus(
            limit=None,
            limit_remaining=None,
            limit_reset=None,
            usage_monthly=1.0,
            is_free_tier=False,
        )
        enforce_key_access(status)
        self.assertTrue(status.access_available)

    def test_exhausted_key_is_blocked(self) -> None:
        status = OpenRouterKeyStatus(
            limit=5.0,
            limit_remaining=0.0,
            limit_reset="monthly",
            usage_monthly=5.0,
            is_free_tier=False,
        )
        with self.assertRaisesRegex(
            ProviderAccessBlocked,
            "spending limit exhausted",
        ):
            enforce_key_access(status)

    def test_negative_remaining_is_blocked(self) -> None:
        status = OpenRouterKeyStatus(
            limit=5.0,
            limit_remaining=-0.01,
            limit_reset="monthly",
            usage_monthly=5.01,
            is_free_tier=False,
        )
        with self.assertRaises(ProviderAccessBlocked):
            enforce_key_access(status)

    def test_missing_data_fails_closed(self) -> None:
        with self.assertRaisesRegex(ProviderPreflightError, "missing data object"):
            parse_key_status({"unexpected": {}})

    @patch("src.openrouter_preflight.requests.get")
    def test_fetch_uses_current_key_endpoint_without_leaking_key(
        self,
        mock_get: Mock,
    ) -> None:
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": {
                "limit": 10,
                "limit_remaining": 2,
                "limit_reset": "monthly",
                "usage_monthly": 8,
                "is_free_tier": False,
            }
        }
        mock_get.return_value = response

        status = fetch_key_status("secret-token", timeout_seconds=3)

        self.assertEqual(status.limit_remaining, 2.0)
        mock_get.assert_called_once_with(
            OPENROUTER_KEY_URL,
            headers={"Authorization": "Bearer secret-token"},
            timeout=3,
        )

    @patch("src.openrouter_preflight.requests.get")
    def test_http_error_fails_closed(self, mock_get: Mock) -> None:
        response = Mock()
        response.status_code = 401
        response.text = "unauthorized"
        mock_get.return_value = response
        with self.assertRaisesRegex(ProviderPreflightError, "HTTP 401"):
            fetch_key_status("secret-token")

    @patch("src.openrouter_preflight.requests.get")
    def test_transport_error_fails_closed(self, mock_get: Mock) -> None:
        mock_get.side_effect = requests.Timeout("timeout")
        with self.assertRaisesRegex(
            ProviderPreflightError,
            "transport failure",
        ):
            fetch_key_status("secret-token")


if __name__ == "__main__":
    unittest.main()
