from src.spineforge_v20_story_reaudit_handoff import build_story_reaudit_handoff


def test_stage7_handoff_uses_only_frozen_stage6_product_as_story_source():
    handoff = build_story_reaudit_handoff()

    assert handoff["schema"] == "spineforge-v20-story-reaudit-handoff.v1"
    assert handoff["artifact_type"] == "IMMUTABLE_STAGE7_REAUDIT_INPUT"
    assert handoff["stage"] == 7
    assert handoff["status"] == "READY_NOT_AUTHORIZED"
    assert handoff["immutable"] is True
    assert handoff["artifact_id"] == (
        "story-reaudit-handoff:cff54c7a1491cc5d10724a0d44e8157c8b9e580279b53004c2894e0dc5b06cf3"
    )
    assert handoff["source_stage6_artifact_id"] == (
        "story-local-repair:eca2fd757acea1bc5bf982ea3ded100a62fdae68687d0652d61ff729795614f1"
    )
    assert handoff["repaired_story_text_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
    assert handoff["stable_span_count"] == 199
    assert len(handoff["changed_span_ids"]) == 24
    assert handoff["no_change_span_ids"] == ["S161"]
    assert handoff["reader"]["exact_age"] == 12
    assert handoff["paid_execution_authorized"] is False
    assert handoff["reaudit_policy"]["full_story_required"] is True
    assert handoff["reaudit_policy"]["all_199_stable_spans_required"] is True
    assert handoff["reaudit_policy"]["changed_spans_only_forbidden"] is True
    assert handoff["reaudit_policy"]["automatic_retry_enabled"] is False
    assert handoff["next_stage_on_accept"] == "ENGLISH_MASTER_SEAL"
