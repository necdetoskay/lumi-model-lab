from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any

import requests

OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"


class ProviderPreflightError(RuntimeError):
    pass


class ProviderAccessBlocked(ProviderPreflightError):
    pass


@dataclass(frozen=True)
class OpenRouterKeyStatus:
    limit: float | None
    limit_remaining: float | None
    limit_reset: str | None
    usage_monthly: float | None
    is_free_tier: bool | None

    @property
    def access_available(self) -> bool:
        return self.limit_remaining is None or self.limit_remaining > 0

    def safe_payload(self) -> dict[str, Any]:
        return {
            "provider": "openrouter",
            "access_available": self.access_available,
            "limit_configured": self.limit is not None,
            "limit_remaining": self.limit_remaining,
            "limit_reset": self.limit_reset,
            "usage_monthly": self.usage_monthly,
            "is_free_tier": self.is_free_tier,
        }


def _optional_number(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderPreflightError(f"OpenRouter key payload has invalid {field}")
    return float(value)


def parse_key_status(payload: dict[str, Any]) -> OpenRouterKeyStatus:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ProviderPreflightError("OpenRouter key payload is missing data object")

    is_free_tier = data.get("is_free_tier")
    if is_free_tier is not None and not isinstance(is_free_tier, bool):
        raise ProviderPreflightError(
            "OpenRouter key payload has invalid is_free_tier"
        )

    limit_reset = data.get("limit_reset")
    if limit_reset is not None and not isinstance(limit_reset, str):
        raise ProviderPreflightError(
            "OpenRouter key payload has invalid limit_reset"
        )

    return OpenRouterKeyStatus(
        limit=_optional_number(data.get("limit"), "limit"),
        limit_remaining=_optional_number(
            data.get("limit_remaining"),
            "limit_remaining",
        ),
        limit_reset=limit_reset,
        usage_monthly=_optional_number(
            data.get("usage_monthly"),
            "usage_monthly",
        ),
        is_free_tier=is_free_tier,
    )


def fetch_key_status(
    api_key: str,
    *,
    timeout_seconds: float = 15.0,
) -> OpenRouterKeyStatus:
    if not api_key.strip():
        raise ProviderPreflightError("OPENROUTER_API_KEY is missing")

    try:
        response = requests.get(
            OPENROUTER_KEY_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise ProviderPreflightError(
            f"OpenRouter key preflight transport failure: {exc}"
        ) from exc

    if response.status_code != 200:
        detail = response.text[:500].replace("\n", " ")
        raise ProviderPreflightError(
            f"OpenRouter key preflight HTTP {response.status_code}: {detail}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderPreflightError(
            "OpenRouter key preflight returned non-JSON response"
        ) from exc

    if not isinstance(payload, dict):
        raise ProviderPreflightError(
            "OpenRouter key preflight returned invalid JSON payload"
        )
    return parse_key_status(payload)


def enforce_key_access(status: OpenRouterKeyStatus) -> None:
    if status.limit_remaining is not None and status.limit_remaining <= 0:
        reset = status.limit_reset or "unspecified"
        raise ProviderAccessBlocked(
            "OpenRouter key spending limit exhausted "
            f"(reset={reset}); qualification must not start"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail-fast OpenRouter provider-access preflight."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a safe machine-readable status payload.",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    status = fetch_key_status(api_key)

    if args.json:
        print(json.dumps(status.safe_payload(), ensure_ascii=False))
    else:
        print(
            "OpenRouter preflight: "
            f"access_available={status.access_available} "
            f"limit_configured={status.limit is not None} "
            f"limit_reset={status.limit_reset or 'none'}"
        )

    enforce_key_access(status)


if __name__ == "__main__":
    main()
