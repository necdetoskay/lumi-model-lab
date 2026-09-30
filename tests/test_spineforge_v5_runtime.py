from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import src.spineforge_v4 as v4
import src.spineforge_v5 as sf
from src.spine_context_pack_v1 import SpineContextPackV1

PACK = Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
RAW_FIXTURE = Path("data/specifications/story_lab/spineforge_v4_replay_fixture.json")


def _v4_normalized() -> dict:
    raw = copy.deepcopy(json.loads(RAW_FIXTURE.read_text())["creative_raw_payload"])
    normalized, _ = v4._normalize_creative_raw(raw)
    return normalized


def _blueprint() -> dict:
    source = _v4_normalized()
    spine = source["episode_spine"]
    return {
        "schema": "spineforge-creative-blueprint.v2",
        "creative_model": "model-authored-label",
        "creative_signature": source["creative_signature"],
        "episode_intent": {
            "title": spine["title"],
            "story_promise": spine["story_promise"],
            "protagonist_role": spine["protagonist_role"],
            "immediate_objective": spine["immediate_objective"],
            "central_question": spine["central_question"],
            "stakes": spine["stakes"],
            "opening_hook": spine["opening_hook"],
            "decision_pressure": spine["decision_point"]["pressure"],
            "climax_idea": spine["climax"],
            "local_payoff": spine["local_payoff"],
            "forward_hook": spine["forward_hook"],
            "unresolved_question": spine["reversal"]["unresolved_after_reversal"],
            "constraints": spine["constraints"],
        },
        "creative_beats": [
            {
                "key": beat["key"],
                "location_ref": beat["location_ref"],
                "dramatic_function": beat["purpose"],
                "character_action": beat["character_action"],
                "external_pressure_or_event": beat["external_event"],
                "discovery_or_change": beat["new_information"],
                "causal_dependency_keys": beat["causal_dependency_keys"],
            }
            for beat in spine["beats"]
        ],
        "roleplay_threads": source["creative_signature"]["roleplay_opportunities"],
        "self_check_notes": [],
    }


def _assembly() -> dict:
    return {
        "schema": "spineforge-structural-assembly.v1",
        "structural_model": "model-authored-label",
        "preserved_creative_strengths": [
            "Impossible-road hook",
            "Evidence-under-wonder engine",
        ],
        "episode_spine": _v4_normalized()["episode_spine"],
        "compilation_notes": ["Strict EpisodeSpine compiled from the creative blueprint."],
        "creative_deviations": [],
    }


def _gate_accept() -> dict:
    names = [
        "STORY_DESIRE", "ROLEPLAY_POTENTIAL", "SCENE_POTENTIAL",
        "CHARACTER_DRIVENNESS", "WORLD_SPECIFICITY", "WONDER_OR_INTRIGUE",
        "AGE_MATURITY", "CAUSAL_COHERENCE", "ESCALATION", "REVERSAL_QUALITY",
        "AGENCY", "BRANCH_EXECUTABILITY", "CLIMAX_PAYOFF", "LOCAL_SATISFACTION",
        "SAGA_ALIGNMENT", "WRITER_EXECUTABILITY", "FRESHNESS",
    ]
    return {
        "schema": "spineforge-product-gate.v1",
        "dimensions": [
            {
                "name": name,
                "score": 4,
                "blocking_failure": False,
                "reason": "meets threshold",
            }
            for name in names
        ],
        "decision": "ACCEPT",
        "blocking_reasons": [],
        "decision_reason": "Product-ready.",
    }


def _body() -> dict:
    return {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cost": 0.001,
        }
    }


def test_v5_full_stubbed_chain_reaches_human_stop(monkeypatch, tmp_path: Path) -> None:
    seq = [_blueprint(), _assembly(), _gate_accept()]
    captured = []

    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured) - 1], _body(), {}, []

    monkeypatch.setattr(sf, "call_structured_json_with_retry", fake)
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)

    result = sf.run(
        context_pack_path=PACK,
        out_path=tmp_path / "result.json",
        api_key="x",
    )
    assert result["status"] == "awaiting_human_review"
    assert result["human_review"]["writer_authorized"] is False
    assert len(captured) == 3
    assert result["spine_product"]["schema"] == "spineforge-product.v5"
    assert result["spine_product"]["creative_blueprint"]["creative_model"] == sf.AION_MODEL
    assert result["spine_product"]["structural_assembly"]["structural_model"] == sf.SONNET_MODEL


