from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import MockCanonicalStateV1, build_spine_context_pack
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v4_case_manifest import load_spineforge_v4_case

PROFILE=Path(
    "data/specifications/story_lab/"
    "spineforge_runtime_profile_v4_normalizer_integrity_frozen.json"
)
CASE=Path(
    "data/specifications/story_lab/"
    "spineforge_v4_age18_forbidden_cartographer_case_v1.json"
)
LEDGER=Path(
    "data/specifications/story_lab/"
    "spineforge_v4_age18_forbidden_cartographer_cost_ledger_v1.json"
)


def test_v4_runtime_hashes_match()->None:
    result=verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v4"
    assert result["verified_files"]==26


def test_v4_case_materializes_exact_expected_pack()->None:
    case=load_spineforge_v4_case(CASE)
    source=MockCanonicalStateV1.model_validate_json(
        Path(case.canonical_state_source).read_text(encoding="utf-8")
    )
    pack=build_spine_context_pack(source)
    assert pack.context_pack_id==case.expected_context_pack_id
    assert pack.context_fingerprint==case.expected_context_fingerprint


def test_v4_starts_zero_spend_and_without_paid_trigger()->None:
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger["status"]=="READY_FOR_ATTEMPT_1"
    assert ledger["attempts"]==[]
    assert ledger["v4_actual_spend"]=={
        "api_calls":0,
        "total_tokens":0,
        "cost_usd":0,
        "latency_seconds":0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not Path("experiments/triggers/spineforge-v4.json").exists()


def test_v4_preserves_prior_revision_history_without_reclassification()->None:
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    history=ledger["prior_revision_history"]
    assert history[0]["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v2"
    assert history[0]["run_id"]==36663676934
    assert history[0]["cost_usd"]==0.0240562
    assert history[1]["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v3"
    assert history[1]["run_id"]==36666428511
    assert history[1]["status"]=="cancelled_no_result_artifact"
    assert history[1]["provider_billing_verified"] is False


def test_v4_runtime_contains_no_case_specific_names()->None:
    profile=json.loads(PROFILE.read_text(encoding="utf-8"))
    forbidden=["Leyra","Ashen Gate","Greyfen","forbidden_cartographer"]
    for row in profile["runtime_freeze"]["files"]:
        path=Path(row["path"])
        if path.suffix.lower() not in {".py",".md",".yml",".yaml",".txt"}:
            continue
        text=path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into frozen v4 runtime {path}"


def test_v1_v2_v3_and_v4_frozen_hashes_verify()->None:
    profiles=[
        ("v1","data/specifications/story_lab/spineforge_runtime_profile_v1_frozen.json",25),
        ("v2","data/specifications/story_lab/spineforge_runtime_profile_v2_context_frozen.json",26),
        ("v3","data/specifications/story_lab/spineforge_runtime_profile_v3_contract_recovery_frozen.json",26),
        ("v4","data/specifications/story_lab/spineforge_runtime_profile_v4_normalizer_integrity_frozen.json",26),
    ]
    for _,path,count in profiles:
        result=verify_spineforge_runtime(Path(path))
        assert result["verified"] is True
        assert result["verified_files"]==count
