"""SERA v0.39: offline v0.10 blind model DOUBLE, auto-repair, SQLite story."""
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from experiments.sera.blind_story_recovery_v039 import (
    blind_recover, run_scene, source_event_id,
)
from experiments.sera.coverage import prose_hash
from experiments.sera.multi_character_world_lab_v037 import ScenarioLab
from experiments.sera.world_state_v02 import fingerprint

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "multi_character_story_v037.json"
WORLD = "lab-mara-ensemble-world-a"
MARA_TEXT = "Mara handed the pocket-watch to Elin."
ELIN_TEXT = "Elin carried the pocket-watch into hallway."
ALIASES = {
    "mara": ["Mara"], "elin": ["Elin"], "rho": ["Rho"],
    "pocket-watch": ["pocket-watch"], "notebook": ["notebook"],
    "pencil": ["pencil"], "rho-cloak": ["rho-cloak"],
}


def response(prose, kind, refs, *, missing=None, claim=False, no_events=False):
    """Untrusted model transcript. Does NOT receive expected fixture actions."""
    mentions = []
    for ref, spelling in refs:
        if ref == missing:
            continue
        mentions.append({
            "entity_ref": ref, "role": "MENTIONED",
            "evidence_quote": spelling, "occurrence": 0,
        })
    return {"rows":[{
        "sentence_id": "s001", "disposition":
            "NO_TRACKED_CHANGE" if no_events else "STATE_EVENT",
        "reason": "synthetic blind model proposal, not proof of truth",
        "mentions": mentions,
        "events": [] if no_events else [{
            "kind": kind,
            "epistemic": "REPORTED_CLAIM" if claim else "OBSERVED_ACTION",
            "effect": "OBJECT" if kind == "TRANSFER" else "WORLD",
            "evidence_quote": prose, "occurrence": 0,
            "entity_refs": [ref for ref, _ in refs],
            "reason": "candidate action described in one exact sentence",
        }],
    }]}


def mara_reply(*, request, attempt, previous_findings):
    task = json.loads(request["messages"][1]["content"])
    assert task["target_sentences"][0]["quote"] == MARA_TEXT
    assert "validator_world" not in str(task)
    assert "fixture_grants" not in str(task)
    if attempt == 2:
        assert any("SWEEP_MISSING_ENTITY_HINT" in f
                   for f in previous_findings)
    return response(MARA_TEXT, "TRANSFER", [
        ("mara","Mara"), ("pocket-watch","pocket-watch"), ("elin","Elin"),
    ],missing="pocket-watch" if attempt == 1 else None)


def elin_reply(*, request, attempt, previous_findings):
    task=json.loads(request["messages"][1]["content"])
    assert task["target_sentences"][0]["quote"] == ELIN_TEXT
    if attempt == 1:
        return {"rows":[{
            "sentence_id":"s001","disposition":"STATE_EVENT",
            "reason":"malformed first extraction",
            "mentions":[], "events":[{
                "kind":"MOVE","epistemic":"OBSERVED_ACTION",
                "effect":"WORLD",
                "evidence_quote":"Elin teleported into hallway",
                "occurrence":0,"entity_refs":["elin"],
                "reason":"fabricated location evidence",
            }],
        }]}
    assert any("SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE" in f
               for f in previous_findings)
    return response(ELIN_TEXT, "MOVE", [
        ("elin","Elin"),("pocket-watch","pocket-watch"),
    ])


def fixture_event(prose,scene,typ,payload,minute):
    event_id=source_event_id(
        world_id=WORLD,scene_key=scene,prose=prose,
        sweep_event_id="batch_001:s001:e1",
    )
    ev={
        "event_id":event_id,"type":typ,"at_minute":minute,
        "reason":"externally pinned synthetic test fixture",
        "evidence_ref":"synthetic-scene:"+scene+":"+prose_hash(prose),
        "payload":payload,
    }
    return ev, {event_id:fingerprint(ev)}


def run_mara(lab,reply=mara_reply,attempts=2,**overrides):
    ev, grants=fixture_event(
        MARA_TEXT,"Mara-S1","TRANSFER_HOLDER",{
            "entity_id":"pocket-watch", "from_id":"mara","to_id":"elin",
        },1)
    kwargs=dict(
        lab=lab,run_id="mara-s1",scene_key="Mara-S1",prose=MARA_TEXT,
        approved_fixture_event=ev,fixture_approvals=grants,
        aliases=ALIASES,lexicon={},
        reply_for_blind_batch=reply,max_attempts=attempts,
    )
    kwargs.update(overrides)
    return run_scene(**kwargs)


def run_elin(lab,reply=elin_reply,attempts=2,**overrides):
    ev,grants=fixture_event(
        ELIN_TEXT,"Elin-S2","MOVE_CHARACTER",{
            "character_id":"elin","to_location":"hallway",
        },4)
    kwargs=dict(
        lab=lab,run_id="elin-s2",scene_key="Elin-S2",prose=ELIN_TEXT,
        approved_fixture_event=ev,fixture_approvals=grants,
        aliases=ALIASES,lexicon={},reply_for_blind_batch=reply,
        scene_window={"earliest_minute":1,"latest_minute":12},
        max_attempts=attempts,
    )
    kwargs.update(overrides)
    return run_scene(**kwargs)


def setup(lab):
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    lab.seed(fixture)
    lab.begin_story(run_id="mara-s1",world_id=WORLD,character_id="mara")
    lab.begin_story(run_id="elin-s2",world_id=WORLD,character_id="elin")


