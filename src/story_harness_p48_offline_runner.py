"""P4.8 actual frozen v21.4 adapter callbacks, but NEW story; strictly fake provider.

Run from the immutable original v21.4 checkout as cwd. A TEMPORARY
source-aware profile is materialized from independently pinned P4.8
artifacts. Only simulation=True is allowed. The original frozen verifier
still validates original source; the new profile is not treated as part of
the original frozen v21.4 run or as approved for paid execution.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",required=True)
    p.add_argument("--pinned-root",required=True)
    a=p.parse_args()
    root=Path(a.repo_root).resolve(strict=True)
    pin=Path(a.pinned_root).resolve(strict=True)
    if Path.cwd().resolve(strict=True)!=pin:
        raise RuntimeError("P4.8 runner requires exact pinned v21.4 cwd")
    def no_network(*unused_args,**unused_kwargs):
        raise RuntimeError("OFFLINE_PROVIDER_NETWORK_FORBIDDEN")
    socket.create_connection=no_network
    socket.socket.connect=no_network
    socket.socket.connect_ex=no_network

    sys.path.insert(0,str(pin))
    from src.spineforge_v21_freeze import verify_v21_runtime
    from src.spineforge_v21_paid_quality_once import (
        execute_paid_quality_once,AUTHORIZATION_MARKER,_load_source_story)
    from src.spineforge_v21_model_adapter import (
        execute_initial_audit_call,execute_scene_repair_call,execute_final_audit_call)
    from src.spineforge_v21_constraints import load_constraints

    proof=json.loads((root/"configs/story_harness_p48_source_profile.json").read_text())
    source=json.loads((root/proof["source_story"]["artifact_path"]).read_text())
    old=json.loads((pin/"data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json").read_text())
    original_freeze=verify_v21_runtime()
    assert source["immutable"] and source["status"]=="FROZEN"
    assert source["repaired_story_text_sha256"]==proof["source_story"]["story_sha256"]
    assert old["source_story"]["story_sha256"]!=proof["source_story"]["story_sha256"]
    assert proof["real_provider_dispatch_allowed"] is False
    assert proof["candidate_scene_scope_review_status"]=="REMAP_OF_ORIGINAL_APPROVED_BEAT_NOT_HUMAN_REAPPROVED"
    result=[]
    for name in ("clean_synthetic","one_repair_synthetic","provider_transport_failure",
                 "missing_usage","out_of_bounded_scope"):
        with TemporaryDirectory(prefix="p48-fake-source-") as tmp:
            t=Path(tmp)
            new_artifact=copy.deepcopy(source)
            new_artifact["repaired_story_path"]=str((root/source["repaired_story_path"]).resolve(strict=True))
            artifactpath=t/"story.json"
            artifactpath.write_text(json.dumps(new_artifact))
            profile=copy.deepcopy(old)
            profile["source_story"]={
                "artifact_path":str(artifactpath),
                "artifact_id":source["artifact_id"],
                "story_sha256":source["repaired_story_text_sha256"],
                "story_file_sha256":source["repaired_story_file_sha256"],
                "approved_spine_hash":proof["approved_spine_hash"]
            }
            profile["approved_spine"]={
                "artifact_path":str(pin/proof["approved_spine_approval_path"]),
                "selection_path":str(root/proof["candidate_selection_path"]),
                "constraints_path":str(root/proof["candidate_constraints_path"]),
                "constraints_sha256":json.loads(
                    (root/proof["candidate_constraints_path"]).read_text()
                )["artifact_sha256"]
            }
            profile["paid_boundary"]["paid_execution_authorized"]=False
            profile["paid_boundary"]["authorization_consumed"]=True
            profile["paid_boundary"]["authorization_marker"]=AUTHORIZATION_MARKER
            profile_path=t/"offline-profile.json"
            profile_path.write_text(json.dumps(profile))
            _,story=_load_source_story(profile)
            assert hashlib.sha256(story.encode()).hexdigest()==proof["source_story"]["story_sha256"]
            approved=load_constraints(profile)
            assert (approved["scene_scope"]["start_span_id"]==
                    proof["candidate_scene_scope"]["start_span_id"] and
                    approved["scene_scope"]["end_span_id"]==
                    proof["candidate_scene_scope"]["end_span_id"])
            observed=[]
            def transport(**kwargs):
                stage=kwargs["request_class"]
                payload=json.loads(kwargs["user_prompt"])
                observed.append(stage)
                if "initial" in stage:
                    projected=payload["story_segments"]
                    rebuilt="".join(a+b for _,a,b in projected["spans"])+projected["trailing_whitespace"]
                    assert rebuilt==story
                    assert payload["source_story_sha256"]==proof["source_story"]["story_sha256"]
                    assert payload["approved_spine_hash"]==proof["approved_spine_hash"]
                    assert len(payload["story_segments"]["spans"])==len(source["repaired_segments"])
                    assert payload["reader_profile"]["exact_age"]==12
                    findings=[]
                    if name in ("one_repair_synthetic","out_of_bounded_scope"):
                        span="S184" if name=="one_repair_synthetic" else "S080"
                        quote=next(x["repaired_text"] for x in source["repaired_segments"] if x["span_id"]==span)
                        findings=[{
                            "family":"physical_feasibility",
                            "severity":"serious","repair_scope":"SCENE_REPAIR",
                            "span_ids":[span],"exact_text":quote,
                            "reason":"Offline synthetic test only, not a real audit finding"
                        }]
                    raw={"findings":findings,"summary":"OFFLINE_FAKE_NOT_QUALITY_EVIDENCE"}
                elif "scene_repair" in stage:
                    assert name=="one_repair_synthetic"
                    assert payload["source_story_sha256"]==proof["source_story"]["story_sha256"]
                    assert payload["scene_cluster"]["start_span_id"]=="S167"
                    assert payload["scene_cluster"]["end_span_id"]=="S203"
                    assert payload["entry_boundary"]["span_id"]=="S166"
                    assert payload["exit_boundary"]["span_id"]=="S204"
                    projected=payload["source_scene_segments"]
                    original_scene="".join(a+b for _,a,b in projected["spans"])+projected["trailing_whitespace"]
                    raw={"replacement_scene":original_scene,
                         "resolved_blocking_finding_indexes":[0],
                         "preserved_invariants":[],
                         "summary":"NO_EDIT synthetic callback, not semantic repair"}
                else:
                    assert name=="one_repair_synthetic"
                    assert payload["routing_policy"]["scope"]=="REPAIRED_SCENE_PLUS_BOUNDARIES"
                    assert "full_story" not in payload and "story_segments" not in payload
                    raw={"findings":[],"summary":"FAKE_FINAL_NOT_QUALITY_ACCEPT"}
                if name=="provider_transport_failure":
                    raise RuntimeError("SYNTHETIC transport error (no provider)")
                if name=="missing_usage":
                    return raw,{},{"max_tokens":kwargs["max_tokens"],
                                   "response_format":{"type":"json_schema"}},[]
                return (
                    raw,
                    {"usage":{"prompt_tokens":120,"completion_tokens":30,
                              "total_tokens":150,"cost":0.01}},
                    {"max_tokens":kwargs["max_tokens"],
                     "response_format":{"type":"json_schema"}},
                    [],
                )
            def callback(adapter):
                return lambda payload:adapter(api_key="",payload=payload,call_fn=transport)
            data,envelope=execute_paid_quality_once(
                api_key="",run_id=name,profile_path=profile_path,
                output_root=t/"fake-result",simulation=True,
                initial_audit_fn=callback(execute_initial_audit_call),
                scene_repair_fn=callback(execute_scene_repair_call),
                final_audit_fn=callback(execute_final_audit_call),
                # New profile is NOT part of immutable v21.4 freeze;
                # original frozen code/files are verified unchanged separately.
                verify_fn=lambda _:verify_v21_runtime(),
            )
            assert envelope["simulation"] is True
            assert envelope["explicit_paid_authorization"] is False
            assert envelope["source_story_sha256"]==proof["source_story"]["story_sha256"]
            result.append({"scenario":name,"runtime_status":data["status"],
                           "stage_attempts":len(observed),
                           "model_call_records":data.get("quality_model_calls",0),
                           "scene_repair_count":data.get("repair_count",0),
                           "original_v21_runtime":original_freeze["runtime_revision"],
                           "real_provider_calls":0,"real_cost_usd":"0",
                           "synthetic_quality_accept_is_real":False,
                           "english_master_allowed":False,"q25_allowed":False})
    expected={
      "clean_synthetic":("ACCEPT",1),
      "one_repair_synthetic":("ACCEPT",3),
      "provider_transport_failure":("REJECT_PROVIDER_FAILURE",1),
      "missing_usage":("REJECT_PROVIDER_FAILURE",1),
      "out_of_bounded_scope":("REJECT_UNBOUNDED_REPAIR_SCOPE",1),
    }
    for row in result:
        assert (row["runtime_status"],row["stage_attempts"])==expected[row["scenario"]]
        assert row["real_provider_calls"]==0
        assert row["synthetic_quality_accept_is_real"] is False
    print(json.dumps({"schema":"lumi.story-harness-p48-new-writer-mock-callbacks.v1",
      "source_story_sha256":proof["source_story"]["story_sha256"],
      "source_story_artifact_id":source["artifact_id"],
      "original_v21_4_profile_verified":True,
      "new_profile_is_purely_offline_provisional":True,
      "synthetic_scenarios":result,
      "real_paid_dispatch_possible":False,
      "real_provider_calls":0,"provider_cost_usd":"0",
      "independent_story_quality_accepted":False},sort_keys=True))

if __name__=="__main__":main()

