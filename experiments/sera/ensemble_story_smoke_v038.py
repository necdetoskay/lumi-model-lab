"""Run two synthetic Mara/Elin story scenes and emit verifiable JSON evidence.

No model calls, StoryForge billing, human review, G2 SQL or canon mutation.
Only the story fixture itself issues isolated exact-fingerprint TEST grants.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import prose_hash
from experiments.sera.multi_character_world_lab_v037 import ScenarioLab
from experiments.sera.story_scene_rehearsal_v038 import rehearsal
from experiments.sera.world_state_v02 import fingerprint, canonical

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "multi_character_story_v037.json"
WORLD = "lab-mara-ensemble-world-a"


def _input(prose, key, event_id, kind, refs, event_type, payload, minute):
    return {
        "scene_key": key, "prose": prose,
        "source_event": {
            "event_id": event_id, "sentence_id": "s001",
            "kind": kind, "effect": "OBJECT" if kind == "TRANSFER" else "WORLD",
            "epistemic": "OBSERVED_ACTION",
            "entity_refs": refs, "start": 0, "end": len(prose), "quote": prose,
        },
        "reducer_event": {
            "event_id": event_id, "type": event_type,
            "at_minute": minute,
            "reason": "external synthetic regression fixture",
            "evidence_ref": "synthetic-scene:" + key + ":" + prose_hash(prose),
            "payload": payload,
        },
    }


def run_smoke():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    aliases = {
        **{c["id"]: [c["name"]] for c in fixture["characters"]},
        **{obj["id"]: [obj["id"]] for obj in fixture["objects"]},
    }
    routes = {
        route["from_id"]+"->"+route["to_id"]: route["min_minutes"]
        for route in fixture["routes"]
    }
    first = _input(
        "Mara handed the pocket-watch to Elin.", "Mara-S1",
        "mara-watch-gift", "TRANSFER",
        ["mara","pocket-watch","elin"], "TRANSFER_HOLDER",
        {"entity_id":"pocket-watch","from_id":"mara","to_id":"elin"}, 1,
    )
    second = _input(
        "Elin carried the pocket-watch into hallway.", "Elin-S2",
        "elin-carries-watch", "MOVE",
        ["elin","pocket-watch"], "MOVE_CHARACTER",
        {"character_id":"elin","to_location":"hallway"}, 4,
    )
    with ScenarioLab() as lab:
        seed = lab.seed(fixture)
        lab.begin_story(run_id="mara-run",world_id=WORLD,character_id="mara")
        lab.begin_story(run_id="elin-run",world_id=WORLD,character_id="elin")
        before = lab.head(WORLD)
        event1 = first["reducer_event"]
        scene1 = rehearsal(
            lab=lab,run_id="mara-run",expected_revision=0,
            registered_aliases=aliases,candidate_lexicon={},
            fixture_grants={event1["event_id"]:fingerprint(event1)},
            relation_case={
                "entry":before,"registered_aliases":aliases,
                "verified_fact_registry":{},
                "transitions":[{
                    "source_event_id":event1["event_id"],
                    "operation":"TRANSFER_HOLDER","object_id":"pocket-watch",
                    "from_id":"mara","to_id":"elin","fact_id":None,
                }],
                "policy_id":"fixture:v038:ensemble-watch-handoff",
            },
            **first,
        )
        state1 = lab.head(WORLD)
        event2 = second["reducer_event"]
        scene2 = rehearsal(
            lab=lab,run_id="elin-run",expected_revision=1,
            registered_aliases=aliases,candidate_lexicon={},
            fixture_grants={event2["event_id"]:fingerprint(event2)},
            temporal_case={
                "entry":state1,"scene_key":"Elin-S2",
                "scene_window":{
                    "scene_key":"Elin-S2","entry_revision":1,
                    "earliest_minute":1,"latest_minute":12,
                },
                "events":[{
                    "event_id":event2["event_id"],"ordinal":1,
                    "actor_id":"elin","kind":"MOVEMENT",
                    "to_location":"hallway","earliest_minute":None,
                    "latest_minute":None,"exact_minute":None,"depends_on":[],
                }],
                "travel_minutes":routes,
            },
            **second,
        )
        state2 = lab.head(WORLD)
        assert state2["revision"] == 2
        assert state2["entities"]["pocket-watch"]["holder"] == "elin"
        assert state2["entities"]["pocket-watch"]["owner"] == "mara"
        assert state2["entities"]["pocket-watch"]["location"] == "hallway"
        assert state2["entities"]["mara"]["location"] == "workshop"
        assert lab.store.verify_replay(WORLD) is True
        assert scene1["scene_assurance_status"] == "HOLD"
        assert scene2["scene_assurance_status"] == "HOLD"
        assert scene1["provider_calls"]+scene2["provider_calls"] == 0
        assert scene1["canonical_commit_authorized"] is False
        assert scene2["canonical_commit_authorized"] is False
        return {
            "schema":"sera.synthetic-story-smoke-evidence.v0.38",
            "status":"SYNTHETIC_TWO_SCENE_SQLITE_REPLAY_PASS",
            "source":"SYNTHETIC_FIXTURE_NOT_G2",
            "world_id":WORLD,
            "characters":seed["character_ids"],
            "initial_revision":0,
            "final_revision":state2["revision"],
            "scenes":[{
                "scene_key":s["scene_key"],
                "entry_revision":s["entry_revision"],
                "exit_revision":s["exit_revision"],
                "source_prose_sha256":s["source_prose_sha256"],
                "scene_assurance_status":s["scene_assurance_status"],
                "preview_kind":s["preview_kind"],
            } for s in (scene1,scene2)],
            "final_watch":{
                "owner":state2["entities"]["pocket-watch"]["owner"],
                "holder":state2["entities"]["pocket-watch"]["holder"],
                "location":state2["entities"]["pocket-watch"]["location"],
            },
            "sqlite_hash_chain_replay":True,
            "final_world_sha256":sha256(canonical(state2).encode()).hexdigest(),
            "independent_semantic_qualification":False,
            "provider_calls":0,
            "model_cost_usd":"0",
            "production_db_writes":0,
            "canonical_commit_authorized":False,
        }


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--output", type=Path)
    args=cli.parse_args()
    result=run_smoke()
    value=json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(value+"\n",encoding="utf-8")
    print(value)


if __name__=="__main__":
    main()
