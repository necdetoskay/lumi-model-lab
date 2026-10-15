"""Synthetic model-output contract tests only: no real outcome review/commit."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from experiments import v3_f2_world_outcome_evidence_gate as w


def fake_model_response():
    original=json.loads((w.STAGED/"state-proposals.json").read_text())
    quote="Dessa signed beneath the record."
    assert quote in (w.STAGED/"story.en.txt").read_text()
    return {
        "schema":w.REQUIRED_MODEL_OUTPUT_SCHEMA,
        "source_story_sha256":w.EXPECTED_EN,
        "selected_branch":"seal_bounded_report",
        "branch_evidence_quotes":[quote],
        "candidate_reviews":[{
            "candidate_id":v["candidate_id"],
            "condition_verdict":"EARNED" if i==0 else "NOT_EARNED",
            "evidence_quotes":[quote] if i==0 else [],
            "reason":"SYNTHETIC_ONLY: provenance quote exists, independent semantic review needed",
        } for i,v in enumerate(original["candidate_operations"])],
    }


def test_model_branch_and_five_candidate_output_never_grants_commit():
    output=w.validate_judge_output(fake_model_response())
    assert output["status"]=="MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED"
    assert output["model_selected_branch"]=="seal_bounded_report"
    assert output["proposed_saga_milestone"]["model_evidence_suggests_earned"] is True
    assert output["proposed_saga_milestone"]["committed"] is False
    assert output["applied_operations"]==[]
    assert output["world_state_transaction"] is None
    assert output["world_state_commit_authorized"] is False
    assert output["world_state_committed"] is False
    assert output["publication_authorized"] is False
    assert len(output["approved_persistent_candidates"])==5
    assert all(x["applied"] is False for x in output["approved_persistent_candidates"])


@pytest.mark.parametrize("mutate,reason",[
    (lambda x:x.update({"selected_branch":"third_branch"}),"WORLD_JUDGE_INVALID_BRANCH"),
    (lambda x:x.update({"source_story_sha256":"a"*64}),"WORLD_JUDGE_WRONG_SOURCE"),
    (lambda x:x["branch_evidence_quotes"].append("This fabricated quotation did not happen."),
     "WORLD_JUDGE_BRANCH_QUOTE_FABRICATED"),
    (lambda x:x["candidate_reviews"].pop(),"WORLD_JUDGE_INCOMPLETE_CANDIDATE_SET"),
    (lambda x:x["candidate_reviews"][0].update({"candidate_id":"f2-outcome-08"}),
     "WORLD_JUDGE_UNAPPROVED_CANDIDATE"),
    (lambda x:x["candidate_reviews"][0].update({"evidence_quotes":[]}),
     "WORLD_JUDGE_EARNED_WITHOUT_QUOTE"),
    (lambda x:x["candidate_reviews"][0].update({"evidence_quotes":["unrelated fabricated source quote"]}),
     "WORLD_JUDGE_INVENTED_EVIDENCE_QUOTE"),
])
def test_model_contract_fails_closed_on_fabrications_or_missing_evidence(mutate,reason):
    payload=fake_model_response()
    mutate(payload)
    with pytest.raises(w.OutcomeStop,match=reason):
        w.validate_judge_output(payload)


def test_wrong_branch_cannot_earn_sealed_field_record_milestone():
    payload=fake_model_response()
    payload["selected_branch"]="extend_testing"
    with pytest.raises(w.OutcomeStop,match="WORLD_JUDGE_BRANCH_MILESTONE_CONTRADICTION"):
        w.validate_judge_output(payload)


def test_uncommitted_candidate_data_remains_identical_after_model_review():
    source=w.STAGED/"state-proposals.json"
    before=source.read_bytes()
    output=w.validate_judge_output(fake_model_response())
    assert source.read_bytes()==before
    assert len(output["approved_persistent_candidates"])==5
    assert all(x["commit_authorized"] is False for x in output["approved_persistent_candidates"])


def test_tampered_bilingual_stage_blocks_model_result(tmp_path):
    payload=fake_model_response()
    tmp=tmp_path/"fake-stage";tmp.mkdir()
    for name in ("delivery-manifest.json","state-proposals.json","story.en.txt","story.tr.txt"):
        (tmp/name).write_bytes((w.STAGED/name).read_bytes())
    (tmp/"story.en.txt").write_text((tmp/"story.en.txt").read_text()+"\nChanged!")
    with pytest.raises(w.OutcomeStop,match="WORLD_JUDGE_SOURCE_HASH_MISMATCH"):
        w.validate_judge_output(payload,stage_dir=tmp)
