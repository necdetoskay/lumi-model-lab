from src.spineforge_v20_story_reaudit_cycle2_handoff import (
    build_story_reaudit_cycle2_handoff,
)


def test_stage9_handoff_uses_only_frozen_stage8_product():
    handoff = build_story_reaudit_cycle2_handoff()

    assert handoff["schema"] == "spineforge-v20-story-reaudit-cycle2-handoff.v1"
    assert handoff["artifact_type"] == "IMMUTABLE_STAGE9_REAUDIT_INPUT"
    assert handoff["stage"] == 9
    assert handoff["status"] == "READY_NOT_AUTHORIZED"
    assert handoff["immutable"] is True
    assert handoff["artifact_id"] == (
        "story-reaudit-cycle2-handoff:1558e2ec00a6c6c0d2365d442dc4eafbafc9663de23443540b53e4f874387474"
    )
    assert handoff["source_stage8_artifact_id"] == (
        "story-local-repair-cycle2:61237a22b0d46ba41cc44f51026b9dc4cf83030d794fdb5668e44bad00a1fa87"
    )
    assert handoff["repaired_story_text_sha256"] == (
        "b9a4675cd79f458ee8d29fd11f1bb5fdddfe4abec68c394efcddf60fb892eb95"
    )
    assert handoff["stable_span_count"] == 199
    assert len(handoff["changed_span_ids"]) == 14
    assert handoff["no_change_span_ids"] == ["S161", "S182"]
    assert handoff["paid_execution_authorized"] is False
    assert handoff["reaudit_policy"]["full_story_required"] is True
    assert handoff["reaudit_policy"]["all_199_stable_spans_required"] is True
    assert handoff["reaudit_policy"]["changed_spans_only_forbidden"] is True
