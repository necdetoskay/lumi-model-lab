"""Third *real* paid Sonnet output: saved, deterministic and still non-canonical.

No new provider request. 14/16 is raw identity agreement with an unreviewed
author-reference, NOT independently adjudicated extractor precision.
"""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_extractor_adapter import offline_replay
from src.q25_raw_reconciliation import project_raw
from src.q25_withheld_trial import evaluate

DIR = Path("evidence/q25/Q25-WITHHELD-TRIAL-20261012")


def load(name):
    return json.loads((DIR / name).read_text(encoding="utf8"))


def inputs():
    request = load("request.json")
    return dict(
        seed=request["seed"], prose=request["prose_record"]["text"],
        policy=request["policy"],
        raw_output=load("paid-attempt-03-raw-extraction.json"),
    )


def test_real_paid_response_passes_generic_source_gate_without_any_rewrite():
    kw = inputs()
    originals = copy.deepcopy(kw)
    report = offline_replay(**kw)
    assert report["status"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert report["coverage"]["counts"] == {
        "CANDIDATE": 13, "PARTIAL_CANDIDATES": 2,
        "STRUCTURAL_ONLY": 23, "UNASSESSED": 17, "UNKNOWN": 2,
    }
    assert report["coverage"]["blocking_field_count"] == 57
    assert report["provider_calls"] == 0
    assert report["state_commit_authorized"] is False
    assert report["semantic_support_certified"] is False
    assert report["full_story_state_qualified"] is False
    assert kw == originals
    assert offline_replay(**kw) == report


def test_first_source_accepted_real_response_yields_unapproved_terminal_hypothesis():
    kw = inputs()
    projected = project_raw(**kw)
    assert projected["schema"] == "q25.raw-terminal-hypothesis.v1"
    assert projected["blocking_field_count"] == 57
    assert projected["raw_response_trust"] == "UNTRUSTED_SOURCE_QUOTED_CANDIDATES_ONLY"
    assert projected["structural_consistency"]["status"] == (
        "STRUCTURALLY_COHERENT_CANDIDATES_ONLY")
    assert projected["structural_consistency"]["reciprocal_container_pairs"] == 0
    objects = projected["candidate_state"]["objects"]
    assert objects["blue_string"]["container"]["status"] == "NONE"
    assert objects["wooden_box"]["contains"] == []
    assert objects["blue_string"]["owner"]["ref"] == "Defne"
    assert objects["red_kite"]["properties"]["ready"]["terminal_proposal"] is True
    assert objects["red_kite"]["properties"]["string_attached"]["terminal_proposal"] is True
    assert objects["blue_string"]["properties"]["found"]["terminal_proposal"] is True
    assert objects["blue_string"]["properties"]["tied_to_kite"]["terminal_proposal"] is True
    assert objects["wooden_box"]["properties"]["lid_closed"]["terminal_proposal"] is None
    new = [(k,v) for k,v in objects.items() if k.startswith("new_")]
    assert len(new) == 1
    assert new[0][1]["identity_status"] == "PROPOSED"
    assert new[0][1]["owner"]["status"] == "UNKNOWN"
    assert new[0][1]["location"]["status"] == "UNKNOWN"
    assert projected["candidate_state"]["proposed_world_time"] is None
    assert projected["candidate_state"]["world_time_unassessed"] is True
    assert len(projected["proposed_obligation_closures"]) == 3
    assert projected["approved_obligation_closures"] == []
    assert projected["terminal_state_complete"] is False
    assert projected["independent_semantic_review_completed"] is False
    assert projected["semantic_support_certified"] is False
    assert projected["full_story_state_qualified"] is False
    assert projected["state_commit_authorized"] is False
    assert projected["production_write_performed"] is False


def test_provisional_14_2_2_identity_score_does_not_become_real_quality_claim():
    report = evaluate(
        request_package=load("request.json"),
        reference_package=load("provisional-reference.json"),
        raw_response=load("paid-attempt-03-raw-extraction.json"),
        origin="PAID_ATTEMPT_03_ARCHIVED_WITH_SEPARATE_PROVIDER_USAGE_LEDGER",
    )
    assert report["candidate_structural_replay_status"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert report["reference_claim_count"] == 16
    assert report["candidate_claim_count"] == 16
    score = report["overall"]
    assert (score["true_positive"],score["false_positive"],score["false_negative"]) == (14,2,2)
    assert score["precision"] == pytest.approx(.875)
    assert score["recall"] == pytest.approx(.875)
    assert score["f1"] == pytest.approx(.875)
    assert score["reference_quote_exact_matches"] == 3
    assert len(report["extra_claims_not_in_reference"]) == 2
    assert len(report["missed_reference_claims"]) == 2
    assert {x["group"] for x in report["extra_claims_not_in_reference"]} == {
        "character_claims"}
    assert report["by_claim_group"]["character_claims"]["true_positive"] == 0
    assert report["reference_labels_independently_adjudicated"] is False
    assert report["independent_human_adjudication_complete"] is False
    assert report["real_model_success_measured"] is False
    assert report["state_commit_authorized"] is False
    assert report["provider_calls"] == 0


def test_authentic_usage_ledger_preserved_but_does_not_claim_state_success():
    ledger = load("paid-attempt-03-public-ledger.json")
    assert ledger["outcome"] == "SOURCE_BOUND_CANDIDATES_ONLY"
    assert ledger["attempted_calls"] == ledger["provider_calls"] == 1
    assert ledger["model"] == "anthropic/claude-sonnet-5.5"
    assert ledger["model_schema_profile"] == "ANTHROPIC_STRICT_V1"
    assert ledger["usage"] == {
        "prompt_tokens": 6788, "completion_tokens": 2883,
        "total_tokens": 9671, "actual_cost_usd": 0.042406,
    }
    assert ledger["candidate_count"] == 16
    assert ledger["review_status"] == "AWAITING_EXTERNAL_REVIEW"
    assert ledger["terminal_state_complete"] is False
    assert ledger["state_commit_authorized"] is False


@pytest.mark.parametrize("damage", [
    "unqualified_subject", "non_knowledge_epistemic", "invented_owner",
    "fabricated_quote", "fake_source_sha", "state_promotion",
])
def test_paid_gate_remains_fail_closed_on_prev_failures_or_false_authority(damage):
    kw = inputs()
    raw = kw["raw_output"]
    if damage == "unqualified_subject":
        raw["terminal_relations"][0]["subject"] = "blue_string"
    elif damage == "non_knowledge_epistemic":
        raw["character_claims"].append(dict(
            actor="Bora", field="emotion", value="hurt",
            epistemic_type="REPORTED", other_actor=None,
            evidence={"quote": "Kırıldım ama özrünü duydum"}))
    elif damage == "invented_owner":
        raw["terminal_relations"].append(dict(
            subject="new:gold_paper_star", kind="OWNED_BY",
            target="character:SomeoneElse",
            evidence={"quote": "altın renkli kâğıt yıldızı yapıştırdı"}))
    elif damage == "fabricated_quote":
        raw["objects"][0]["mention"]["quote"] = "The paper star flew away."
    elif damage == "fake_source_sha":
        raw["source_sha256"] = "0"*64
    elif damage == "state_promotion":
        raw["state_commit_authorized"] = True
    with pytest.raises(ValueError):
        offline_replay(**kw)


def test_cli_replay_is_deterministic_and_source_files_are_not_changed():
    files = [DIR / name for name in [
        "request.json", "provisional-reference.json",
        "paid-attempt-03-raw-extraction.json",
        "paid-attempt-03-public-ledger.json",
    ]]
    before = [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]
    cmd = [
        sys.executable, "-X", "utf8", "-m", "src.q25_withheld_trial",
        "--request-package", str(files[0]),
        "--reference-package", str(files[1]),
        "--raw-response", str(files[2]),
    ]
    result = json.loads(subprocess.check_output(cmd, encoding="utf8", text=True))
    assert result["overall"]["true_positive"] == 14
    assert result["real_model_success_measured"] is False
    assert before == [hashlib.sha256(f.read_bytes()).hexdigest() for f in files]


def test_frozen_terminal_hypothesis_matches_recomputed_raw_projection_exactly():
    archived = load("paid-attempt-03-terminal-hypothesis.json")
    regenerated = project_raw(**inputs())
    assert archived == regenerated
    assert archived["state_commit_authorized"] is False
    assert archived["semantic_support_certified"] is False
    assert archived["full_story_state_qualified"] is False
    assert archived["independent_semantic_review_completed"] is False
    assert archived["production_write_performed"] is False


def test_frozen_semantic_packet_matches_unmodified_model_source():
    from src.q25_semantic_review import build_review_packet
    kw = inputs()
    archived = load("paid-attempt-03-review-packet.json")
    generated = build_review_packet(
        seed=kw["seed"], prose=kw["prose"], raw_output=kw["raw_output"],
        policy=kw["policy"],
    )
    assert archived == generated
    assert archived["review_status"] == "AWAITING_EXTERNAL_REVIEW"
    assert archived["state_commit_authorized"] is False
    assert archived["semantic_support_certified"] is False
