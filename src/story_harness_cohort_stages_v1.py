"""Shared offline stage validators for any B01–B10 Story Harness source.

Reuses historical P4.22/P4.23/P4.24 source-bound gates, never upgrades an
unverified model response to an independently authenticated quality claim.
The final state is a noncanonical proposal, without any mutable Canon writes.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json

from src.story_harness_p422_independent_audit import (
    audit_wire, verify_auditor_reply
)
from src.story_harness_p423_master import qualify_master
from src.story_harness_p424_q25_evidence import (
    extraction_wire, verify_model_response, verify_candidate, COST_CAP
)
from src.story_harness_p416_input_bridge import sha
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-cohort-common-stages.v1"

def must(ok, msg):
    if not ok:
        raise HarnessStop("COHORT_STAGE_STOP_" + msg)

def prepare_quality_request(source):
    """B07 original bytes need their exact historical 22000 byte exception."""
    must(type(source) is dict and source.get("case_id") in
         {f"B{i:02d}" for i in range(1, 11)}, "CASE_UNREGISTERED")
    bound = (22000 if source["case_id"] == "B07" and
             source["story"].get("word_count") == 2708 else 20000)
    request = audit_wire(source, max_request_bytes=bound)
    must(request["stream"] is False and
         request["provider"]["allow_fallbacks"] is False,
         "QUALITY_ROUTING_CHANGED")
    return request

def make_pilot_bundle(source, audit):
    """Validate source-bound QA and assemble byte-identical Master candidate.

    Caller MUST separately authenticate the frozen model/provider response and
    original auditor receipt; this offline function cannot do so by itself.
    """
    qualified = qualify_master(source, audit)
    words = source["story"]["story_text"]
    digest = hashlib.sha256(words.encode("utf-8")).hexdigest()
    must(digest == qualified["story_sha256"], "MASTER_CHANGED")
    master = {
        "case_id": source["case_id"],
        "source_pack_sha256": qualified["source_pack_sha256"],
        "source_story_sha256": qualified["story_sha256"],
        "source_spine_sha256": qualified["spine_sha256"],
        "quality_initial_verdict": "ACCEPT",
        "original_auditor_generation_id": qualified["auditor_generation_id"],
        "english_master_sha256": digest,
        "manual_text_edits": 0,
        "q25_read_only_extraction_allowed": True,
        "production_state_write_authorized": False,
        "original_v21_final_quality_certified": False,
        "provider_evidence_externally_attested": False,
    }
    return {
        "schema": SCHEMA, "source": source, "audit": audit,
        "master": master, "english_master_text": words,
        "production_state_write_authorized": False,
    }

def prepare_real_q25_request(bundle):
    must(bundle.get("schema") == SCHEMA and
         bundle["master"]["source_story_sha256"] ==
         bundle["source"]["story"]["story_sha256"] and
         bundle["master"]["manual_text_edits"] == 0,
         "MASTER_OR_SOURCE_DRIFT")
    request = extraction_wire(bundle)
    must(request["stream"] is False and
         request["provider"]["allow_fallbacks"] is False,
         "Q25_ROUTING_CHANGED")
    return request

def validate_real_q25_response(bundle, response):
    """Provider-schema verification only; no self-attested genuine result."""
    receipt = verify_model_response(bundle, response)
    must(receipt["case_id"] == bundle["source"]["case_id"] and
         receipt["story_sha256"] ==
         bundle["master"]["english_master_sha256"] and
         receipt["final_story_state_committed"] is False and
         receipt["production_state_write_authorized"] is False,
         "Q25_NOT_SAME_STORY")
    return receipt

def read_only_state_projection(bundle, q25_receipt):
    """Case-neutral projection. Every change remains a quote-bound candidate."""
    source = bundle["source"]
    pack = source["pack"]
    story = source["story"]
    must(q25_receipt.get("schema") ==
         "lumi.story-harness-p424-q25-evidence-proposal.v1" and
         q25_receipt.get("case_id") == source["case_id"] and
         q25_receipt.get("source_pack_sha256") == pack["pack_sha256"] and
         q25_receipt.get("story_sha256") == story["story_sha256"] and
         q25_receipt.get("spine_sha256") == source["spine"]["spine_sha256"] and
         q25_receipt.get("provenance_verified") is True and
         q25_receipt.get("quote_matching_verified") is True and
         q25_receipt.get("final_story_state_committed") is False and
         q25_receipt.get("production_state_write_authorized") is False,
         "Q25_PROVENANCE")
    try:
        cost = Decimal(q25_receipt["provider_reported_cost_usd"])
    except Exception:
        raise HarnessStop("COHORT_STAGE_STOP_Q25_COST_UNKNOWN") from None
    must(cost.is_finite() and 0 < cost <= COST_CAP, "Q25_COST_CAP")
    proposal = q25_receipt.get("evidence_proposal")
    must(type(proposal) is dict, "Q25_EVIDENCE_MISSING")
    envelope = {
        "source_pack_sha256": pack["pack_sha256"],
        "story_sha256": story["story_sha256"],
        "spine_sha256": source["spine"]["spine_sha256"],
        "evidence_json": json.dumps(proposal, ensure_ascii=False),
        "explanation": "Revalidated quote-grounded Q25 observations in read-only mode."
    }
    approved = verify_candidate(bundle, envelope)
    canon = deepcopy(pack["canonical_state"])
    initially = list(canon["protagonist"]["known_locations"])
    discovered = [x["location_id"] for x in approved["discovered_locations"]]
    result = {
        "schema": "lumi.story-harness-cohort-read-only-final-state.v1",
        "case_id": source["case_id"],
        "source_pack_sha256": pack["pack_sha256"],
        "story_sha256": story["story_sha256"],
        "canonical_start_snapshot_sha256": sha(canon),
        "artifact_classification": "READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON",
        "protagonist_name": canon["protagonist"]["name"],
        "proposed_final_location": deepcopy(approved["final_location"]),
        "proposed_known_locations": initially + [x for x in discovered
                                                  if x not in initially],
        "object_observation_candidates": deepcopy(approved["object_observations"]),
        "initial_canonical_objects_unchanged": deepcopy(canon["objects"]),
        "initial_open_obligations_unchanged": deepcopy(canon["open_obligations"]),
        "obligation_outcome_candidates": deepcopy(approved["open_obligation_outcomes"]),
        "unknown_facts_retained": deepcopy(approved["unknown_facts_retained"]),
        "initial_world_time": canon["world_time"],
        "final_world_time": None,
        "independent_state_semantics_certified": False,
        "original_v21_full_final_quality_certified": False,
        "production_state_write_authorized": False,
        "production_change": False,
        "model_calls_for_projection": 0,
        "manual_prose_edits": 0,
    }
    must(result["unknown_facts_retained"] == canon["unknown_facts"] and
         result["initial_open_obligations_unchanged"] == canon["open_obligations"] and
         result["final_world_time"] is None and
         all(x["ownership"] == "UNKNOWN"
             for x in result["object_observation_candidates"]),
         "INVENTED_STATE")
    return result