class BlindStoryRecoveryV039Tests(unittest.TestCase):
    def setUp(self):
        self.lab=ScenarioLab()
        setup(self.lab)

    def tearDown(self):
        self.lab.close()

    def test_model_double_recovers_missing_entity_then_bad_quote_across_two_scenes(self):
        one=run_mara(self.lab)
        self.assertEqual(one["status"],
                         "SYNTHETIC_STORY_SCENE_COMMITTED_NONCANONICAL")
        self.assertEqual([x["status"] for x in one["blind_extraction_attempts"]],
                         ["REEXTRACTION_REQUIRED","SOURCE_BOUND_CANDIDATE"])
        self.assertEqual(self.lab.head(WORLD)["revision"],1)
        two=run_elin(self.lab)
        self.assertEqual(two["status"],
                         "SYNTHETIC_STORY_SCENE_COMMITTED_NONCANONICAL")
        self.assertEqual([x["status"] for x in two["blind_extraction_attempts"]],
                         ["REEXTRACTION_REQUIRED","SOURCE_BOUND_CANDIDATE"])
        self.assertEqual((two["entry_revision"],two["exit_revision"]),(1,2))
        self.assertEqual(self.lab.head(WORLD)["entities"]["pocket-watch"]["owner"],
                         "mara")
        self.assertEqual(self.lab.head(WORLD)["entities"]["pocket-watch"]["holder"],
                         "elin")
        self.assertEqual(self.lab.head(WORLD)["entities"]["pocket-watch"]["location"],
                         "hallway")
        self.assertEqual(self.lab.head(WORLD)["entities"]["mara"]["location"],
                         "workshop")
        self.assertTrue(self.lab.store.verify_replay(WORLD))
        self.assertEqual(one["scene_assurance_status"],"HOLD")
        self.assertEqual(two["scene_assurance_status"],"HOLD")
        self.assertEqual(one["provider_calls"]+two["provider_calls"],0)
        self.assertEqual(one["production_db_writes"]+
                         two["production_db_writes"],0)
        self.assertFalse(one["canonical_commit_authorized"])
        self.assertFalse(two["canonical_commit_authorized"])
        self.assertNotIn("secret-elins-note",
                         json.dumps(self.lab.context("mara-s1")))

    def test_missing_entity_with_no_second_chance_finalizes_without_changes(self):
        result=run_mara(self.lab,attempts=1)
        self.assertEqual(result["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(self.lab.head(WORLD)["revision"],0)
        self.assertEqual(len(result["attempts"]),1)
        self.assertEqual(self.lab.db.execute(
            "SELECT count(*) FROM lab_run_events").fetchone()[0],0)

    def test_reply_without_any_event_never_drops_physical_action(self):
        def omitted(*,request,attempt,previous_findings):
            return response(MARA_TEXT,"TRANSFER",[
                ("mara","Mara"), ("pocket-watch","pocket-watch"),
                ("elin","Elin")],no_events=True)
        out=run_mara(self.lab,reply=omitted)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(len(out["attempts"]),2)
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_reported_claim_does_not_become_physical_event(self):
        def reported(*,request,attempt,previous_findings):
            return response(MARA_TEXT,"TRANSFER",[
                ("mara","Mara"),("pocket-watch","pocket-watch"),
                ("elin","Elin")],claim=True)
        out=run_mara(self.lab,reply=reported)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_invalid_model_evidence_is_retried_then_safe_final(self):
        out=run_elin(self.lab,reply=elin_reply,attempts=1)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_untrusted_model_receives_no_expected_fixture_grant(self):
        observed=[]
        def spy(*,request,attempt,previous_findings):
            observed.append(deepcopy(request))
            return response(MARA_TEXT,"TRANSFER",[
                ("mara","Mara"),("pocket-watch","pocket-watch"),
                ("elin","Elin")])
        out=run_mara(self.lab,reply=spy)
        self.assertEqual(out["status"],
                         "SYNTHETIC_STORY_SCENE_COMMITTED_NONCANONICAL")
        self.assertEqual(len(observed),1)
        body=str(observed[0])
        self.assertNotIn("TRANSFER_HOLDER",body)
        self.assertNotIn("synthetic-scene:",body)
        self.assertNotIn("secret-elins-note",body)
        self.assertNotIn("fixture_approvals",body)
        self.assertNotIn("validator_world",body)

    def test_separate_trusted_action_cannot_be_replaced_by_model_event(self):
        ev,grants=fixture_event(
            MARA_TEXT,"Mara-S1","TRANSFER_HOLDER",{
                "entity_id":"pocket-watch","from_id":"mara","to_id":"rho",
            },1)
        # Explicitly wrong recipient: rho is in hallway, and source quote
        # mentions Elin, so an untrusted model cannot self-authorize it.
        out=run_mara(self.lab,reply=lambda **k:response(
            MARA_TEXT,"TRANSFER",[
                ("mara","Mara"),("pocket-watch","pocket-watch"),
                ("elin","Elin")]),approved_fixture_event=ev,
            fixture_approvals=grants)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(self.lab.head(WORLD)["revision"],0)

    def test_restart_can_resume_against_latest_shared_world_head(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"v039.sqlite")
            with ScenarioLab(path) as first:
                setup(first)
                self.assertEqual(run_mara(first)["exit_revision"],1)
            with ScenarioLab(path) as recovered:
                self.assertEqual(run_elin(recovered)["exit_revision"],2)
                self.assertTrue(recovered.store.verify_replay(WORLD))

    def test_scene_ids_are_scoped_not_reused_from_sweep_local_ids(self):
        self.assertNotEqual(source_event_id(
            world_id=WORLD,scene_key="Mara-S1",prose=MARA_TEXT,
            sweep_event_id="batch_001:s001:e1",
        ),source_event_id(
            world_id=WORLD,scene_key="Elin-S2",prose=ELIN_TEXT,
            sweep_event_id="batch_001:s001:e1",
        ))


if __name__=="__main__":
    unittest.main()
