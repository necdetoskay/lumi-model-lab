"""Real archived Luna evidence replay, no new provider call or text edit."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from experiments import v3_f2_world_outcome_offline_replay as replay
from experiments import v3_f2_world_outcome_evidence_gate as gate


def original_response():
    return json.loads(replay.SOURCE_MODEL.read_text())["model_json"]


def test_real_luna_one_post_archival_provenance_and_replay(tmp_path):
    result=replay.replay(out_dir=tmp_path/"results")
    assert result["status"]=="MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED"
    assert result["original_provider_response_sha256"]==replay.SOURCE_SHA
    assert result["original_provider_generation_id"]==replay.GENERATION_ID
    assert result["provider_cost_usd_in_original_run"]=="0.0030664"
    assert result["additional_provider_posts"]==0
    assert result["additional_provider_cost_usd"]=="0"
    assert result["source_original_run_result"]=="STAGE_STOP"
    assert result["model_response_was_not_edited"] is True
    assert result["model_selected_branch"]=="seal_bounded_report"
    assert result["model_earned_outcome_candidates"]==5
    assert result["reviewed_outcome_candidates"]==5
    assert result["italic_boundary_accepted_quote_count"]==1
    assert result["world_state_committed"] is False
    assert result["publication_authorized"] is False
    assert result["applied_operations"]==[]
    outcome=json.loads((tmp_path/"results"/"world-outcome-proposal.json").read_text())
    assert len(outcome["approved_persistent_candidates"])==5
    assert all(x["model_condition_verdict"]=="EARNED" for x in outcome["approved_persistent_candidates"])
    assert all(x["applied"] is False for x in outcome["approved_persistent_candidates"])
    assert outcome["world_state_transaction"] is None


def test_exact_original_provider_json_is_not_modified_by_replay(tmp_path):
    before=replay.SOURCE_MODEL.read_bytes()
    en=gate.STAGED/"story.en.txt"
    tr=gate.STAGED/"story.tr.txt"
    before_en,before_tr=en.read_bytes(),tr.read_bytes()
    replay.replay(out_dir=tmp_path/"x")
    assert replay.SOURCE_MODEL.read_bytes()==before
    assert en.read_bytes()==before_en
    assert tr.read_bytes()==before_tr


def test_exact_original_quote_repair_is_formatting_delimiter_only():
    result=original_response()
    story=(gate.STAGED/"story.en.txt").read_text()
    quoted=result["candidate_reviews"][0]["evidence_quotes"][3]
    assert quoted not in story
    assert gate._quote_provenance(quoted,story)=="ITALIC_CLOSER_BOUNDARY_ONLY"
    assert quoted[:-1] in story
    assert result["candidate_reviews"][0]["condition_verdict"]=="EARNED"


@pytest.mark.parametrize("modified",[
    lambda q:q.replace("cause of this response","cause of this catastrophe"),
    lambda q:q.replace("Whether it recurs","Whether it certainly recurs"),
    lambda q:q[:-1]+"* *",
    lambda q:"Unobserved new scene. "+q,
    lambda q:q.replace("Not established","Established"),
    lambda q:q+" no new invented sentence",
])
def test_quote_validator_still_rejects_any_new_literary_claim(modified):
    payload=original_response()
    quote=payload["candidate_reviews"][0]["evidence_quotes"][3]
    payload["candidate_reviews"][0]["evidence_quotes"][3]=modified(quote)
    with pytest.raises(gate.OutcomeStop,match="WORLD_JUDGE_INVENTED_EVIDENCE_QUOTE"):
        gate.validate_judge_output(payload)


def test_replay_cannot_write_to_existing_destination(tmp_path):
    out=tmp_path/"x"
    replay.replay(out_dir=out)
    with pytest.raises(Exception,match="WORLD_REPLAY_DESTINATION_EXISTS"):
        replay.replay(out_dir=out)


def test_real_model_output_all_rows_with_provenance():
    payload=original_response()
    outcome=gate.validate_judge_output(payload)
    assert outcome["model_selected_branch"]=="seal_bounded_report"
    assert outcome["branch_quote_provenance"]==["EXACT","EXACT","EXACT"]
    assert sum(tag=="ITALIC_CLOSER_BOUNDARY_ONLY"
               for c in outcome["approved_persistent_candidates"]
               for tag in c["quote_provenance"])==1
    assert outcome["proposed_saga_milestone"]["committed"] is False
    assert outcome["world_state_commit_authorized"] is False
    assert outcome["published"] is False
