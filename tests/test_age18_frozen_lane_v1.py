from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.frozen_lane_stage import run as run_stage
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest

PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
CASE=Path("data/specifications/story_lab/age18_forbidden_cartographer_frozen_case_v1.json")
LEDGER=Path("data/specifications/story_lab/age18_forbidden_cartographer_frozen_cost_ledger_v1.json")


def test_frozen_runtime_hashes_match() -> None:
    result=verify_frozen_lane(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"]=="AGE18-FROZEN-v1"
    assert result["verified_files"]>=30


def test_leyra_case_is_data_only_and_starts_from_zero_frozen_spend() -> None:
    case=load_case_manifest(CASE)
    ledger=json.loads(LEDGER.read_text())
    assert case["status"]=="READY_FOR_FROZEN_SPINE_F1"
    assert case["restart_policy"]["does_not_feed_pre_freeze_F1_feedback_into_first_frozen_spine"] is True
    assert ledger["frozen_attempt"]["product_path"]["api_calls"]==0
    assert ledger["frozen_attempt"]["product_path"]["tokens"]==0
    assert ledger["frozen_attempt"]["product_path"]["cost_usd"]==0.0
    assert ledger["frozen_attempt"]["qualification_waste"]["cost_usd"]==0.0
    assert ledger["pre_freeze_discovery_spend"]["cost_usd"]==0.09225655


def test_case_specific_runtime_files_are_removed() -> None:
    assert not Path("src/forbidden_cartographer_f1_gate_recovery.py").exists()
    assert not Path("src/forbidden_cartographer_f1_safe_normalize.py").exists()
    assert not Path(".github/workflows/age18-forbidden-cartographer-f1.yml").exists()
    assert not Path(".github/workflows/age18-forbidden-cartographer-f1-recovery.yml").exists()


def test_frozen_runtime_contains_no_qualified_story_names() -> None:
    profile=json.loads(PROFILE.read_text())
    forbidden=[
        "Deniz","Beacon Ridge","Meridian Harbor",
        "Leyra","Ashen Gate","Greyfen",
        "forbidden_cartographer",
    ]
    for row in profile["runtime_freeze"]["files"]:
        path=Path(row["path"])
        if path.suffix.lower() not in {".py",".md",".yml",".yaml",".txt"}:
            continue
        text=path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into frozen runtime file {path}"


def test_story_data_is_not_part_of_runtime_hash_set() -> None:
    profile=json.loads(PROFILE.read_text())
    paths={row["path"] for row in profile["runtime_freeze"]["files"]}
    case=json.loads(CASE.read_text())
    assert set(case["inputs"].values()).isdisjoint(paths)


def test_paid_stage_rejects_missing_explicit_authorization(tmp_path:Path) -> None:
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"frozen-lane-stage-trigger.v1",
        "stage":"SPINE",
        "paid_authorized":False,
        "case_manifest":"does-not-matter.json",
    }))
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        run_stage(trigger_path=trigger,out_dir=tmp_path/"out")


def test_runtime_hash_change_invalidates_lane(tmp_path:Path) -> None:
    profile=json.loads(PROFILE.read_text())
    profile["runtime_freeze"]["files"][0]["sha256"]="0"*64
    bad=tmp_path/"profile.json"
    bad.write_text(json.dumps(profile))
    with pytest.raises(RuntimeError,match="Frozen lane runtime changed"):
        verify_frozen_lane(bad)


def test_no_paid_trigger_exists_yet() -> None:
    assert not Path("experiments/triggers/age18-frozen-lane-stage.json").exists()
