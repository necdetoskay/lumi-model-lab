"""Q25 clock/physical-relation annotation sidecar: read-only, zero cost."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_terminal_supplement import project_supplement

ROOT = Path("evidence/q25")
GREENHOUSE = ROOT / "Q25-GREENHOUSE-COLD-TRIAL-20261012"
KITE = ROOT / "Q25-WITHHELD-TRIAL-20261012"


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def scenario(case):
    raw_name = (
        "paid-attempt-01-raw-extraction.json" if case == GREENHOUSE
        else "paid-attempt-03-raw-extraction.json"
    )
    package = read(case / "request.json")
    return {
        "seed": package["seed"], "prose": package["prose_record"]["text"],
        "policy": package["policy"],
        "raw_output": read(case / raw_name),
        "supplement": read(case / "terminal-supplement-author-annotation.json"),
    }


def test_greenhouse_clock_and_covering_proposed_without_accepted_story_state():
    args = scenario(GREENHOUSE)
    before = copy.deepcopy(args)
    result = project_supplement(**args)
    assert result["schema"] == "q25.terminal-supplement-projection.v1"
    assert result["source_kind"] == "AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED"
    assert result["countdown_candidate_count"] == 1
    assert result["physical_relation_candidate_count"] == 1
    clock = result["world_time_candidates"][0]
    assert clock["path"] == "/world/time/minutes_until_shift_end"
    assert clock["seed_value"] == 25
    assert clock["terminal_proposal"] == 10
    assert clock["evidence"]["text"] == "Nöbet bitimine on dakika kaldığında"
    assert args["prose"][clock["evidence"]["start"]:clock["evidence"]["end"]] == clock["evidence"]["text"]
    edge = result["physical_relation_candidates"][0]
    assert edge["subject"] == "object:blue_tarp"
    assert edge["kind"] == "COVERING"
    assert edge["target"] == "object:seedling_tray"
    assert edge["source_binding_only"] is True
    assert edge["owner_inferred"] is False
    assert edge["location_inferred"] is False
    assert result["supplement_not_in_existing_extractor_contract"] is True
    assert result["independently_authenticated_reviewer"] is False
    assert result["semantic_support_certified"] is False
    assert result["full_story_state_qualified"] is False
    assert result["state_commit_authorized"] is False
    assert result["production_write_performed"] is False
    assert result["provider_calls"] == 0
    assert result["provider_cost_usd"] == 0.0
    assert args == before
    assert project_supplement(**args) == result


def test_kite_attachment_is_source_bound_and_elapsed_time_remains_unknown():
    args = scenario(KITE)
    result = project_supplement(**args)
    assert result["countdown_candidate_count"] == 0
    assert result["world_time_candidates"] == []
    assert result["physical_relation_candidate_count"] == 1
    edge = result["physical_relation_candidates"][0]
    assert edge["kind"] == "ATTACHED_TO"
    assert edge["subject"] == "new:gold_paper_star"
    assert edge["target"] == "object:red_kite"
    assert "altın renkli kâğıt yıldızı yapıştırdı" in edge["evidence"]["text"]
    assert result["state_commit_authorized"] is False


@pytest.mark.parametrize("mutation", [
    "seed_hash", "prose_hash", "raw_digest", "initial_clock",
    "wrong_clock", "negative_clock", "equal_clock", "greater_clock",
    "unseeded_clock", "made_up_clock_quote", "duplicate_clock",
    "invalid_edge_object", "invalid_edge_new_key", "wrong_edge_target",
    "self_link", "repeated_edge", "unsupported_relation",
    "fabricated_relation_evidence", "forged_origin", "corrupt_raw",
    "wrong_policy", "fake_canonical_authority",
])
def test_supplement_fails_closed_on_forgeries_and_missing_provenance(mutation):
    case = scenario(GREENHOUSE)
    suppl = case["supplement"]
    clock = suppl["world_time_claims"][0]
    edge = suppl["physical_relation_claims"][0]
    if mutation == "seed_hash":
        suppl["seed_sha256"] = "0"*64
    elif mutation == "prose_hash":
        suppl["source_sha256"] = "0"*64
    elif mutation == "raw_digest":
        suppl["raw_output_sha256"] = "0"*64
    elif mutation == "initial_clock":
        clock["expected_seed_value"] = 24
    elif mutation == "wrong_clock":
        clock["proposed_terminal_value"] = True
    elif mutation == "negative_clock":
        clock["proposed_terminal_value"] = -1
    elif mutation == "equal_clock":
        clock["proposed_terminal_value"] = 25
    elif mutation == "greater_clock":
        clock["proposed_terminal_value"] = 30
    elif mutation == "unseeded_clock":
        clock["field"] = "minutes_until_unknown"
    elif mutation == "made_up_clock_quote":
        clock["evidence"]["quote"] = "Nöbet bitimine iki dakika kaldığında"
    elif mutation == "duplicate_clock":
        suppl["world_time_claims"].append(copy.deepcopy(clock))
    elif mutation == "invalid_edge_object":
        edge["subject"] = "object:magic_tarp"
    elif mutation == "invalid_edge_new_key":
        edge["subject"] = "new:nonexistent_entity"
    elif mutation == "wrong_edge_target":
        edge["target"] = "character:Eren"
    elif mutation == "self_link":
        edge["target"] = edge["subject"]
    elif mutation == "repeated_edge":
        suppl["physical_relation_claims"].append(copy.deepcopy(edge))
    elif mutation == "unsupported_relation":
        edge["kind"] = "OWNED_BY"
    elif mutation == "fabricated_relation_evidence":
        edge["evidence"]["quote"] = "Mavi branda havaya uçtu ve kayboldu"
    elif mutation == "forged_origin":
        suppl["source_kind"] = "INDEPENDENTLY_VERIFIED_BY_AI"
    elif mutation == "corrupt_raw":
        case["raw_output"]["source_sha256"] = "0"*64
    elif mutation == "wrong_policy":
        case["policy"]["allow_new_ordinary_objects"] = False
    elif mutation == "fake_canonical_authority":
        suppl["state_commit_authorized"] = True
    with pytest.raises(ValueError):
        project_supplement(**case)


def test_no_implicit_clock_and_no_implicit_owner_or_location_when_empty():
    case = scenario(GREENHOUSE)
    case["supplement"]["world_time_claims"] = []
    case["supplement"]["physical_relation_claims"] = []
    result = project_supplement(**case)
    assert result["world_time_candidates"] == []
    assert result["physical_relation_candidates"] == []
    assert result["state_commit_authorized"] is False
    assert result["countdown_candidate_count"] == 0
    assert result["physical_relation_candidate_count"] == 0


def test_kite_ambiguity_cannot_be_filled_using_source_free_time_annotation():
    case = scenario(KITE)
    case["supplement"]["world_time_claims"] = [{
        "field": "minutes_until_demo",
        "expected_seed_value": 20,
        "proposed_terminal_value": 7,
        "evidence": {"quote": "Tam kaç dakika geçtiği söylenmedi."},
    }]
    # Even though this uncertainty quote exists, it never supplies the
    # numerical 7-minute value. Fail closed before producing a candidate.
    with pytest.raises(ValueError, match="numeric minute anchor"):
        project_supplement(**case)


def test_wrong_numeric_value_or_unspecified_terminal_time_is_not_proposed():
    case = scenario(GREENHOUSE)
    claim = case["supplement"]["world_time_claims"][0]
    claim["proposed_terminal_value"] = 9
    with pytest.raises(ValueError, match="numeric minute anchor"):
        project_supplement(**case)
    claim["proposed_terminal_value"] = 10
    claim["evidence"]["quote"] = "Nöbetin bitmesine yirmi beş dakika vardı."
    with pytest.raises(ValueError, match="numeric minute anchor"):
        project_supplement(**case)


def test_clock_lexical_anchor_is_conservative_and_explicit():
    from src.q25_terminal_supplement import _explicit_turkish_minute_anchor
    assert _explicit_turkish_minute_anchor("Nöbet bitimine on dakika kaldı", 10)
    assert _explicit_turkish_minute_anchor("yirmi beş dakika vardı", 25)
    assert _explicit_turkish_minute_anchor("12 dakika kaldı", 12)
    assert not _explicit_turkish_minute_anchor("yirmi beş dakika vardı", 10)
    assert not _explicit_turkish_minute_anchor("Tam kaç dakika geçtiği söylenmedi.", 7)
    assert not _explicit_turkish_minute_anchor("on dakika kaldı", 11)


def test_cli_replay_creates_no_model_call_or_canonical_state_write():
    expected = project_supplement(**scenario(GREENHOUSE))
    command = [
        sys.executable, "-X", "utf8", "-m", "src.q25_terminal_supplement",
        "--request-package", str(GREENHOUSE / "request.json"),
        "--raw-response", str(GREENHOUSE / "paid-attempt-01-raw-extraction.json"),
        "--supplement", str(GREENHOUSE / "terminal-supplement-author-annotation.json"),
    ]
    result = json.loads(subprocess.check_output(command, text=True, encoding="utf8"))
    assert result == expected
    assert result["provider_calls"] == 0
    assert result["state_commit_authorized"] is False


def test_withheld_model_request_cannot_see_author_supplement():
    from src.q25_withheld_trial import preflight
    package = read(GREENHOUSE / "request.json")
    wire = preflight(request_package=package, model="anthropic/claude-sonnet-5.5")
    assert wire["reference_labels_loaded"] is False
    assert wire["reference_labels_sent_to_model"] is False
    assert "terminal-supplement-annotation" not in json.dumps(package)


@pytest.mark.parametrize("case", [GREENHOUSE, KITE])
def test_frozen_sidecar_projection_is_recomputed_exactly_without_authority(case):
    archive = read(case / "terminal-supplement-projection.json")
    actual = project_supplement(**scenario(case))
    assert archive == actual
    assert archive["base_hypothesis_sha256"] == actual["base_hypothesis_sha256"]
    assert archive["annotation_sha256"] == actual["annotation_sha256"]
    assert archive["provider_calls"] == 0
    assert archive["provider_cost_usd"] == 0
    assert archive["state_commit_authorized"] is False
    assert archive["full_story_state_qualified"] is False
    assert archive["independently_authenticated_reviewer"] is False
    assert archive["semantic_support_certified"] is False
    assert archive["source_kind"] == "AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED"
