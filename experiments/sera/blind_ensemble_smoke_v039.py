"""Self-hosted v0.39 offline story smoke with synthetic BLIND model double.

The transcripts deliberately live in the *tests* fixture module. This
executable is itself a TEST HARNESS, not production model transport.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.multi_character_world_lab_v037 import ScenarioLab
from experiments.sera.tests.test_blind_story_recovery_v039 import (
    WORLD, setup, run_mara, run_elin,
)
from experiments.sera.world_state_v02 import canonical


def smoke():
    with ScenarioLab() as lab:
        setup(lab)
        first=run_mara(lab)
        second=run_elin(lab)
        head=lab.head(WORLD)
        assert first["status"] == "SYNTHETIC_STORY_SCENE_COMMITTED_NONCANONICAL"
        assert second["status"] == first["status"]
        assert first["entry_revision"] == 0 and first["exit_revision"] == 1
        assert second["entry_revision"] == 1 and second["exit_revision"] == 2
        assert [x["status"] for x in first["blind_extraction_attempts"]] == [
            "REEXTRACTION_REQUIRED", "SOURCE_BOUND_CANDIDATE",
        ]
        assert [x["status"] for x in second["blind_extraction_attempts"]] == [
            "REEXTRACTION_REQUIRED", "SOURCE_BOUND_CANDIDATE",
        ]
        assert lab.store.verify_replay(WORLD)
        watch=head["entities"]["pocket-watch"]
        assert (watch["owner"],watch["holder"],watch["location"]) == (
            "mara","elin","hallway",
        )
        assert (first["scene_assurance_status"] ==
                second["scene_assurance_status"] == "HOLD")
        assert (first["provider_calls"]==second["provider_calls"]==0)
        assert (first["production_db_writes"]==
                second["production_db_writes"]==0)
        assert (first["canonical_commit_authorized"] is False and
                second["canonical_commit_authorized"] is False)
        failures=lab.db.execute(
            "SELECT COUNT(*) FROM lab_run_events",
        ).fetchone()[0]
        assert failures == 2
        return {
            "schema":"sera.synthetic-blind-story-smoke.v0.39",
            "status":"SYNTHETIC_BLIND_RECOVERY_TWO_SCENE_PASS",
            "world_id":WORLD,
            "fixture_character_count":3,
            "final_revision":head["revision"],
            "scenes":[{
                "scene":s["scene_key"],
                "entry_revision":s["entry_revision"],
                "exit_revision":s["exit_revision"],
                "source_only_attempts":s["blind_extraction_attempts"],
                "assurance_status":s["scene_assurance_status"],
            } for s in (first,second)],
            "final_watch":{
                "owner":watch["owner"],
                "holder":watch["holder"],
                "location":watch["location"],
            },
            "sqlite_hash_chain_replay":True,
            "final_world_sha256":sha256(canonical(head).encode()).hexdigest(),
            "model_provider":"SYNTHETIC_SCRIPTED_BLIND_TEST_DOUBLE",
            "model_call_count":0,
            "paid_cost_usd":"0",
            "human_intervention_required":False,
            "semantic_completeness_proven":False,
            "canonical_commit_authorized":False,
            "production_db_writes":0,
        }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    proof=smoke()
    text=json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+"\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
