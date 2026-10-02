from pathlib import Path

from src.spineforge_v20_story_local_repair_artifact import (
    build_story_local_repair_artifact,
)


def test_stage6_repair_product_is_immutable_and_preserves_199_span_lineage():
    artifact = build_story_local_repair_artifact()

    assert artifact["schema"] == "spineforge-v20-story-local-repair-artifact.v1"
    assert artifact["artifact_type"] == "IMMUTABLE_REPAIRED_ENGLISH_STORY"
    assert artifact["stage"] == 6
    assert artifact["status"] == "FROZEN"
    assert artifact["immutable"] is True
    assert artifact["artifact_id"] == (
        "story-local-repair:eca2fd757acea1bc5bf982ea3ded100a62fdae68687d0652d61ff729795614f1"
    )
    assert artifact["repaired_story_text_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
    assert artifact["patch_count"] == 24
    assert artifact["no_change_resolution_count"] == 1
    assert artifact["stable_span_count"] == 199
    assert artifact["no_change_span_ids"] == ["S161"]
    assert artifact["mandatory_full_reaudit"] is True
    assert artifact["next_stage"] == "STORY_REAUDIT"

    s006 = next(x for x in artifact["repaired_segments"] if x["span_id"] == "S006")
    assert s006["disposition"] == "PATCH"
    assert s006["source_text"] == '"I saw it first," Nisa said, arriving at his shoulder.'
    assert s006["repaired_text"] == '"I saw it first," Nisa said, stepping up beside him.'

    s161 = next(x for x in artifact["repaired_segments"] if x["span_id"] == "S161")
    assert s161["disposition"] == "NO_CHANGE"
    assert s161["repaired_text"] == s161["source_text"]


def test_stage6_repair_product_file_and_canonical_text_hashes_are_distinct_and_locked():
    artifact = build_story_local_repair_artifact()
    assert artifact["repaired_story_file_sha256"] == (
        "4a241d65e87440a2ce97297aa3be794d2f476633b28348d38c395a73f57b36ed"
    )
    assert artifact["repaired_story_file_sha256"] != artifact["repaired_story_text_sha256"]
    assert Path(artifact["repaired_story_path"]).exists()
