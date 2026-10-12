"""Open-story offline calibration proves metric wiring, not model accuracy."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_extraction_benchmark import calibrate
from src.q25_extractor_adapter import build_extraction_request

FIXTURE = Path(
    "evidence/q25/Q25-NEW-STORY-CALIBRATION-20261012/fixture.json"
)
CLAIM_GROUPS = (
    "objects", "terminal_relations", "character_claims", "goal_claims",
    "obligation_claims", "thread_claims", "property_claims",
)


def data():
    return json.loads(FIXTURE.read_text(encoding="utf8"))


def arguments(fixture):
    return {
        "seed": fixture["seed"], "prose": fixture["prose"],
        "policy": fixture["policy"],
        "gold_raw_output": fixture["gold_raw_output"],
        "candidate_raw_output": fixture["flawed_candidate_raw_output"],
    }


def test_a_second_turkish_scenario_exercises_existing_adapter_with_new_names():
    d = data()
    original = copy.deepcopy(d)
    request = build_extraction_request(seed=d["seed"], prose=d["prose"])
    assert request["allowed_characters"] == ["Aylin", "Kerem"]
    assert request["allowed_open_obligations"] == [
        "check_log_then_search", "correct_and_apologize", "recover_card",
    ]
    assert request["seed_sha256"] == d["gold_raw_output"]["seed_sha256"]
    assert request["source_sha256"] == d["gold_raw_output"]["source_sha256"]
    assert request["immutable_seed"]["story_id"] == "yellow-card-calibration-01"
    assert "q25.extractor-raw-output.v1" == request["output_schema"]
    assert d["blind_holdout"] is False
    assert "MANUALLY_CURATED" in d["gold_annotation_origin"]
    assert "NOT_AN_API_RESPONSE" in d["candidate_origin"]
    assert original == d


def test_manually_curated_reference_envelope_passes_structural_replay_only():
    d = data()
    r = calibrate(**{**arguments(d), "candidate_raw_output": d["gold_raw_output"]})
    assert r["candidate_structural_replay_status"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert r["reference_claim_count"] == r["candidate_claim_count"] == 12
    assert r["overall"] == {
        "true_positive": 12, "false_positive": 0, "false_negative": 0,
        "precision": 1.0, "recall": 1.0, "f1": 1.0,
        "reference_quote_exact_matches": 12,
    }
    assert r["coverage_field_count"] > 0
    assert r["reference_labels_independently_adjudicated"] is False
    assert r["real_model_success_measured"] is False
    assert r["semantic_support_certified"] is False
    assert r["full_story_state_qualified"] is False
    assert r["state_commit_authorized"] is False
    assert r["provider_calls"] == 0
    assert r["provider_cost_usd"] == 0


def test_flawed_synthetic_prediction_exposes_wrong_and_missing_claims():
    d = data()
    before = copy.deepcopy(d)
    r = calibrate(**arguments(d))
    assert r["reference_claim_count"] == 12
    assert r["candidate_claim_count"] == 10
    score = r["overall"]
    assert (score["true_positive"], score["false_positive"],
            score["false_negative"]) == (8, 2, 4)
    assert score["precision"] == 0.8
    assert score["recall"] == pytest.approx(2 / 3)
    assert score["f1"] == pytest.approx(8 / 11)
    assert score["reference_quote_exact_matches"] == 8
    extra = r["extra_claims_not_in_reference"]
    assert {x["group"] for x in extra} == {"terminal_relations", "character_claims"}
    assert any(x["identity"] == ("new:white_folder", "OWNED_BY", "character:Aylin")
               or x["identity"] == ["new:white_folder", "OWNED_BY", "character:Aylin"]
               for x in extra)
    assert any(x["group"] == "character_claims" and
               x["identity"][1:4] == ("emotion", "relieved", None)
               for x in extra)
    assert len(r["matched_reference_claims"]) == 8
    assert len(r["missed_reference_claims"]) == 4
    assert sum(g["true_positive"] for g in r["by_claim_group"].values()) == 8
    assert sum(g["false_positive"] for g in r["by_claim_group"].values()) == 2
    assert sum(g["false_negative"] for g in r["by_claim_group"].values()) == 4
    assert r["evaluation_scope"] == (
        "OPEN_FIXTURE_CLAIM_IDENTITY_NOT_BLIND_MODEL_EVALUATION")
    assert r["real_model_success_measured"] is False
    assert r["provider_calls"] == 0
    assert d == before
    assert calibrate(**arguments(d)) == r


def test_empty_prediction_never_claims_full_recall_or_success():
    kw = arguments(data())
    empty = copy.deepcopy(kw["candidate_raw_output"])
    for group in CLAIM_GROUPS:
        empty[group] = []
    kw["candidate_raw_output"] = empty
    report = calibrate(**kw)
    assert report["overall"]["true_positive"] == 0
    assert report["overall"]["false_positive"] == 0
    assert report["overall"]["false_negative"] == 12
    assert report["overall"]["precision"] == 0.0
    assert report["overall"]["recall"] == 0.0
    assert report["real_model_success_measured"] is False


def test_same_identity_wrong_quote_does_not_count_as_reference_citation_match():
    kw = arguments(data())
    kw["candidate_raw_output"] = copy.deepcopy(kw["gold_raw_output"])
    kw["candidate_raw_output"]["goal_claims"][0]["evidence"] = [
        {"quote": "Aylin gülümsedi."}
    ]
    r = calibrate(**kw)
    assert r["overall"]["true_positive"] == 12  # identity only
    assert r["overall"]["reference_quote_exact_matches"] == 11
    assert r["false_positive_semantic_support_independently_verified"] is False


@pytest.mark.parametrize("damage", [
    "wrong_seed", "wrong_source", "missing_quote", "fake_actor",
    "fake_goal", "invented_decisive_clue", "new_owner_not_admitted",
    "duplicate_relation", "raw_authority_injection", "type_changed",
    "gold_modified", "duplicate_semantic_identity",
])
def test_invalid_raw_envelopes_fail_closed_in_existing_gates(damage):
    kw = arguments(data())
    raw = kw["candidate_raw_output"]
    if damage == "wrong_seed":
        raw["seed_sha256"] = "0" * 64
    elif damage == "wrong_source":
        raw["source_sha256"] = "0" * 64
    elif damage == "missing_quote":
        raw["objects"][0]["mention"]["quote"] = "A neon-white folder appeared from thin air."
    elif damage == "fake_actor":
        raw["character_claims"][0]["actor"] = "NeverSeen"
    elif damage == "fake_goal":
        raw["goal_claims"][0]["goal_id"] = "invented_goal"
    elif damage == "invented_decisive_clue":
        raw["objects"][0]["role"] = "DECISIVE_CLUE"
    elif damage == "new_owner_not_admitted":
        kw["policy"]["allow_new_ordinary_objects"] = False
    elif damage == "duplicate_relation":
        raw["terminal_relations"].append(copy.deepcopy(raw["terminal_relations"][0]))
    elif damage == "raw_authority_injection":
        raw["state_commit_authorized"] = True
    elif damage == "type_changed":
        raw["goal_claims"][0]["outcome"] = 1
    elif damage == "gold_modified":
        kw["gold_raw_output"]["source_sha256"] = "0" * 64
    elif damage == "duplicate_semantic_identity":
        raw["objects"].append(copy.deepcopy(raw["objects"][0]))
    with pytest.raises(ValueError):
        calibrate(**kw)


def test_cli_replays_frozen_fixture_and_cannot_modify_it():
    before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_extraction_benchmark",
        "--fixture", str(FIXTURE),
    ]
    result = json.loads(subprocess.check_output(cmd, text=True, encoding="utf8"))
    assert result == calibrate(**arguments(data()))
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == before
