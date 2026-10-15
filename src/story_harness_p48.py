"""P4.8: qualify the *new 2491-word Writer source* with original frozen adapters OFFLINE.

Previous v21.4 paid profile is immutable and permanently bound to the
original, older story. This intentionally NEW source-aware profile, Writer
artifact and remapped scene scope are provisional, never paid authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from src.story_harness_p47 import qualify as qualify_p47
from src.story_harness_v1 import HarnessStop,load_json,secure_artifact

SCHEMA="lumi.story-harness-p48-new-writer-callback-qualification.v1"
PROFILE="configs/story_harness_p48_source_profile.json"
PROFILE_SHA="c3aa9f0a344ab4e4c87ec110280d8e0197fe740af557f10bbf0d13c8f74f0d2d"
SELECTION="configs/story_harness_p48_remapped_scene_selection.json"
ARTIFACT="evidence/story_harness_p48/new-story-writer-candidate.json"
CONSTRAINTS="evidence/story_harness_p48/candidate-remapped-constraints.json"
RUNNER="src/story_harness_p48_offline_runner.py"
RUNNER_SHA="dec92753f5376a8292dd1a25d2b536ec1b891168eeb3102710c90cbbe846be29"
PINNED_COMMIT="2eb3d825b5baf8f0f16ccb23805f619d433c7236"
STORY_SHA="74529205bd799f46221f22a26aeff93c4ddfe8418cbca2523d43c94e63919e28"
OLD_STORY_SHA="4f64a28eca70f29689e06d1baad3d3a471682bf3e4fce86dabad1c641410f636"
SPINE="f9c5bed93448d6c56787466ae583dfcee06d0f856641d9c3901136f142bffae6"
CALL_CASES={
    "clean_synthetic":("ACCEPT",1),
    "one_repair_synthetic":("ACCEPT",3),
    "provider_transport_failure":("REJECT_PROVIDER_FAILURE",1),
    "missing_usage":("REJECT_PROVIDER_FAILURE",1),
    "out_of_bounded_scope":("REJECT_UNBOUNDED_REPAIR_SCOPE",1),
}


def _must(value, why):
    if not value:raise HarnessStop(why)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _local_bytes(root,relative):
    _must(relative in (PROFILE,SELECTION,ARTIFACT,CONSTRAINTS,RUNNER),
          "Unexpected new source/qualification file path")
    p=root
    for part in Path(relative).parts:
        p=p/part
        _must(not p.is_symlink(),"Symlink source artifact forbidden")
    _must(p.is_file() and p.resolve().is_relative_to(root) and
          p.stat().st_size<250000,"Missing/oversized source qualification file")
    return p.read_bytes()


def _source_profile(root,pinned):
    raw=_local_bytes(root,PROFILE)
    _must(_sha(raw)==PROFILE_SHA,"P4.8 source-bound new profile SHA drift")
    profile=json.loads(raw)
    _must(profile["schema"]=="lumi.story-harness-p48-new-writer-source.v1"
        and profile["source_original_frozen_commit"]==PINNED_COMMIT
        and profile["source_p47_git_commit"]=="6eca192180d0827c91fe80540455a33ad6593f4b"
        and profile["source_story"]["artifact_path"]==ARTIFACT
        and profile["source_story"]["story_sha256"]==STORY_SHA
        and profile["approved_spine_hash"]==SPINE
        and profile["reader_profile"]=={
            "exact_age":12,"target_words_min":1600,"target_words_max":2500}
        and profile["candidate_selection_path"]==SELECTION
        and profile["candidate_constraints_path"]==CONSTRAINTS
        and profile["model_slots"]=={
            "BLOCKING_AUDITOR":"anthropic/claude-sonnet-5.5",
            "SCENE_REPAIRER":"anthropic/claude-sonnet-5.5"}
        and profile["max_quality_calls"]==3
        and profile["max_repairs"]==1
        and profile["full_story_final_reaudit_forbidden"] is True
        and profile["candidate_scene_scope_review_status"]==
            "REMAP_OF_ORIGINAL_APPROVED_BEAT_NOT_HUMAN_REAPPROVED"
        and profile["bridge_full_scene_span_range"]=={
            "start_span_id":"S162","end_span_id":"S206",
            "span_count":45,"fully_bounded_one_scene_repair_feasible":False}
        and profile["candidate_scene_scope"]=={
            "start_span_id":"S167","end_span_id":"S203","span_count":37,
            "outside_scope_blocking_policy":"REJECT_UNBOUNDED_REPAIR_SCOPE"}
        and profile["old_quality_total_target_usd"]==.1
        and profile["user_quality_target_overrun_permitted"] is True
        and profile["proposed_paid_total_ceiling_usd"]==.25
        and profile["explicit_finite_paid_execution_grant"] is None
        and profile["real_provider_dispatch_allowed"] is False
        and profile["pricing_routing_request_count_verified"] is False
        and profile["real_provider_spend_guaranteed"] is False
        and profile["independent_quality_accept"] is False
        and profile["english_master_authorized"] is False
        and profile["q25_authorized"] is False
        and profile["state_write_authorized"] is False,
        "Unreviewed new Writer source cannot authorize actual paid or quality ACCEPT")

    source=load_json(_local_bytes(root,ARTIFACT))
    _must(_sha(_local_bytes(root,ARTIFACT))==
          profile["source_story"]["artifact_sha256"]
          and source["schema"]=="lumi.v21.5-writer-source-candidate.v1"
          and source["status"]=="FROZEN" and source["immutable"] is True
          and source["model_generated"] is False
          and source["semantic_quality_accepted"] is False
          and source["repaired_story_path"]==
              "evidence/story_harness_p47/offline-full-story-route-truth-revision.txt"
          and source["repaired_story_text_sha256"]==STORY_SHA
          and source["artifact_id"]==profile["source_story"]["artifact_id"]
          and source["artifact_id"]=="story-writer-candidate:"+STORY_SHA
          and source["word_count"]==2491 and source["reader_age"]==12
          and source["approved_spine_hash"]==SPINE,
          "Real new Writer candidate artifact identity mismatched")

    prev=qualify_p47(repo_root=root,pinned_source_root=pinned)
    _must(prev["p47_candidate_story_sha256"]==STORY_SHA
          and prev["independent_semantic_quality_accept"] is False
          and prev["new_model_quality_calls"]==0,
          "P4.8 cannot promote a predecessor's synthetic or old story receipt")

    selection=load_json(_local_bytes(root,SELECTION))
    _must(_sha(_local_bytes(root,SELECTION))==profile["selection_sha256"]
          and selection["scene_scope"]["start_span_id"]=="S167"
          and selection["scene_scope"]["end_span_id"]=="S203"
          and selection["scene_scope"]["spine_beat_key"]=="escape_climb"
          and selection["approved_spine_hash"]==SPINE,
          "Scene constraint scope incorrectly bound to old segments")

    derived=load_json(_local_bytes(root,CONSTRAINTS))
    _must(_sha(_local_bytes(root,CONSTRAINTS))==
          profile["candidate_constraints_sha256"]
          and derived["scene_scope"]==selection["scene_scope"]
          and derived["approved_spine_hash"]==SPINE
          and derived["context_fingerprint"]==profile["context_fingerprint"]
          and derived["approval_file_sha256"]==profile["approval_sha256"]
          and derived["derivation"]=="EXACT_APPROVED_FIELD_PROJECTION_NOT_SEMANTIC_EXTRACTION",
          "Constraint projection hash/context mismatch")
    approval=pinned/profile["approved_spine_approval_path"]
    _must(approval.is_file()
          and _sha(approval.read_bytes())==profile["approval_sha256"],
          "Original human-approved Spine source changed")

    paragraphs=source["repaired_segments"]
    _must(len(paragraphs)==228
          and [row["span_id"] for row in paragraphs]==[
              f"S{i:03d}" for i in range(1,229)]
          and all(row["disposition"]=="UNCHANGED"
                  and row["source_text"]==row["repaired_text"]
                  for row in paragraphs),
          "P4.8 segment IDs/canon were fabricated")
    story=(root/source["repaired_story_path"]).read_text().rstrip("\n")
    _must(_sha(story.encode())==STORY_SHA
          and story.count("The old explorers' knots showed the way.")==1
          and _sha((root/source["repaired_story_path"]).read_bytes())==
              source["repaired_story_file_sha256"],
          "Actual new manuscript bytes are not the source for the quality runner")
    cursor=0
    for row in paragraphs:
        part=row["repaired_text"]
        pos=story.find(part,cursor)
        _must(pos>=0 and not story[cursor:pos].strip(),
              "New Writer spans omit/misorder manuscript prose")
        cursor=pos+len(part)
    _must(not story[cursor:].strip(),
          "New Writer spans do not cover trailing prose")
    return profile,source,prev


def _run_original_callbacks(root,pinned,python):
    _must(_sha(_local_bytes(root,RUNNER))==RUNNER_SHA,
          "Offline new-story original-model-adapter callback runner changed")
    cmd=[python,str(root/RUNNER),"--repo-root",str(root),
         "--pinned-root",str(pinned)]
    env=os.environ.copy()
    for key in tuple(env):
        if any(secret in key.upper() for secret in ("KEY","TOKEN","SECRET","PASSWORD")):
            env.pop(key,None)
    try:
        process=subprocess.run(cmd,cwd=pinned,env=env,capture_output=True,
                               text=True,timeout=50,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise HarnessStop("Cannot run original frozen v21 adapter in fake mode") from exc
    _must(process.returncode==0 and len(process.stdout)<40000,
          "New source callbacks not qualified: "+
              process.stderr[-270:].replace("\n"," "))
    try:
        result=json.loads(process.stdout)
    except ValueError as exc:
        raise HarnessStop("P4.8 original fake callback returned non-JSON") from exc
    return result


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable):
    root=Path(repo_root).resolve(strict=True)
    pinned=Path(pinned_source_root).resolve(strict=True)
    profile,writer,prev=_source_profile(root,pinned)
    cases=_run_original_callbacks(root,pinned,python_executable)
    _must(cases["source_story_sha256"]==STORY_SHA
          and cases["source_story_artifact_id"]==writer["artifact_id"]
          and cases["original_v21_4_profile_verified"] is True
          and cases["new_profile_is_purely_offline_provisional"] is True
          and cases["real_paid_dispatch_possible"] is False
          and cases["real_provider_calls"]==0
          and cases["provider_cost_usd"]=="0"
          and cases["independent_story_quality_accepted"] is False,
          "Fake callback proof falsely promoted to paid execution or real quality")
    actual=cases["synthetic_scenarios"]
    _must(len(actual)==5 and set(x["scenario"] for x in actual)==set(CALL_CASES),
          "P4.8 fake callback scenarios missing")
    details=[]
    for x in actual:
        _must((x["runtime_status"],x["stage_attempts"])==
              CALL_CASES[x["scenario"]]
              and x["model_call_records"]==x["stage_attempts"]
              and x["scene_repair_count"] in (0,1)
              and x["real_provider_calls"]==0
              and x["real_cost_usd"]=="0"
              and x["synthetic_quality_accept_is_real"] is False
              and x["english_master_allowed"] is False
              and x["q25_allowed"] is False,
              "Fake v21 model callback accepted as real/new-story quality")
        details.append({
           "scenario":x["scenario"],"runtime_status":x["runtime_status"],
           "fake_adapter_attempts":x["stage_attempts"],
           "real_provider_calls":0,"is_real_quality_accept":False
        })
    return {
      "schema":SCHEMA,
      "writer_source_story_sha256":STORY_SHA,
      "writer_artifact_id":writer["artifact_id"],
      "actual_english_story_words":writer["word_count"],
      "new_writer_segment_count":228,
      "original_spine_hash":SPINE,
      "approved_human_spine_binding_preserved":True,
      "old_frozen_v21_4_story_sha256":OLD_STORY_SHA,
      "old_paid_model_profile_reused_for_new_story":False,
      "real_v21_4_code_and_adapters_executed_offline":True,
      "provisional_new_story_constraints":True,
      "new_scene_repair_scoped_spans":"S167-S203",
      "max_bounded_repair_spans":40,
      "actual_bridge_scene_spans":"S162-S206",
      "bridge_scene_exceeds_bounded_repair_scope":True,
      "strict_out_of_scope_repair_rejection_observed":True,
      "synthetic_adapter_scenarios":details,
      "synthetic_accept_is_not_real_quality_accepted":True,
      "independent_semantic_quality_accepted":False,
      "actual_new_paid_provider_calls":0,
      "actual_new_paid_cost_usd":"0",
      "user_quality_target_overrun_permitted":True,
      "proposed_total_usd":0.25,
      "finite_explicit_paid_authorization_issued":False,
      "provider_price_route_and_input_exposure_verified":False,
      "english_master_seal_emitted":False,
      "q25_admission_authorized":False,
      "canonical_state_commit_authorized":False,
      "stop_reason":"P48_OFFLINE_NEW_STORY_ADAPTER_BOUND_PAID_DISABLED",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    a=p.parse_args()
    root=Path(a.repo_root).resolve(strict=True)
    r=qualify(repo_root=root,pinned_source_root=a.pinned_source_root)
    if a.verify_report:
        _must(load_json(secure_artifact(root,a.verify_report))==r,
              "Frozen new-story bounded callback receipt changed")
    print(json.dumps(r,sort_keys=True,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()

