from __future__ import annotations

from pathlib import Path

from src.spine_context_pack_v1 import SpineContextPackV1, write_spine_context_pack
from src.spineforge_v11 import run
from src.spineforge_v11_contract import AUDIT_DIMENSIONS


def _valid_spine(pack: SpineContextPackV1) -> dict:
    location = pack.approved_premise["location_refs"][0]
    phases = [
        "HOOK",
        "ORIENT",
        "COMPLICATION",
        "INVESTIGATION",
        "ESCALATION",
        "REVERSAL",
        "DECISION",
        "CLIMAX",
        "PAYOFF",
    ]
    beats = []
    for index, phase in enumerate(phases, start=1):
        key = f"beat_{index:02d}"
        beats.append({
            "key": key,
            "phase": phase,
            "purpose": f"Advance the playable situation through {phase.lower()}.",
            "location_ref": location,
            "character_action": "Leyra actively tests, compares, chooses, or acts on available evidence.",
            "external_event": "The environment or social pressure changes in response.",
            "new_information": "A bounded observation changes the available interpretation.",
            "causal_dependency_keys": [] if index == 1 else [f"beat_{index - 1:02d}"],
            "escalation_delta": "Pressure or consequence increases.",
            "state_change": "Leyra has a materially changed decision state.",
            "payoff_contribution": "The episode-level promise moves toward resolution.",
        })

    intended = list(pack.saga["intended_milestone_keys"])
    return {
        "schema": "episode-spine.v2",
        "premise_key": pack.approved_premise["key"],
        "title": "The Line That Returned",
        "exact_age": int(pack.reader_profile["exact_age"]),
        "session": pack.session_target["name"],
        "target_words_min": int(pack.session_target["target_words_min"]),
        "target_words_max": int(pack.session_target["target_words_max"]),
        "episode_role": "MAIN_SAGA_PROGRESS" if intended else "WORLD_EXPLORATION",
        "story_promise": "Leyra must determine what the returned boundary evidence really permits her to claim.",
        "protagonist_role": "An apprentice cartographer acting through professional judgment.",
        "immediate_objective": "Complete the authorized survey and decide what can responsibly be reported.",
        "central_question": "What does the changed boundary evidence actually prove?",
        "stakes": "A wrong conclusion can mislead the ward-keepers and damage Leyra's professional credibility.",
        "constraints": ["No crossing the forbidden passage.", "Separate observation from inference."],
        "opening_hook": "A legal map and the physical boundary disagree in a way Leyra cannot dismiss.",
        "logistics_plan": {
            "time_window": "One field window before dusk.",
            "location_sequence": [location],
            "movement_constraints": ["Remain within authorized exterior survey access."],
            "feasibility_rationale": "The episode stays inside one permitted survey area.",
        },
        "beats": beats,
        "escalation_ladder": [
            "A routine discrepancy appears.",
            "Repeated measurements make the discrepancy harder to dismiss.",
            "The evidence creates professional and relational pressure.",
            "Leyra must choose what claim she is willing to stand behind.",
        ],
        "reversal": {
            "prior_belief": "The discrepancy is probably an ordinary copying or measurement problem.",
            "evidence": [{
                "claim": "The repeated field response is inconsistent with a simple copying error.",
                "supporting_beat_keys": ["beat_04", "beat_05", "beat_06"],
                "certainty": "OBSERVED",
            }],
            "reinterpretation": "The map disagreement is now a live field anomaly, not merely clerical noise.",
            "inference_ceiling": "The evidence does not prove why the anomaly exists or that the passage reopened.",
            "unresolved_after_reversal": "Cause, intent, and any hidden history remain unknown.",
        },
        "decision_point": {
            "pressure": "Leyra must decide how strongly to characterize the anomaly before conditions fade.",
            "branches": [
                {
                    "key": "document_only",
                    "option": "Record only the bounded observations and request another survey.",
                    "immediate_action": "Create a conservative field record.",
                    "evidence_state_after_choice": "Observed facts remain separated from hypothesis.",
                    "cost_or_risk": "The immediate warning may be weaker than some ward-keepers want.",
                    "relationship_or_access_effect": "Shows procedural restraint.",
                    "climax_requirement": "Defend why restraint is the responsible professional action.",
                    "local_payoff_if_earned": "A defensible survey record survives scrutiny.",
                },
                {
                    "key": "flag_anomaly",
                    "option": "Flag the anomaly as urgent while explicitly labeling the cause unknown.",
                    "immediate_action": "Escalate the bounded finding without claiming a hidden explanation.",
                    "evidence_state_after_choice": "Observation and hypothesis remain visibly separated.",
                    "cost_or_risk": "Leyra risks professional pushback for escalating incomplete evidence.",
                    "relationship_or_access_effect": "Tests trust with mentor and keepers.",
                    "climax_requirement": "Make the case using only witnessed evidence.",
                    "local_payoff_if_earned": "The anomaly receives attention without becoming false canon.",
                },
            ],
            "what_is_unknown": "The cause and larger significance of the anomaly.",
            "outcome_uncommitted": True,
        },
        "climax": "Leyra must commit to an evidence-bounded professional stance under pressure rather than chase an attractive theory.",
        "local_payoff": "The survey ends with a usable, defensible account of what changed and what remains unknown.",
        "forward_hook": "The bounded anomaly creates a legitimate reason for future investigation.",
        "persistent_outcome_candidates": [{
            "type": "KNOWLEDGE",
            "description": "Leyra may retain a documented observation that the field state and legal map disagree.",
            "commit_condition": "Commit only if the final story earns and records the observation.",
        }],
        "saga_progression": {
            "intended_milestone_keys": intended,
            "commit_only_if_earned": True,
            "completion_evidence": ["The story must earn any milestone through witnessed field evidence and Leyra's decision."],
        },
        "anti_repetition_signature": {
            "core_problem_shape": "professional evidence conflict under access limits",
            "primary_activity": "field survey, comparison, interpretation, and decision",
            "main_location_pattern": "bounded exterior survey",
            "climax_shape": "evidence-bounded professional choice",
            "distinct_from_recent_episodes_because": "The test fixture has no recent episode history.",
        },
        "writer_rules": [
            "Keep Leyra active rather than passive.",
            "Preserve the difference between observation, inference, and hypothesis.",
            "Do not reveal hidden Saga truth.",
        ],
    }


