from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import MockCanonicalStateV1, build_spine_context_pack
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v3_case_manifest import load_spineforge_v3_case

PROFILE=Path("data/specifications/story_lab/spineforge_runtime_profile_v3_contract_recovery_frozen.json")
CASE=Path("data/specifications/story_lab/spineforge_v3_age18_forbidden_cartographer_case_v1.json")
LEDGER=Path("data/specifications/story_lab/spineforge_v3_age18_forbidden_cartographer_cost_ledger_v1.json")


def test_v3_runtime_hashes_match()->None:
    result=verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v3"
    assert result["verified_files"]==26


def test_v3_case_materializes_exact_expected_pack()->None:
    case=load_spineforge_v3_case(CASE)
    source=MockCanonicalStateV1.model_validate_json(Path(case.canonical_state_source).read_text())
    pack=build_spine_context_pack(source)
    assert pack.context_pack_id==case.expected_context_pack_id
    assert pack.context_fingerprint==case.expected_context_fingerprint


def test_v3_records_cancelled_attempt_without_claiming_provider_billing()->None:
    ledger=json.loads(LEDGER.read_text())
    assert ledger["status"]=="QUALIFICATION_ABORTED_ATTEMPT_1"
    assert len(ledger["attempts"])==1
    attempt=ledger["attempts"][0]
    assert attempt["run_id"]==36666428511
    assert attempt["workflow_conclusion"]=="cancelled"
    assert attempt["result_artifact_written"] is False
    assert attempt["stage_envelope_written"] is False
    assert attempt["context_pack_materialized"] is True
    assert attempt["recorded_model_calls"]==0
    assert attempt["provider_billing_verified"] is False
    assert ledger["v3_actual_spend"]["recorded_api_calls"]==0
    assert ledger["v3_actual_spend"]["provider_billing_verified"] is False
    assert ledger["prior_revision_waste"]["cost_usd"]==0.0240562
    assert ledger["paid_boundary"]["authorized"] is False
    assert ledger["paid_boundary"]["next_scope"]=="NEW_SPINEFORGE_RUNTIME_REVISION_REQUIRED"

    trigger=json.loads(Path("experiments/triggers/spineforge-v3.json").read_text())
    assert trigger["paid_authorized"] is True
    assert trigger["attempt_index"]==1


def test_v3_runtime_contains_no_case_specific_names()->None:
    profile=json.loads(PROFILE.read_text())
    forbidden=["Leyra","Ashen Gate","Greyfen","forbidden_cartographer"]
    for row in profile["runtime_freeze"]["files"]:
        path=Path(row["path"])
        if path.suffix.lower() not in {".py",".md",".yml",".yaml",".txt"}:
            continue
        text=path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into frozen v3 runtime {path}"


def test_v2_and_v3_remain_distinct_frozen_revisions()->None:
    v2=json.loads(Path("data/specifications/story_lab/spineforge_runtime_profile_v2_context_frozen.json").read_text())
    v3=json.loads(PROFILE.read_text())
    assert v2["runtime_freeze"]["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v2"
    assert v3["runtime_freeze"]["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v3"
    assert v2["runtime_freeze"]["runtime_source_commit"]!=v3["runtime_freeze"]["runtime_source_commit"]
