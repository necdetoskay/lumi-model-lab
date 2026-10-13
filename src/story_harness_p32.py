"""P3.2 English Master admission preflight for ONE real frozen island story.

Verifies P3.1 same-story history first; checks original pinned cycle-10
REAUDIT request and exact source routing policy, not a fabricated ACCEPT.
An unrelated ACCEPT, a qualified audit, or a repair artifact cannot grant
the English Master seal / Q25 authority. No model or production operations.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

from src.story_harness_p31 import (
    qualify as qualify_quality,
    WRITER_SHA,
    REPAIR_RUNS,
)
from src.story_harness_p30 import EXPECTED_ARTIFACT_ID
from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA="lumi.story-harness-p32-english-master-admission.v1"
SOURCES="configs/story_harness_p32_english_master_admission.json"
SOURCES_SHA256="97be8a57dcdf9dbf1c944c97284b89faf3dfdf6648d3e24ffc9e4c9421f99b54"
REASON="ENGLISH_MASTER_NOT_ADMISSIBLE"
C10=10
_ALLOWED_PREFIXES=("evidence/spineforge-v20",)
_MASTER_FILE_MARKERS=("english-master","english_master","master-seal","master_seal")
_REQUIRED_SOURCE_ROWS={"terminal_quality_candidate":
                       {"cycle","story_product","story_text","reaudit_handoff","next_state"},
                       "historical_policy_sources":
                       {"quality_loop_runtime","quality_loop_contract"}}


def _must(yes,why):
    if not yes:raise HarnessStop(why)


def _inventory(base,override=None):
    raw=secure_artifact(base,SOURCES)
    _must(digest(raw)==SOURCES_SHA256,"P3.2 source inventory digest changed")
    obj=load_json(raw)
    _must(obj==override if override is not None else True,
          "P3.2 pinned source inventory changed by caller")
    _must(obj["schema"]=="lumi.story-harness-p32-english-master-admission-sources.v1"
          and obj["source_commit"]==PINNED_SOURCE_COMMIT
          and obj["source_cohort_prefix"]=="evidence/spineforge-v20",
          "P3.2 schema, Git or cohort identity changed")
    _must(set(obj)=={
        "schema","source_commit","source_cohort_prefix",
        "terminal_quality_candidate","historical_policy_sources",
        "cross_story_counterexample","admissible_accepted_reaudit_artifacts",
        "admissible_english_master_seals","admissible_q25_sources",
    },"P3.2 inventory structural source violation")
    for key,fields in _REQUIRED_SOURCE_ROWS.items():
        _must(set(obj[key])==fields,"Missing or extra P3.2 immutable source role")
    _must(obj["terminal_quality_candidate"]["cycle"]==C10,
          "Unexpected terminal repair cycle")
    for key in ("admissible_accepted_reaudit_artifacts",
                "admissible_english_master_seals","admissible_q25_sources"):
        _must(obj[key]==[], "Unverified same-story ACCEPT/English Master/Q25 registry was inserted")
    return obj


def _pinned_bytes(root, row, *, expected=None, roots=("evidence/", "src/")):
    _must(isinstance(row,dict) and set(row)=={"path","sha256"},
          "Invalid frozen artifact/source role")
    path=row["path"]
    _must(isinstance(path,str) and any(path.startswith(p) for p in roots)
          and not Path(path).is_absolute() and ".." not in Path(path).parts
          and "\\" not in path and Path(path).suffix in {".json",".py",".txt"},
          "Invalid source artifact path")
    if expected is not None:
        _must(path==expected,"Original English Master source role substituted")
    current=root
    for part in Path(path).parts:
        current=current/part
        _must(not current.is_symlink(),"Historical evidence path used symlink")
    _must(current.is_file() and current.resolve().is_relative_to(root)
          and current.stat().st_size < 220000,
          "Missing/oversized historical source")
    raw=current.read_bytes()
    _must(digest(raw)==row["sha256"], "Source or historical story bytes differ")
    return raw


def _tracked_scope(root:Path,commit:str,prefix:str):
    """Git object-tree path inventory of exact immutable commit, not filesystem scan."""
    args=["git","ls-tree","-r","--name-only",commit,"--","evidence"]
    env={"PATH":os.defpath,"HOME":"/nonexistent",
         "GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":"/dev/null"}
    try:
        result=subprocess.run(args,cwd=root,env=env,
                              text=True,capture_output=True,timeout=10,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise HarnessStop("Could not inspect pinned Git tree") from exc
    _must(result.returncode==0 and len(result.stdout)<200000
          and not result.stderr,"Frozen Git object tree unavailable")
    paths=[row for row in result.stdout.splitlines() if row.startswith(prefix)]
    _must(100 <= len(paths) <= 1000 and len(paths)==len(set(paths)),
          "Pinned island evidence tree not in approved bounded cohort")
    _must(all(p.startswith(prefix) for p in paths),
          "Git tree escaped original island experiment scope")
    return paths


def _policy_dict(node):
    if not isinstance(node,ast.Dict):return None
    out={}
    for key,value in zip(node.keys,node.values):
        if not isinstance(key,ast.Constant) or not isinstance(key.value,str):return None
        if not isinstance(value,ast.Constant):continue
        out[key.value]=value.value
    return out


def _inspect_original_quality_accept_branch(python_source):
    """Read exact original AST: decision == ACCEPT is policy, not an observed decision."""
    root=ast.parse(python_source.decode("utf-8"))
    found=[]
    for node in ast.walk(root):
        if not isinstance(node,ast.If):continue
        test=node.test
        if (not isinstance(test,ast.Compare) or
            not isinstance(test.left,ast.Name) or test.left.id!="decision" or
            len(test.ops)!=1 or not isinstance(test.ops[0],ast.Eq) or
            len(test.comparators)!=1 or not isinstance(test.comparators[0],ast.Constant)):
            continue
        branch=test.comparators[0].value
        for assign in node.body:
            if isinstance(assign,ast.Assign) and len(assign.targets)==1 and (
                isinstance(assign.targets[0],ast.Name) and
                assign.targets[0].id=="next_state"
            ):
                fields=_policy_dict(assign.value)
                if fields is not None:found.append((branch,fields))
    allowed=[record for name,record in found if name=="ACCEPT"]
    repair=[record for name,record in found if name=="LOCAL_REPAIR_REQUIRED"]
    _must(len(allowed)==1 and len(repair)==1,
          "Pinned historical quality-loop routing branches not found")
    a,r=allowed[0],repair[0]
    _must(a.get("status")=="QUALITY_LOOP_ACCEPTED" and
          a.get("current_action")=="ENGLISH_MASTER_SEAL" and
          a.get("paid_execution_authorized") is False and
          a.get("automatic_paid_transition_enabled") is False and
          r.get("current_action")=="LOCAL_REPAIR" and
          r.get("paid_execution_authorized") is False,
          "Historical English Master policy routing changed")
    return {"policy_has_accept_branch":True,
            "policy_accept_route":"ENGLISH_MASTER_SEAL",
            "accept_branch_is_actual_history":False,
            "policy_automatic_paid_transition_authorized":False}


def _terminal_candidate(source,roles,history):
    root=f"evidence/spineforge-v20-paid-writer/{REPAIR_RUNS[C10]}"
    product_path=root+"/age12-island-v20-story-quality-repair-c10-product.json"
    story_path=root+"/age12-island-v20-story-quality-repair-c10-story.txt"
    handoff_path=root+"/age12-island-v20-story-quality-repair-c10-next-handoff.json"
    state_path=root+"/story-quality-loop-next-state.json"
    product=load_json(_pinned_bytes(source,roles["story_product"],expected=product_path))
    raw=_pinned_bytes(source,roles["story_text"],expected=story_path)
    handoff=load_json(_pinned_bytes(source,roles["reaudit_handoff"],expected=handoff_path))
    state=load_json(_pinned_bytes(source,roles["next_state"],expected=state_path))
    last=history["repair_reaudit_cycles"][-1]
    _must(product["repair_cycle_index"]==C10 and
          product["status"]=="FROZEN" and product["immutable"] is True
          and product["artifact_id"]==last["repaired_story_artifact_id"] and
          product["repaired_story_text_sha256"]==last["repaired_story_sha256"] and
          product["repaired_story_path"]==story_path and
          product["repaired_story_file_sha256"]==roles["story_text"]["sha256"] and
          digest(raw.rstrip(b"\n"))==product["repaired_story_text_sha256"],
          "Cycle10 story text, product or prior P3.1 accepted history was replaced")
    _must(handoff["schema"]=="spineforge-v20-story-quality-reaudit-handoff.v1"
          and handoff["cycle_index"]==C10 and handoff["stage"]==25
          and handoff["status"]=="READY_NOT_AUTHORIZED"
          and handoff["immutable"] is True
          and handoff["paid_execution_authorized"] is False
          and handoff["source_story_artifact_id"]==product["artifact_id"]
          and handoff["source_story_artifact_path"]==product_path
          and handoff["source_story_artifact_sha256"]==roles["story_product"]["sha256"]
          and handoff["repaired_story_path"]==story_path
          and handoff["repaired_story_text_sha256"]==product["repaired_story_text_sha256"]
          and handoff["repaired_story_file_sha256"]==roles["story_text"]["sha256"]
          and handoff["next_stage_on_accept"]=="ENGLISH_MASTER_SEAL"
          and handoff["next_stage_on_local_repair"]=="STORY_LOCAL_REPAIR"
          and handoff["next_stage_on_structural_or_replan"]=="STOP",
          "Cycle10 re-audit input or future ACCEPT policy was promoted")
    pol=handoff["reaudit_policy"]
    _must(pol["full_story_required"] is True and
          pol["all_199_stable_spans_required"] is True and
          pol["automatic_retry_enabled"] is False and
          pol["automatic_repair_loop_enabled"] is False and
          pol["translation_forbidden"] is True and
          pol["state_commit_forbidden"] is True,
          "Cycle10 immutable full-story review constraints were relaxed")
    _must(state["schema"]=="spineforge-v20-story-quality-loop-next-state.v1"
          and state["status"]=="NEXT_ACTION_READY_NOT_AUTHORIZED"
          and state["current_action"]=="REAUDIT"
          and state["current_stage"]==25
          and state["cycle_index"]==C10
          and state["source_story_artifact_id"]==product["artifact_id"]
          and state["source_story_artifact_path"]==product_path
          and state["source_story_artifact_sha256"]==roles["story_product"]["sha256"]
          and state["handoff_artifact_id"]==handoff["artifact_id"]
          and state["handoff_path"]==handoff_path
          and state["handoff_sha256"]==roles["reaudit_handoff"]["sha256"]
          and state["paid_execution_authorized"] is False
          and state["automatic_paid_transition_enabled"] is False,
          "Cycle10 NextState was treated as sealed or already accepted")
    return {"candidate_source_story_sha256":product["repaired_story_text_sha256"],
            "candidate_repair_product_sha256":roles["story_product"]["sha256"],
            "candidate_artifact_id":product["artifact_id"],
            "candidate_handoff_sha256":roles["reaudit_handoff"]["sha256"],
            "last_qualified_cycle":history["last_completed_reaudit_cycle"],
            "next_state_action":state["current_action"],
            "next_state_status":state["status"],
            "on_accept_policy_route":handoff["next_stage_on_accept"],
            "cycle10_paid_reaudit_authorized":handoff["paid_execution_authorized"]}


def _cross_story(source,row,history,terminal):
    accepted=load_json(_pinned_bytes(
        source,row,
        expected="evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-06-20261005/result.json"))
    _must(accepted["status"]=="ACCEPT" and
          accepted["accepted_story_sha256"] not in (
              terminal["candidate_source_story_sha256"],WRITER_SHA),
          "Cross-story Lighthouse cannot be treated as the island English Master")
    return {"counterexample_status":accepted["status"],
            "counterexample_origin":"lighthouse-patch-campaign",
            "counterexample_sha256":accepted["accepted_story_sha256"],
            "accepted_as_island_english_master":False}


def _admission_prerequisite_contract(history, terminal, seals, accepted):
    """A future authorized vN can add an entirely new verified seal manifest.

    P3.2 deliberately forbids enrollment on this historical source commit:
    receipts and stage-success labels cannot override the missing quality gate.
    """
    _must(history["original_story_quality_accepted"] is False
          and history["last_verified_story_audit_decision"]=="LOCAL_REPAIR_REQUIRED"
          and history["unreviewed_cycle10_story_pending_reaudit"] is True
          and history["last_completed_reaudit_cycle"]==9
          and terminal["next_state_action"]=="REAUDIT"
          and accepted==[] and seals==[],
          "P3.2 frozen cohort cannot be promoted to an accepted English Master")
    return {
       "same_story_lineage_proven":True,
       "original_completed_story_quality_ACCEPT":False,
       "cycle10_completed_reaudit_proven":False,
       "latest_accepted_story_sha256_proven":False,
       "registered_exact_same_story_english_master_seal":False,
       "quality_model_gate_reexecuted":False,
       "english_master_admission_authorized":False,
    }


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable,override_inventory=None):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    manifest=_inventory(base,override=override_inventory)
    history=qualify_quality(repo_root=base,pinned_source_root=source,
                            python_executable=python_executable)
    _must(history["state"]=="STOPPED_UNACCEPTED_STORY"
          and history["stop_reason"]=="STORY_QUALITY_NOT_ACCEPTED"
          and history["provider_calls"]==0
          and history["full_cycle3_to_cycle10_lineage_ids_and_hashes_verified"] is True,
          "Source story quality chain did not qualify")
    paths=_tracked_scope(source,PINNED_SOURCE_COMMIT,manifest["source_cohort_prefix"])
    master_named=[p for p in paths if any(marker in p.lower() for marker in _MASTER_FILE_MARKERS)]
    _must(master_named==[], "Unexpected unqualified English Master file in historical cohort")
    runtime=_pinned_bytes(
        source,manifest["historical_policy_sources"]["quality_loop_runtime"],
        expected="src/spineforge_v20_paid_story_quality_loop_once.py")
    quality_code=_pinned_bytes(
        source,manifest["historical_policy_sources"]["quality_loop_contract"],
        expected="src/spineforge_v20_story_quality_loop.py")
    ast.parse(quality_code.decode("utf-8"))
    policy=_inspect_original_quality_accept_branch(runtime)
    terminal=_terminal_candidate(source,manifest["terminal_quality_candidate"],history)
    cross=_cross_story(source,manifest["cross_story_counterexample"],history,terminal)
    requirements=_admission_prerequisite_contract(history,terminal,
                   manifest["admissible_english_master_seals"],
                   manifest["admissible_accepted_reaudit_artifacts"])
    return {
      "schema":SCHEMA,
      "mode":"OFFLINE_FROZEN_ENGLISH_MASTER_ADMISSION_PREFLIGHT",
      "source_commit":PINNED_SOURCE_COMMIT,
      "cohort_manifest_sha256":SOURCES_SHA256,
      "p31_qualified_quality_receipt_sha256":digest(canonical_bytes(history)),
      "historical_island_tracked_source_file_count":len(paths),
      "historical_english_master_named_files":master_named,
      "historical_english_master_artifact_found":False,
      "historical_quality_accept_receipt_found":False,
      "historical_runtime_source_ast_checked":True,
      "historical_policy":policy,
      "terminal_candidate":terminal,
      "unrelated_accepted_story_reference":cross,
      "required_admission_checks":requirements,
      "original_english_master_seal_registered":False,
      "q25_source_registered":False,
      "admitted_english_master_story_sha256":None,
      "final_english_master_artifact_id":None,
      "stop_reason":REASON,
      "state":"STOPPED_UNSEALED_UNACCEPTED_STORY",
      "english_master_seal_execution_authorized":False,
      "english_master_story_accepted":False,
      "q25_extraction_authorized":False,
      "final_story_state_authorized":False,
      "state_commit_authorized":False,
      "production_write_performed":False,
      "provider_calls":0,"provider_cost_usd":"0",
    }


def verify_report(report,*,repo_root,pinned_source_root,python_executable=sys.executable):
    computed=qualify(repo_root=repo_root,pinned_source_root=pinned_source_root,
                    python_executable=python_executable)
    _must(report==computed,"Stored English Master receipt was edited/forged")
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    args=p.parse_args()
    base=Path(args.repo_root).resolve(strict=True)
    outcome=qualify(repo_root=base,pinned_source_root=args.pinned_source_root)
    if args.verify_report:
        _must(load_json(secure_artifact(base,args.verify_report))==outcome,
              "Stored English Master receipt is not fresh evidence")
    print(json.dumps(outcome,indent=2,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()