def _accept_audit() -> dict:
    return {
        "schema": "spineforge-v11-audit.v1",
        "decision": "ACCEPT",
        "dimensions": [
            {
                "name": name,
                "score": 5,
                "blocking_failure": False,
                "evidence": ["The mock spine supplies concrete protected evidence."],
                "reason": "Protected for zero-cost control flow verification.",
            }
            for name in sorted(AUDIT_DIMENSIONS)
        ],
        "blocking_defects": [],
        "repair_targets": [],
        "preserve": ["active protagonist", "evidence discipline"],
        "decision_reason": "Mock audit accepts the structurally valid control fixture.",
    }


def test_v11_runtime_calls_sonnet_exactly_twice_then_stops(tmp_path: Path):
    source = Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")
    pack_path = tmp_path / "pack.json"
    pack = write_spine_context_pack(source_path=source, out_path=pack_path)

    outputs = [_valid_spine(pack), _accept_audit()]
    calls = []

    def fake_call(**kwargs):
        calls.append(kwargs)
        raw = outputs[len(calls) - 1]
        body = {
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 500,
                "total_tokens": 1500,
                "cost": 0.007,
            }
        }
        request = {"response_format": {"type": "json_object"}, "provider": {"order": ["anthropic"]}}
        return raw, body, request, []

    result = run(
        context_pack_path=pack_path,
        out_path=tmp_path / "result.json",
        api_key="zero-cost-test",
        call_fn=fake_call,
    )

    assert result["status"] == "awaiting_human_review"
    assert len(calls) == 2
    assert [call["model"] for call in calls] == [
        "anthropic/claude-sonnet-5.5",
        "anthropic/claude-sonnet-5.5",
    ]
    assert result["automatic_repair_enabled"] is False
    assert result["writer_authorized"] is False
    assert result["deterministic_checks"]["episode_spine_contract_valid"] is True
    assert result["audit"]["decision"] == "ACCEPT"
