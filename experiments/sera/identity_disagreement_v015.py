"""SERA v0.15 contrast blind identity result vs earlier Mara hypotheses.

Comparison is performed ONLY AFTER the independent paid response was
archived. Earlier v0.14 Mara rule hypotheses are NEVER included in
the model's prompt. Agreement is NOT gold, human adjudication, a
semantic accuracy metric, or authority to create/attach world objects.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from experiments.sera.coverage import CoverageError

SCHEMA="sera.identity-independent-review-disagreement.v0.15"

def require(ok,code):
    if not ok:
        raise CoverageError(code)

def compare(*,forensic:dict,prior:dict)->dict:
    require(isinstance(forensic,dict) and forensic.get("schema")==
             "sera.paid-blind-identity-forensic-recovery.v0.15.1" and
            forensic.get("source_run_id")==38872615837 and
            forensic.get("all_original_model_rows_returned")==16 and
            forensic.get("paid_model_calls_during_recovery")==0 and
            forensic.get("canonical_commit_authorized") is False and
            forensic.get("new_entity_creations")==0 and
            forensic.get("new_relation_attachments")==0 and
            forensic.get("human_gold_adjudicated") is False and
            isinstance(forensic.get("source_bound_model_proposals"),list) and
            isinstance(forensic.get("quarantined_original_model_rows"),list),
            "V015_CONTRAST_PAID_FORENSIC_PROVENANCE_INVALID")
    require(isinstance(prior,dict) and
            prior.get("schema")=="sera.mara-s1-identity-and-events-review.v0.14" and
            prior.get("source_prose_sha256")==
                forensic.get("source_prose_sha256") and
            prior.get("all_unregistered_refs_proposed")==16 and
            prior.get("created_entities")==0 and
            prior.get("approved_relation_links")==0 and
            prior.get("canonical_commit_authorized") is False and
            isinstance(prior.get("entity_identity_proposals"),list),
            "V015_CONTRAST_PREVIOUS_HYPOTHESES_INVALID")
    earlier={x["source_entity_ref"]:x for x in
             prior["entity_identity_proposals"]}
    valid={x["entity_ref"]:x for x in
           forensic["source_bound_model_proposals"]}
    invalid={x["entity_ref"]:x for x in
             forensic["quarantined_original_model_rows"]}
    require(len(earlier)==len(prior["entity_identity_proposals"])==16 and
            len(valid)==len(forensic["source_bound_model_proposals"]) and
            len(invalid)==len(forensic["quarantined_original_model_rows"]) and
            set(valid).isdisjoint(invalid) and
            set(valid)|set(invalid)==set(earlier) and
            len(valid)+len(invalid)==16,
            "V015_CONTRAST_ENTITY_COVERAGE_INVALID")
    rows=[]
    class_matches=0
    relation_matches=0
    parent_matches=0
    fully_matches=0
    review_flags=Counter()
    for ref in sorted(earlier):
        p=earlier[ref]
        if ref in valid:
            d=valid[ref]
            model={
                "classification":d["proposed_classification"],
                "relation":d["proposed_relation"],
                "relation_target":d["proposed_relation_target"],
                "support_quote":(
                    d["source_support"]["quote"] if d["source_support"]
                    else None),
            }
            binder="SOURCE_BOUND_NOT_SEMANTICALLY_APPROVED"
            quarantine_error=None
        else:
            bad=invalid[ref]
            raw=bad["model_row_unmodified"]
            model={
                "classification":raw.get("classification"),
                "relation":raw.get("relation"),
                "relation_target":raw.get("relation_target"),
                "support_quote":raw.get("support_quote"),
            }
            binder="QUARANTINED_SOURCE_OR_SCHEMA_INVALID"
            quarantine_error=bad["error_code"]
        pcls=p["proposed_classification"]
        prel=p["proposed_relation"]
        ptgt=p["proposed_relation_target"]
        cc=model["classification"]==pcls
        rc=model["relation"]==prel
        tc=model["relation_target"]==ptgt
        class_matches+=cc
        relation_matches+=rc
        parent_matches+=tc
        fully_matches+=cc and rc and tc
        risks=[]
        if not cc:
            risks.append("BLIND_CLASS_DISAGREES_WITH_PRIOR_HYPOTHESIS")
        if not rc:
            risks.append("RELATION_TYPE_DISAGREES_WITH_PRIOR_HYPOTHESIS")
        if not tc:
            risks.append("RELATION_TARGET_DISAGREES_WITH_PRIOR_HYPOTHESIS")
        if ref in invalid:
            risks.append("BLIND_ROW_QUARANTINED_INVALID_CONTRACT")
        if model["classification"] in (
            "DOCUMENT_SUBENTRY_CANDIDATE",
            "DOCUMENT_ALIAS_CANDIDATE",
            "DOCUMENT_COMPONENT_CANDIDATE",
        ) and model["relation_target"] not in (None,ptgt):
            # v0.2 OBJECT alone cannot prove a target is a document;
            # preserve uncertainty instead of trusting model/hand rules.
            risks.append("DOCUMENT_PARENT_ASPECT_NOT_TYPE_QUALIFIED")
        if not risks:
            risks.append("TWO_UNTRUSTED_INTERPRETATIONS_AGREE_NOT_GOLD")
        review_flags.update(risks)
        rows.append({
            "entity_ref":ref,
            "prior_source_anchored_hypothesis":{
                "class":pcls,"relation":prel,"target":ptgt,
            },
            "blind_model_original_opinion":model,
            "blind_deterministic_binding":binder,
            "blind_quarantine_error":quarantine_error,
            "class_agreement_not_accuracy":bool(cc),
            "relation_agreement_not_accuracy":bool(rc),
            "parent_agreement_not_accuracy":bool(tc),
            "semantic_review_flags":sorted(set(risks)),
            "automatic_entity_creation":False,
            "automatic_relation_attachment":False,
            "canonical_commit_authorized":False,
            "status":"INDEPENDENT_REVIEW_STILL_REQUIRED",
        })
    return {
        "schema":SCHEMA,
        "source_prose_sha256":forensic["source_prose_sha256"],
        "original_model_mentioned_refs":len(rows),
        "blind_source_bound_proposal_count":len(valid),
        "blind_quarantined_count":len(invalid),
        "category_agreement_count_NOT_SEMANTIC_ACCURACY":class_matches,
        "relation_agreement_count_NOT_SEMANTIC_ACCURACY":relation_matches,
        "parent_agreement_count_NOT_SEMANTIC_ACCURACY":parent_matches,
        "full_tuple_agreement_count_NOT_GOLD":fully_matches,
        "review_flag_frequency":dict(sorted(review_flags.items())),
        "rows":rows,
        "model_calls_during_comparison":0,
        "world_db_writes":0,
        "entity_creations":0,
        "attached_relations":0,
        "human_gold_adjudicated":False,
        "canonical_commit_authorized":False,
        "status":"BLIND_VERSUS_PRIOR_HYPOTHESES_COMPARED_ALL_IDENTITIES_HOLD",
    }
