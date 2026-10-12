from tests.relay_event_fixture import event
import pytest
from pydantic import ValidationError

from src.spineforge_relay_v1_contracts import (
    CharacterState,
    SceneContractV1,
    StoryStateV1,
)
from src.spineforge_relay_v1_guard import (
    SemanticGuardReportV1,
    build_semantic_guard_input,
    combine_scene_validation,
    deterministic_scene_findings,
    normalize_semantic_guard,
)


H = "a" * 64


def state():
    return StoryStateV1(
        story_id="guard-test",
        revision=0,
        global_spine_sha256=H,
        story_intent_sha256=H,
        characters={
            "Duru": CharacterState(
                location="harbor",
                knowledge=["lighthouse_location", "coastal_route"],
            )
        },
        next_spine_beat="SC01",
    )


def contract():
    return SceneContractV1(
        scene_id="SC01",
        scene_plan_sha256=H,
        story_state_revision=0,
        story_state_sha256=H,
        global_spine_sha256=H,
        story_intent_sha256=H,
        consumed_spine_beats=["SC01"],
        next_spine_beat="SC02",
        required_events=[event("Duru", "INDICATE_DESTINATION", "lighthouse")],
        entry_state={},
        required_exit_state={},
        target_words_min=40,
        target_words_max=50,
    )


def test_deterministic_word_budget_is_blocking():
    findings = deterministic_scene_findings(
        prose=" ".join(["word"] * 51),
        contract=contract(),
    )
    assert [x.code for x in findings] == ["WORD_BUDGET_OUTSIDE_CONTRACT"]
    assert findings[0].severity == "BLOCKING"


def test_semantic_guard_requires_exact_prose_anchor():
    prose = "Duru said, \"They always carry their treasure to the tower before a storm.\""
    raw = {
        "schema_name": "spineforge-relay.semantic-guard.v1",
        "decision": "REWRITE",
        "findings": [{
            "code": "UNSUPPORTED_DRAGON_RULE",
            "family": "epistemic",
            "severity": "BLOCKING",
            "exact_text": "They always carry their treasure to the tower before a storm.",
            "reason": "Duru has no authority for this general dragon behavior.",
            "repair_instruction": "Remove the unsupported rule and rely only on observable lighthouse evidence.",
        }],
        "summary": "One blocking epistemic leak.",
    }
    report = normalize_semantic_guard(raw=raw, prose=prose)
    assert report.decision == "REWRITE"

    bad = dict(raw)
    bad["findings"] = [dict(raw["findings"][0], exact_text="not in prose")]
    with pytest.raises(RuntimeError, match="exact_text"):
        normalize_semantic_guard(raw=bad, prose=prose)


def test_pass_cannot_hide_blocking_finding():
    with pytest.raises(ValidationError):
        SemanticGuardReportV1.model_validate({
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "PASS",
            "findings": [{
                "code": "LEAK",
                "family": "epistemic",
                "severity": "BLOCKING",
                "exact_text": "x",
                "reason": "x",
                "repair_instruction": "x",
            }],
            "summary": "bad",
        })


def test_combined_attempt_one_requires_rewrite_when_semantic_blocking():
    prose = "Duru said the dragon was a mother."
    deterministic = []
    semantic = normalize_semantic_guard(
        raw={
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "REWRITE",
            "findings": [{
                "code": "MOTHER_KNOWLEDGE_LEAK",
                "family": "epistemic",
                "severity": "BLOCKING",
                "exact_text": "the dragon was a mother",
                "reason": "Duru does not know this.",
                "repair_instruction": "Remove the unsupported claim.",
            }],
            "summary": "Blocking leak.",
        },
        prose=prose,
    )
    result = combine_scene_validation(
        scene_id="SC01",
        attempt=1,
        deterministic=deterministic,
        semantic=semantic,
    )
    assert result.decision == "REWRITE"
    assert result.semantic_guard_used is True


def test_combined_attempt_two_rejects_non_convergent():
    prose = "Duru said the dragon was a mother."
    semantic = normalize_semantic_guard(
        raw={
            "schema_name": "spineforge-relay.semantic-guard.v1",
            "decision": "REWRITE",
            "findings": [{
                "code": "MOTHER_KNOWLEDGE_LEAK",
                "family": "epistemic",
                "severity": "BLOCKING",
                "exact_text": "the dragon was a mother",
                "reason": "Duru does not know this.",
                "repair_instruction": "Remove the unsupported claim.",
            }],
            "summary": "Blocking leak.",
        },
        prose=prose,
    )
    result = combine_scene_validation(
        scene_id="SC01",
        attempt=2,
        deterministic=[],
        semantic=semantic,
    )
    assert result.decision == "REJECT_NON_CONVERGENT"


def test_guard_input_carries_authoritative_state_and_deterministic_findings():
    prose = " ".join(["word"] * 51)
    det = deterministic_scene_findings(prose=prose, contract=contract())
    payload = build_semantic_guard_input(
        state=state(),
        contract=contract(),
        prose=prose,
        deterministic_findings=det,
    )
    assert payload["story_state"]["characters"]["Duru"]["knowledge"] == [
        "lighthouse_location",
        "coastal_route",
    ]
    assert payload["deterministic_findings"][0]["code"] == "WORD_BUDGET_OUTSIDE_CONTRACT"
    assert payload["semantic_policy"]["epistemic_claims_need_provenance"] is True
