"""Greenhouse cold-story baseline before any paid request.

All gold labels are authored and unreviewed; comparing labels to themselves
does not measure model performance, independence or accepted StoryState.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_withheld_trial import preflight, evaluate, unpack_request
from src.q25_raw_reconciliation import project_raw
from src.q25_openrouter_pilot import build_wire_request, PilotStop

BASE = Path("evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012")
MODEL = "anthropic/claude-sonnet-5.5"


def request():
    return json.loads((BASE / "request.json").read_text(encoding="utf8"))


def reference():
    return json.loads((BASE / "provisional-reference.json").read_text(encoding="utf8"))


def test_completely_separate_story_source_compiles_without_seeing_answers():
    package, key = request(), reference()
    before = copy.deepcopy((package, key))
    assert package["schema_name"] == "q25.withheld-request.v1"
    assert package["request_id"] == key["request_id"] == "GREENHOUSE-01"
    assert package["labels_included"] is False
    assert package["model_inputs_only"] is True
    assert "Mina" in package["seed"]["characters"]
    assert "Eren" in package["seed"]["characters"]
    assert package["seed"]["topology"]["locations"] == [
        "greenhouse", "storage_room", "courtyard"]
    assert package["seed"]["characters"]["Eren"]["location"] == "storage_room"
    p = preflight(request_package=package, model=MODEL)
    assert p["seed_sha256"] == key["seed_sha256"]
    assert p["source_sha256"] == key["source_sha256"]
    assert p["reference_labels_loaded"] is False
    assert p["reference_labels_sent_to_model"] is False
    assert p["max_calls"] == 1
    assert p["max_cost_usd"] == "0.20"
    assert p["state_commit_authorized"] is False
    inp = unpack_request(package)
    wire = build_wire_request(seed=inp["seed"], prose=inp["prose"],
                              model=MODEL, max_tokens=3500)
    serialized = json.dumps(wire, ensure_ascii=False)
    assert "raw_reference" not in serialized
    assert "provisional-reference" not in serialized
    assert "copper_bell" not in serialized
    assert "read_Defne_placement_note" not in serialized
    assert wire["provider"] == {
        "require_parameters": True, "allow_fallbacks": False}
    assert (package, key) == before
    assert p == preflight(request_package=package, model=MODEL)


def test_reference_is_source_bound_but_not_independently_reviewed_or_model_output():
    data = request()
    ref = reference()
    result = evaluate(request_package=data, reference_package=ref,
                      raw_response=ref["raw_reference"])
    assert result["reference_claim_count"] == result["candidate_claim_count"] == 16
    assert result["overall"]["true_positive"] == 16
    assert result["overall"]["false_positive"] == 0
    assert result["overall"]["false_negative"] == 0
    assert result["real_model_success_measured"] is False
    assert result["reference_labels_independently_adjudicated"] is False
    assert result["independent_human_adjudication_complete"] is False
    assert result["state_commit_authorized"] is False
    assert result["provider_calls"] == 0


def test_author_reference_structural_projection_exposes_time_and_attachment_gaps():
    data = request()
    ref = reference()["raw_reference"]
    result = project_raw(
        seed=data["seed"], prose=data["prose_record"]["text"],
        raw_output=ref, policy=data["policy"])
    assert result["schema"] == "q25.raw-terminal-hypothesis.v1"
    assert result["blocking_field_count"] == 54
    assert result["structural_consistency"]["status"] == (
        "STRUCTURALLY_COHERENT_CANDIDATES_ONLY")
    objects = result["candidate_state"]["objects"]
    assert objects["roof_vent"]["properties"]["open"]["terminal_proposal"] is False
    assert objects["seedling_tray"]["properties"]["covered"]["terminal_proposal"] is True
    assert objects["seedling_tray"]["properties"]["wet"]["terminal_proposal"] is None
    assert objects["blue_tarp"]["properties"]["folded"]["terminal_proposal"] is False
    assert objects["blue_tarp"]["location"]["ref"] == "greenhouse"
    bell = next(x for name, x in objects.items() if name.startswith("new_"))
    assert bell["owner"]["status"] == "UNKNOWN"
    assert bell["location"]["status"] == "UNKNOWN"
    assert result["candidate_state"]["characters"]["Eren"]["initial_reference"]["location"] == "storage_room"
    assert any(x["field"] == "location" and x["candidate_terminal_value"] == "greenhouse"
               for x in result["candidate_state"]["characters"]["Eren"][
                   "terminal_scalar_change_candidates"])
    assert result["candidate_state"]["world_initial_reference"]["time"][
        "minutes_until_shift_end"] == 25
    assert result["candidate_state"]["proposed_world_time"] is None
    assert result["candidate_state"]["world_time_unassessed"] is True
    assert len(result["proposed_obligation_closures"]) == 3
    assert result["approved_obligation_closures"] == []
    assert result["state_commit_authorized"] is False
    assert result["full_story_state_qualified"] is False
    assert result["independent_semantic_review_completed"] is False


@pytest.mark.parametrize("error", [
    "story_modified", "seed_modified", "reference_sha_forged",
    "reference_claim_unknown", "new_character_unverified", "fake_quote",
    "fake_paid_status", "labels_mixed_into_request",
])
def test_cold_story_and_sealed_labels_fail_closed_on_tampering(error):
    data = request()
    key = reference()
    raw = copy.deepcopy(key["raw_reference"])
    if error == "story_modified":
        data["prose_record"]["text"] += " new unsupported claim"
    elif error == "seed_modified":
        data["seed"]["objects"]["roof_vent"]["state"]["open"] = False
    elif error == "reference_sha_forged":
        key["source_sha256"] = "0" * 64
    elif error == "reference_claim_unknown":
        raw["property_claims"][0]["object_id"] = "invented_prop"
    elif error == "new_character_unverified":
        raw["character_claims"][0]["actor"] = "HiddenObserver"
    elif error == "fake_quote":
        raw["objects"][0]["mention"]["quote"] = "not in original story"
    elif error == "fake_paid_status":
        key["review_status"] = "INDEPENDENTLY_CERTIFIED"
    elif error == "labels_mixed_into_request":
        data["provisional_reference"] = key
    with pytest.raises(ValueError):
        evaluate(request_package=data, reference_package=key, raw_response=raw)


def test_workflow_is_manual_only_single_paid_post_and_excludes_reference():
    workflow = Path(".github/workflows/q25-offline-diagnostic.yml").read_text("utf8")
    paid = workflow.split("  paid-extractor-pilot:\n", 1)[1]
    assert "          - greenhouse-01" in workflow
    assert "greenhouse-01)" in paid
    assert "--request-package evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/request.json" in paid
    assert "Q25_TRIAL_CASE" in paid
    assert "provisional-reference.json" not in paid
    assert "github.event_name == 'workflow_dispatch' && inputs.execute_paid == true && github.run_attempt == 1" in paid
    assert paid.count("--execute-paid-once") == 1
    assert "--max-cost-usd 0.20" in paid
    assert "--max-tokens 3500" in paid


def test_preflight_cli_has_zero_provider_calls():
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_withheld_trial",
        "--request-package", str(BASE / "request.json"), "--model", MODEL,
    ]
    result = json.loads(subprocess.check_output(cmd, text=True, encoding="utf8"))
    assert result == preflight(request_package=request(), model=MODEL)
    assert result["provider_calls"] == 0
    assert result["state_commit_authorized"] is False
