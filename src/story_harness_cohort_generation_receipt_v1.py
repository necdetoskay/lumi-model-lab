"""OpenRouter generation usage/cost cross-check for LUMI frozen cohort.

READ-ONLY, NEVER model POST. A network-backed GET can independently compare
generation ID, route, token counts and charge to the original completion.
An injected/mock opener NEVER counts as authenticated evidence. This module
does not authorize a paid batch; receipt identity does not certify story quality.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import re
import urllib.request
import urllib.parse

from src.story_harness_p410 import canonical_json
from src.story_harness_cohort_launch_gate_v1 import usd, must
from src.story_harness_p417_live_pilot import MODEL, PROVIDER
from src.story_harness_v1 import HarnessStop

ENDPOINT = "https://openrouter.ai/api/v1/generation"
MAX_BYTES = 16384
GEN_ID = re.compile(r"^gen-[0-9A-Za-z-]{6,124}$")
SCHEMA = "lumi.story-harness-cohort-provider-generation-read-only.v1"

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HarnessStop("GENERATION_GET_STOP_REDIRECT")

def require_id(value):
    must(type(value) is str and GEN_ID.fullmatch(value) is not None,
         "INVALID_PROVIDER_GENERATION_ID")
    return value

def get_generation(*, api_key, generation_id, opener=None):
    """GET metadata for a single exact producer stage; no retries or POST."""
    must(type(api_key) is str and api_key.startswith("sk-or-") and
         10 <= len(api_key) <= 256 and
         not any(c.isspace() for c in api_key),
         "INFERENCE_KEY_UNAVAILABLE")
    generation_id = require_id(generation_id)
    url = ENDPOINT + "?" + urllib.parse.urlencode({"id": generation_id})
    request = urllib.request.Request(
        url, method="GET",
        headers={"Authorization": "Bearer " + api_key,
                 "Accept": "application/json"})
    try:
        with (opener or urllib.request.build_opener(_NoRedirect())).open(
            request, timeout=12
        ) as response:
            must(response.status == 200 and response.geturl() == url,
                 "GENERATION_GET_BAD_STATUS_OR_REDIRECT")
            raw = response.read(MAX_BYTES + 1)
            must(len(raw) <= MAX_BYTES, "GENERATION_GET_RESPONSE_OVERSIZE")
        body = json.loads(raw)
        must(type(body) is dict and type(body.get("data")) is dict,
             "GENERATION_GET_INVALID_ENVELOPE")
        return body
    except HarnessStop:
        raise
    except Exception:
        # Never log private request/headers, provider bodies, tokens or prose.
        raise HarnessStop("COHORT_LAUNCH_STOP_GENERATION_METADATA_UNKNOWN") from None

def validate_generation(snapshot, *, generation_id, stage,
                        reported_cost_usd, prompt_tokens, completion_tokens,
):
    """Correlate provider lookup to the exact stage response, fail closed."""
    from src.story_harness_cohort_pipeline_v1 import STAGE_MAX
    require_id(generation_id)
    must(stage in STAGE_MAX, "UNREGISTERED_GENERATION_STAGE")
    must(type(snapshot) is dict and type(snapshot.get("data")) is dict,
         "GENERATION_DATA_UNAVAILABLE")
    data = snapshot["data"]
    must(data.get("id") == generation_id and data.get("model") == MODEL and
         data.get("provider_name") == PROVIDER and
         data.get("cancelled") is False and
         data.get("finish_reason") == "stop" and
         data.get("is_byok") is False,
         "GENERATION_ROUTE_OR_FINALITY_MISMATCH")
    must(type(prompt_tokens) is int and prompt_tokens >= 0 and
         type(completion_tokens) is int and completion_tokens >= 0 and
         type(data.get("tokens_prompt")) is int and
         type(data.get("tokens_completion")) is int and
         data["tokens_prompt"] == prompt_tokens and
         data["tokens_completion"] == completion_tokens,
         "GENERATION_TOKEN_USAGE_MISMATCH")
    reported = usd(str(reported_cost_usd))
    billed = usd(str(data.get("total_cost")))
    must(reported > 0 and billed == reported and billed <= STAGE_MAX[stage],
         "GENERATION_COST_UNRECONCILED")
    return {
        "schema": SCHEMA, "stage": stage,
        "generation_id": generation_id,
        "model": MODEL, "upstream": PROVIDER,
        "reported_cost_usd": format(reported, "f"),
        "provider_generation_cost_usd": format(billed, "f"),
        "tokens_prompt": prompt_tokens,
        "tokens_completion": completion_tokens,
        "provider_response_sha256": hashlib.sha256(canonical_json(snapshot)).hexdigest(),
        "authenticated_live_metadata_get": False,
        "provider_origin_independently_attested": False,
        "independent_story_quality_accepted": False,
        "cohort_paid_dispatch_authorized": False,
        "new_model_post_attempts": 0,
    }

def read_and_verify_generation(*, api_key, generation_id, stage,
                               reported_cost_usd, prompt_tokens,
                               completion_tokens, opener=None):
    response = get_generation(
        api_key=api_key, generation_id=generation_id, opener=opener)
    checked = validate_generation(
        response, generation_id=generation_id, stage=stage,
        reported_cost_usd=reported_cost_usd,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    # Only the private network-entry path can elevate metadata provenance.
    checked["authenticated_live_metadata_get"] = opener is None
    checked["provider_origin_independently_attested"] = opener is None
    return checked
