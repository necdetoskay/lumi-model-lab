"""No payment, no human edit, no publication and no world-state mutation."""
import json
import hashlib

import pytest

from experiments import v3_f2_final_delivery_stage as delivery


def test_real_bilingual_source_chain_verifies():
    data=delivery.verify_sources()
    assert data["source_frozen_checks"]==43
    assert data["english_word_count"]==2767
    assert data["turkish_word_count"]==2173
    assert len(data["candidates"])==5


def test_stage_copies_accepted_prose_byte_for_byte(tmp_path):
    out=tmp_path/"delivered"
    record=delivery.stage(out)
    assert record["status"]=="DELIVERY_STAGED_UNPUBLISHED"
    assert record["english"]["sha256"]==delivery.ENGLISH_SHA
    assert record["turkish"]["sha256"]==delivery.TURKISH_SHA
    assert (out/"story.en.txt").read_bytes()==delivery.ENGLISH.read_bytes()
    assert (out/"story.tr.txt").read_bytes()==delivery.TURKISH.read_bytes()
    assert record["stage_new_provider_posts"]==0
    assert record["stage_new_spend_usd"]=="0"
    assert record["published"] is False
    assert record["publish_authorized"] is False
    assert record["world_state_committed"] is False
    assert record["world_state_commit_authorized"] is False
    assert record["finalizer_publication_ready_not_asserted"] is True


def test_spine_candidate_descriptions_remain_uncommitted(tmp_path):
    delivery.stage(tmp_path/"f2")
    state=json.loads((tmp_path/"f2"/"state-proposals.json").read_text())
    approved=json.loads(delivery.APPROVED.read_text())
    candidates=approved["episode_spine"]["persistent_outcome_candidates"]
    assert len(state["candidate_operations"])==len(candidates)==5
    assert state["episode_branch_resolution"]=="NOT_INDEPENDENTLY_ASSESSED"
    assert state["milestone_eligibility"]=="UNDETERMINED"
    assert state["applied_operations"]==[]
    assert state["world_state_committed"] is False
    assert state["pending_model_evidence_matching"] is True
    for item,source in zip(state["candidate_operations"],candidates):
        assert item["source_description"]==source["description"]
        assert item["source_commit_condition"]==source["commit_condition"]
        assert item["condition_evaluation"]=="NOT_EVALUATED"
        assert item["applied"] is False
        assert item["commit_authorized"] is False


def test_second_staging_attempt_refused_and_existing_story_unchanged(tmp_path):
    target=tmp_path/"f2"
    delivery.stage(target)
    before=(target/"delivery-manifest.json").read_bytes()
    with pytest.raises(delivery.DeliveryStop,match="DELIVERY_OUTPUT_ALREADY_EXISTS"):
        delivery.stage(target)
    assert (target/"delivery-manifest.json").read_bytes()==before


def test_changed_turkish_acceptance_is_stopped_before_output(tmp_path,monkeypatch):
    fake=tmp_path/"falsified-tr.txt"
    fake.write_bytes(delivery.TURKISH.read_bytes()+b" unauthorized post-acceptance edit")
    monkeypatch.setattr(delivery,"TURKISH",fake)
    out=tmp_path/"delivery"
    with pytest.raises(delivery.DeliveryStop,match="STAGED_SOURCE_SHA_MISMATCH"):
        delivery.stage(out)
    assert not out.exists()


def test_changed_english_acceptance_is_stopped_before_output(tmp_path,monkeypatch):
    fake=tmp_path/"tampered-en.txt"
    fake.write_bytes(delivery.ENGLISH.read_bytes()+b" changed")
    monkeypatch.setattr(delivery,"ENGLISH",fake)
    out=tmp_path/"delivery"
    with pytest.raises(delivery.DeliveryStop,match="STAGED_SOURCE_SHA_MISMATCH"):
        delivery.stage(out)
    assert not out.exists()


def test_false_release_permission_in_accepted_turkish_qa_blocks_staging(tmp_path,monkeypatch):
    doc=json.loads(delivery.TURKISH_QUAL.read_text())
    doc["publication_authorized"]=True
    forged=tmp_path/"faked-tr-qual.json"
    forged.write_text(json.dumps(doc))
    monkeypatch.setattr(delivery,"TURKISH_QUAL",forged)
    with pytest.raises(delivery.DeliveryStop,match="TURKISH_ACCEPTANCE_CONTRACT_MISMATCH"):
        delivery.stage(tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_forged_sol_adjudication_confirmed_finding_blocks_staging(tmp_path,monkeypatch):
    doc=json.loads(delivery.TURKISH_SOL.read_text())
    doc["evaluations"][0]["decision"]="CONFIRM"
    forged=tmp_path/"faked-sol.json"
    forged.write_text(json.dumps(doc))
    monkeypatch.setattr(delivery,"TURKISH_SOL",forged)
    with pytest.raises(delivery.DeliveryStop,match="TURKISH_PROVENANCE_MANIFEST_MISMATCH"):
        delivery.stage(tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_staged_manifest_hashes_are_self_consistent(tmp_path):
    target=tmp_path/"f2"
    result=delivery.stage(target)
    on_disk=json.loads((target/"delivery-manifest.json").read_text())
    assert on_disk==result
    assert on_disk["state_proposals"]["sha256"]==hashlib.sha256(
        (target/"state-proposals.json").read_bytes()
    ).hexdigest()
    assert on_disk["provenance"]["english_manifest_sha256"]==delivery.sha(delivery.ENGLISH_MANIFEST)
    assert on_disk["provenance"]["turkish_manifest_sha256"]==delivery.sha(delivery.TURKISH_MANIFEST)


def test_frozen_v3_finalizer_is_not_invoked_or_authorized(tmp_path):
    result=delivery.stage(tmp_path/"f2")
    assert result["status"]!="publication_ready"
    assert result["finalizer_publication_ready_not_asserted"] is True
    state=json.loads((tmp_path/"f2"/"state-proposals.json").read_text())
    assert not any(x["applied"] for x in state["candidate_operations"])
