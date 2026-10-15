"""P4.7 source-scoped route-truth correction with explicit real-quality STOP.

A new Writer-level authored full manuscript replaces one erroneous sentence
about Arda's rope.  Checks true P4.6 source, all changed bytes, SHA, source-
anchored provisional review; original frozen v21.4 is bound to a DIFFERENT
story, and is never silently reused to review this new candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.story_harness_v1 import HarnessStop,secure_artifact,load_json
from src.story_harness_p46 import review as review_p46

SCHEMA="lumi.story-harness-p47-route-truth-preflight.v1"
MANIFEST="configs/story_harness_p47_route_truth_revision.json"
MANIFEST_SHA="b9224a0f529a1c5617ac5a3d97a64462a477147f8dd7e7fa13d01aaa54f373fe"
REVIEW_BRIEF="evidence/story_harness_p47/offline-editorial-review-brief.json"
REVIEW_SHA="e6e67cd7e397a58228f146c312c92a56405c817528a010dd7b3bb7c9fa050887"
PARENT="evidence/story_harness_p46/offline-full-story-writer-revision.txt"
CHILD="evidence/story_harness_p47/offline-full-story-route-truth-revision.txt"
PINNED_V21_PROFILE="data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json"
PINNED_V21_PROFILE_SHA="37362ae6155b5a319d1776d68a9014c23628d476379dd1621b606267b1199161"
EDITORIAL_IDS=("LOAD_CAPACITY","SAFETY_SLIDER","GLIDER_EQUIPMENT",
               "TURNAROUND_PRESSURE","AGE_AND_AGENCY","ROUTE_TRUTH")


def _must(ok,why):
    if not ok: raise HarnessStop(why)


def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _read_exact(root:Path,relative:str,allow_evidence=False):
    _must(isinstance(relative,str) and ".." not in Path(relative).parts
          and not Path(relative).is_absolute()
          and not "\\" in relative,
          "Unsafe source artifact path")
    if allow_evidence:
        _must(relative in (PARENT,CHILD),"Wrong story lineage selected")
    else:
        _must(relative==PINNED_V21_PROFILE,"Wrong real-runtime source profile")
    p=root
    for part in Path(relative).parts:
        p=p/part
        _must(not p.is_symlink(),"Symlinked source rejected")
    _must(p.is_file() and p.resolve().is_relative_to(root)
          and p.stat().st_size<=30000,
          "Missing/oversized original or editorial evidence")
    return p.read_bytes()


def _manifest(root):
    b=secure_artifact(root,MANIFEST)
    _must(_sha(b)==MANIFEST_SHA,"P4.7 editorial source manifest changed")
    m=json.loads(b)
    _must(m["schema"]=="lumi.story-harness-p47-route-truth-revision.v1"
          and m["source_repo_commit"]=="bcc351899bc3396618546bbddac506baedb632cb"
          and m["p46_artifact_path"]==PARENT
          and m["p47_artifact_path"]==CHILD
          and m["reader_age"]==12
          and m["p46_story_words"]==2482
          and m["p47_story_words"]==2491
          and m["quality_status"]=="UNREVIEWED"
          and m["source_producer"]=="OFFLINE_ASSISTANT_WRITER_EDIT"
          and m["semantic_review_outcome"]=="NOT_INDEPENDENTLY_REVIEWED"
          and m["bounded_v21_4_source_admissible"] is False
          and m["new_model_profile_required_before_real_audit"] is True
          and m["real_authorized_paid_attempt"] is False
          and m["paid_total_ceiling_usd"] is None
          and m["provider_calls"]==0 and m["provider_cost_usd"]=="0"
          and m["english_master_authorized"] is False
          and m["q25_authorized"] is False
          and m["canonical_state_commit_authorized"] is False
          and m["user_allows_quality_target_overrun"] is True
          and m["quality_target_usd"]==0.10
          and m["proposed_single_attempt_ceiling_usd"]==0.25,
          "P4.7 authorial edit falsely authorized a real paid audit/ACCEPT")
    return m


def _real_profile_denial(pinned,m):
    raw=_read_exact(pinned,PINNED_V21_PROFILE)
    _must(_sha(raw)==PINNED_V21_PROFILE_SHA,
          "Original v21.4 profile changed or not source frozen")
    profile=json.loads(raw)
    frozen=profile["source_story"]
    _must(profile["runtime_freeze"]["runtime_revision"]==
          "SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and profile["paid_boundary"]["paid_execution_authorized"] is False
          and frozen["story_sha256"]==m["original_v21_4_bound_story_sha256"]
          and frozen["artifact_id"]==m["original_v21_4_bound_story_artifact_id"]
          and frozen["approved_spine_hash"]==m["approved_spine_hash"]
          and frozen["story_sha256"] != m["p47_story_sha256"],
          "Wrong original v21.4 source identity or unsafe new source admission")
    return frozen["story_sha256"]


def _editorial_review(root,m,new):
    b=secure_artifact(root,REVIEW_BRIEF)
    _must(_sha(b)==REVIEW_SHA,"P4.7 provisional literary review changed")
    brief=json.loads(b)
    _must(brief["schema"]=="lumi.story-harness-p47-editorial-review-brief.v1"
          and brief["source_story_sha256"]==m["p47_story_sha256"]
          and brief["review_origin"]=="ASSISTANT_EDITORIAL_PASS_NOT_INDEPENDENT"
          and brief["signed_semantic_review_present"] is False
          and brief["quality_accept"] is False
          and brief["verdict"]==
          "PRELIMINARY_EDITORIAL_CANDIDATE_NEEDS_INDEPENDENT_QUALITY_AUDIT",
          "Pretend independent editorial acceptance denied")
    items=brief["review_items"]
    _must([i["id"] for i in items]==list(EDITORIAL_IDS),
          "Missing source-bound literary/physical review concerns")
    for item in items:
        quote=item["quote"]
        pos=item["char_offset"]
        _must(type(pos) is int and pos>=0
              and isinstance(quote,str)
              and len(quote)>=25
              and new[pos:pos+len(quote)]==quote
              and _sha(quote.encode())==item["quote_sha256"]
              and item["independent_verifier_approved"] is False
              and len(item["review_question"])>40
              and item["status"] in ("NEEDS_REVIEW","EDITORIAL_FIX_APPLIED"),
              "Ungrounded/hallucinated reviewer issue")
    _must([x["status"] for x in items]==["NEEDS_REVIEW"]*5+
          ["EDITORIAL_FIX_APPLIED"],
          "Unresolved quality risks silently dismissed")
    return len(items)


def qualify(*,repo_root,pinned_source_root):
    root=Path(repo_root).resolve(strict=True)
    pinned=Path(pinned_source_root).resolve(strict=True)
    m=_manifest(root)
    p46=review_p46(repo_root=root)
    _must(p46["status"]=="UNREVIEWED_AUTHORIAL_FULL_STORY_REVISION"
          and p46["provider_calls"]==0
          and p46["independent_semantic_quality_accept"] is False,
          "P4.6 predecessor is no longer an unreviewed source")
    parent=_read_exact(root,PARENT,allow_evidence=True)
    child=_read_exact(root,CHILD,allow_evidence=True)
    _must(_sha(parent)==m["p46_artifact_file_sha256"]
          and _sha(parent.rstrip(b"\n"))==m["p46_story_sha256"]
          and _sha(child)==m["p47_artifact_file_sha256"]
          and _sha(child.rstrip(b"\n"))==m["p47_story_sha256"]
          and p46["revised_story_sha256"]==m["p46_story_sha256"],
          "P4.7 source/new story SHA changed")
    source=parent.decode("utf8")
    actual=child.decode("utf8")
    edit=m["editorial_single_substitution"]
    old=edit["old"]
    replacement=edit["new"]
    _must(edit["id"]=="ROUTE_CAUSAL_TRUTH_001"
          and edit["source_spine_span"]=="S159-S177"
          and isinstance(edit["offset"],int)
          and source[edit["offset"]:edit["offset"]+len(old)]==old
          and source.count(old)==1 and actual.count(replacement)==1
          and _sha(old.encode())==edit["old_sha256"]
          and _sha(replacement.encode())==edit["new_sha256"]
          and len(old)>50 and len(replacement)>60,
          "Route-line correction is not exact and source-anchored")
    _must(source.replace(old,replacement,1)==actual
          and old not in actual
          and len(source.split())==2482
          and len(actual.split())==2491,
          "Story contains changes beyond approved single Writer-level edit")
    _must("The old knots continued inland." in actual
          and "Arda free his expedition line" in actual
          and "both gliders' landing tethers" in actual
          and "The old explorers' knots showed the way." in actual
          and "To reach Nisa, he'd have to let it go." in actual
          and "The Island That Wasn't on Any Map" in actual,
          "Story events/route-motivations were dropped")
    reviewer_items=_editorial_review(root,m,actual)
    old_profile_story_sha=_real_profile_denial(pinned,m)
    return {
      "schema":SCHEMA,
      "status":"OFFLINE_WRITER_CANDIDATE_UNREVIEWED",
      "previous_p46_story_sha256":m["p46_story_sha256"],
      "p47_candidate_story_sha256":m["p47_story_sha256"],
      "story_word_count":m["p47_story_words"],
      "source_commit":m["source_repo_commit"],
      "single_change_id":edit["id"],
      "other_prose_bytes_unchanged":True,
      "old_v21_4_frozen_story_sha256":old_profile_story_sha,
      "original_frozen_model_runner_reusable_for_new_story":False,
      "independent_reviewer_findings_total":0,
      "preliminary_editorial_findings_total":reviewer_items,
      "editorial_open_semantic_risk_count":reviewer_items-1,
      "independent_semantic_quality_accept":False,
      "new_quality_model_profile_required":True,
      "real_paid_attempt_authorized":False,
      "new_model_quality_calls":0,
      "provider_cost_usd":"0",
      "english_master_seal_emitted":False,
      "q25_admission_authorized":False,
      "state_commit_authorized":False,
      "budget_target_overrun_previously_permitted":True,
      "proposed_paid_attempt_usd":0.25,
      "finite_explicit_paid_grant_present":False,
      "stop_reason":"NEW_STORY_SHA_REQUIRES_SEPARATE_QUALITY_RUNNER_QUALIFICATION",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    args=p.parse_args()
    root=Path(args.repo_root).resolve(strict=True)
    report=qualify(repo_root=root,pinned_source_root=args.pinned_source_root)
    if args.verify_report:
        _must(load_json(secure_artifact(root,args.verify_report))==report,
              "P4.7 frozen Writer revision proof mismatched")
    print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True))


if __name__=="__main__": main()

