"""P4.13 versioned, NON-EQUIVALENT Sonnet temperature wire projection.

The immutable v21.4 adapter still REQUESTS temperature=0. The separately
versioned new-story harness may preview an omission for a provider endpoint
that explicitly does not advertise temperature. Omission is not temperature=0
and must never be called equivalent or authorized for real provider dispatch.

NO credentials, network calls, model POST, spending grant or story acceptance.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from src.story_harness_p410 import MODEL, PROVIDER, STAGES, canonical_json
from src.story_harness_p412 import analyze_catalog
from src.story_harness_p49 import STORY_SHA, must

PROJECTION_SCHEMA = "lumi.story-harness-p413-non-equivalent-temperature-omission.v1"
EXACT_MISSING = ["temperature"]
MAX_PRICE = {"prompt": 2, "completion": 10}


def adapt_wire(*, preview, catalog, allow_sampling_semantics_change=False):
    """Return explicit offline wire projection + safe metadata-only disclosure.

    Must be invoked on a trusted P4.10 request_preview, and only with catalog
    facts for exact Anthropic route. A catalog supplied in tests or repo JSON is
    never treated as authenticated request-time metadata or permission.
    """
    must(allow_sampling_semantics_change is True,
         "Explicit acknowledgement of NON-EQUIVALENT sampling change required")
    must(type(preview) is dict
         and preview.get("source_story_sha256") == STORY_SHA
         and preview.get("live_dispatch_allowed") is False
         and preview.get("authenticated_provider_route") is False
         and preview.get("method") == "POST",
         "Source-bound offline preview required")
    stage = preview.get("stage")
    must(stage in STAGES, "Unknown adapter stage")
    original = preview.get("body")
    must(type(original) is dict
         and original.get("model") == MODEL
         and original.get("temperature") == 0.0
         and type(original.get("messages")) is list
         and len(original["messages"]) == 2
         and original.get("max_tokens") == STAGES[stage][1]
         and original.get("stream") is False
         and original.get("provider") == {
             "only": [PROVIDER], "allow_fallbacks": False,
             "require_parameters": True,
         }
         and original.get("response_format", {}).get("type") == "json_schema"
         and original.get("response_format", {}).get("json_schema", {}).get("strict") is True,
         "Unsupported callback/body mutation")
    info = analyze_catalog(catalog)
    must(info["model"] == MODEL and info["provider"] == PROVIDER
         and info["route_tag"] == "anthropic"
         and info["missing_request_parameters"] == EXACT_MISSING
         and info["blockers"] == ["UNSUPPORTED_REQUEST_PARAMETERS:temperature"],
         "Exact sole compatibility blocker must be unsupported temperature")
    # Do not quietly change the original callback/adapter or copy its prompt.
    wire = deepcopy(original)
    removed = wire.pop("temperature")
    must(removed == 0.0 and "temperature" not in wire,
         "Temperature omission did not apply")
    wire["provider"] = {**wire["provider"], "max_price": dict(MAX_PRICE)}
    allowed = {"max_tokens", "response_format", "structured_outputs"}
    route = catalog["data"]["endpoints"]
    matched = [r for r in route if type(r) is dict and
               r.get("provider_name") == PROVIDER and r.get("tag") == "anthropic"]
    must(len(matched) == 1 and allowed.issubset(set(matched[0]["supported_parameters"])),
         "Missing strict-schema or max_tokens capability")
    must(wire["provider"] == {
        "only": [PROVIDER], "allow_fallbacks": False,
        "require_parameters": True, "max_price": MAX_PRICE,
    }, "Provider override or fallback")
    disclosure = {
        "schema": PROJECTION_SCHEMA,
        "stage": stage,
        "story_sha256": STORY_SHA,
        "model": MODEL, "provider": PROVIDER,
        "catalog_sha256": info["catalog_sha256"],
        "original_request_sha256": hashlib.sha256(canonical_json(original)).hexdigest(),
        "exact_wire_sha256": hashlib.sha256(canonical_json(wire)).hexdigest(),
        "original_temperature": 0,
        "wire_temperature_parameter": "OMITTED",
        "sampling_semantics_equivalent": False,
        "sampling_semantics_change_acknowledged_for_offline_test": True,
        "other_request_parameters_preserved": True,
        "provider_fallback_allowed": False,
        "max_price_usd_per_million": {"prompt": 2, "completion": 10},
        "catalog_is_authenticated_request_quote": False,
        "request_token_upper_bound_verified": False,
        "requires_separate_human_live_authorization": True,
        "live_dispatch_allowed": False,
        "reason": "P413_EXPLICIT_NON_EQUIVALENT_TEMPERATURE_OMISSION_TEST_ONLY",
    }
    return wire, disclosure


def status():
    return {
        "schema": PROJECTION_SCHEMA,
        "temperature_zero_preserved_on_original_v21_adapter": True,
        "proposed_provider_wire_temperature": "OMITTED_ONLY_AFTER_ACK",
        "sampling_semantics_equivalent": False,
        "strict_schema_and_no_fallback_preserved": True,
        "source_story_sha256": STORY_SHA,
        "provider_calls": 0,
        "cost_usd": "0",
        "live_dispatch_allowed": False,
        "quality_accepted": False,
        "english_master_authorized": False,
        "q25_authorized": False,
        "state_write_authorized": False,
        "stop_reason": "P413_ROUTING_COMPATIBILITY_OFFLINE_QUALITY_STILL_BLOCKED",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(status(), sort_keys=True, indent=2))
