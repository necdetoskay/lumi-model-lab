"""Pinned model/schema capability metadata for Q25 strict extraction.

These are our qualified *request construction policies*, not capabilities
guaranteed by OpenRouter's changing provider endpoints. Live catalog checks
remain mandatory. Unsupported wire constraints are validated locally instead.
"""
from __future__ import annotations

import copy

from src.q25_entity_candidates import fingerprint

# Anthropic strict JSON: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
# Gemini: https://ai.google.dev/gemini-api/docs/structured-output
# OpenRouter routing: https://openrouter.ai/docs/guides/features/structured-outputs
# Conservative policy is NOT a claim that Gemini rejects those keywords.
_APPLICATION_ONLY_CONSTRAINTS = (
    "minLength", "maxLength", "pattern", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "maxItems", "uniqueItems", "minProperties", "maxProperties",
)

_REJECT_UNSUPPORTED_CONSTRUCTS = (
    "patternProperties", "unevaluatedProperties", "dependentSchemas",
    "not", "if", "then", "else",
)

MODEL_METADATA = {
    "anthropic/claude-sonnet-5.5": {
        "schema_profile": "ANTHROPIC_STRICT_V1",
        "vendor_family": "anthropic",
        "capability_basis": "ANTHROPIC_DOCUMENTED_STRICT_SCHEMA_LIMITS",
        "wire_constraints_enforced_locally": _APPLICATION_ONLY_CONSTRAINTS,
        "rejected_schema_keywords": _REJECT_UNSUPPORTED_CONSTRUCTS,
        "allowed_min_items": (0, 1),
        "max_optional_parameters": 24,
        "max_union_parameters": 16,
        "raw_response_validation": "FULL_ORIGINAL_PYDANTIC_SCHEMA",
        "provider_capabilities_must_be_checked_live": True,
        "source": "https://platform.claude.com/docs/en/build-with-claude/structured-outputs",
    },
    "google/gemini-2.5-flash": {
        "schema_profile": "OPENROUTER_CONSERVATIVE_V1",
        "vendor_family": "google",
        "capability_basis": "SHARED_CONSERVATIVE_SUBSET_NOT_VERIFIED_VENDOR_RESTRICTIONS",
        "wire_constraints_enforced_locally": _APPLICATION_ONLY_CONSTRAINTS,
        "rejected_schema_keywords": _REJECT_UNSUPPORTED_CONSTRUCTS,
        "allowed_min_items": (0, 1),
        "max_optional_parameters": 24,
        "max_union_parameters": 16,
        "raw_response_validation": "FULL_ORIGINAL_PYDANTIC_SCHEMA",
        "provider_capabilities_must_be_checked_live": True,
        "source": "https://ai.google.dev/gemini-api/docs/structured-output",
    },
}


def model_metadata(model: str) -> dict:
    """No guesses or default fallback for an unregistered model."""
    if model not in MODEL_METADATA:
        raise ValueError("No qualified Q25 model/schema metadata for model")
    profile = copy.deepcopy(MODEL_METADATA[model])
    if not profile["provider_capabilities_must_be_checked_live"]:
        raise ValueError("Live provider capability check cannot be disabled")
    if profile["raw_response_validation"] != "FULL_ORIGINAL_PYDANTIC_SCHEMA":
        raise ValueError("Unsafe model profile without local strict validation")
    return profile


def model_metadata_sha256(model: str) -> str:
    return fingerprint(model_metadata(model))
