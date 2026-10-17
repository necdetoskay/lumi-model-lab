"""SERA v0.53 — join independently signed G2 physical baseline to prose.

A signed physical registry certifies an ENTRY snapshot (locations, holders,
owners, facts), not the truth of a model-proposed future action. A model
cannot sign its own physical baseline or approve a world mutation.
All events remain proposals; no inferred event time or canonical writes.
"""
from __future__ import annotations

from copy import deepcopy

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.g2_physical_pinned_reader_v036 import project_pinned_physical
from experiments.sera.source_chronology_v052 import build_source_chronology
from experiments.sera.world_state_v02 import canonical

SCHEMA="sera.v053-signed-physical-source-reconciliation"
NONOBJECTIVE=frozenset({
    "REPORTED_CLAIM","NEGATED","HYPOTHESIS","UNCERTAIN","CLAIM_ONLY",
    "REPORTED_ONLY",
})


def need(ok,code):
    if not ok:
        raise CoverageError(code)


def reconcile_signed_physical_source(
    *,prose,scene_key,registry,candidate_lexicon,chronology,
    authority,projection,public_key_pem,raw_public_key_sha256,
    key_id,issuer,audience,expected_nonce,consume_nonce,now=None,
    model_report=None,
):
    """App-owned signed G2 physical baseline + source-bound model proposal.

    This is an opt-in/read-only gate. The signer, nonce consumption and G2
    scope must be managed OUTSIDE the storyteller/LLM and its prompt.
    Even a fully signed entry world does NOT attest that the model event
    happened; it only makes pre-event registered relations available.
    """
    need(isinstance(chronology,dict) and
         chronology.get("source_prose_sha256")==prose_hash(prose) and
         chronology.get("scene_key")==scene_key and
         chronology.get("canonical_commit_authorized") is False and
         chronology.get("world_db_writes")==0 and
         chronology.get("source_graph_status")=="HOLD_NONCANONICAL",
         "V053_CHRONOLOGY_SOURCE_UNTRUSTED")
    # Do NOT call the loose v0.33 verify_projection injection: the ONLY
    # authority path is v0.36 pinned Ed25519 + one-use nonce.
    trusted=project_pinned_physical(
        authority=authority,projection=projection,
        public_key_pem=public_key_pem,
        raw_public_key_sha256=raw_public_key_sha256,
        key_id=key_id,issuer=issuer,audience=audience,
        expected_nonce=expected_nonce,consume_nonce=consume_nonce,now=now)
    need(trusted.get("physical_source_verified") is True and
         trusted.get("physical_source_status")=="SIGNED_READONLY_SHADOW_ONLY" and
         trusted.get("canonical_commit_authorized") is False and
         trusted.get("world_db_writes")==0 and
         trusted.get("g2_commit_request") is None,
         "V053_PHYSICAL_SOURCE_NOT_INDEPENDENTLY_ATTESTED")
    expected=build_source_chronology(
        prose=prose,scene_key=scene_key,
        world_sha256=trusted["world_sha256"],
        registry=registry,candidate_lexicon=candidate_lexicon,
        model_report=model_report)
    need(chronology==expected,
         "V053_CHRONOLOGY_NOT_BOUND_TO_PINNED_PHYSICAL_WORLD")
    entities=trusted["world"]["entities"]
    events_by_id={(e["source_sentence_id"],e["event_id"]):e
                  for e in chronology["model_candidate_events"]}
    proposals=[]
    if model_report is not None:
        # v0.52 chronology validates all model source quotes, sentence links,
        # source SHA, and event coverage before any event is read here.
        for raw in model_report["candidate_events"]:
            ident=(raw["sentence_id"],raw["event_id"])
            e=events_by_id[ident]
            refs=raw.get("entity_refs")
            need(isinstance(refs,list) and
                 all(isinstance(x,str) and x for x in refs) and
                 len(refs)==len(set(refs)),
                 "V053_MODEL_EVENT_ENTITY_REFS_INVALID")
            known=[r for r in refs if r in entities]
            unknown=[r for r in refs if r not in entities]
            nonobjective=e["model_epistemic"] in NONOBJECTIVE
            if nonobjective:
                disposition="CLAIM_OR_UNCERTAIN_NOT_OBJECTIVE"
            elif unknown or not refs:
                disposition="ENTITY_IDENTITY_NOT_PHYSICALLY_REGISTERED"
            else:
                disposition="REGISTERED_BASELINE_ONLY_EVENT_NOT_ATTESTED"
            proposals.append({
                "event_id":e["event_id"],
                "sentence_id":e["source_sentence_id"],
                "source_ordinal":e["source_ordinal"],
                "evidence_start":e["source_start"],
                "evidence_end":e["source_end"],
                "evidence_quote":e["exact_evidence_quote"],
                "model_event_kind":e["model_event_kind"],
                "epistemic":e["model_epistemic"],
                "registered_entity_refs":known,
                "unregistered_or_candidate_refs":unknown,
                "baseline":{k:{
                    "location":entities[k]["location"],
                    "owner":entities[k]["owner"],
                    "holder":entities[k]["holder"],
                    "worn_by":entities[k]["worn_by"],
                } for k in known},
                "event_action_minute":None,
                "event_occurrence_verified":False,
                "proposed_effect_allowed":False,
                "status":disposition,
            })
    need(len(proposals)==len(chronology["model_candidate_events"]),
         "V053_PROPOSAL_EVENT_COVERAGE_MISMATCH")
    return {
        "schema":SCHEMA,"source_prose_sha256":prose_hash(prose),
        "entry_world_sha256":trusted["world_sha256"],
        "g2_physical_snapshot_sha256":trusted["physical_snapshot_sha256"],
        "g2_physical_attestation_sha256":trusted["physical_attestation_sha256"],
        "trusted_physical_key_id":trusted["physical_key_id"],
        "chronology_sha256":chronology["chronology_sha256"],
        "registered_physical_entry_entity_count":len(entities),
        "registered_physical_entry":[
            {
                "entity_id":identifier,
                "kind":entity["kind"],
                "location_id":entity["location"],
                "owner_id":entity["owner"],
                "holder_id":entity["holder"],
                "worn_by_id":entity["worn_by"],
            } for identifier,entity in sorted(entities.items())
        ],
        "registered_route_count":len(trusted["registered_routes"]),
        "source_sentence_count":chronology["source_sentence_count"],
        "source_order_is_event_clock":False,
        "model_candidate_event_count":len(proposals),
        "model_event_proposals":proposals,
        "physical_baseline_status":"SIGNED_G2_ENTRY_ONLY",
        "scene_event_truth_status":"UNVERIFIED_MODEL_PROPOSALS",
        "status":"HOLD_NONCANONICAL_REQUIRES_INDEPENDENT_EVENT_PROOF",
        "verified_future_event_count":0,
        "world_mutations_performed":0,
        "canonical_commit_authorized":False,
        "world_db_writes":0,
    }
