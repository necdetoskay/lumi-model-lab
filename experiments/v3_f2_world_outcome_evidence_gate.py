"""Validate model-originated outcome evidence WITHOUT committing world state.

The judge model, NOT an operator, supplies branch resolution, exact cited
story excerpts and a condition verdict for each frozen Spine candidate.
This module validates quoted evidence and outputs a NON-EXECUTABLE proposal.
It provides no provider calls, persistence adapter, or commit API.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STAGED=Path("evidence/v3-f2-final-delivery-staging-20261015")
EXPECTED_EN="990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8"
EXPECTED_TR="a163d9cbde430bd2023bb9e673d0e8ff4b380c7567aa84c4b476252dd2ddca19"
REQUIRED_MODEL_OUTPUT_SCHEMA="lumi.v3-f2.world-outcome-evidence-judge.v1"
VALID_BRANCHES={"seal_bounded_report","extend_testing"}


class OutcomeStop(RuntimeError):
    pass


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(condition:bool,reason:str):
    if not condition:
        raise OutcomeStop(reason)


def _quote_provenance(quote:str,story:str)->str | None:
    """Verify exact prose, permitting ONLY a misplaced terminal italic marker.

    For an italicized paragraph such as "*Sentence one. Sentence two.*",
    a judge may quote just "*Sentence one.*" while the source italic
    span continues. The words are exact and the extra final '*' is
    formatting markup only, NOT an invented literary fact.
    """
    if not isinstance(quote,str) or len(quote.strip())<12:
        return None
    if quote in story:
        return "EXACT"
    if (len(quote)<30 or not quote.startswith("*") or not quote.endswith("*")
        or quote.count("*")!=2):
        return None
    # Accept only the ONE terminal markdown marker moved earlier. No
    # deleted/replaced/rewritten content is permitted.
    source_prefix=quote[:-1]
    if story.count(source_prefix)!=1:
        return None
    start=story.find(source_prefix)
    end=start+len(source_prefix)
    # The italic passage must continue after the cited words and end
    # later within the same source paragraph, not a different section.
    if story[end:end+1]!=" ":
        return None
    rest=story[end:].split("\n",1)[0]
    if not rest.endswith("*") or rest.count("*")!=1:
        return None
    return "ITALIC_CLOSER_BOUNDARY_ONLY"


def validate_judge_output(payload:dict,*,stage_dir:Path=STAGED)->dict:
    """Inspect model evidence only; NEVER assert commit-ready authority."""
    d=json.loads((stage_dir/"delivery-manifest.json").read_text(encoding="utf-8"))
    original=json.loads((stage_dir/"state-proposals.json").read_text(encoding="utf-8"))
    english_path=stage_dir/"story.en.txt"
    turkish_path=stage_dir/"story.tr.txt"
    story=english_path.read_text(encoding="utf-8")
    _check(d["status"]=="DELIVERY_STAGED_UNPUBLISHED"
           and d["published"] is False
           and d["world_state_committed"] is False
           and d["publish_authorized"] is False
           and d["world_state_commit_authorized"] is False,
           "STAGE_NOT_UNPUBLISHED")
    _check(_sha(english_path)==EXPECTED_EN
           and _sha(turkish_path)==EXPECTED_TR
           and d["english"]["sha256"]==EXPECTED_EN
           and d["turkish"]["sha256"]==EXPECTED_TR,
           "WORLD_JUDGE_SOURCE_HASH_MISMATCH")
    _check(d["state_proposals"]["sha256"]==_sha(stage_dir/"state-proposals.json"),
           "WORLD_JUDGE_CANDIDATE_MANIFEST_CHANGED")
    _check(original["world_state_committed"] is False
           and original["applied_operations"]==[]
           and original["milestone_eligibility"]=="UNDETERMINED",
           "WORLD_JUDGE_SOURCE_ALREADY_COMMITTED")
    _check(isinstance(payload,dict)
           and payload.get("schema")==REQUIRED_MODEL_OUTPUT_SCHEMA,
           "WORLD_JUDGE_WRONG_MODEL_SCHEMA")
    _check(payload.get("source_story_sha256")==EXPECTED_EN,
           "WORLD_JUDGE_WRONG_SOURCE")
    branch=payload.get("selected_branch")
    _check(branch in VALID_BRANCHES,"WORLD_JUDGE_INVALID_BRANCH")
    _check(isinstance(payload.get("branch_evidence_quotes"),list)
           and len(payload["branch_evidence_quotes"])>=1,
           "WORLD_JUDGE_BRANCH_EVIDENCE_MISSING")
    branch_provenance=[]
    for quote in payload["branch_evidence_quotes"]:
        proof=_quote_provenance(quote,story)
        _check(proof is not None,"WORLD_JUDGE_BRANCH_QUOTE_FABRICATED")
        branch_provenance.append(proof)
    reviews=payload.get("candidate_reviews")
    source=original["candidate_operations"]
    _check(isinstance(reviews,list) and len(reviews)==len(source),
           "WORLD_JUDGE_INCOMPLETE_CANDIDATE_SET")
    seen=set()
    evaluated=[]
    for row in reviews:
        _check(isinstance(row,dict),"WORLD_JUDGE_INVALID_REVIEW_ROW")
        cid=row.get("candidate_id")
        _check(isinstance(cid,str) and cid not in seen,
               "WORLD_JUDGE_DUPLICATE_REVIEW_ID")
        seen.add(cid)
        expected=next((x for x in source if x["candidate_id"]==cid),None)
        _check(expected is not None,"WORLD_JUDGE_UNAPPROVED_CANDIDATE")
        verdict=row.get("condition_verdict")
        _check(verdict in ("EARNED","NOT_EARNED"),
               "WORLD_JUDGE_INVALID_CONDITION_VERDICT")
        explanation=row.get("reason")
        _check(isinstance(explanation,str) and len(explanation.strip())>=12,
               "WORLD_JUDGE_RATIONALE_REQUIRED")
        quotes=row.get("evidence_quotes")
        _check(isinstance(quotes,list),"WORLD_JUDGE_EVIDENCE_LIST_REQUIRED")
        if verdict=="EARNED":
            _check(len(quotes)>=1,"WORLD_JUDGE_EARNED_WITHOUT_QUOTE")
        quote_provenance=[]
        for quote in quotes:
            proof=_quote_provenance(quote,story)
            _check(proof is not None,"WORLD_JUDGE_INVENTED_EVIDENCE_QUOTE")
            quote_provenance.append(proof)
        # The sealed-field-record knowledge milestone cannot be earned
        # on the branch where the formal report was never signed.
        if branch=="extend_testing" and cid=="f2-outcome-01" and verdict=="EARNED":
            raise OutcomeStop("WORLD_JUDGE_BRANCH_MILESTONE_CONTRADICTION")
        evaluated.append({
            "candidate_id":cid,
            "kind":expected["kind"],
            "source_description":expected["source_description"],
            "source_commit_condition":expected["source_commit_condition"],
            "model_condition_verdict":verdict,
            "evidence_quotes":quotes,
            "quote_provenance":quote_provenance,
            "model_explanation":explanation,
            "candidate_state":"EVALUATED_BUT_UNCOMMITTED",
            "commit_authorized":False,
            "applied":False,
        })
    _check(seen=={x["candidate_id"] for x in source},
           "WORLD_JUDGE_MISSING_APPROVED_CANDIDATE")
    milestone=bool(
        branch=="seal_bounded_report"
        and next(x for x in evaluated if x["candidate_id"]=="f2-outcome-01")["model_condition_verdict"]=="EARNED"
    )
    return {
        "schema":"lumi.v3-f2.world-outcome-evaluated-uncommitted.v1",
        "case_id":d["case_id"],
        "english_sha256":EXPECTED_EN,
        "turkish_sha256":EXPECTED_TR,
        "status":"MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED",
        "model_selected_branch":branch,
        "branch_evidence_quotes":payload["branch_evidence_quotes"],
        "branch_quote_provenance":branch_provenance,
        "approved_persistent_candidates":evaluated,
        "proposed_saga_milestone":{
            "key":"forbidden_passage_observed",
            "model_evidence_suggests_earned":milestone,
            "committed":False,
        },
        "world_state_transaction":None,
        "applied_operations":[],
        "world_state_commit_authorized":False,
        "world_state_committed":False,
        "publication_authorized":False,
        "published":False,
    }
