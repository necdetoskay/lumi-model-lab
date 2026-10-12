"""Q25 annotated story evidence is untrusted and cannot write canonical state."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_entity_candidates import fingerprint
from src.q25_offline_diagnostic import digest
from src.q25_state_admission import build_draft
from src.q25_story_evidence import extend_draft

Q24 = Path("evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24")
ENTITY = Path("evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json")
POLICY = Path("evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json")
STORY = Path("evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal.json")


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def q24():
    seed = read(Q24 / "seed-input.json")
    prose = read(Q24 / "writer-2-text.json")["text"]
    admission = build_draft(seed=seed, prose=prose, proposal=read(ENTITY), policy=read(POLICY))
    return seed, prose, admission, read(STORY)


def run(seed, prose, admission, story, entity_proposal=None, policy=None):
    return extend_draft(seed=seed, prose=prose, admission_result=admission,
                        entity_proposal=entity_proposal if entity_proposal is not None else read(ENTITY),
                        policy=policy if policy is not None else read(POLICY),
                        story_proposal=story)


def test_q24_character_knowledge_goals_obligations_and_threads_are_separate_proposals():
    seed, prose, admission, story = q24()
    before = (copy.deepcopy(seed), copy.deepcopy(admission))
    result = run(seed, prose, admission, story)
    draft = result["draft_state"]
    assert len(draft["proposed_character_changes"]) == 2
    assert len(draft["proposed_goal_outcomes"]) == 3
    assert len(draft["proposed_narrative_obligations"]) == 3
    assert len(draft["proposed_thread_outcomes"]) == 3
    assert all(c["outcome"] == "SATISFIED" for c in draft["proposed_narrative_obligations"])
    assert all(c["outcome"] == "ACHIEVED" for c in draft["proposed_goal_outcomes"])
    assert draft["characters"] == admission["draft_state"]["characters"]
    assert draft["objects"] == admission["draft_state"]["objects"]
    assert draft["objects"]["blue_atlas"]["contains"] == []
    assert draft["objects"]["red_bookmark"]["properties"]["found"] is False
    assert seed["narrative_obligations"][0]["status"] == "OPEN"
    assert result["full_story_state_qualified"] is False
    assert result["semantic_support_certified"] is False
    assert result["state_commit_authorized"] is False
    assert result["provider_calls"] == 0
    assert (seed, admission) == before
    assert result == run(seed, prose, admission, story)


@pytest.mark.parametrize("damage", [
    "wrong_seed", "wrong_source", "invalid_citation", "unknown_actor",
    "duplicate_knowledge", "knowledge_without_epistemic", "knowledge_in_seed",
    "unexpected_other_actor", "unknown_relationship", "invalid_location",
    "duplicate_emotion", "unknown_goal", "duplicate_goal",
    "unknown_obligation", "duplicate_obligation", "not_open_obligation",
    "unknown_thread", "duplicate_thread", "out_of_order_evidence",
])
def test_untrusted_story_claims_fail_closed(damage):
    seed, prose, admission, story = q24()
    item = story["character_claims"][0]
    entity = read(ENTITY)
    if damage == "wrong_seed":
        story["seed_sha256"] = "0" * 64
    elif damage == "wrong_source":
        story["source_sha256"] = "0" * 64
    elif damage == "invalid_citation":
        item["evidence"]["text"] = "invented quotation"
    elif damage == "unknown_actor":
        item["actor"] = "Invented"
    elif damage == "duplicate_knowledge":
        story["character_claims"].append(copy.deepcopy(item))
    elif damage == "knowledge_without_epistemic":
        item["epistemic_type"] = None
    elif damage == "knowledge_in_seed":
        item["value"] = seed["characters"]["Nisa"]["knowledge"][0]
    elif damage == "unexpected_other_actor":
        item["other_actor"] = "Cem"
    elif damage == "unknown_relationship":
        item.update(field="relationship_trust", other_actor="Invented", epistemic_type=None)
    elif damage == "invalid_location":
        item.update(field="location", value="invented_room", epistemic_type=None)
    elif damage == "duplicate_emotion":
        story["character_claims"].append(copy.deepcopy(story["character_claims"][1]))
    elif damage == "unknown_goal":
        story["goal_claims"][0]["goal_id"] = "invented_goal"
    elif damage == "duplicate_goal":
        story["goal_claims"].append(copy.deepcopy(story["goal_claims"][0]))
    elif damage == "unknown_obligation":
        story["obligation_claims"][0]["obligation_id"] = "invented"
    elif damage == "duplicate_obligation":
        story["obligation_claims"].append(copy.deepcopy(story["obligation_claims"][0]))
    elif damage == "not_open_obligation":
        seed["narrative_obligations"][0]["status"] = "DONE"
        story["seed_sha256"] = fingerprint(seed)
        entity["seed_sha256"] = fingerprint(seed)
        admission = build_draft(seed=seed, prose=prose, proposal=entity, policy=read(POLICY))
    elif damage == "unknown_thread":
        story["thread_claims"][0]["thread_id"] = "invented"
    elif damage == "duplicate_thread":
        story["thread_claims"].append(copy.deepcopy(story["thread_claims"][0]))
    elif damage == "out_of_order_evidence":
        story["obligation_claims"][0]["evidence"].reverse()
    with pytest.raises(ValueError):
        run(seed, prose, admission, story, entity_proposal=entity)


def test_blocked_admission_and_tampered_draft_cannot_be_extended():
    seed, prose, admission, story = q24()
    bad = copy.deepcopy(admission)
    bad["structural_admission"] = "BLOCKED_BY_POLICY"
    bad["draft_state"] = None
    with pytest.raises(ValueError):
        run(seed, prose, bad, story)
    bad = copy.deepcopy(admission)
    bad["state_commit_authorized"] = True
    with pytest.raises(ValueError):
        run(seed, prose, bad, story)
    bad = copy.deepcopy(admission)
    bad["draft_state"]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        run(seed, prose, bad, story)


@pytest.mark.parametrize("tamper", [
    "object_contents", "object_owner", "knowledge", "world", "topology", "identity_map"
])
def test_forged_admission_fields_cannot_be_laundered(tamper):
    seed, prose, admission, story = q24()
    forged = copy.deepcopy(admission)
    draft = forged["draft_state"]
    if tamper == "object_contents":
        draft["objects"]["blue_atlas"]["contains"] = ["red_bookmark"]
    elif tamper == "object_owner":
        new_book = draft["objects"]["red_bookmark"]["container"]["ref"]
        draft["objects"][new_book]["owner"] = {"status": "KNOWN", "ref": "Nisa"}
    elif tamper == "knowledge":
        draft["characters"]["Nisa"]["knowledge"].append("invented_knowledge")
    elif tamper == "world":
        draft["world"]["setting"] = "magical_library"
    elif tamper == "topology":
        draft["topology"]["locations"].append("invented_room")
    elif tamper == "identity_map":
        draft["identity_map"]["object:red_bookmark"] = "blue_atlas"
    with pytest.raises(ValueError, match="deterministic replay"):
        run(seed, prose, forged, story)


def test_unannotated_fields_remain_unresolved_and_none_are_inferred():
    seed, prose, admission, story = q24()
    story = {**story, "character_claims": [], "goal_claims": [],
             "obligation_claims": [], "thread_claims": []}
    draft = run(seed, prose, admission, story)["draft_state"]
    for key in ("proposed_character_changes", "proposed_goal_outcomes",
                "proposed_narrative_obligations", "proposed_thread_outcomes"):
        assert draft[key] == []
    assert draft["full_story_state_qualified"] is False
    assert draft["coverage"] == "OBJECT_RELATIONS_ONLY_NOT_FULL_STORY_STATE"


def test_read_only_cli_replays_q24_without_touching_sources():
    roots = [Q24, ENTITY.parent, POLICY.parent, STORY.parent]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for root in roots for p in root.rglob("*") if p.is_file()}
    command = [
        sys.executable, "-X", "utf8", "-m", "src.q25_story_evidence",
        "--seed", str(Q24 / "seed-input.json"),
        "--prose-record", str(Q24 / "writer-2-text.json"),
        "--entity-proposal", str(ENTITY),
        "--policy", str(POLICY),
        "--story-proposal", str(STORY),
    ]
    output = json.loads(subprocess.check_output(command, text=True, encoding="utf8"))
    seed, prose, admission, story = q24()
    assert output == run(seed, prose, admission, story)
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for root in roots for p in root.rglob("*") if p.is_file()}


def test_proposal_has_only_frozen_verbatim_citations():
    seed, prose, admission, story = q24()
    assert story["seed_sha256"] == fingerprint(seed)
    assert story["source_sha256"] == digest(prose)
    assert all(prose[c["evidence"]["start"]:c["evidence"]["end"]] == c["evidence"]["text"]
               for c in story["character_claims"])
    assert run(seed, prose, admission, story)["story_proposal_sha256"] == fingerprint(story)
