"""P4.6: deterministic full-manuscript authorial revision (not v21 repair/ACCEPT).

Replays four exact editorial phrase substitutions on immutable P4.5 English
candidate and compares entire resulting bytes with its newly frozen artifact.
No provider, no implicit quality acceptance, no Q25/StoryState.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.story_harness_v1 import HarnessStop,secure_artifact,load_json

SCHEMA="lumi.story-harness-p46-writer-revision-proof.v1"
MANIFEST="configs/story_harness_p46_full_story_editorial.json"
MANIFEST_SHA="a4780fc32f8c0020c13e7ab6a3a85c6e3153d70acedfa75e55073155b4b37aa5"
RECEIPT="evidence/story_harness_p46/writer-revision-proof.json"
SOURCE_REVIEW="evidence/story_harness_p45/pinned-editorial-rewrite-receipt.json"
P45_SOURCE_COMMIT="ad9c2316e80ddd68bcd2b9ab21dd3c3b2728a140"
SCOPE=("GLIDER_TETHERS","TURNAROUND_CAMP","JOURNAL_URGENCY","TURNAROUND_BEAT")


def check(ok,message):
    if not ok:
        raise HarnessStop(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _bytes(root,relative):
    check(isinstance(relative,str)
          and (relative.startswith("evidence/story_harness_p45/")
               or relative.startswith("evidence/story_harness_p46/"))
          and not Path(relative).is_absolute() and ".." not in Path(relative).parts,
          "Invalid source story path")
    p=root
    for part in Path(relative).parts:
        p=p/part
        check(not p.is_symlink(),"Symlink source or editorial file rejected")
    check(p.is_file() and p.resolve().is_relative_to(root)
          and p.stat().st_size<=30000,
          "Missing or oversized editorial story")
    return p.read_bytes()


def review(*,repo_root):
    root=Path(repo_root).resolve(strict=True)
    manifest_data=secure_artifact(root,MANIFEST)
    check(sha(manifest_data)==MANIFEST_SHA,"P4.6 immutable editorial contract changed")
    m=json.loads(manifest_data)
    check(m["schema"]=="lumi.p46-authored-writer-revision.v1"
          and m["source_git_commit"]==P45_SOURCE_COMMIT
          and m["editorial_origin"]=="OFFLINE_ASSISTANT_AUTHORED_WRITER_REVISION_NOT_MODEL_GENERATED"
          and m["approved_spine_hash"]=="f9c5bed93448d6c56787466ae583dfcee06d0f856641d9c3901136f142bffae6"
          and m["quality_decision"]=="UNREVIEWED"
          and m["independent_semantic_quality_accept"] is False
          and m["english_master_seal_allowed"] is False
          and m["q25_allowed"] is False
          and m["state_commit_allowed"] is False
          and m["real_provider_calls"]==0 and m["new_v21_repair_calls"]==0
          and m["cost_usd"]=="0"
          and m["paid_budget_override"]==
             "USER_PERMITTED_0_10_TARGET_OVERRUN_ONLY_NOT_0_25_DISPATCH_GRANT",
          "Unreviewed authorial revision granted execution or quality authority")
    p45=load_json(secure_artifact(root,SOURCE_REVIEW))
    check(p45["status"]=="EDITORIAL_TEXT_CREATED_BUT_UNREVIEWED"
          and p45["real_provider_quality_accept"] is False
          and p45["source_story_sha256"] != m["new_story_content_sha256"]
          and p45["new_full_story_file_sha256"]==m["parent_story_file_sha256"],
          "Parent frozen P4.5 story/provenance swapped")

    parent_bytes=_bytes(root,m["parent_story_relpath"])
    actual_bytes=_bytes(root,m["new_story_relpath"])
    check(sha(parent_bytes)==m["parent_story_file_sha256"]
          and sha(parent_bytes.rstrip(b"\n"))==m["parent_story_content_sha256"]
          and sha(actual_bytes)==m["new_story_file_sha256"]
          and sha(actual_bytes.rstrip(b"\n"))==m["new_story_content_sha256"],
          "P4.6 writer input or output SHA mismatched")
    old=parent_bytes.decode("utf8")
    result=old
    changes=m["editorial_changes"]
    check([x["id"] for x in changes]==list(SCOPE)
          and len(changes)==4,
          "Unexpected writer revision scope")
    applied=[]
    for change in changes:
        source=change["old_text"]
        replacement=change["new_text"]
        check(isinstance(source,str) and isinstance(replacement,str)
              and len(source)>=48 and len(replacement)>=35
              and result.count(source)==1
              and old.index(source)==change["source_offset"]
              and sha(source.encode())==change["old_sha256"]
              and sha(replacement.encode())==change["new_sha256"]
              and source!=replacement,
              "Unpinned extra writer event or changed source fragment")
        result=result.replace(source,replacement,1)
        applied.append({"id":change["id"],
                        "old_text_sha256":change["old_sha256"],
                        "new_text_sha256":change["new_sha256"]})
    check(result.encode("utf8")==actual_bytes,
          "Full authorial revised English manuscript did not match exact replay")
    scene=_bytes(root,m["retained_bridge_scene"]).decode("utf8").strip()
    check(sha(scene.encode())==m["retained_bridge_scene_sha256"]
          and old.count(scene)==1 and result.count(scene)==1,
          "Frozen repaired bridge sequence modified")
    check(len(result.split())==m["new_story_word_count"]==2482
          and len(old.split())==m["original_story_word_count"]==2494,
          "P4.6 reader age manuscript-length bound changed")
    check("both gliders' landing tethers to separate living roots" in result
          and result.index("landing tethers")<result.index("Only when they held did Arda free")
          and "They turned toward the shore." in result
          and "Our signal" in result and "He stopped at the final page" in result
          and "Behind them, the island went into the wall" in result,
          "Critical glider anchor, turnaround, discovery or closing beat was lost")
    return {
      "schema":SCHEMA,
      "status":"UNREVIEWED_AUTHORIAL_FULL_STORY_REVISION",
      "parent_p45_full_story_sha256":m["parent_story_content_sha256"],
      "revised_story_sha256":m["new_story_content_sha256"],
      "revised_story_words":m["new_story_word_count"],
      "source_authority":"OFFLINE_ASSISTANT_EDITORIAL_ONLY",
      "retained_p45_bridge_scene_sha256":m["retained_bridge_scene_sha256"],
      "editorial_changes_verified":applied,
      "other_source_content_unchanged":True,
      "independent_semantic_quality_accept":False,
      "new_model_quality_review_performed":False,
      "new_v21_repair_calls":0,
      "english_master_seal_issued":False,
      "q25_source_admitted":False,
      "story_state_commit_authorized":False,
      "paid_execution_authorized":False,
      "provider_calls":0,
      "provider_cost_usd":"0",
      "stop_reason":"FULL_STORY_REVISION_AWAITS_INDEPENDENT_QUALITY_AUDIT",
    }


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--repo-root",default=".")
    a.add_argument("--verify-receipt")
    opt=a.parse_args()
    root=Path(opt.repo_root).resolve(strict=True)
    data=review(repo_root=root)
    if opt.verify_receipt:
        check(load_json(secure_artifact(root,opt.verify_receipt))==data,
              "Stored P4.6 offline receipt does not equal canonical source replay")
    print(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True))


if __name__=="__main__":
    main()

