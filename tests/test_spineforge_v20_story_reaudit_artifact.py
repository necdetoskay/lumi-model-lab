from src.spineforge_v20_story_reaudit_artifact import build_story_reaudit_product


def test_stage7_reaudit_product_is_immutable_and_routes_only_remaining_findings():
    product = build_story_reaudit_product()
    assert product["schema"] == "spineforge-v20-story-reaudit-product.v1"
    assert product["artifact_type"] == "IMMUTABLE_STAGE7_REAUDIT_RESULT"
    assert product["stage"] == 7
    assert product["status"] == "FROZEN"
    assert product["immutable"] is True
    assert product["artifact_id"] == (
        "story-reaudit-product:7ec8360d92ab8a77431e78a039340b56277cc2ec7ac2ea301fe847f059655abe"
    )
    assert product["embedded_reaudit_artifact_id"] == (
        "story-reaudit:bb0eab55d2c5e5f868fff67c7ce742ecd2a5877c5a82263d6cee8dafbe514874"
    )
    assert product["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert product["next_stage"] == "STORY_LOCAL_REPAIR"
    assert product["finding_count"] == 16
    assert product["full_story_reaudited"] is True
    assert product["stable_span_count"] == 199
    assert product["source_repaired_story_text_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
