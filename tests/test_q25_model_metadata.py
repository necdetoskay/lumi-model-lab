"""Q25 per-model structured output restrictions are request metadata, not relaxed canon."""
import copy
import json

import pytest

from src.q25_model_metadata import (
    MODEL_METADATA, model_metadata, model_metadata_sha256,
)
from src.q25_extractor_adapter import RawExtractorOutput
from src.q25_openrouter_pilot import (
    PilotStop, MODEL_ALLOWLIST, build_wire_request, parse_completion,
    provider_safe_json_schema, pricing_snapshot,
)


def nodes(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from nodes(item)


def test_models_have_explicit_separate_metadata_not_a_single_global_assumption():
    sonnet = model_metadata("anthropic/claude-sonnet-5.5")
    gemini = model_metadata("google/gemini-2.5-flash")
    assert sonnet["schema_profile"] == "ANTHROPIC_STRICT_V1"
    assert sonnet["capability_basis"] == "ANTHROPIC_DOCUMENTED_STRICT_SCHEMA_LIMITS"
    assert gemini["schema_profile"] == "OPENROUTER_CONSERVATIVE_V1"
    assert gemini["capability_basis"] == (
        "SHARED_CONSERVATIVE_SUBSET_NOT_VERIFIED_VENDOR_RESTRICTIONS")
    assert "minLength" in sonnet["wire_constraints_enforced_locally"]
    assert "maxLength" in sonnet["wire_constraints_enforced_locally"]
    assert "pattern" in sonnet["wire_constraints_enforced_locally"]
    assert sonnet["allowed_min_items"] == (0, 1)
    assert sonnet["max_optional_parameters"] == 24
    assert sonnet["max_union_parameters"] == 16
    assert sonnet["raw_response_validation"] == "FULL_ORIGINAL_PYDANTIC_SCHEMA"
    assert sonnet["provider_capabilities_must_be_checked_live"] is True
    assert gemini["provider_capabilities_must_be_checked_live"] is True
    assert MODEL_ALLOWLIST == set(MODEL_METADATA)
    assert len(model_metadata_sha256("anthropic/claude-sonnet-5.5")) == 64
    assert model_metadata_sha256("anthropic/claude-sonnet-5.5") != (
        model_metadata_sha256("google/gemini-2.5-flash"))
    sonnet["wire_constraints_enforced_locally"] = ()
    assert "minLength" in model_metadata(
        "anthropic/claude-sonnet-5.5")["wire_constraints_enforced_locally"]


def test_unknown_model_has_no_implicit_profile_or_provider_routing():
    with pytest.raises(ValueError):
        model_metadata("imagined/unregistered")
    with pytest.raises(PilotStop, match="not qualified|allowlist"):
        provider_safe_json_schema(
            RawExtractorOutput.model_json_schema(), model="imagined/unregistered")


@pytest.mark.parametrize("model", sorted(MODEL_ALLOWLIST))
def test_each_wire_schema_is_derived_from_model_profile_without_mutating_original(model):
    base = RawExtractorOutput.model_json_schema()
    original = copy.deepcopy(base)
    filtered = provider_safe_json_schema(base, model=model)
    assert base == original
    assert filtered == provider_safe_json_schema(base, model=model)
    assert filtered != base
    assert filtered["additionalProperties"] is False
    for item in nodes(filtered):
        assert not set(model_metadata(model)["wire_constraints_enforced_locally"]) & set(item)
        if item.get("type") == "object":
            assert item.get("additionalProperties") is False
    # The expected strict semantic structure stays intact: no fields deleted.
    assert filtered["required"] == base["required"]
    assert list(filtered["properties"]) == list(base["properties"])
    assert list(filtered["$defs"]) == list(base["$defs"])
    assert filtered["$defs"]["RawProperty"]["required"] == (
        base["$defs"]["RawProperty"]["required"])
    assert "minLength" in json.dumps(base)
    assert any("enforced by application" in node.get("description", "")
               for node in nodes(filtered))


@pytest.mark.parametrize("model", sorted(MODEL_ALLOWLIST))
def test_wire_does_not_reintroduce_banned_keywords_and_preserves_strict_fallback(model):
    seed = {
        "characters": {"A": {"condition": {"goal": "go"}}},
        "objects": {},
        "topology": {"locations": ["room"]},
    }
    wire = build_wire_request(seed=seed, prose="A went to a room.",
                              model=model, max_tokens=500)
    schema = wire["response_format"]["json_schema"]["schema"]
    assert schema == provider_safe_json_schema(
        RawExtractorOutput.model_json_schema(), model=model)
    assert wire["response_format"]["json_schema"]["strict"] is True
    assert wire["provider"] == {
        "require_parameters": True, "allow_fallbacks": False,
    }
    assert all("minLength" not in obj and "maxLength" not in obj
               for obj in nodes(schema))


def test_local_pydantic_still_rejects_unqualified_claims_after_wire_relaxation():
    raw = {
        "schema_name": "q25.extractor-raw-output.v1",
        "seed_sha256": "a" * 64,
        "source_sha256": "b" * 64,
        "objects": [{
            "key": "UNSAFE-ID", "description": "A",
            "role": "ORDINARY_OBJECT",
            "mention": {"quote": "short"},
        }],
        "terminal_relations": [], "character_claims": [],
        "goal_claims": [], "obligation_claims": [],
        "thread_claims": [], "property_claims": [],
    }
    with pytest.raises(PilotStop, match="raw JSON contract"):
        parse_completion({"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(raw)}
        }]})


@pytest.mark.parametrize("model", sorted(MODEL_ALLOWLIST))
def test_pricing_ledger_receives_schema_profile_without_inferring_endpoint_capabilities(model):
    row = {
        "id": model,
        "supported_parameters": ["response_format", "structured_outputs"],
        "context_length": 250000,
        "pricing": {"prompt": "0.000001", "completion": "0.000004",
                    "request": "0"},
    }
    snapshot = pricing_snapshot({"data": [row]}, model)
    assert snapshot["schema_profile"] == model_metadata(model)["schema_profile"]
    assert snapshot["model_metadata_sha256"] == model_metadata_sha256(model)
    row["supported_parameters"].remove("structured_outputs")
    with pytest.raises(PilotStop):
        pricing_snapshot({"data": [row]}, model)


def test_model_metadata_validation_cannot_be_overridden_to_disable_local_checks(monkeypatch):
    patched = copy.deepcopy(MODEL_METADATA["anthropic/claude-sonnet-5.5"])
    patched["raw_response_validation"] = "IGNORE"
    monkeypatch.setitem(MODEL_METADATA, "anthropic/claude-sonnet-5.5", patched)
    with pytest.raises(ValueError, match="Unsafe"):
        model_metadata("anthropic/claude-sonnet-5.5")
