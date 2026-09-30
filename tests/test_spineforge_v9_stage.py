from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v9_case_manifest import SpineForgeContextCaseV9
from src.spineforge_v9_stage import run as run_stage


def test_v9_case_contract_is_strict() -> None:
    value = SpineForgeContextCaseV9.model_validate(
        {
            "schema": "spineforge-context-case.v9",
            "case_id": "case.v9",
            "runtime_profile": "profile.json",
            "canonical_state_source": "state.json",
            "expected_context_pack_id": "pack",
            "expected_context_fingerprint": "f" * 64,
            "qualification_kind": "TEST",
            "exact_age": 18,
            "narrative_family": "TEST",
            "status": "READY",
            "cost_ledger": "ledger.json",
            "max_attempts": 3,
            "rules": {"partitioned_strict": True},
        }
    )
    assert value.max_attempts == 3


def test_v9_unapproved_trigger_stops_before_case_load(tmp_path: Path) -> None:
    trigger = tmp_path / "trigger.json"
    trigger.write_text(
        json.dumps(
            {
                "schema_version": "spineforge-v9-trigger.v1",
                "scope": "SPINEFORGE_V9_ATTEMPT",
                "paid_authorized": False,
                "case_manifest": "does-not-exist.json",
                "attempt_index": 1,
            }
        )
    )
    with pytest.raises(RuntimeError, match="not explicitly authorized"):
        run_stage(trigger_path=trigger, out_dir=tmp_path / "out")


def test_v9_attempt_bounds_stop_before_runtime(tmp_path: Path, monkeypatch) -> None:
    case = tmp_path / "case.json"
    profile = tmp_path / "profile.json"
    source = tmp_path / "state.json"
    profile.write_text("{}")
    source.write_text("{}")
    case.write_text(
        json.dumps(
            {
                "schema": "spineforge-context-case.v9",
                "case_id": "case.v9",
                "runtime_profile": str(profile),
                "canonical_state_source": str(source),
                "expected_context_pack_id": "pack",
                "expected_context_fingerprint": "f" * 64,
                "qualification_kind": "TEST",
                "exact_age": 18,
                "narrative_family": "TEST",
                "status": "READY",
                "cost_ledger": "ledger.json",
                "max_attempts": 3,
                "rules": {},
            }
        )
    )
    trigger = tmp_path / "trigger.json"
    trigger.write_text(
        json.dumps(
            {
                "schema_version": "spineforge-v9-trigger.v1",
                "scope": "SPINEFORGE_V9_ATTEMPT",
                "paid_authorized": True,
                "case_manifest": str(case),
                "attempt_index": 4,
            }
        )
    )
    monkeypatch.setattr(
        "src.spineforge_v9_stage.verify_spineforge_runtime",
        lambda path: {"runtime_revision": "TEST-V9", "verified_files": 1},
    )
    with pytest.raises(RuntimeError, match="exceeds case bounds"):
        run_stage(trigger_path=trigger, out_dir=tmp_path / "out")
