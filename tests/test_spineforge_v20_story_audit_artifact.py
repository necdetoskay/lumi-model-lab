from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from src.spineforge_v20_story_audit_artifact import (
    build_story_audit_source,
    load_verified_writer_story_artifact,
    run_story_audit_once,
)


MANIFEST = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)


def _copy_artifact_tree(tmp_path: Path) -> Path:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in ("story_path", "result_path", "envelope_path"):
        src = Path(manifest[key])
        dst = tmp_path / src
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    manifest_dst = tmp_path / MANIFEST
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MANIFEST, manifest_dst)
    return manifest_dst


def test_writer3_stage4_manifest_verifies_exact_immutable_product():
    verified = load_verified_writer_story_artifact(manifest_path=MANIFEST)
    manifest = verified["manifest"]

    assert verified["input_verified"] is True
    assert manifest["stage"] == 4
    assert manifest["status"] == "FROZEN"
    assert manifest["immutable"] is True
    assert manifest["source_run_id"] == 36965340665
    assert manifest["attempt_index"] == 3
    assert manifest["story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert manifest["word_count"] == 2324
    assert manifest["next_stage"] == "STORY_AUDIT"
    assert verified["result"]["status"] == "writer_generated"
    assert "arriving at his shoulder" in verified["story"]


def test_story_audit_stops_before_model_call_when_story_hash_changes(tmp_path: Path):
    copied_manifest = _copy_artifact_tree(tmp_path)
    manifest = json.loads(copied_manifest.read_text(encoding="utf-8"))
    story_path = tmp_path / manifest["story_path"]
    story_path.write_text(
        story_path.read_text(encoding="utf-8") + "\nTAMPERED\n",
        encoding="utf-8",
    )
    called = False

    def must_not_call(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("Audit model must not run on stale/tampered source artifact.")

    with pytest.raises(RuntimeError, match="hash mismatch"):
        run_story_audit_once(
            manifest_path=copied_manifest,
            audit_call_fn=must_not_call,
            repo_root=tmp_path,
        )
    assert called is False


def test_story_audit_source_is_deterministic_and_bound_to_writer_artifact():
    left = build_story_audit_source(manifest_path=MANIFEST)
    right = build_story_audit_source(manifest_path=MANIFEST)

    assert left == right
    assert left["stage"] == 5
    assert left["source_artifact_id"].startswith("writer-story:")
    assert left["source_story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert left["audit_source_id"].startswith("story-audit-source:")
    assert left["story_segments"]


def test_story_audit_local_language_defect_produces_separate_immutable_audit_artifact():
    before = load_verified_writer_story_artifact(manifest_path=MANIFEST)
    original_story = before["story"]
    original_sha = before["manifest"]["story_sha256"]

    def fake_audit(**kwargs):
        segment = next(
            row
            for row in kwargs["audit_source"]["story_segments"]
            if "arriving at his shoulder" in row["text"]
        )
        return {
            "summary": "One bounded language-naturalness defect.",
            "findings": [
                {
                    "family": "language_naturalness",
                    "severity": "minor",
                    "repair_scope": "LOCAL_REPAIR",
                    "span_ids": [segment["id"]],
                    "exact_text": "arriving at his shoulder",
                    "reason": "The idiom is understandable but unnatural in this context.",
                }
            ],
        }

    audit = run_story_audit_once(
        manifest_path=MANIFEST,
        audit_call_fn=fake_audit,
    )

    after = load_verified_writer_story_artifact(manifest_path=MANIFEST)
    assert audit["schema"] == "spineforge-v20-story-audit-artifact.v1"
    assert audit["artifact_type"] == "IMMUTABLE_STORY_AUDIT"
    assert audit["stage"] == 5
    assert audit["input_verified"] is True
    assert audit["source_story_mutated"] is False
    assert audit["source_story_sha256"] == original_sha
    assert audit["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert audit["next_stage"] == "STORY_LOCAL_REPAIR"
    assert audit["artifact_id"].startswith("story-audit:")
    assert after["story"] == original_story
    assert after["manifest"]["story_sha256"] == original_sha


def test_story_audit_clean_result_routes_to_english_master_seal():
    def clean_audit(**kwargs):
        return {
            "summary": "No material defect found.",
            "findings": [],
        }

    audit = run_story_audit_once(
        manifest_path=MANIFEST,
        audit_call_fn=clean_audit,
    )
    assert audit["decision"] == "ACCEPT"
    assert audit["next_stage"] == "ENGLISH_MASTER_SEAL"
    assert audit["source_story_mutated"] is False


def test_story_audit_replan_blocks_downstream_progression():
    def replan_audit(**kwargs):
        first = kwargs["audit_source"]["story_segments"][0]
        return {
            "summary": "Synthetic replan qualification case.",
            "findings": [
                {
                    "family": "spine_fidelity",
                    "severity": "critical",
                    "repair_scope": "REPLAN",
                    "span_ids": [first["id"]],
                    "exact_text": "",
                    "reason": "Synthetic qualification: approved story path itself is invalid.",
                }
            ],
        }

    audit = run_story_audit_once(
        manifest_path=MANIFEST,
        audit_call_fn=replan_audit,
    )
    assert audit["decision"] == "REPLAN_REQUIRED"
    assert audit["next_stage"] == "STOP"
