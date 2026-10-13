"""P4.5: actually rewrite source-island bridge scene offline, preserving v21 spine.

This is an authorial EDITORIAL candidate, NOT a model output, accepted English
Master, semantic reviewer approval, or paid execution authorization. Original
v21 apply_scene_rewrite and targeted audit payload code are invoked unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_p22 import _python_runtime_env
from src.story_harness_p44 import qualify as qualify_story_forensic
from src.story_harness_v1 import HarnessStop,canonical_bytes,digest,load_json,secure_artifact

SCHEMA="lumi.story-harness-p45-offline-scene-editorial-candidate.v1"
MANIFEST="configs/story_harness_p45_editorial_bridge_candidate.json"
MANIFEST_SHA="ffa70bcd765ab9e64fe391982f19574a6b76c32fd04288bbf013f47c78a4786f"
SCENE="evidence/story_harness_p45/offline-editorial-bridge-scene.txt"
FULL_STORY="evidence/story_harness_p45/offline-editorial-full-story.txt"
REQUIRED_IDS=("BANK-001","SWING-002","CROSS-003",
              "LOAD-004","TRUST-005","LOSS-006")
PINNED_WRITER="evidence/spineforge-v20-paid-writer/37204419845/"
PINNED_PAID="evidence/spineforge-v21-paid-quality/37230896244/v21-bounded-quality-result.json"
_SCRIPT=r"""
import hashlib,json,os,socket,sys
from pathlib import Path
def block(*a,**kw):raise RuntimeError("P4.5 cannot call a provider")
socket.create_connection=block
socket.socket.connect=block
socket.socket.connect_ex=block
from src.spineforge_v21_freeze import verify_v21_runtime
from src.spineforge_v21_bounded_quality import apply_scene_rewrite
from src.spineforge_v21_quality_runtime import build_targeted_final_audit_payload
freeze=verify_v21_runtime()
root=Path.cwd()
story=(root/sys.argv[1]).read_text().rstrip("\n")
product=json.loads((root/sys.argv[2]).read_text())
paid=json.loads((root/sys.argv[3]).read_text())
replacement=Path(sys.argv[4]).read_text().strip()
handoff=paid["quality_calls"][1]["input"]
rewrite=apply_scene_rewrite(source_story=story,
   story_segments=product["repaired_segments"],
   cluster=handoff["scene_cluster"],replacement_scene=replacement)
targeted=build_targeted_final_audit_payload(
   repaired_story_sha256=rewrite["repaired_story_sha256"],
   replacement_scene=replacement,scene_repair_handoff=handoff,
   approved_spine_hash=handoff["approved_spine_hash"],
   canon_invariants=handoff["canon_invariants"])
assert "full_story" not in targeted and "story_segments" not in targeted
assert targeted["routing_policy"]["full_story_reaudit_forbidden"] is True
assert targeted["routing_policy"]["another_repair_forbidden"] is True
assert targeted["entry_boundary"]["span_id"]=="S158"
assert targeted["exit_boundary"]["span_id"]=="S178"
assert targeted["replacement_scene"]==replacement
story=rewrite["repaired_story"]
prefix=story[:rewrite["source_char_start"]]
suffix=story[rewrite["source_char_start"]+len(replacement):]
assert hashlib.sha256(prefix.encode()).hexdigest()==rewrite["prefix_sha256"]
assert hashlib.sha256(suffix.encode()).hexdigest()==rewrite["suffix_sha256"]
assert rewrite["source_char_start"]==9993 and rewrite["source_char_end"]==11495
assert paid["status"]=="REJECT_PROVIDER_FAILURE"
print(json.dumps({
 "runtime_revision":freeze["runtime_revision"],
 "source_story_sha256":rewrite["source_story_sha256"],
 "source_cluster_sha256":rewrite["source_cluster_sha256"],
 "source_char_start":rewrite["source_char_start"],
 "source_char_end":rewrite["source_char_end"],
 "source_span_count":rewrite["source_span_count"],
 "new_span_count":rewrite["repaired_span_count"],
 "candidate_full_story_sha256":rewrite["repaired_story_sha256"],
 "candidate_full_story_word_count":len(story.split()),
 "replacement_scene_sha256":rewrite["replacement_scene_sha256"],
 "replacement_scene_word_count":len(replacement.split()),
 "outside_cluster_unchanged":rewrite["outside_cluster_unchanged"],
 "original_mutated":rewrite["source_mutated"],
 "targeted_final_audit_payload_schema":targeted["schema"],
 "targeted_final_audit_scope":targeted["routing_policy"]["scope"],
 "full_story_reaudit_forbidden":targeted["routing_policy"]["full_story_reaudit_forbidden"],
 "another_repair_forbidden":targeted["routing_policy"]["another_repair_forbidden"],
 "entry_boundary_span_id":targeted["entry_boundary"]["span_id"],
 "exit_boundary_span_id":targeted["exit_boundary"]["span_id"],
 "original_quality_status":paid["status"],
 "actual_new_provider_quality_calls":0,
 "real_quality_accepted":False,
 },sort_keys=True))
