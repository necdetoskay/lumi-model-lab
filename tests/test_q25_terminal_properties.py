"""Regression and adversarial tests for read-only Q25 terminal property candidates."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_terminal_properties import property_candidates
from src.q25_state_coverage import coverage_report

ROOT = Path("evidence/q25")
BASE = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
ENTITY = ROOT / "Q25-ENTITY-CANDIDATE-20261012/proposal.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"
STORY = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012/story-proposal.json"
PROPERTY = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012/property-proposal.json"


def read(p):
    return json.loads(p.read_text(encoding="utf8"))


def inputs():
    return {
        "seed": read(BASE / "seed-input.json"),
        "prose": read(BASE / "writer-2-text.json")["text"],
        "entity_proposal": read(ENTITY),
        "policy": read(POLICY),
        "proposal": read(PROPERTY),
    }


def test_q24_property_claim_is_candidate_and_seed_remains_unchanged():
    kw = inputs()
    before = copy.deepcopy(kw)
    result = property_candidates(**kw)
    assert result["status"] == "SOURCE_BOUND_CANDIDATES_NOT_SEMANTICALLY_VERIFIED"
    assert result["proposed_properties"] == kw["proposal"]["claims"]
    assert result["proposed_properties"][0]["expected_seed_value"] is False
    assert result["proposed_properties"][0]["proposed_terminal_value"] is True
    assert kw["seed"]["objects"]["red_bookmark"]["state"]["found"] is False
    assert result["state_commit_authorized"] is False
    assert result["semantic_support_certified"] is False
    assert result["full_story_state_qualified"] is False
    assert result["provider_calls"] == 0
    assert kw == before
    assert result == property_candidates(**kw)


def test_coverage_marks_only_the_cited_property_and_preserves_other_gaps():
    kw = inputs()
    old = coverage_report(seed=kw["seed"], prose=kw["prose"],
        entity_proposal=kw["entity_proposal"], policy=kw["policy"],
        story_proposal=read(STORY))
    new = coverage_report(seed=kw["seed"], prose=kw["prose"],
        entity_proposal=kw["entity_proposal"], policy=kw["policy"],
        story_proposal=read(STORY), property_proposal=kw["proposal"])
    rows = {r["path"]: r for r in new["fields"]}
    key = "/objects/red_bookmark/properties/found"
    assert rows[key]["status"] == "CANDIDATE"
    assert rows[key]["evidence"] == kw["proposal"]["claims"][0]["evidence"]
    assert rows["/objects/red_bookmark/properties/returned_to_owner"]["status"] == "UNASSESSED"
    assert rows["/world/time"]["status"] == "UNASSESSED"
    assert sum(new["counts"].values()) == new["blocking_field_count"]
    assert new["blocking_field_count"] == old["blocking_field_count"]
    assert new["counts"]["CANDIDATE"] == old["counts"]["CANDIDATE"] + 1
    assert new["counts"]["UNASSESSED"] == old["counts"]["UNASSESSED"] - 1
    assert "property_proposal_sha256" in new and "property_proposal_sha256" not in old
    assert not new["full_story_state_qualified"]
    assert not new["state_commit_authorized"]


@pytest.mark.parametrize("damage", [
    "bad_seed", "bad_source", "missing_object", "new_book", "missing_property",
    "container", "list_value", "type_change", "precondition",
    "no_op", "bad_quote", "out_of_bounds", "empty_evidence",
    "duplicate_claim", "duplicate_evidence", "unknown_kind", "policy_denial",
])
def test_bad_property_candidates_fail_closed(damage):
    kw = inputs()
    claim = kw["proposal"]["claims"][0]
    if damage == "bad_seed":
        kw["proposal"]["seed_sha256"] = "0" * 64
    elif damage == "bad_source":
        kw["proposal"]["source_sha256"] = "0" * 64
    elif damage == "missing_object":
        claim["object_id"] = "unknown_object"
    elif damage == "new_book":
        claim["object_id"] = "new_9812aca595ec152bb0146faf97bc51e0cf92ffc47b1fd2e6b7bb68c6218c85a9"
    elif damage == "missing_property":
        claim["property_name"] = "invented_status"
    elif damage == "container":
        claim.update(property_name="container", expected_seed_value="blue_atlas", proposed_terminal_value="red_bookmark")
    elif damage == "list_value":
        claim["proposed_terminal_value"] = ["invented"]
    elif damage == "type_change":
        claim["proposed_terminal_value"] = "true"
    elif damage == "precondition":
        claim["expected_seed_value"] = True
    elif damage == "no_op":
        claim["proposed_terminal_value"] = False
    elif damage == "bad_quote":
        claim["evidence"][0]["text"] = "nonexistent quote"
    elif damage == "out_of_bounds":
        claim["evidence"][0]["end"] = len(kw["prose"]) + 100
    elif damage == "empty_evidence":
        claim["evidence"] = []
    elif damage == "duplicate_claim":
        kw["proposal"]["claims"].append(copy.deepcopy(claim))
    elif damage == "duplicate_evidence":
        claim["evidence"].append(copy.deepcopy(claim["evidence"][0]))
    elif damage == "unknown_kind":
        claim["evidence_kind"] = "CERTIFIED"
    elif damage == "policy_denial":
        kw["policy"]["allow_new_ordinary_objects"] = False
    with pytest.raises(ValueError):
        property_candidates(**kw)


def test_structurally_valid_citation_does_not_mean_semantic_truth():
    kw = inputs()
    kw["proposal"]["claims"][0]["evidence_kind"] = "INFERRED"
    result = property_candidates(**kw)
    assert result["proposed_properties"][0]["evidence_kind"] == "INFERRED"
    assert result["semantic_support_certified"] is False


def test_empty_claims_are_not_implicit_facts():
    kw = inputs()
    kw["proposal"]["claims"] = []
    result = property_candidates(**kw)
    assert result["proposed_properties"] == []
    assert result["full_story_state_qualified"] is False


def test_q24_property_cli_replays_without_mutating_archived_files():
    kw = inputs()
    sources = [BASE / "seed-input.json", BASE / "writer-2-text.json",
               ENTITY, POLICY, PROPERTY, STORY]
    original_hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
    cmd = [sys.executable, "-X", "utf8", "-m", "src.q25_terminal_properties",
           "--seed", str(sources[0]), "--prose-record", str(sources[1]),
           "--entity-proposal", str(ENTITY), "--policy", str(POLICY),
           "--property-proposal", str(PROPERTY)]
    output = json.loads(subprocess.check_output(cmd, encoding="utf8", text=True))
    assert output == property_candidates(**kw)
    assert original_hashes == [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]


@pytest.mark.parametrize("structural_key", ["owner", "location", "held_by", "identity_status", "inventory"])
def test_property_claim_cannot_impersonate_graph_or_identity_field(structural_key):
    from src.q25_entity_candidates import fingerprint
    kw = inputs()
    kw["seed"]["objects"]["red_bookmark"]["state"][structural_key] = "seed_value"
    sha = fingerprint(kw["seed"])
    kw["entity_proposal"]["seed_sha256"] = sha
    kw["proposal"]["seed_sha256"] = sha
    kw["proposal"]["claims"][0].update(
        property_name=structural_key,
        expected_seed_value="seed_value", proposed_terminal_value="changed_value",
    )
    with pytest.raises(ValueError, match="non-relational properties"):
        property_candidates(**kw)


def test_coverage_cli_with_explicit_property_proposal_is_deterministic():
    kw = inputs()
    sources = [BASE / "seed-input.json", BASE / "writer-2-text.json",
               ENTITY, POLICY, STORY, PROPERTY]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
    cmd = [sys.executable, "-X", "utf8", "-m", "src.q25_state_coverage",
           "--seed", str(sources[0]), "--prose-record", str(sources[1]),
           "--entity-proposal", str(ENTITY), "--policy", str(POLICY),
           "--story-proposal", str(STORY), "--property-proposal", str(PROPERTY)]
    actual = json.loads(subprocess.check_output(cmd, encoding="utf8", text=True))
    expected = coverage_report(seed=kw["seed"], prose=kw["prose"],
        entity_proposal=kw["entity_proposal"], policy=kw["policy"],
        story_proposal=read(STORY), property_proposal=kw["proposal"])
    assert actual == expected
    assert actual["fields"] and actual["state_commit_authorized"] is False
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
