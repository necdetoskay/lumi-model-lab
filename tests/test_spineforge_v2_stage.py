from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.spineforge_v2_stage as stage
from src.spine_context_pack_v1 import SpineContextPackV1

PACK=Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
MOCK=Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")


def _profile(path:Path)->None:
    path.write_text(json.dumps({
        "schema_version":"spineforge-runtime-profile.v1",
        "runtime_id":"test.spineforge.v2",
        "runtime":{
            "creative_prompt":"prompts/spineforge_creative_architect_v2_context.md",
            "hardener_prompt":"prompts/spineforge_structural_hardener_v2_context.md",
            "product_gate_prompt":"prompts/spineforge_product_gate_v2_context.md"
        },
        "runtime_freeze":{
            "enabled":True,
            "runtime_revision":"TEST",
            "files":[{"path":"src/spineforge_v2_stage.py","sha256":"unused-in-test"}]
        }
    }))


def _case(tmp_path:Path,profile:Path,pack:SpineContextPackV1)->Path:
    path=tmp_path/"case.json"
    path.write_text(json.dumps({
        "schema":"spineforge-context-case.v1",
        "case_id":"case.v2",
        "runtime_profile":str(profile),
        "canonical_state_source":str(MOCK),
        "expected_context_pack_id":pack.context_pack_id,
        "expected_context_fingerprint":pack.context_fingerprint,
        "qualification_kind":"TEST",
        "exact_age":18,
        "narrative_family":"HIGH_FANTASY_MYSTERY",
        "status":"READY",
        "cost_ledger":"unused.json",
        "max_attempts":3,
        "rules":{"data_only":True}
    }))
    return path


def test_stage_materializes_context_before_model_runtime(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v2-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V2_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":1
    }))

    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST",
        "verified_files":1,
    })
    captured={}
    def fake_run(**kwargs):
        captured.update(kwargs)
        materialized=SpineContextPackV1.model_validate_json(
            kwargs["context_pack_path"].read_text()
        )
        return {
            "status":"awaiting_human_review",
            "attempt_index":1,
            "context_fingerprint":materialized.context_fingerprint,
        }
    monkeypatch.setattr(stage,"run_spineforge",fake_run)

    envelope=stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
    assert envelope["context_fingerprint"]==pack.context_fingerprint
    assert captured["context_pack_path"].name=="spine_context_pack.json"
    assert captured["revision_feedback_path"] is None


def test_changed_canonical_state_stops_before_spineforge(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    profile=tmp_path/"profile.json"
    _profile(profile)

    changed=json.loads(MOCK.read_text())
    changed["current_situation_notes"].append("Canonical state changed.")
    changed_path=tmp_path/"changed_state.json"
    changed_path.write_text(json.dumps(changed))

    case=tmp_path/"case.json"
    case.write_text(json.dumps({
        "schema":"spineforge-context-case.v1",
        "case_id":"case.v2",
        "runtime_profile":str(profile),
        "canonical_state_source":str(changed_path),
        "expected_context_pack_id":pack.context_pack_id,
        "expected_context_fingerprint":pack.context_fingerprint,
        "qualification_kind":"TEST",
        "exact_age":18,
        "narrative_family":"HIGH_FANTASY_MYSTERY",
        "status":"READY",
        "cost_ledger":"unused.json",
        "max_attempts":3,
        "rules":{"data_only":True}
    }))
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v2-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V2_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":1
    }))

    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST",
        "verified_files":1,
    })
    called=[]
    monkeypatch.setattr(stage,"run_spineforge",lambda **kwargs:called.append(kwargs))
    with pytest.raises(RuntimeError,match="fingerprint differs"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
    assert called==[]


def test_paid_authorization_checked_before_case_load(tmp_path:Path)->None:
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v2-trigger.v1",
        "paid_authorized":False,
        "scope":"SPINEFORGE_V2_ATTEMPT",
        "case_manifest":"does-not-exist.json",
        "attempt_index":1
    }))
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
