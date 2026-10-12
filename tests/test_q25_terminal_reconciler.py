"""Q25 reconciliation is a source-bound, read-only candidate—not final canon."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_terminal_reconciler import _checked_graph, classify_field, reconcile


ROOT = Path("evidence/q25")
Q24 = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
CASE = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012"
ENTITY = ROOT / "Q25-ENTITY-CANDIDATE-20261012/proposal.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"
STORY = CASE / "story-proposal-knowledge-extension.json"
PROPERTY = CASE / "property-proposal-return-candidate.json"
ANNOTATIONS = CASE / "review-gap-annotations.json"
ASSESSMENTS = CASE / "provisional-meaning-assessment.json"


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def source():
    return {
        "seed": load(Q24 / "seed-input.json"),
        "prose": load(Q24 / "writer-2-text.json")["text"],
        "entity_proposal": load(ENTITY),
        "policy": load(POLICY),
        "story_proposal": load(STORY),
        "property_proposal": load(PROPERTY),
        "annotations": load(ANNOTATIONS),
        "assessments": load(ASSESSMENTS),
    }


def test_q24_reconciler_has_coherent_container_graph_without_forging_canon():
    inputs = source()
    originals = copy.deepcopy(inputs)
    r = reconcile(**inputs)
    assert r["schema"] == "q25.terminal-reconciliation-candidate.v1"
    assert r["field_count"] == 70
    assert sum(r["field_policy_counts"].values()) == 70
    assert r["pending_review_count"] == 70
    assert r["independently_certified_field_count"] == 0
    assert r["approved_narrative_obligation_closures"] == []
    assert r["structural_consistency"]["status"] == (
        "STRUCTURALLY_COHERENT_CANDIDATES_ONLY")
    assert r["structural_consistency"]["reciprocal_container_pairs"] == 1
    assert not r["structural_consistency"]["semantic_truth_checked"]
    assert not r["full_story_state_qualified"]
    assert not r["state_commit_authorized"]
    assert not r["production_write_performed"]
    assert not r["semantic_support_certified"]
    assert r["provider_calls"] == 0
    objects = r["candidate_state"]["objects"]
    book_id = next(k for k in objects if k.startswith("new_"))
    assert objects[book_id]["identity_status"] == "PROPOSED"
    assert objects[book_id]["identity_authority"] == "NEW_UNADMITTED_IDENTITY"
    assert objects[book_id]["owner"]["status"] == "UNKNOWN"
    assert objects[book_id]["location"]["status"] == "UNKNOWN"
    assert objects[book_id]["contains"] == ["red_bookmark"]
    assert objects["red_bookmark"]["container"]["ref"] == book_id
    assert objects["red_bookmark"]["held_by"]["status"] == "NONE"
    assert objects["blue_atlas"]["contains"] == []
    assert objects["red_bookmark"]["owner"]["ref"] == "Nisa"
    assert objects["blue_atlas"]["owner"]["ref"] == "library"
    assert objects["red_bookmark"]["properties"]["found"]["initial_value"] is False
    assert objects["red_bookmark"]["properties"]["found"]["proposed_terminal_value"] is True
    assert objects["red_bookmark"]["properties"]["returned_to_owner"][
        "proposed_terminal_value"] is True
    assert objects["red_bookmark"]["properties"]["returned_to_owner"][
        "provisional_review_category"] == "CONTEXT_DEPENDENT"
    assert objects["red_bookmark"]["properties"]["intentionally_stolen"][
        "proposed_terminal_value"] is None
    assert objects["red_bookmark"]["properties"]["intentionally_stolen"][
        "terminal_value_assessed"] is False
    assert r["structural_consistency"]["directly_held_objects"] == {
        "Cem": [], "Eren": [], "Nisa": []}
    assert inputs == originals
    assert r == reconcile(**inputs)


def test_character_world_and_obligations_stay_in_separate_evidence_layers():
    r = reconcile(**source())
    chars = r["candidate_state"]["characters"]
    assert chars["Nisa"]["initial_condition"]["emotion"] == "worried"
    assert any(x["field"] == "emotion" and x["candidate_terminal_value"] == "relieved"
               for x in chars["Nisa"]["proposed_scalar_changes"])
    assert chars["Nisa"]["terminal_emotion_certified"] is False
    assert chars["Cem"]["initial_relationships"]["Nisa"]["trust"] == "good"
    assert chars["Cem"]["relationship_trust_certified"] is False
    assert chars["Cem"]["knowledge_completeness_certified"] is False
    assert {x["actor"] for x in (
        sum((c["proposed_knowledge_additions"] for c in chars.values()), []))} == {
            "Nisa", "Eren", "Cem"}
    assert chars["Cem"]["proposed_goal_outcome"]["proposed_outcome"] == "ACHIEVED"
    world = r["candidate_state"]["world"]
    assert world["seed_reference"]["time"]["minutes_until_reading_activity"] == 30
    assert world["proposed_terminal_time"] is None
    assert world["time_unassessed"] is True
    assert all(x["seed_status"] == "OPEN" and x["proposed_outcome"] == "SATISFIED"
               for x in r["candidate_state"]["narrative_obligations"])
    assert r["approved_narrative_obligation_closures"] == []


def test_no_unobserved_seed_value_is_promoted_to_proven_terminal():
    r = reconcile(**source())
    rows = {row["path"]: row for row in r["field_decisions"]}
    assert len(rows) == 70
    assert all(not row["initial_is_terminal_proof"] and not row["accepted_as_final"]
               for row in rows.values())
    assert rows["/objects/blue_atlas/owner"]["reconciliation_policy"] == (
        "STRUCTURAL_SEED_OR_PROPOSED_RELATION_ONLY")
    assert rows["/objects/red_bookmark/properties/color"][
        "reconciliation_policy"] == "HISTORICAL_SEED_FACT_UNVERIFIED_AT_TERMINAL"
    assert rows["/objects/red_bookmark/properties/intentionally_stolen"][
        "reconciliation_policy"] == "UNASSESSED_DO_NOT_INFER_UNCHANGED"
    assert rows["/characters/Cem/relationships/Nisa/trust"][
        "reconciliation_policy"] == "UNASSESSED_DO_NOT_INFER_UNCHANGED"
    assert rows["/world/time"]["reconciliation_policy"] == (
        "UNASSESSED_DO_NOT_INFER_UNCHANGED")
    assert rows["/characters/Nisa/knowledge"]["reconciliation_policy"] == (
        "PARTIAL_KNOWLEDGE_CANDIDATE")
    assert rows["/objects/red_bookmark/properties/returned_to_owner"][
        "reconciliation_policy"] == "UNVERIFIED_TERMINAL_CANDIDATE"
    assert any(row["reconciliation_policy"] == "UNKNOWN_REQUIRES_EVIDENCE"
               for row in rows.values())


@pytest.mark.parametrize("bad", [
    "nonreciprocal", "duplicate_contains", "invented_container",
    "dual_holder", "unknown_holder", "forged_location", "self_cycle",
    "wrong_known_ref", "none_with_ref", "invalid_status",
])
def test_candidate_graph_guard_fails_closed_on_inconsistencies(bad):
    r = reconcile(**source())
    objects = copy.deepcopy(r["candidate_state"]["objects"])
    obj = objects["red_bookmark"]
    if bad == "nonreciprocal":
        objects["blue_atlas"]["contains"].append("red_bookmark")
    elif bad == "duplicate_contains":
        book = next(k for k in objects if k.startswith("new_"))
        objects[book]["contains"].append("red_bookmark")
    elif bad == "invented_container":
        obj["container"]["ref"] = "not_a_book"
    elif bad == "dual_holder":
        obj["held_by"] = {"status": "KNOWN", "ref": "Nisa"}
    elif bad == "unknown_holder":
        obj["held_by"] = {"status": "KNOWN", "ref": "UnknownPerson"}
    elif bad == "forged_location":
        obj["location"]["ref"] = "never_in_topology"
    elif bad == "self_cycle":
        obj["container"]["ref"] = "red_bookmark"
    elif bad == "wrong_known_ref":
        obj["location"]["status"] = "KNOWN"
        obj["location"]["ref"] = None
    elif bad == "none_with_ref":
        obj["held_by"]["ref"] = "Nisa"
    elif bad == "invalid_status":
        obj["held_by"]["status"] = "CERTIFIED"
    with pytest.raises(ValueError):
        _checked_graph(objects, {"library_reading_room"}, source()["seed"]["characters"])


@pytest.mark.parametrize("tamper", [
    "seed", "prose", "new_role", "missing_knowledge", "wrong_property_quote",
    "faked_assessment", "policy_denies_unknown_owner",
])
def test_any_invalid_upstream_input_refuses_projection(tamper):
    kw = source()
    if tamper == "seed":
        kw["seed"]["objects"]["red_bookmark"]["state"]["found"] = True
    elif tamper == "prose":
        kw["prose"] += " fabricated."
    elif tamper == "new_role":
        kw["entity_proposal"]["objects"][0]["role"] = "DECISIVE_CLUE"
    elif tamper == "missing_knowledge":
        kw["story_proposal"]["character_claims"][0]["epistemic_type"] = None
    elif tamper == "wrong_property_quote":
        kw["property_proposal"]["claims"][0]["evidence"][0]["text"] = "fake"
    elif tamper == "faked_assessment":
        kw["assessments"]["findings"][0]["review_decision"] = "APPROVED"
    elif tamper == "policy_denies_unknown_owner":
        kw["policy"]["allow_unknown_owner"] = False
    with pytest.raises(ValueError):
        reconcile(**kw)


def test_cli_output_is_identical_and_does_not_write_source_inputs():
    paths = [
        Q24 / "seed-input.json", Q24 / "writer-2-text.json",
        ENTITY, POLICY, STORY, PROPERTY, ANNOTATIONS, ASSESSMENTS,
    ]
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_terminal_reconciler",
        "--seed", str(paths[0]), "--prose-record", str(paths[1]),
        "--entity-proposal", str(ENTITY), "--policy", str(POLICY),
        "--story-proposal", str(STORY), "--property-proposal", str(PROPERTY),
        "--annotations", str(ANNOTATIONS), "--assessments", str(ASSESSMENTS),
    ]
    result = json.loads(subprocess.check_output(cmd, text=True, encoding="utf8"))
    assert result == reconcile(**source())
    assert hashes == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]


def test_reconciliation_classification_rejects_unrecognized_status():
    with pytest.raises(ValueError):
        classify_field({
            "coverage_status": "CERTIFIED",
            "terminal_hypothesis": {"status": "UNKNOWN_INVENTED"},
            "category": "CHARACTER",
            "path": "/characters/Nisa/location",
        })
