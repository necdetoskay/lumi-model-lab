from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.spineforge_v5_stage as stage
from src.spine_context_pack_v1 import SpineContextPackV1

PACK=Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
MOCK=Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")


def _profile(path:Path)->None:
    path.write_text(json.dumps({
        "schema_version":"spineforge-runtime-profile.v1",
        "runtime_id":"test.spineforge.v5",
        "runtime":{
            "creative_prompt":"prompts/spineforge_creative_architect_v5_intent.md",
            "compiler_prompt":"prompts/spineforge_structural_compiler_v5.md",
            "product_gate_prompt":"prompts/spineforge_product_gate_v5.md"
        },
        "runtime_freeze":{
            "enabled":True,
            "runtime_revision":"TEST-V5",
            "files":[{"path":"src/spineforge_v5_stage.py","sha256":"unused"}]
        }
    }),encoding="utf-8")


def _case(tmp_path:Path,profile:Path,pack:SpineContextPackV1)->Path:
    path=tmp_path/"case.json"
    path.write_text(json.dumps({
        "schema":"spineforge-context-case.v5",
        "case_id":"case.v5",
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
    }),encoding="utf-8")
    return path


def test_stage_materializes_context_and_keeps_writer_blocked(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v5-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V5_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":1
    }),encoding="utf-8")
    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST-V5","verified_files":1
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
    assert envelope["writer_authorized"] is False
    assert envelope["context_fingerprint"]==pack.context_fingerprint
    assert captured["revision_feedback_path"] is None


def test_stage_requires_explicit_paid_authorization(tmp_path:Path)->None:
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v5-trigger.v1",
        "paid_authorized":False,
        "scope":"SPINEFORGE_V5_ATTEMPT",
        "case_manifest":"missing.json",
        "attempt_index":1
    }),encoding="utf-8")
    with pytest.raises(RuntimeError,match="not explicitly authorized"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")


def test_stage_rejects_attempt_over_case_limit_before_runtime(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v5-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V5_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":4
    }),encoding="utf-8")
    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST-V5","verified_files":1
    })
    calls=[]
    monkeypatch.setattr(stage,"run_spineforge",lambda **kwargs:calls.append(kwargs))
    with pytest.raises(RuntimeError,match="exceeds case bounds"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
    assert calls==[]


def test_stage_rejects_stale_feedback_before_runtime(monkeypatch,tmp_path:Path)->None:
    pack=SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    profile=tmp_path/"profile.json"
    _profile(profile)
    case=_case(tmp_path,profile,pack)
    feedback=tmp_path/"feedback.json"
    feedback.write_text(json.dumps({
        "schema":"spineforge-revision-feedback.v5",
        "context_pack_id":pack.context_pack_id,
        "context_fingerprint":"0"*64,
        "source_attempt":1,
        "next_attempt":2
    }),encoding="utf-8")
    trigger=tmp_path/"trigger.json"
    trigger.write_text(json.dumps({
        "schema_version":"spineforge-v5-trigger.v1",
        "paid_authorized":True,
        "scope":"SPINEFORGE_V5_ATTEMPT",
        "case_manifest":str(case),
        "attempt_index":2,
        "revision_feedback":str(feedback)
    }),encoding="utf-8")
    monkeypatch.setattr(stage,"verify_spineforge_runtime",lambda path:{
        "runtime_revision":"TEST-V5","verified_files":1
    })
    calls=[]
    monkeypatch.setattr(stage,"run_spineforge",lambda **kwargs:calls.append(kwargs))
    with pytest.raises(RuntimeError,match="fingerprint differs"):
        stage.run(trigger_path=trigger,out_dir=tmp_path/"out")
    assert calls==[]