"""


def _must(ok, reason):
    if not ok: raise HarnessStop(reason)


def _manifest(repo_root):
    raw=secure_artifact(repo_root,MANIFEST)
    _must(digest(raw)==MANIFEST_SHA,"P4.5 editorial source manifest changed")
    m=load_json(raw)
    _must(m["schema"]=="lumi.story-harness-p45-offline-editorial-rewrite.v1"
          and m["source_commit"]==PINNED_SOURCE_COMMIT
          and m["historical_real_quality_status"]=="REJECT_PROVIDER_FAILURE",
          "P4.5 wrong source or story quality")
    _must(m["source_span_start"]=="S159" and m["source_span_end"]=="S177"
          and m["entry_boundary_span_id"]=="S158"
          and m["exit_boundary_span_id"]=="S178"
          and m["targeted_final_audit_scope"]=="REPAIRED_SCENE_PLUS_BOUNDARIES"
          and m["full_story_final_reaudit_forbidden"] is True,
          "P4.5 scene bounds or audit scope were widened")
    for key in ("independent_quality_accept","paid_quality_authorized",
                "english_master_seal_issued","q25_extraction_allowed",
                "canonical_state_write_allowed"):
        _must(m[key] is False,"P4.5 manual scene promoted to production accepted quality")
    _must(m["actual_model_review_calls"]==0
          and m["max_future_quality_calls"]==3
          and m["max_future_scene_repairs"]==1
          and m["editorial_authority"]=="OFFLINE_ASSISTANT_EDITORIAL_DRAFT_UNREVIEWED"
          and m["forbidden_promotion"]==
            "SYNTHETIC_OR_UNREVIEWED_CANDIDATE_CANNOT_BE_ENGLISH_MASTER",
          "P4.5 editor claimed an unsupported real semantic signoff")
    _must([r["id"] for r in m["brief_structural_obligations"]]==list(REQUIRED_IDS),
          "Missing documented physical/spatial obligations")
    return m


def _fixed_text_artifact(root,relative,expected_file_sha):
    _must(isinstance(relative,str) and relative.startswith("evidence/story_harness_p45/")
          and ".." not in Path(relative).parts and not Path(relative).is_absolute(),
          "Unsafe local editorial text artifact path")
    p=root
    for part in Path(relative).parts:
        p=p/part
        _must(not p.is_symlink(),"Symlink editorial text forbidden")
    _must(p.is_file() and p.resolve().is_relative_to(root)
          and p.stat().st_size<=30000,"Editorial candidate file missing or oversized")
    data=p.read_bytes()
    _must(digest(data)==expected_file_sha,"Editorial candidate file SHA mismatched")
    return data


def _bytes_at_source(source,relative,expected_sha):
    _must(relative.startswith("evidence/") and ".." not in Path(relative).parts
          and not Path(relative).is_absolute(),
          "Unsafe original frozen source path")
    target=source
    for part in Path(relative).parts:
        target=target/part
        _must(not target.is_symlink(),"Symlink source unavailable")
    _must(target.is_file() and target.resolve().is_relative_to(source)
          and digest(target.read_bytes())==expected_sha,
          "Original island story/spine/paid source changed")
    return target.read_bytes()


def _validate_editorial_candidate(m,original,scene,full):
    _must(digest(scene.encode("utf8"))==m["editorial_scene_sha256"]
          and len(scene.split())==m["editorial_scene_words"]==370
          and digest(full.encode("utf8"))==m["complete_candidate_story_sha256"]
          and len(full.split())==m["complete_candidate_words"]==2494
          and m["original_story_word_count"]==2407
          and m["original_scene_word_count"]==283
          and len(full.split())<=2500,
          "P4.5 editorial bytes or approved word envelope changed")
    _must(scene.startswith("They ran to the root bridge")
          and scene.endswith('Arda tightened his grip. "Always."'),
          "S159–S177 replacement boundaries are missing")
    _must("glider-tag" in full and "expedition journal" in full
          and "stone gate" in full
          and "The Island That Wasn't on Any Map" in full,
          "Original character discovery/mystery/canon was dropped")
    _must("Arda and Nisa" not in scene,
          "P4.5 scene must use lived dialog instead of exposition labels")
    _must([row["id"] for row in m["brief_structural_obligations"]]==list(REQUIRED_IDS),
          "Not all six original scene causal obligations are present")
    positions=[]
    for row in m["brief_structural_obligations"]:
        values=row["evidence"]
        _must(len(row["comment"])>=45
              and all(isinstance(v,str) and 10<=len(v)<=125 for v in values),
              "Structural obligation markers are too weak")
        ix=[scene.find(v) for v in values]
        _must(all(x>=0 for x in ix) and ix==sorted(ix)
              and len(set(ix))==len(ix),
              "A rope/side/cut/trust causal step is missing or out of order")
        positions.append({"obligation_id":row["id"],
            "evidence_markers_in_order":len(ix),
            "mechanical_phrase_check_passed":True,
            "semantic_reviewer_accept_proven":False})
    ordered=["He tied one end","She ran three steps","Made it!", "tied it off",
             "Arda clipped his harness","The bridge shuddered",
             "root hooked the taut rope","Its gate jammed",
             "sliced the loaded stretch","The wrenching pull vanished",
             "She dropped flat, seized his wrist","held him at the rim"]
    offsets=[scene.find(x) for x in ordered]
    _must(all(i>=0 for i in offsets) and offsets==sorted(offsets),
          "Scene rope load path and character order contradictory")
    _must(original not in full and scene in full,
          "New candidate has not actually replaced the original broken scene")
    return positions


def _execute_original_v21(root,source,python):
    with TemporaryDirectory(prefix="lumi-p45-",) as tmp:
        env=_python_runtime_env(python,Path(tmp))
        env["TMPDIR"]=tmp
        args=[python,"-c",_SCRIPT,
              PINNED_WRITER+"age12-island-v20-story-quality-repair-c10-story.txt",
              PINNED_WRITER+"age12-island-v20-story-quality-repair-c10-product.json",
              PINNED_PAID,str((root/SCENE).resolve(strict=True))]
        try:
            p=subprocess.run(args,cwd=source,env=env,capture_output=True,
                         encoding="utf8",text=True,timeout=45,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise HarnessStop("Frozen real v21 scene-rewrite engine could not run") from exc
        _must(p.returncode==0 and len(p.stdout)<12000,
              "Original v21 refused editorial repair: "+p.stderr[-350:].replace("\n"," "))
        try:return json.loads(p.stdout)
        except ValueError as exc:
            raise HarnessStop("Real v21 source rewrite did not emit JSON") from exc


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable):
    root=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    m=_manifest(root)
    prev=qualify_story_forensic(repo_root=root,pinned_source_root=source,
                                python_executable=python_executable)
    _must(prev["stop_reason"]=="NOT_READY_FOR_REAL_BOUNDED_QUALITY_ATTEMPT"
          and prev["paid_execution_authorized"] is False,
          "P4.5 bypassed prior source story and budget guard")
    a=_bytes_at_source(source,PINNED_WRITER+"age12-island-v20-story-quality-repair-c10-story.txt",
                       m["source_story_file_sha256"]).decode()
    original=a.rstrip("\n")
    _bytes_at_source(source,PINNED_WRITER+"age12-island-v20-story-quality-repair-c10-product.json",
                     m["product_file_sha256"])
    _bytes_at_source(source,PINNED_PAID,m["historical_paid_result_file_sha256"])
    _must(digest(original.encode())==m["source_story_sha256"]
          and prev["original_story_sha256"]==m["source_story_sha256"]
          and prev["historical_failed_repair_scene_sha256"]!=m["editorial_scene_sha256"]
          and prev["manual_review_is_not_authenticated_model_accept"] is True,
          "Original story SHA, earlier reject, or editorial origin confused")
    scene_raw=_fixed_text_artifact(root,SCENE,m["editorial_scene_file_sha256"])
    _must(digest(scene_raw.rstrip(b"\n"))==m["editorial_scene_sha256"],
          "P4.5 editorial scene text SHA changed")
    scene=scene_raw.decode().strip()
    full_raw=_fixed_text_artifact(root,FULL_STORY,m["result_story_file_sha256"])
    _must(full_raw.endswith(b"\n"),
          "P4.5 full editorial artifact bytes changed")
    full=full_raw.decode().rstrip("\n")
    markers=_validate_editorial_candidate(m,original,scene,full)
    run=_execute_original_v21(root,source,python_executable)
    _must(run["runtime_revision"]=="SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and run["outside_cluster_unchanged"] is True
          and run["original_mutated"] is False
          and run["source_story_sha256"]==m["source_story_sha256"]
          and run["candidate_full_story_sha256"]==m["complete_candidate_story_sha256"]
          and run["replacement_scene_sha256"]==m["editorial_scene_sha256"]
          and run["candidate_full_story_word_count"]==2494
          and run["source_char_start"]==9993
          and run["source_char_end"]==11495
          and run["entry_boundary_span_id"]=="S158"
          and run["exit_boundary_span_id"]=="S178"
          and run["targeted_final_audit_scope"]=="REPAIRED_SCENE_PLUS_BOUNDARIES"
          and run["full_story_reaudit_forbidden"] is True
          and run["another_repair_forbidden"] is True
          and run["original_quality_status"]=="REJECT_PROVIDER_FAILURE"
          and run["real_quality_accepted"] is False
          and run["actual_new_provider_quality_calls"]==0,
          "Real v21 scene rewrite or targeted audit contract failed")
    return {
        "schema":SCHEMA,
        "status":"EDITORIAL_TEXT_CREATED_BUT_UNREVIEWED",
        "source_commit":PINNED_SOURCE_COMMIT,
        "source_manifest_sha256":MANIFEST_SHA,
        "prior_editorial_and_budget_denial_receipt_sha256":digest(canonical_bytes(prev)),
        "source_story_sha256":m["source_story_sha256"],
        "editorial_replacement_scene_sha256":m["editorial_scene_sha256"],
        "new_full_story_sha256":m["complete_candidate_story_sha256"],
        "new_full_story_file_sha256":m["result_story_file_sha256"],
        "new_full_story_words":2494,
        "replaced_original_spans":"S159–S177",
        "original_v21_rewrite_verified":True,
        "outside_cluster_unchanged":True,
        "entry_boundary_preserved":"S158",
        "exit_boundary_preserved":"S178",
        "mechanical_order_checks":markers,
        "mechanical_order_checks_are_not_semantic_quality_proof":True,
        "historical_paid_quality_status":"REJECT_PROVIDER_FAILURE",
        "real_independent_semantic_audit_passed":False,
        "real_provider_quality_accept":False,
        "english_master_seal_emitted":False,
        "q25_extraction_authorized":False,
        "story_state_commit_authorized":False,
        "real_paid_execution_authorized":False,
        "requested_one_attempt_budget_ceiling_usd":0.25,
        "budget_ceiling_is_only_a_proposal":True,
        "provider_calls":0,
        "provider_cost_usd":"0",
        "stop_reason":"EDITORIAL_REWRITE_READY_FOR_INDEPENDENT_QUALITY_REVIEW",
        "state":"STOPPED_BEFORE_REAL_QUALITY_AUDIT",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    a=p.parse_args()
    root=Path(a.repo_root).resolve(strict=True)
    report=qualify(repo_root=root,pinned_source_root=a.pinned_source_root)
    if a.verify_report:
        _must(load_json(secure_artifact(root,a.verify_report))==report,
              "P4.5 candidate receipt does not match immutable source")
    print(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False))


if __name__=="__main__":main()

