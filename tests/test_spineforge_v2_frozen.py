from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spine_context_pack_v1 import (
    MockCanonicalStateV1,
    build_spine_context_pack,
)
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v2_case_manifest import load_spineforge_v2_case
from src.spineforge_v2_stage import run as run_stage

PROFILE=Path(
    "data/specifications/story_lab/"
    "spineforge_runtime_profile_v2_context_frozen.json"
)
CASE=Path(
    "data/specifications/story_lab/"
    "spineforge_v2_age18_forbidden_cartographer_case_v1.json"
)
LEDGER=Path(
    "data/specifications/story_lab/"
    "spineforge_v2_age18_forbidden_cartographer_cost_ledger_v1.json"
)


def test_contextpack_v2_runtime_hashes_match() -> None:
    result=verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v2"
    assert result["verified_files"]>=25


def test_case_materializes_exact_expected_pack() -> None:
    case=load_spineforge_v2_case(CASE)
    source=MockCanonicalStateV1.model_validate_json(
        Path(case.canonical_state_source).read_text()
    )
    pack=build_spine_context_pack(source)
    assert pack.context_pack_id==case.expected_context_pack_id
    assert pack.context_fingerprint==case.expected_context_fingerprint


def test_v2_attempt1_failure_and_spend_are_preserved_as_history() -> None:
    ledger=json.loads(LEDGER.read_text())
    assert ledger["status"]=="QUALIFICATION_FAILED_ATTEMPT_1"
    assert len(ledger["attempts"])==1
    attempt=ledger["attempts"][0]
    assert attempt["run_id"]==36663676934
    assert attempt["status"]=="creative_contract_rejected"
    assert attempt["api_calls"]==1
    assert attempt["models_called"]==["aion-labs/aion-3.5-mini"]
    assert attempt["models_not_called"]==[
        "anthropic/claude-sonnet-5.5",
        "openai/gpt-5.6-luna",
    ]
    assert ledger["actual_spend"]["api_calls"]==1
    assert ledger["actual_spend"]["total_tokens"]==22146
    assert ledger["actual_spend"]["cost_usd"]==pytest.approx(0.0240562)
    assert ledger["paid_boundary"]["authorized"] is False

    trigger=json.loads(
        Path("experiments/triggers/spineforge-v2.json").read_text()
    )
    assert trigger["attempt_index"]==1
    assert trigger["paid_authorized"] is True


def test_context_case_data_is_not_part_of_frozen_runtime_hashes() -> None:
    profile=json.loads(PROFILE.read_text())
    runtime_paths={row["path"] for row in profile["runtime_freeze"]["files"]}
    case=json.loads(CASE.read_text())
    assert case["canonical_state_source"] not in runtime_paths
    assert str(CASE) not in runtime_paths
    assert str(LEDGER) not in runtime_paths
    assert (
        "data/specifications/story_lab/"
        "age18_forbidden_cartographer_spine_context_pack_v1.json"
    ) not in runtime_paths


def test_v2_runtime_has_no_story_specific_names() -> None:
    profile=json.loads(PROFILE.read_text())
    forbidden=[
        "Leyra",
        "Ashen Gate",
        "Greyfen",
        "forbidden_cartographer",
        "Deniz",
        "Beacon Ridge",
        "Meridian Harbor",
    ]
    for row in profile["runtime_freeze"]["files"]:
        path=Path(row["path"])
        if path.suffix.lower() not in {".py",".md",".yml",".yaml",".txt"}:
            continue
        text=path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, (
                f"{token} leaked into ContextPack v2 runtime {path}"
            )


def test_hash_change_invalidates_v2_runtime(tmp_path:Path) -> None:
    profile=json.loads(PROFILE.read_text())
    profile["runtime_freeze"]["files"][0]["sha256"]="0"*64
    bad=tmp_path/"bad.json"
    bad.write_text(json.dumps(profile))
    with pytest.raises(
        RuntimeError,
        match="SpineForge frozen runtime changed",
    ):
        verify_spineforge_runtime(bad)


def test_paid_attempt_without_authorization_stops_before_case_load(
    tmp_path:Path,
) -> None:
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v2-trigger.v1",
        "paid_authorized":False,
        "scope":"SPINEFORGE_V2_ATTEMPT",
        "case_manifest":"does-not-exist.json",
        "attempt_index":1,
    }))
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        run_stage(trigger_path=trigger,out_dir=tmp_path/"out")


def test_v1_and_v2_are_distinct_frozen_revisions() -> None:
    v1=json.loads(
        Path(
            "data/specifications/story_lab/"
            "spineforge_runtime_profile_v1_frozen.json"
        ).read_text()
    )
    v2=json.loads(PROFILE.read_text())
    assert v1["runtime_freeze"]["runtime_revision"]=="SPINEFORGE-FROZEN-v1"
    assert v2["runtime_freeze"]["runtime_revision"]=="SPINEFORGE-CONTEXTPACK-FROZEN-v2"
    assert v1["runtime_freeze"]["runtime_source_commit"]!=v2["runtime_freeze"]["runtime_source_commit"]
