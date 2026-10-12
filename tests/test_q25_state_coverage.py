import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_state_coverage import coverage_report

ROOT = Path("evidence/q25")
BASE = ROOT / "Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24"
ENTITY = ROOT / "Q25-ENTITY-CANDIDATE-20261012/proposal.json"
POLICY = ROOT / "Q25-ADMISSION-DRAFT-20261012/policy.json"
STORY = ROOT / "Q25-STORY-STATE-CANDIDATES-20261012/story-proposal.json"


def read(p):
    return json.loads(p.read_text(encoding="utf8"))


def case():
    return dict(seed=read(BASE / "seed-input.json"),
                prose=read(BASE / "writer-2-text.json")["text"],
                entity_proposal=read(ENTITY),
                policy=read(POLICY),
                story_proposal=read(STORY))


def test_q24_coverage_is_incomplete_even_when_all_obligations_have_citations():
    kw = case()
    before = copy.deepcopy(kw)
    report = coverage_report(**kw)
    rows = {r["path"]: r for r in report["fields"]}
    new = next(k for k in rows if k.startswith("/objects/new_") and k.endswith("/owner"))
    assert rows[new]["status"] == "UNKNOWN"
    assert rows[new.replace("/owner", "/location")]["status"] == "UNKNOWN"
    assert rows["/objects/red_bookmark/properties/found"]["status"] == "UNASSESSED"
    assert rows["/objects/blue_atlas/contains"]["status"] == "STRUCTURAL_ONLY"
    assert rows["/characters/Nisa/knowledge"]["status"] == "PARTIAL_CANDIDATES"
    assert rows["/characters/Nisa/condition/emotion"]["status"] == "CANDIDATE"
    assert rows["/characters/Cem/condition/emotion"]["status"] == "UNASSESSED"
    assert rows["/characters/Eren/condition/goal"]["status"] == "CANDIDATE"
    assert rows["/narrative_obligations/investigate_evidence/status"]["status"] == "CANDIDATE"
    assert rows["/narrative_obligations/recover_bookmark/status"]["status"] == "CANDIDATE"
    assert rows["/narrative_obligations/correct_and_apologize/status"]["status"] == "CANDIDATE"
    assert rows["/open_threads/correct_suspicion"]["status"] == "CANDIDATE"
    assert rows["/world/time"]["status"] == "UNASSESSED"
    assert report["coverage"].startswith("INCOMPLETE")
    assert report["blocking_field_count"] == len(rows)
    assert sum(report["counts"].values()) == len(rows)
    assert not report["state_commit_authorized"]
    assert not report["full_story_state_qualified"]
    assert not report["semantic_support_certified"]
    assert report["provider_calls"] == 0
    assert kw == before
    assert report == coverage_report(**kw)



def test_q24_seed_to_candidate_comparison_exposes_changes_and_all_gaps():
    kw = case()
    kw["property_proposal"] = read(ROOT / "Q25-STORY-STATE-CANDIDATES-20261012/property-proposal.json")
    before = copy.deepcopy(kw)
    report = coverage_report(**kw)
    delta = report["initial_to_candidate_comparison"]
    objects = {d["path"]: d for d in delta["object_changes"]}
    assert objects["/objects/red_bookmark/properties/found"]["seed_value"] is False
    assert objects["/objects/red_bookmark/properties/found"]["candidate_terminal_value"] is True
    assert objects["/objects/red_bookmark/container"]["seed_value"] == "blue_atlas"
    assert objects["/objects/red_bookmark/container"]["candidate_terminal_value"].startswith("new_")
    assert objects["/objects/blue_atlas/contains"]["seed_value"] == ["red_bookmark"]
    assert objects["/objects/blue_atlas/contains"]["candidate_terminal_value"] == []
    assert "/objects/red_bookmark/properties/returned_to_owner" not in objects
    assert any(x["path"] == "/objects/red_bookmark/properties/returned_to_owner"
               and x["status"] == "UNASSESSED" for x in delta["explicit_gaps"])
    assert {c["actor"] for c in delta["character_changes"] if c["field"] == "knowledge"} == {"Nisa", "Eren", "Cem"}
    assert len(delta["goal_outcomes"]) == 3
    assert set(delta["proposed_closed_obligations"]) == {
        "investigate_evidence", "recover_bookmark", "correct_and_apologize"}
    assert delta["independently_certified_closed_obligations"] == []
    assert set(delta["contested_or_unverified_obligations"]) == set(delta["proposed_closed_obligations"])
    assert all(x["disposition"] == "PENDING_INDEPENDENT_SEMANTIC_REVIEW"
               for x in delta["narrative_obligations"])
    assert {x["proposed_outcome"] for x in delta["open_threads"]} == {"RESOLVED"}
    assert len(delta["new_object_candidates"]) == 1
    assert delta["new_object_candidates"][0]["owner"]["status"] == "UNKNOWN"
    assert delta["new_object_candidates"][0]["location"]["status"] == "UNKNOWN"
    assert delta["world_time"]["disposition"] == "UNASSESSED"
    assert not delta["state_commit_authorized"]
    assert not report["state_commit_authorized"]
    assert kw == before


def test_no_claims_never_infers_a_closed_goal_or_obligation():
    kw = case()
    kw["story_proposal"].update(
        character_claims=[], goal_claims=[],
        obligation_claims=[], thread_claims=[]
    )
    r = coverage_report(**kw)
    bypath = {row["path"]: row for row in r["fields"]}
    assert bypath["/characters/Nisa/condition/goal"]["status"] == "UNASSESSED"
    assert bypath["/narrative_obligations/recover_bookmark/status"]["status"] == "UNASSESSED"
    assert bypath["/open_threads/find_missing_bookmark"]["status"] == "UNASSESSED"
    assert not r["full_story_state_qualified"]


@pytest.mark.parametrize("tamper", [
    "source_sha", "wrong_quote", "invented_goal",
    "uncited_obligation", "unapproved_object", "unknown_owner_disallowed",
])
def test_coverage_does_not_allow_invalid_or_denied_inputs(tamper):
    kw = case()
    if tamper == "source_sha":
        kw["story_proposal"]["source_sha256"] = "0" * 64
    elif tamper == "wrong_quote":
        kw["story_proposal"]["goal_claims"][0]["evidence"][0]["text"] = "Not the source"
    elif tamper == "invented_goal":
        kw["story_proposal"]["goal_claims"][0]["goal_id"] = "wishful_result"
    elif tamper == "uncited_obligation":
        kw["story_proposal"]["obligation_claims"][0]["evidence"] = []
    elif tamper == "unapproved_object":
        kw["entity_proposal"]["objects"][0]["role"] = "DECISIVE_CLUE"
    elif tamper == "unknown_owner_disallowed":
        kw["policy"]["allow_unknown_owner"] = False
    with pytest.raises(ValueError):
        coverage_report(**kw)


def test_report_cli_is_read_only_and_matches_python_output():
    kw = case()
    sources = [BASE / "seed-input.json", BASE / "writer-2-text.json", ENTITY, POLICY, STORY]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
    cmd = [sys.executable, "-X", "utf8", "-m", "src.q25_state_coverage",
           "--seed", str(sources[0]), "--prose-record", str(sources[1]),
           "--entity-proposal", str(ENTITY), "--policy", str(POLICY),
           "--story-proposal", str(STORY)]
    text = subprocess.check_output(cmd, encoding="utf8", text=True)
    assert json.loads(text) == coverage_report(**kw)
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
