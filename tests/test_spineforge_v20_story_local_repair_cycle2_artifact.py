from src.spineforge_v20_story_local_repair_cycle2_artifact import (
    build_story_local_repair_cycle2_artifact,
)


def test_stage8_product_is_immutable_and_preserves_199_span_lineage():
    artifact = build_story_local_repair_cycle2_artifact()

    assert artifact["schema"] == "spineforge-v20-story-local-repair-cycle2-artifact.v1"
    assert artifact["artifact_type"] == "IMMUTABLE_REPAIRED_ENGLISH_STORY_CYCLE2"
    assert artifact["stage"] == 8
    assert artifact["status"] == "FROZEN"
    assert artifact["immutable"] is True
    assert artifact["artifact_id"] == (
        "story-local-repair-cycle2:61237a22b0d46ba41cc44f51026b9dc4cf83030d794fdb5668e44bad00a1fa87"
    )
    assert artifact["repaired_story_text_sha256"] == (
        "b9a4675cd79f458ee8d29fd11f1bb5fdddfe4abec68c394efcddf60fb892eb95"
    )
    assert artifact["patch_count"] == 14
    assert artifact["no_change_resolution_count"] == 2
    assert artifact["no_change_span_ids"] == ["S161", "S182"]
    assert artifact["stable_span_count"] == 199
    assert artifact["mandatory_full_reaudit"] is True
    assert artifact["next_stage"] == "STORY_REAUDIT"
