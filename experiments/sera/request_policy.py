"""SERA hard policy: never impose application-configured LLM output token limits.

An OpenRouter/provider model can still have its OWN hard context/output limit.
This policy prevents OUR request builders from adding arbitrary output ceilings
the user explicitly prohibited. It is not a cost, retry or provider control.
"""
from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_OUTPUT_LIMIT_FIELDS = frozenset({
    "max_tokens",
    "max_completion_tokens",
    "max_output_tokens",
    "max_generation_tokens",
    "max_new_tokens",
    "num_predict",
    "n_predict",
})

# Reviewed provider clients that can issue direct requests in SERA.
CLIENTS = (
    "mara_s1_typed_live_v05.py",
    "mara_s1_resume.py",
    "extractor_adapter.py",
    "openrouter_real_transport_v052.py",
)


class UserOutputLimitPolicyError(ValueError):
    pass


def enforce_no_output_token_limit(payload: dict) -> dict:
    """Reject any token-output ceiling, including nested model settings."""
    if not isinstance(payload, dict):
        raise UserOutputLimitPolicyError("MODEL_PAYLOAD_NOT_OBJECT")

    def visit(node, location="$"):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str) and key.lower() in FORBIDDEN_OUTPUT_LIMIT_FIELDS:
                    raise UserOutputLimitPolicyError(
                        f"USER_OUTPUT_TOKEN_LIMIT_FORBIDDEN:{location}.{key}"
                    )
                visit(value, f"{location}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{location}[{index}]")

    visit(payload)
    return payload


def verify_current_sera_clients(path: Path | None = None) -> list[str]:
    """Offline CI guard: prevent new limit keys and missing request guards.

    Checks direct network clients only. A new provider client MUST be added
    to CLIENTS during review; other repos/shared runtime code need separate
    guards before any future paid use.
    """
    root = path or Path(__file__).resolve().parent
    checked = []
    for name in CLIENTS:
        source = (root / name).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                        and key.value.lower() in FORBIDDEN_OUTPUT_LIMIT_FIELDS):
                        raise UserOutputLimitPolicyError(
                            f"OUTPUT_LIMIT_LITERAL_IN_PROVIDER_CLIENT:{name}:{key.value}"
                        )
        if "enforce_no_output_token_limit(" not in source:
            raise UserOutputLimitPolicyError(
                f"PROVIDER_CLIENT_MISSING_OUTPUT_POLICY:{name}"
            )
        checked.append(name)
    return checked


if __name__ == "__main__":
    for client in verify_current_sera_clients():
        print("NO_OUTPUT_TOKEN_CAP_POLICY_PASS", client)
