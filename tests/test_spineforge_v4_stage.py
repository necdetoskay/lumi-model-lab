from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.spineforge_v4_stage as stage
from src.spine_context_pack_v1 import SpineContextPackV1

PACK=Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
MOCK=Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")


def _profile(path:Path)->None:
    path.write_text(json.dumps({
        "schema_version":"spineforge-runtime-profile.v1",
        "runtime_id":"test.spineforge.v4",
        "runtime":{
            "creative_prompt":"prompts/spineforge_creative_architect_v3_context.md",
            "hardener_prompt":"prompts/spineforge_structural_hardener_v2_context.md",
            "product_gate_prompt":"prompts/spineforge_product_gate_v2_context.md"
        },
        "runtime_freeze":{
            "enabled":True,
            "runtime_revision":"TEST-V4",
            "files":[{"path":"src/spineforge_v4_stage.py","sha256":"unused"}]
        }
    }))


def _case(tmp_path:Path,profile:Path,pack:SpineContextPackV1)->Path:
    path=tmp_path/"case.json"
    path.write_text(json.dumps({
        "schema":"spineforge-context-case.v4",
        "case_id":"case.v3",
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


def test_v4_stage_materializes_context_before_runtime(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v4-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V4_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":1
    }))
    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST-V4","verified_files":1
    })
    captured={}
    def fake_run(**kwargs):
        captured.update(kwargs)
        materialized=SpineContextPackV1.model_validate_json(kwargs["context_pack_path"].read_text())
        return {
            "status":"awaiting_human_review",
            "attempt_index":1,
            "context_fingerprint":materialized.context_fingerprint,
        }
    monkeypatch.setattr(stage,"run_spineforge",fake_run)
    envelope=stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
    assert envelope["context_fingerprint"]==pack.context_fingerprint
    assert captured["revision_feedback_path"] is None
    assert envelope["writer_authorized"] is False


def test_v4_stage_paid_authorization_stops_before_case_load(tmp_path:Path)->None:
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v4-trigger.v1",
        "paid_authorized":False,
        "scope":"SPINEFORGE_V4_ATTEMPT",
        "case_manifest":"does-not-exist.json",
        "attempt_index":1
    }))
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")


def test_v4_stage_attempt_gt1_requires_feedback(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v4-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V4_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":2
    }))
    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST-V4","verified_files":1
    })
    with pytest.raises(RuntimeError,match="Attempt >1 requires"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")


def test_v4_stage_stale_feedback_stops_before_runtime(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text())
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    feedback=tmp_path/"feedback.json"
    feedback.write_text(json.dumps({
        "schema":"spineforge-revision-feedback.v3",
        "context_pack_id":pack.context_pack_id,
        "context_fingerprint":"0"*64,
        "source_attempt":1,
        "next_attempt":2
    }))
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v4-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V4_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":2,
        "revision_feedback":str(feedback)
    }))
    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST-V4","verified_files":1
    })
    called=[]
    monkeypatch.setattr(stage,"run_spineforge",lambda **kwargs:called.append(kwargs))
    with pytest.raises(RuntimeError,match="fingerprint differs"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
    assert called==[]
