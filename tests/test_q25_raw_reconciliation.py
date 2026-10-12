"""End-to-end generic model-shaped response projection, source bound and not canon."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.q25_raw_reconciliation import project_raw

FIXTURE = Path("evidence/q25/Q25-NEW-STORY-CALIBRATION-20261012/fixture.json")


def saved():
    return json.loads(FIXTURE.read_text(encoding="utf8"))


def inputs(case, scenario="gold"):
    return {
        "seed": case["seed"], "prose": case["prose"],
        "raw_output": (
            case["gold_raw_output"] if scenario == "gold"
            else case["flawed_candidate_raw_output"]),
        "policy": case["policy"],
    }


@pytest.mark.parametrize("scenario", ["gold", "flawed"])
def test_open_story_projects_structurally_coherent_unverified_state(scenario):
    fixture = saved()
    source = inputs(fixture, scenario)
    original = copy.deepcopy(source)
    result = project_raw(**source)
    assert result["schema"] == "q25.raw-terminal-hypothesis.v1"
    assert result["raw_response_trust"] == "UNTRUSTED_SOURCE_QUOTED_CANDIDATES_ONLY"
    assert result["structural_consistency"]["status"] == (
        "STRUCTURALLY_COHERENT_CANDIDATES_ONLY")
    assert result["structural_consistency"]["reciprocal_container_pairs"] == 1
    assert "blocked" not in result
    assert result["blocking_field_count"] == sum(result["coverage_counts"].values())
    assert all(not row["terminal_accepted"] and not row["inherited_seed_is_proof"]
               for row in result["field_decisions"])
    assert result["independent_semantic_review_completed"] is False
    assert result["terminal_state_complete"] is False
    assert result["semantic_support_certified"] is False
    assert result["state_commit_authorized"] is False
    assert result["production_write_performed"] is False
    assert result["provider_calls"] == 0
    book = next((k, x) for k, x in result["candidate_state"]["objects"].items()
                if k.startswith("new_"))
    book_id, book_obj = book
    bookmark = result["candidate_state"]["objects"]["yellow_card"]
    assert book_obj["identity_status"] == "PROPOSED"
    assert book_obj["contains"] == ["yellow_card"]
    assert bookmark["container"]["ref"] == book_id
    assert bookmark["held_by"]["status"] == "NONE"
    assert result["candidate_state"]["objects"]["green_map"]["contains"] == []
    assert book_obj["location"]["status"] == "UNKNOWN"
    assert bookmark["owner"]["ref"] == "Aylin"
    assert bookmark["properties"]["found"]["initial_reference"] is False
    assert bookmark["properties"]["intentionally_stolen"]["terminal_proposal"] is None
    assert result["candidate_state"]["world_initial_reference"]["time"][
        "minutes_until_presentation"] == 15
    assert result["candidate_state"]["proposed_world_time"] is None
    assert result["approved_obligation_closures"] == []
    assert result == project_raw(**source)
    assert original == source


def test_flawed_prediction_is_structurally_admissible_not_semantically_true():
    reference = project_raw(**inputs(saved(), "gold"))
    flawed = project_raw(**inputs(saved(), "flawed"))
    def folder(report):
        return next(x for name, x in report["candidate_state"]["objects"].items()
                    if name.startswith("new_"))
    assert folder(reference)["owner"]["status"] == "UNKNOWN"
    assert folder(flawed)["owner"]["status"] == "KNOWN"
    assert folder(flawed)["owner"]["ref"] == "Aylin"
    assert folder(flawed)["relation_authority"] == (
        "STRUCTURAL_CANDIDATE_NOT_SEMANTICALLY_VERIFIED")
    correct = reference["candidate_state"]["objects"]["yellow_card"]["properties"]["found"]
    missing = flawed["candidate_state"]["objects"]["yellow_card"]["properties"]["found"]
    assert correct["terminal_proposal"] is True
    assert missing["terminal_proposal"] is None
    assert missing["value_status"] == "UNASSESSED_SEED_REFERENCE_ONLY"
    assert len(reference["proposed_obligation_closures"]) == 3
    assert len(flawed["proposed_obligation_closures"]) == 2
    assert reference["approved_obligation_closures"] == flawed["approved_obligation_closures"] == []
    assert any(c["candidate_terminal_value"] == "relieved"
               for c in flawed["candidate_state"]["characters"]["Aylin"][
                   "terminal_scalar_change_candidates"])
    assert reference["state_commit_authorized"] is False
    assert flawed["state_commit_authorized"] is False


@pytest.mark.parametrize("corruption", [
    "source_hash", "nonexistent_quote", "new_actor",
    "fake_decisive_clue", "unsupported_goal",
    "injected_state_commit", "policy_denial",
])
def test_invalid_response_cannot_reach_reconciliation(corruption):
    values = inputs(saved(), "gold")
    raw = values["raw_output"]
    if corruption == "source_hash":
        raw["source_sha256"] = "0" * 64
    elif corruption == "nonexistent_quote":
        raw["objects"][0]["mention"]["quote"] = "The white folder magically flew."
    elif corruption == "new_actor":
        raw["character_claims"][0]["actor"] = "NotInSeed"
    elif corruption == "fake_decisive_clue":
        raw["objects"][0]["role"] = "DECISIVE_CLUE"
    elif corruption == "unsupported_goal":
        raw["goal_claims"][0]["goal_id"] = "made_up_goal"
    elif corruption == "injected_state_commit":
        raw["state_commit_authorized"] = True
    elif corruption == "policy_denial":
        values["policy"]["allow_new_ordinary_objects"] = False
    with pytest.raises(ValueError):
        project_raw(**values)



def test_frozen_q24_raw_envelope_still_projects_without_annotation_worklist():
    root = Path("evidence/q25")
    old = root / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
    q24_data = {
        "seed": json.loads((old / "seed-input.json").read_text(encoding="utf8")),
        "prose": json.loads((old / "writer-2-text.json").read_text(encoding="utf8"))["text"],
        "raw_output": json.loads((
            root / "Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json"
        ).read_text(encoding="utf8")),
        "policy": json.loads((
            root / "Q25-ADMISSION-DRAFT-20261012/policy.json"
        ).read_text(encoding="utf8")),
    }
    result = project_raw(**q24_data)
    objects = result["candidate_state"]["objects"]
    book = next(k for k in objects if k.startswith("new_"))
    assert objects["red_bookmark"]["container"]["ref"] == book
    assert objects["blue_atlas"]["contains"] == []
    assert objects["red_bookmark"]["properties"]["found"]["terminal_proposal"] is True
    assert objects["red_bookmark"]["properties"]["returned_to_owner"][
        "terminal_proposal"] is None  # old Q24 raw output never claimed it
    assert result["blocking_field_count"] == 70
    assert set(result["proposed_obligation_closures"]) == {
        "investigate_evidence", "recover_bookmark", "correct_and_apologize"}
    assert result["approved_obligation_closures"] == []
    assert result["full_story_state_qualified"] is False


def test_readonly_cli_projects_saved_json_on_unseen_story(tmp_path):
    case = saved()
    sources = {
        "seed": case["seed"],
        "prose-record": {"text": case["prose"]},
        "raw-response": case["gold_raw_output"],
        "policy": case["policy"],
    }
    paths = {}
    for name, data in sources.items():
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf8")
        paths[name] = path
    cmd = [sys.executable, "-X", "utf8", "-m", "src.q25_raw_reconciliation"]
    for name, path in paths.items():
        cmd += ["--" + name, str(path)]
    result = json.loads(subprocess.check_output(cmd, encoding="utf8", text=True))
    assert result == project_raw(**inputs(case, "gold"))
    assert result["state_commit_authorized"] is False
