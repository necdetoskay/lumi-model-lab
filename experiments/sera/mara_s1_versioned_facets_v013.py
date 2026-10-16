"""SERA v0.13 real Mara isolated typed reducer qualification.

Read original v0.12 source-bound repair suggestions, adapt only its three
known facet proposals into a versioned NEW world schema and run with a
SIMULATED test approval fixture. This is not a real S1 canonical commit.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.mara_s1_v04_audit import EXPECTED_SHA,PATH
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.world_state_v02 import canonical
from experiments.sera.world_state_v013 import (
    MODE,create,digest,simulate_batch,verify_replay,
    restore_simulated_revision,
)

def need(flag,code):
    if not flag:
        raise CoverageError(code)

def adapt(*,prose:str,corrections:dict)->list[dict]:
    need(prose_hash(prose)==EXPECTED_SHA and
         isinstance(corrections,dict) and
         corrections.get("schema")=="sera.mara-s1-provisional-corrections.v0.12" and
         corrections.get("source_prose_sha256")==EXPECTED_SHA and
         corrections.get("status")=="PROPOSED_REPAIR_ONLY_CANNOT_COMMIT" and
         corrections.get("canonical_commit_authorized") is False and
         corrections.get("world_state_writes")==0,
         "V013_MARA_SOURCE_OR_AUTHORITY_INVALID")
    refs=corrections.get("shadow_facet_proposals")
    need(isinstance(refs,list) and len(refs)==3,
         "V013_MARA_THREE_SOURCE_FACETS_REQUIRED")
    expected=[
        ("openable.case_position","vane_watch","s004",
         "PROPOSED_SOURCE_OBSERVATION_NOT_CANONICAL"),
        ("openable.case_position","vane_watch","s011",
         "PROPOSED_TRANSITION_NOT_CANONICAL"),
        ("document.written_entries","mara_notebook","s021",
         "PROPOSED_APPEND_NOT_CANONICAL"),
    ]
    kinds=("OBSERVE_OPENABLE","SET_OPENABLE","APPEND_DOCUMENT_ENTRY")
    actors=("vane","vane","mara")
    names=("mara-v13-observe-watch-case","mara-v13-close-watch-case",
           "mara-v13-write-notebook")
    events=[]
    last=-1
    for i,(row,(facet,owner,sid,status)) in enumerate(zip(refs,expected)):
        need(row.get("facet")==facet and
             row.get("owner_object_id")==owner and
             row.get("source_sentence_id")==sid and
             row.get("status")==status and
             row.get("action_time_minute") is None,
             "V013_MARA_PROPOSAL_CONTRACT_CHANGED")
        evidence=row.get("evidence")
        need(isinstance(evidence,dict) and
             type(evidence.get("start")) is int and
             type(evidence.get("end")) is int and
             evidence["start"]>last and
             0<=evidence["start"]<evidence["end"]<=len(prose) and
             prose[evidence["start"]:evidence["end"]]==evidence.get("quote"),
             "V013_MARA_PROPOSAL_SOURCE_INVALID")
        last=evidence["start"]
        if i==0:
            need(row.get("old")=="UNKNOWN" and row.get("new")=="OPEN" and
                 row.get("observation_not_scene_action") is True,
                 "V013_MARA_WATCH_OPEN_BASELINE_UNPROVEN")
            payload={"expected":"UNKNOWN","observed":"OPEN"}
        elif i==1:
            need(row.get("old")=="OPEN" and row.get("new")=="CLOSED" and
                 "observation_not_scene_action" not in row,
                 "V013_MARA_WATCH_CLOSE_TRANSITION_UNPROVEN")
            payload={"expected":"OPEN","next":"CLOSED"}
        else:
            need(row.get("operation")=="APPEND_VERBATIM" and
                 row.get("quoted_entry")==evidence["quote"] and
                 row.get("quoted_entry")==
                 "Discrepancy documented; explanation unknown.",
                 "V013_MARA_DOCUMENT_ENTRY_NOT_EXACT")
            payload={"expected_append_count":0,"text":row["quoted_entry"]}
        events.append({
            "event_id":names[i],"type":kinds[i],
            "actor_id":actors[i],"object_id":owner,
            "sentence_id":sid,"evidence":deepcopy(evidence),
            "payload":payload,
        })
    return events

def run(*,corrections:dict)->dict:
    prose=json.loads(PATH.read_text(encoding="utf-8"))["prose"]
    need(prose_hash(prose)==EXPECTED_SHA,"V013_MARA_SOURCE_MISMATCH")
    world=entry_state()
    initial=create(base_world=world,prose=prose,
                   openables=["vane_watch"],documents=["mara_notebook"])
    events=adapt(prose=prose,corrections=corrections)
    original_world=canonical(world)
    start=canonical(initial)
    result=simulate_batch(
        state=initial,events=events,prose=prose,
        approvals={x["event_id"]:digest(x) for x in events},
        mode=MODE,
    )
    need(verify_replay(state=result,prose=prose),
         "V013_MARA_REPLAY_FAILED")
    prior=restore_simulated_revision(
        state=result,prose=prose,revision=0)
    need(canonical(prior)==start and
         canonical(world)==original_world,
         "V013_MARA_ORIGINAL_MUTATED")
    return {
        "schema":"sera.mara-s1-v013-versioned-facets-qualification",
        "source_prose_sha256":EXPECTED_SHA,
        "scene_key":corrections["scene_key"],
        "source_v02_world_sha256":initial["base_world_sha256"],
        "world_v02_snapshot_unchanged":canonical(world)==original_world,
        "state_schema":result["schema"],
        "simulated_reducer_events":len(events),
        "source_only_events":events,
        "versioned_aspects":result["aspects"],
        "head_hash":result["head_hash"],
        "simulated_revision":result["revision"],
        "history_verifies_deterministically":True,
        "reconstructed_initial_snapshot_unchanged":canonical(prior)==start,
        "simulated_authority_only":MODE,
        "actual_source_action_times_set":0,
        "production_database_writes":0,
        "real_canonical_authorization":False,
        "gold_reference_qualified":False,
        "status":"VERSIONED_TYPED_REDUCER_SIMULATION_GREEN_CANONICAL_S1_HOLD",
    }

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--corrections",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    report=run(corrections=json.loads(
        args.corrections.read_text(encoding="utf-8")
    ))
    if args.output.exists():
        raise CoverageError("V013_MARA_OUTPUT_ALREADY_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "simulated_reducer_events":report["simulated_reducer_events"],
        "world_v02_snapshot_unchanged":report["world_v02_snapshot_unchanged"],
        "versioned_watch":report["versioned_aspects"]["vane_watch"]["position"],
        "notebook_new_entries":len(
            report["versioned_aspects"]["mara_notebook"]["observed_appends"]),
        "history_verifies_deterministically":
            report["history_verifies_deterministically"],
        "real_canonical_authorization":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
