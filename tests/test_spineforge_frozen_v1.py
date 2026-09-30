from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_case_manifest import load_spineforge_case
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_stage import run as run_stage

PROFILE=Path("data/specifications/story_lab/spineforge_runtime_profile_v1_frozen.json")
CASE=Path("data/specifications/story_lab/spineforge_age18_forbidden_cartographer_case_v1.json")
LEDGER=Path("data/specifications/story_lab/spineforge_age18_forbidden_cartographer_cost_ledger_v1.json")


def test_spineforge_runtime_hashes_match() -> None:
    result=verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"]=="SPINEFORGE-FROZEN-v1"
    assert result["verified_files"]>=20


def test_first_case_is_data_only_and_zero_cost() -> None:
    case=load_spineforge_case(CASE)
    ledger=json.loads(LEDGER.read_text())
    assert case["status"]=="READY_FOR_ATTEMPT_1"
    assert case["rules"]["runtime_and_prompts_frozen"] is True
    assert case["rules"]["max_attempts"]==3
    assert ledger["attempts"]==[]
    assert ledger["actual_spend"]["api_calls"]==0
    assert ledger["actual_spend"]["total_tokens"]==0
    assert ledger["actual_spend"]["cost_usd"]==0.0
    assert ledger["paid_boundary"]["authorized"] is False


def test_case_inputs_are_not_runtime_files() -> None:
    profile=json.loads(PROFILE.read_text())
    runtime_paths={row["path"] for row in profile["runtime_freeze"]["files"]}
    case=json.loads(CASE.read_text())
    assert set(case["inputs"].values()).isdisjoint(runtime_paths)


def test_frozen_runtime_has_no_case_specific_story_names() -> None:
    profile=json.loads(PROFILE.read_text())
    forbidden=[
        "Leyra","Ashen Gate","Greyfen","forbidden_cartographer",
        "Deniz","Beacon Ridge","Meridian Harbor",
    ]
    for row in profile["runtime_freeze"]["files"]:
        path=Path(row["path"])
        if path.suffix.lower() not in {".py",".md",".yml",".yaml",".txt"}:
            continue
        text=path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into frozen SpineForge runtime {path}"


def test_runtime_hash_change_invalidates_active_revision(tmp_path:Path) -> None:
    profile=json.loads(PROFILE.read_text())
    profile["runtime_freeze"]["files"][0]["sha256"]="0"*64
    bad=tmp_path/"bad.json"
    bad.write_text(json.dumps(profile))
    with pytest.raises(RuntimeError,match="SpineForge frozen runtime changed"):
        verify_spineforge_runtime(bad)


def test_paid_attempt_rejects_missing_authorization_before_case_load(tmp_path:Path) -> None:
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-trigger.v1",
        "paid_authorized":False,
        "scope":"SPINEFORGE_ATTEMPT",
        "case_manifest":"does-not-exist.json",
        "attempt_index":1,
    }))
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        run_stage(trigger_path=trigger,out_dir=tmp_path/"out")


def test_no_paid_trigger_exists_yet() -> None:
    assert not Path("experiments/triggers/spineforge-v1.json").exists()


def test_old_age18_frozen_runtime_profile_is_not_spineforge_profile() -> None:
    old=json.loads(
        Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json").read_text()
    )
    new=json.loads(PROFILE.read_text())
    assert old["runtime_freeze"]["runtime_revision"]=="AGE18-FROZEN-v1"
    assert new["runtime_freeze"]["runtime_revision"]=="SPINEFORGE-FROZEN-v1"
    assert old["runtime_freeze"]["runtime_source_commit"]!=new["runtime_freeze"]["runtime_source_commit"]
