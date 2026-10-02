from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v20 import run
from src.spineforge_v20_obligations import load_qualification_cases


PACK = Path("data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json")


def _architect_response(pack: SpineContextPackV1) -> dict:
    locs = pack.approved_premise["location_refs"]
    return {
        "schema": "narrative-spine.v1",
        "title": "The Island That Wasn't on Any Map",
        "episode_concept": {
            "story_promise": "Arda and Nisa reach an uncharted island before it vanishes.",
            "story_family": "ADVENTURE_EXPLORATION",
            "tone": "adventurous, tense, wonder-filled",
            "target_reader_effect": "curiosity, momentum, and earned mystery",
        },
        "protagonist": {
            "role": "young explorer",
            "immediate_goal": "reach the island and learn whether someone was there before",
            "pressure": "the route home is closing",
        },
        "central_question": "Who reached the island before them, and how far should Arda go before turning back?",
        "stakes": "They can lose their route home or lose the discovery.",
        "world_specific_elements": [
            {"context_ref": locs[1], "narrative_use": "first landing"},
            {"context_ref": locs[2], "narrative_use": "active exploration"},
            {"context_ref": locs[3], "narrative_use": "prior expedition discovery"},
        ],
        "beats": [
            {
                "key": "land",
                "location_ref": locs[1],
                "character_action": "Arda commits to the landing with Nisa.",
                "external_change": "The island starts drifting faster.",
                "new_information": "Their route home is already shrinking.",
                "consequence": "They move inland instead of lingering.",
                "escalation": "The cloud wall closes in.",
            },
            {
                "key": "trace",
                "location_ref": locs[2],
                "character_action": "They follow a human-made trail marker through unfamiliar terrain.",
                "external_change": "The trail leads away from their return point.",
                "new_information": "Someone else definitely explored this island.",
                "consequence": "Arda pushes toward the abandoned site.",
                "escalation": "Nisa argues that they are going too far.",
            },
            {
                "key": "site",
                "location_ref": locs[3],
                "character_action": "Arda searches the abandoned site and finds one concrete expedition trace.",
                "external_change": "The return corridor begins collapsing.",
                "new_information": "The earlier explorers expected the island to move again.",
                "consequence": "Arda chooses to take the trace and turn back now.",
                "escalation": "They must race the closing route.",
            },
            {
                "key": "escape",
                "location_ref": locs[1],
                "character_action": "Arda and Nisa launch together and escape with the discovered trace.",
                "external_change": "The island disappears into the cloud wall.",
                "new_information": "They were not first, but they are the first current scouts to return with proof of its history.",
                "consequence": "The island becomes a real unresolved discovery.",
                "escalation": "The clue points toward a larger mystery.",
            },
        ],
        "decision": {
            "required": True,
            "pressure": "The return corridor is almost gone.",
            "options": [
                {
                    "option": "follow the final clue deeper",
                    "immediate_cost": "risk losing the route home",
                    "possible_consequence": "learn more but become stranded",
                },
                {
                    "option": "turn back with the expedition trace",
                    "immediate_cost": "leave the deepest clue unresolved",
                    "possible_consequence": "return safely with a bounded discovery",
                },
            ],
        },
        "climax": "Arda chooses to turn back with the expedition trace and races Nisa to the gliders as the route closes.",
        "local_payoff": "They escape with proof that the island has a prior expedition history while its origin remains unknown.",
        "unresolved_hooks": ["Who left the expedition trace?", "Where does the island go?"],
        "reveal_limits": ["Do not explain the island's ultimate origin or destination."],
        "persistent_outcome_candidates": [
            {
                "type": "KNOWLEDGE",
                "description": "The uncharted island has evidence of prior explorers.",
                "commit_condition": "Delivered prose shows the trace being found and brought back.",
            }
        ],
        "writer_rules": [
            "Keep exploration and movement foregrounded.",
            "Do not turn the episode into a measurement or reporting sequence.",
        ],
    }


def _architect_call(**kwargs):
    raw = _architect_response(
        SpineContextPackV1.model_validate(
            json.loads(kwargs["user_prompt"])["spine_context_pack"]
        )
    )
    return raw, {"usage": {}}, {"response_format": {"type": "json_object"}}, []


def _gate_call(**kwargs):
    raw = {
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "Ready for human review.",
    }
    return raw, {"usage": {}}, {"response_format": {"type": "json_schema"}}, []


