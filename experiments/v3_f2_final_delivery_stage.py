"""Read-only F2 bilingual delivery staging; NEVER publication or world-state commit.

This external qualification is NOT the frozen V3 finalizer. It checks
both real-model acceptance chains, copies their unchanged accepted prose,
and exposes only unassessed Spine outcome candidates for a future
independently authorized world-state decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from src.frozen_lane_verify import verify_frozen_lane

CASE_ID="age18.forbidden-cartographer.fantasy.frozen-01"
FROZEN_SHA="63e1e3ce82c244bc5bb02b0463a9a1a6715c941b"
ENGLISH_SHA="990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8"
TURKISH_SHA="a163d9cbde430bd2023bb9e673d0e8ff4b380c7567aa84c4b476252dd2ddca19"
ORIGINAL_SHA="eb38aea3c43a9e59d748ee0cf6f53475bfaf1d4c412c46e0893c78ccc3874eeb"
APPROVED_SHA="21f1e4e0c9f25cd1c970cccc2df8d09a0f236c9102321df7da086f85a3dac1a0"
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
APPROVED=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")
ORIGINAL=Path("evidence/v3-f2-aion-writer-38703469212/story-en.txt")
ENGLISH=Path("evidence/v3-f2-final-luna-recheck-38712035968/english-quality-accepted.txt")
ENGLISH_QUAL=Path("evidence/v3-f2-final-luna-recheck-38712035968/qualification.json")
ENGLISH_MODEL=Path("evidence/v3-f2-final-luna-recheck-38712035968/model-03-post_repair_coherence_reaudit.json")
PRIOR_LUNA=Path("evidence/v3-f2-autonomous-quality-38709109136/model-01-initial_coherence_audit.json")
PRIOR_SOL=Path("evidence/v3-f2-autonomous-quality-38709109136/model-02-bounded_model_repair.json")
TURKISH=Path("evidence/v3-f2-tr-sol-adjudication-38715418567/turkish-quality-accepted.txt")
TURKISH_ORIGINAL=Path("evidence/v3-f2-turkish-luna-findings-38713969969/translation-tr.txt")
TURKISH_QUAL=Path("evidence/v3-f2-tr-sol-adjudication-38715418567/adjudication-outcome.json")
TURKISH_SOL=Path("evidence/v3-f2-tr-sol-adjudication-38715418567/sol-adjudication.json")
TURKISH_LUNA=Path("evidence/v3-f2-turkish-luna-findings-38713969969/fidelity-result.json")
ENGLISH_MANIFEST=Path("docs/qualifications/V3_F2_ENGLISH_AUTOMATED_ACCEPTANCE_MANIFEST_20261015.json")
TURKISH_MANIFEST=Path("docs/qualifications/V3_F2_TURKISH_ACCEPTANCE_MANIFEST_20261015.json")
MODEL_AUDIT_INITIAL_SHA="7d2a67f89372fe1c65868b8f3dd64dea946685c161536e0af2cc45af958ac189"
MODEL_PATCH_SHA="3865c48f43929da6f10b577a72a00d2d81cc0d7a4bee3219c74b3e775946d0b3"
MODEL_LUNA_FIDELITY_SHA="40cf924ce239050fd9ed046f3d9199af0f262c57d0296cf44cc4a8ab918be591"
SOL_MODEL="openai/gpt-5.6-sol"
EXPECTED_COST_USD="0.4364515"


class DeliveryStop(RuntimeError):
    """Evidence/provenance inconsistent; no release artifact shall be created."""


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path:Path)->dict:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise DeliveryStop("INVALID_SOURCE_JSON")
    return payload


def require(condition:bool,reason:str):
    if not condition:
        raise DeliveryStop(reason)


def verify_sources()->dict:
    frozen=verify_frozen_lane(PROFILE)
    require(frozen.get("verified_files")==43 and frozen.get("verified") is True,
            "FROZEN_43_SOURCE_VERIFICATION_FAILED")
    for path,expected in (
        (APPROVED,APPROVED_SHA),(ORIGINAL,ORIGINAL_SHA),
        (ENGLISH,ENGLISH_SHA),(TURKISH,TURKISH_SHA),
        (TURKISH_ORIGINAL,TURKISH_SHA),
        (PRIOR_LUNA,MODEL_AUDIT_INITIAL_SHA),
        (PRIOR_SOL,MODEL_PATCH_SHA),
        (TURKISH_LUNA,MODEL_LUNA_FIDELITY_SHA),
    ):
        require(path.is_file() and sha(path)==expected,"STAGED_SOURCE_SHA_MISMATCH:"+str(path))
    approved=load(APPROVED)
    qe,qt=load(ENGLISH_QUAL),load(TURKISH_QUAL)
    me,mt=load(ENGLISH_MANIFEST),load(TURKISH_MANIFEST)
    audit=load(ENGLISH_MODEL)
    sol=load(TURKISH_SOL)
    first_luna=load(PRIOR_LUNA)
    first_sol=load(PRIOR_SOL)
    prior_fidelity=load(TURKISH_LUNA)
    require(approved.get("qualification_provenance",{}).get("case_id")==CASE_ID,
            "WRONG_CASE_AUTHORITY")
    require(approved["qualification_provenance"].get("frozen_v3_sha")==FROZEN_SHA,
            "WRONG_FROZEN_RUNTIME")
    require(approved.get("source_run_id")==38700326961
            and approved.get("human_review",{}).get("verdict")=="APPROVE"
            and approved.get("gate",{}).get("decision")=="ACCEPT",
            "SPINE_NOT_APPROVED")
    require(qe.get("status")=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
            and qe.get("accepted_story_sha256")==ENGLISH_SHA
            and qe.get("original_story_sha256")==ORIGINAL_SHA
            and qe.get("source_writer_run")==38703469212
            and qe.get("source_quality_run")==38709109136
            and qe.get("live_recheck_calls")==1
            and qe.get("model_authored_local_edits")==1
            and qe.get("translation_authorized") is False
            and qe.get("world_state_commit_authorized") is False,
            "ENGLISH_ACCEPTANCE_CONTRACT_MISMATCH")
    require(me.get("case_id")==CASE_ID
            and me.get("status")==qe["status"]
            and me.get("accepted_story_sha256")==ENGLISH_SHA
            and me.get("final_qualification_sha256")==sha(ENGLISH_QUAL)
            and me.get("source_frozen_v3_sha")==FROZEN_SHA,
            "ENGLISH_PROVENANCE_MANIFEST_MISMATCH")
    require(audit.get("model")=="openai/gpt-5.6-luna"
            and audit.get("generation_id")==qe.get("final_luna_generation_id")
            and isinstance(audit.get("model_json",{}).get("evaluations"),list)
            and len(audit["model_json"]["evaluations"])==9
            and not any(x.get("present") for x in audit["model_json"]["evaluations"])
            and me.get("final_luna_model_response_sha256")==sha(ENGLISH_MODEL),
            "ENGLISH_REAL_LUNA_RECHECK_MISSING")
    proposal=first_sol["model_json"]["repairs"]
    require(first_luna.get("model")=="openai/gpt-5.6-luna"
            and first_sol.get("model")=="openai/gpt-5.6-sol"
            and len(proposal)==1,"ENGLISH_MODEL_REPAIR_PROVENANCE_INVALID")
    old,new=proposal[0].get("old"),proposal[0].get("new")
    original=ORIGINAL.read_text(encoding="utf-8")
    require(isinstance(old,str) and isinstance(new,str)
            and old!=new and original.count(old)==1
            and ENGLISH.read_text(encoding="utf-8")==original.replace(old,new,1),
            "ENGLISH_STORY_NOT_EXACT_SOL_REPAIR")
    require(qt.get("status")=="AUTOMATED_TURKISH_FIDELITY_ACCEPTED"
            and qt.get("confirmed_findings")==0
            and qt.get("model_posts")==1
            and qt.get("manual_text_edits")==0
            and qt.get("publication_authorized") is False
            and qt.get("world_state_commit_authorized") is False,
            "TURKISH_ACCEPTANCE_CONTRACT_MISMATCH")
    require(mt.get("case_id")==CASE_ID and mt.get("status")==qt["status"]
            and mt.get("accepted_turkish_sha256")==TURKISH_SHA
            and mt.get("story_english_accepted_sha256")==ENGLISH_SHA
            and mt.get("qualification_sha256")==sha(TURKISH_QUAL)
            and mt.get("sol_adjudication_sha256")==sha(TURKISH_SOL)
            and mt.get("translation_run_id")==38713969969
            and mt.get("sol_adjudication_run_id")==38715418567,
            "TURKISH_PROVENANCE_MANIFEST_MISMATCH")
    require(TURKISH.read_bytes()==TURKISH_ORIGINAL.read_bytes(),
            "TURKISH_TEXT_WAS_EDITED_OUTSIDE_GEMINI")
    require(sol.get("status") is None or isinstance(sol.get("status"),str),
            "SOL_FORMAT_INVALID")
    require(sol.get("schema_version")=="episode-fidelity-adjudication.v1"
            and sol.get("fidelity_findings") is None
            and sol.get("confirmed_fidelity_findings")==[]
            and len(sol.get("evaluations") or [])==3
            and {r.get("finding_index") for r in sol["evaluations"]}=={0,1,2}
            and all(r.get("decision")=="REJECT" for r in sol["evaluations"])
            and sol.get("fidelity_model") is None,
            "SOL_FIDELITY_DECISION_NOT_THREE_REJECTS")
    require(prior_fidelity.get("status")=="findings_need_adjudication"
            and len(prior_fidelity.get("fidelity_findings") or [])==3,
            "LUNA_FIDELITY_ORIGINAL_FINDINGS_CHANGED")
    require(mt.get("all_f1_f2_writer_quality_turkish_cost_usd")==EXPECTED_COST_USD,
            "HISTORICAL_COST_TALLY_MISMATCH")
    spine=approved["episode_spine"]
    candidates=spine.get("persistent_outcome_candidates")
    require(isinstance(candidates,list) and len(candidates)>0
            and all(isinstance(x,dict) and x.get("type")
                    and x.get("description") and x.get("commit_condition")
                    for x in candidates),"PERSISTENT_OUTCOME_CANDIDATES_MISSING")
    require(spine.get("decision_point",{}).get("outcome_uncommitted") is True,
            "SOURCE_SPINE_ALREADY_MARKED_COMMITTED")
    return {
        "english_word_count":qe["word_count"],
        "turkish_word_count":mt["accepted_turkish_words"],
        "spine":spine,
        "candidates":candidates,
        "source_frozen_checks":frozen["verified_files"],
        "sol_generation_id":mt["sol_generation_id"],
        "luna_generation_id":qe["final_luna_generation_id"],
    }


def _write_exact(path:Path,content:bytes):
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def stage(out_dir:Path)->dict:
    source=verify_sources()  # no output or payment before full evidence preflight
    require(not out_dir.exists(),"DELIVERY_OUTPUT_ALREADY_EXISTS")
    require(source["english_word_count"]==2767
            and source["turkish_word_count"]==2173,
            "UNEXPECTED_ACCEPTED_WORD_COUNTS")
    out_dir.mkdir(parents=True,mode=0o700)
    en=out_dir/"story.en.txt"
    tr=out_dir/"story.tr.txt"
    _write_exact(en,ENGLISH.read_bytes())
    _write_exact(tr,TURKISH.read_bytes())
    state_proposals=[]
    for index,row in enumerate(source["candidates"],1):
        state_proposals.append({
            "candidate_id":f"f2-outcome-{index:02d}",
            "kind":row["type"],
            "source_description":row["description"],
            "source_commit_condition":row["commit_condition"],
            "condition_evaluation":"NOT_EVALUATED",
            "evidence_spans":[],
            "candidate_state":"PROPOSED_UNCOMMITTED",
            "commit_authorized":False,
            "applied":False,
        })
    proposal_manifest={
        "schema":"lumi.v3-f2.state-transition-proposals.v1",
        "case_id":CASE_ID,
        "episode_branch_resolution":"NOT_INDEPENDENTLY_ASSESSED",
        "saga_progression_milestone_key":"forbidden_passage_observed",
        "milestone_eligibility":"UNDETERMINED",
        "approved_spine_is_plan_not_committed_canon":True,
        "candidate_operations":state_proposals,
        "pending_model_evidence_matching":True,
        "authority_to_commit":False,
        "applied_operations":[],
        "world_state_committed":False,
        "publication_authorized":False,
    }
    _write_exact(out_dir/"state-proposals.json",
                 (json.dumps(proposal_manifest,ensure_ascii=False,indent=2)+"\n").encode())
    manifest={
        "schema":"lumi.v3-f2.delivery-stage.v1",
        "case_id":CASE_ID,
        "title":source["spine"]["title"],
        "source_frozen_sha":FROZEN_SHA,
        "status":"DELIVERY_STAGED_UNPUBLISHED",
        "english_quality":"AUTOMATED_ENGLISH_COHERENCE_ACCEPTED",
        "turkish_quality":"AUTOMATED_TURKISH_FIDELITY_ACCEPTED",
        "english":{"file":"story.en.txt","sha256":sha(en),
                   "words":source["english_word_count"],"source_run":38712035968},
        "turkish":{"file":"story.tr.txt","sha256":sha(tr),
                   "words":source["turkish_word_count"],"source_run":38715418567},
        "quality_model_chain":[
            "aion-labs/aion-3.5-mini",
            "openai/gpt-5.6-luna",
            "openai/gpt-5.6-sol",
            "openai/gpt-5.6-luna",
            "google/gemini-3.8-flash",
            "openai/gpt-5.6-luna",
            "openai/gpt-5.6-sol",
        ],
        "provenance":{
            "approved_spine_sha256":APPROVED_SHA,
            "english_manifest_sha256":sha(ENGLISH_MANIFEST),
            "turkish_manifest_sha256":sha(TURKISH_MANIFEST),
            "final_english_luna_generation_id":source["luna_generation_id"],
            "final_turkish_sol_generation_id":source["sol_generation_id"],
        },
        "state_proposals":{
            "file":"state-proposals.json",
            "sha256":sha(out_dir/"state-proposals.json"),
            "count":len(state_proposals),
            "evaluated":False,
        },
        "historical_experiment_cost_usd":EXPECTED_COST_USD,
        "stage_new_provider_posts":0,
        "stage_new_spend_usd":"0",
        "publish_authorized":False,
        "published":False,
        "world_state_commit_authorized":False,
        "world_state_committed":False,
        "finalizer_publication_ready_not_asserted":True,
    }
    _write_exact(out_dir/"delivery-manifest.json",
                 (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode())
    return manifest


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir",type=Path,required=True)
    args=parser.parse_args()
    result=stage(args.out_dir)
    print(json.dumps({
        "status":result["status"],
        "english_sha256":result["english"]["sha256"],
        "turkish_sha256":result["turkish"]["sha256"],
        "candidate_count":result["state_proposals"]["count"],
        "provider_posts":0,
        "published":False,
        "world_state_committed":False,
    },ensure_ascii=False))