def test_v5_all_models_receive_same_context_pack(monkeypatch, tmp_path: Path) -> None:
    seq = [_blueprint(), _assembly(), _gate_accept()]
    captured = []

    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured) - 1], _body(), {}, []

    monkeypatch.setattr(sf, "call_structured_json_with_retry", fake)
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)

    result = sf.run(context_pack_path=PACK, out_path=tmp_path / "result.json", api_key="x")
    payloads = [json.loads(row["user_prompt"]) for row in captured]
    packs = [row["spine_context_pack"] for row in payloads]
    assert {row["context_pack_id"] for row in packs} == {result["context_pack_id"]}
    assert {row["context_fingerprint"] for row in packs} == {result["context_fingerprint"]}


def test_v5_structural_failure_preserves_blueprint_for_sonnet_retry(monkeypatch, tmp_path: Path) -> None:
    bad = _assembly()
    del bad["episode_spine"]["beats"][0]["new_information"]
    seq = [_blueprint(), bad]
    captured = []

    def fake(**kwargs):
        captured.append(kwargs)
        return seq[len(captured) - 1], _body(), {}, []

    monkeypatch.setattr(sf, "call_structured_json_with_retry", fake)
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)

    result = sf.run(context_pack_path=PACK, out_path=tmp_path / "first.json", api_key="x")
    assert result["status"] == "structural_assembly_contract_rejected"
    assert len(captured) == 2
    fb = result["revision_feedback_candidate"]
    assert fb["retry_stage"] == "STRUCTURAL_COMPILER"
    assert fb["preserved_blueprint"]["schema"] == "spineforge-creative-blueprint.v2"
    assert fb["next_attempt"] == 2


def test_v5_structural_retry_skips_aion(monkeypatch, tmp_path: Path) -> None:
    bad = _assembly()
    del bad["episode_spine"]["beats"][0]["new_information"]
    first_seq = [_blueprint(), bad]
    first_calls = []

    def first_fake(**kwargs):
        first_calls.append(kwargs)
        return first_seq[len(first_calls) - 1], _body(), {}, []

    monkeypatch.setattr(sf, "call_structured_json_with_retry", first_fake)
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)

    first = sf.run(context_pack_path=PACK, out_path=tmp_path / "first.json", api_key="x")
    feedback_path = tmp_path / "feedback.json"
    feedback_path.write_text(json.dumps(first["revision_feedback_candidate"]))

    second_seq = [_assembly(), _gate_accept()]
    second_calls = []

    def second_fake(**kwargs):
        second_calls.append(kwargs)
        return second_seq[len(second_calls) - 1], _body(), {}, []

    monkeypatch.setattr(sf, "call_structured_json_with_retry", second_fake)
    second = sf.run(
        context_pack_path=PACK,
        out_path=tmp_path / "second.json",
        revision_feedback_path=feedback_path,
        api_key="x",
    )
    assert second["attempt_index"] == 2
    assert second["creative_blueprint_reused"] is True
    assert second["status"] == "awaiting_human_review"
    assert len(second_calls) == 2
    assert second_calls[0]["model"] == sf.SONNET_MODEL
    assert second_calls[1]["model"] == sf.LUNA_MODEL


def test_v5_stale_feedback_stops_before_inference(monkeypatch, tmp_path: Path) -> None:
    pack = SpineContextPackV1.model_validate_json(PACK.read_text())
    feedback = {
        "schema": "spineforge-revision-feedback.v5",
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": "0" * 64,
        "source_attempt": 1,
        "next_attempt": 2,
        "source_status": "creative_blueprint_contract_rejected",
        "retry_stage": "CREATIVE_ARCHITECT",
        "must_preserve": ["approved premise"],
        "must_change": ["repair"],
        "creative_feedback": ["repair"],
        "structural_feedback": [],
        "preserved_blueprint": None,
        "validation_errors": ["repair"],
        "authority_freezes": list(pack.hard_freezes),
    }
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(feedback))
    calls = []
    monkeypatch.setattr(sf, "call_structured_json_with_retry", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)
    with pytest.raises(RuntimeError, match="context_fingerprint is stale"):
        sf.run(
            context_pack_path=PACK,
            out_path=tmp_path / "out.json",
            revision_feedback_path=path,
            api_key="x",
        )
    assert calls == []