def test_v20_runtime_uses_story_first_prompt_and_stops_for_human_review():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = load_qualification_cases().cases[0]
    result = run(
        context_pack=pack,
        obligations=case.obligations,
        api_key="not-used",
        architect_call_fn=_architect_call,
        gate_call_fn=_gate_call,
    )
    assert result["schema"] == "spineforge-v20-evidence.v1"
    assert result["status"] == "awaiting_human_review"
    assert result["writer_authorized"] is False
    assert result["generation_topology"][0] == "SONNET_STORY_FIRST_NARRATIVE_SPINE_ARCHITECT"
    assert result["deterministic_validation"]["authority_valid"] is True
    assert result["deterministic_validation"]["reveal_safe"] is True
    assert result["deterministic_validation"]["obligations_valid"] is True


def test_v20_auto_pipeline_runs_clean_story_to_publication_without_human_checkpoint():
    from src.spineforge_v20_auto_pipeline import run_auto_pipeline

    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = load_qualification_cases().cases[0]
    base_story = "The Test Story\n\n" + ("adventure " * 1800)

    def spine_fn(**kwargs):
        return run(
            context_pack=kwargs["context_pack"],
            obligations=kwargs["obligations"],
            api_key=kwargs["api_key"],
            architect_call_fn=_architect_call,
            gate_call_fn=_gate_call,
        )

    def writer_fn(**kwargs):
        handoff = kwargs["handoff"]
        assert handoff["approval_mode"] == "AUTOMATED_PRODUCT_GATE_ACCEPT"
        assert handoff["human_review"]["automated_compatibility_shim"] is True
        return {"status": "writer_generated", "story": base_story}

    def audit_fn(**kwargs):
        return {"status": "clean", "findings": []}

    def repair_fn(**kwargs):
        raise AssertionError("repair must not run for clean story")

    def translation_fn(**kwargs):
        return {"status": "translated", "turkish_delivery": "Türkçe teslim"}

    def fidelity_fn(**kwargs):
        return {"status": "clean", "findings": []}

    result = run_auto_pipeline(
        context_pack=pack,
        obligations=case.obligations,
        api_key="not-used",
        system_prompt="not-used",
        spine_fn=spine_fn,
        writer_fn=writer_fn,
        audit_fn=audit_fn,
        local_repair_fn=repair_fn,
        translation_fn=translation_fn,
        fidelity_fn=fidelity_fn,
    )
    assert result["status"] == "PUBLICATION_READY"
    assert result["approval_mode"] == "AUTOMATED_PRODUCT_GATE_ACCEPT"
    assert result["repair_rounds"] == 0
    assert result["state_commit_authorized"] is True
    assert [row["stage"] for row in result["trace"]] == [
        "SPINE", "WRITER", "STORY_AUDIT", "TRANSLATION", "FIDELITY"
    ]


def test_v20_auto_pipeline_repairs_local_language_defect_and_rechecks_before_translation():
    from src.spineforge_v20_auto_pipeline import run_auto_pipeline

    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = load_qualification_cases().cases[0]
    defect = "Nisa said, arriving at his shoulder."
    fixed = "Nisa said, coming up beside him."
    base_story = "The Test Story\n\n" + defect + " " + ("adventure " * 1800)
    audit_calls = []

    def spine_fn(**kwargs):
        return run(
            context_pack=kwargs["context_pack"],
            obligations=kwargs["obligations"],
            api_key=kwargs["api_key"],
            architect_call_fn=_architect_call,
            gate_call_fn=_gate_call,
        )

    def writer_fn(**kwargs):
        return {"status": "writer_generated", "story": base_story}

    def audit_fn(**kwargs):
        story = kwargs["story"]
        audit_calls.append(story)
        if defect in story:
            return {
                "status": "findings",
                "findings": [{
                    "family": "language_naturalness",
                    "severity": "minor",
                    "repair_scope": "LOCAL_REPAIR",
                    "exact_text": defect,
                    "reason": "Awkward idiom.",
                }],
            }
        return {"status": "clean", "findings": []}

    def repair_fn(**kwargs):
        assert kwargs["findings"][0]["repair_scope"] == "LOCAL_REPAIR"
        return {"replacements": [{"old": defect, "new": fixed}]}

    def translation_fn(**kwargs):
        assert defect not in kwargs["english_master"]
        assert fixed in kwargs["english_master"]
        return {"status": "translated", "turkish_delivery": "Türkçe teslim"}

    def fidelity_fn(**kwargs):
        return {"status": "clean", "findings": []}

    result = run_auto_pipeline(
        context_pack=pack,
        obligations=case.obligations,
        api_key="not-used",
        system_prompt="not-used",
        spine_fn=spine_fn,
        writer_fn=writer_fn,
        audit_fn=audit_fn,
        local_repair_fn=repair_fn,
        translation_fn=translation_fn,
        fidelity_fn=fidelity_fn,
    )
    assert result["status"] == "PUBLICATION_READY"
    assert result["repair_rounds"] == 1
    assert len(audit_calls) == 2
    assert defect not in result["english_master"]
    assert fixed in result["english_master"]
    assert result["repair_evidence"][0]["applied"] == [{"old": defect, "new": fixed}]


def test_v20_auto_pipeline_stops_on_structural_or_replan_defect_without_translation():
    from src.spineforge_v20_auto_pipeline import run_auto_pipeline

    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = load_qualification_cases().cases[0]
    base_story = "The Test Story\n\n" + ("adventure " * 1800)

    def spine_fn(**kwargs):
        return run(
            context_pack=kwargs["context_pack"],
            obligations=kwargs["obligations"],
            api_key=kwargs["api_key"],
            architect_call_fn=_architect_call,
            gate_call_fn=_gate_call,
        )

    def writer_fn(**kwargs):
        return {"status": "writer_generated", "story": base_story}

    def audit_fn(**kwargs):
        return {
            "status": "findings",
            "findings": [{
                "family": "plot",
                "severity": "serious",
                "repair_scope": "REPLAN",
                "reason": "Selected plot path is invalid.",
            }],
        }

    def must_not_run(**kwargs):
        raise AssertionError("downstream stage must not run after REPLAN")

    result = run_auto_pipeline(
        context_pack=pack,
        obligations=case.obligations,
        api_key="not-used",
        system_prompt="not-used",
        spine_fn=spine_fn,
        writer_fn=writer_fn,
        audit_fn=audit_fn,
        local_repair_fn=must_not_run,
        translation_fn=must_not_run,
        fidelity_fn=must_not_run,
    )
    assert result["status"] == "STOP_REPLAN"
    assert result["trace"][-1]["stage"] == "STORY_AUDIT"


def test_v20_auto_pipeline_has_production_defaults_and_usage_lineage():
    import inspect
    from src.spineforge_v20_auto_pipeline import run_auto_pipeline

    params = inspect.signature(run_auto_pipeline).parameters
    for name in [
        "system_prompt", "spine_fn", "audit_fn", "local_repair_fn",
        "translation_fn", "fidelity_fn"
    ]:
        assert params[name].default is None

    for path in [
        "src/spineforge_v20_auto_stages.py",
        "prompts/spineforge_v20_story_audit.md",
        "prompts/spineforge_v20_story_local_repair.md",
        "prompts/translation_en_tr_v2_generic.md",
        "prompts/translation_fidelity_gate_v2_generic.md",
    ]:
        assert Path(path).exists()

    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    case = load_qualification_cases().cases[0]
    story = "The Test Story\n\n" + ("adventure " * 1800)

    def spine_fn(**kwargs):
        return run(
            context_pack=kwargs["context_pack"],
            obligations=kwargs["obligations"],
            api_key=kwargs["api_key"],
            architect_call_fn=_architect_call,
            gate_call_fn=_gate_call,
        )

    def writer_fn(**kwargs):
        return {
            "status": "writer_generated",
            "story": story,
            "writer_usage_rollup": {
                "calls": [{
                    "stage": "writer", "model": "fake", "provider": "test",
                    "status": "completed", "attempt": 1,
                    "input_tokens": 10, "output_tokens": 20, "reasoning_tokens": 0,
                    "cached_tokens": 0, "cache_write_tokens": 0,
                    "total_tokens": 30, "cost_usd": 0.01, "latency_seconds": 1.0,
                }]
            },
        }

    def audit_fn(**kwargs):
        return {"status": "clean", "findings": []}

    def translation_fn(**kwargs):
        return {"status": "translated", "turkish_delivery": "Türkçe teslim"}

    def fidelity_fn(**kwargs):
        return {"status": "clean", "findings": []}

    result = run_auto_pipeline(
        context_pack=pack,
        obligations=case.obligations,
        api_key="not-used",
        spine_fn=spine_fn,
        writer_fn=writer_fn,
        audit_fn=audit_fn,
        local_repair_fn=lambda **kwargs: {"replacements": []},
        translation_fn=translation_fn,
        fidelity_fn=fidelity_fn,
    )
    assert result["status"] == "PUBLICATION_READY"
    assert result["pipeline_usage_rollup"]["totals"]["total_tokens"] == 30
    assert result["total_cost_usd"] == 0.01
    assert result["total_latency_seconds"] == 1.0
