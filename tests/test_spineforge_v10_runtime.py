from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import src.spineforge_v4 as v4
import src.spineforge_v10 as sf
from src.generate import OpenRouterCallError
from src.spine_context_pack_v1 import SpineContextPackV1

PACK = Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
RAW_FIXTURE = Path("data/specifications/story_lab/spineforge_v4_replay_fixture.json")


def _source() -> dict:
    raw = copy.deepcopy(json.loads(RAW_FIXTURE.read_text())["creative_raw_payload"])
    normalized, _ = v4._normalize_creative_raw(raw)
    return normalized


def _blueprint() -> dict:
    source = _source()
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


def _frame() -> dict:
    source = _source()
    spine = source["episode_spine"]
    logistics = spine["logistics_plan"]
    return {
        "schema": "spineforge-structural-frame.v1",
        "preserved_creative_strengths": [
            source["creative_signature"]["dramatic_engine"],
            source["creative_signature"]["central_wonder_or_intrigue"],
        ],
        "title": spine["title"],
        "episode_role": spine["episode_role"],
        "story_promise": spine["story_promise"],
        "protagonist_role": spine["protagonist_role"],
        "immediate_objective": spine["immediate_objective"],
        "central_question": spine["central_question"],
        "stakes": spine["stakes"],
        "constraints": spine["constraints"],
        "opening_hook": spine["opening_hook"],
        "logistics": {
            "time_window": logistics["time_window"],
            "movement_constraints": logistics["movement_constraints"],
            "feasibility_rationale": logistics["feasibility_rationale"],
        },
        "escalation_ladder": spine["escalation_ladder"],
        "climax": spine["climax"],
        "local_payoff": spine["local_payoff"],
        "forward_hook": spine["forward_hook"],
        "writer_rules": spine["writer_rules"],
        "compilation_notes": ["partitioned compile"],
        "creative_deviations": [],
    }


def _beats() -> dict:
    return {
        "schema": "spineforge-structural-beats.v1",
        "beats": _source()["episode_spine"]["beats"],
    }


def _resolution() -> dict:
    spine = _source()["episode_spine"]
    decision = dict(spine["decision_point"])
    decision.pop("outcome_uncommitted", None)
    saga = {"completion_evidence": spine["saga_progression"]["completion_evidence"]}
    return {
        "schema": "spineforge-structural-resolution.v1",
        "reversal": spine["reversal"],
        "decision_point": decision,
        "persistent_outcome_candidates": spine["persistent_outcome_candidates"],
        "saga_progression": saga,
        "anti_repetition_signature": spine["anti_repetition_signature"],
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
            {"name": name, "score": 4, "blocking_failure": False, "reason": "ok"}
            for name in names
        ],
        "decision": "ACCEPT",
        "blocking_reasons": [],
        "decision_reason": "Product-ready.",
    }


def _body(cost: float = 0.001) -> dict:
    return {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cost": cost,
        }
    }


def _install_success_chain(monkeypatch):
    seq = [_blueprint(), _frame(), _beats(), _resolution(), _gate_accept()]
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return seq[len(calls) - 1], _body(), {
            "response_format": {"type": "json_schema"},
            "provider": {"require_parameters": True},
        }, []

    monkeypatch.setattr(sf, "call_structured_json_once", fake)
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)
    return calls


def test_v10_full_partitioned_chain_reaches_human_stop(monkeypatch, tmp_path: Path) -> None:
    calls = _install_success_chain(monkeypatch)
    result = sf.run(context_pack_path=PACK, out_path=tmp_path / "result.json", api_key="secret-test")
    assert result["status"] == "awaiting_human_review"
    assert result["human_review"]["writer_authorized"] is False
    assert len(calls) == 5
    assert [c["model"] for c in calls] == [
        sf.AION_MODEL,
        sf.SONNET_MODEL,
        sf.SONNET_MODEL,
        sf.SONNET_MODEL,
        sf.LUNA_MODEL,
    ]
    product = result["spine_product"]
    assert product["structural_assembly"]["structural_model"] == sf.SONNET_MODEL
    assert product["structural_assembly"]["episode_spine"]["exact_age"] == 18
    assert product["structural_assembly"]["episode_spine"]["saga_progression"]["commit_only_if_earned"] is True
    assert product["structural_assembly"]["episode_spine"]["decision_point"]["outcome_uncommitted"] is True
    assert result["pipeline_usage_rollup"]["totals"]["api_calls"] == 5
    assert "secret-test" not in (tmp_path / "result.json").read_text()


def test_v10_every_call_receives_same_context_pack(monkeypatch, tmp_path: Path) -> None:
    calls = _install_success_chain(monkeypatch)
    result = sf.run(context_pack_path=PACK, out_path=tmp_path / "result.json", api_key="x")
    payloads = [json.loads(row["user_prompt"]) for row in calls]
    packs = [row["spine_context_pack"] for row in payloads]
    assert len(packs) == 5
    assert {row["context_pack_id"] for row in packs} == {result["context_pack_id"]}
    assert {row["context_fingerprint"] for row in packs} == {result["context_fingerprint"]}


def test_v10_checkpoints_aion_usage_before_sonnet_provider_failure(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _blueprint(), _body(0.00125), {
                "response_format": {"type": "json_object"},
                "provider": {},
            }, []
        raise OpenRouterCallError(
            "OpenRouter HTTP 400 for Sonnet: compiled grammar rejected",
            {
                "stage": "http_response",
                "model": sf.SONNET_MODEL,
                "status_code": 400,
                "error_body": {"error": {"message": "compiled grammar rejected"}},
            },
        )

    monkeypatch.setattr(sf, "call_structured_json_once", fake)
    monkeypatch.setattr(sf, "require_qualification_runtime_profile", lambda model: None)
    out = tmp_path / "result.json"
    result = sf.run(context_pack_path=PACK, out_path=out, api_key="never-persist-this")
    persisted = json.loads(out.read_text())
    assert result["status"] == "provider_or_transport_rejected"
    assert persisted["failure"]["stage"] == "spineforge_structural_frame"
    totals = persisted["pipeline_usage_rollup"]["totals"]
    assert totals["api_calls"] == 1
    assert totals["total_tokens"] == 150
    assert totals["cost_usd"] == pytest.approx(0.00125)
    assert "never-persist-this" not in out.read_text()
    assert result["revision_feedback_candidate"]["retry_stage"] == "STRUCTURAL_FRAME"


def test_v10_resolution_retry_reuses_blueprint_frame_and_beats(monkeypatch, tmp_path: Path) -> None:
    first_calls = _install_success_chain(monkeypatch)
    first = sf.run(context_pack_path=PACK, out_path=tmp_path / "first.json", api_key="x")
    assert len(first_calls) == 5

    pack = SpineContextPackV1.model_validate_json(PACK.read_text())
    feedback = {
        "schema": "spineforge-revision-feedback.v7",
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "source_attempt": 1,
        "next_attempt": 2,
        "source_status": "structural_resolution_contract_rejected",
        "retry_stage": "STRUCTURAL_RESOLUTION",
        "must_preserve": ["creative identity"],
        "must_change": ["resolution defect"],
        "preserved_blueprint": first["spine_product"]["creative_blueprint"],
        "preserved_frame": first["spine_product"]["structural_frame"],
        "preserved_beats": first["spine_product"]["structural_beats"],
        "validation_errors": ["resolution defect"],
        "authority_freezes": list(pack.hard_freezes),
    }
    feedback_path = tmp_path / "feedback.json"
    feedback_path.write_text(json.dumps(feedback))

    seq = [_resolution(), _gate_accept()]
    calls = []

    def fake(**kwargs):
        calls.append(kwargs)
        return seq[len(calls) - 1], _body(), {
            "response_format": {"type": "json_schema"},
            "provider": {"require_parameters": True},
        }, []

    monkeypatch.setattr(sf, "call_structured_json_once", fake)
    second = sf.run(
        context_pack_path=PACK,
        out_path=tmp_path / "second.json",
        revision_feedback_path=feedback_path,
        api_key="x",
    )
    assert second["status"] == "awaiting_human_review"
    assert second["attempt_index"] == 2
    assert second["creative_blueprint_reused"] is True
    assert second["structural_frame_reused"] is True
    assert second["structural_beats_reused"] is True
    assert len(calls) == 2
    assert calls[0]["model"] == sf.SONNET_MODEL
    assert calls[1]["model"] == sf.LUNA_MODEL


def test_v10_human_approval_is_fingerprint_bound(monkeypatch, tmp_path: Path) -> None:
    from src.spineforge_v10_human_approval import build_spineforge_v10_approval

    _install_success_chain(monkeypatch)
    evidence = sf.run(context_pack_path=PACK, out_path=tmp_path / "result.json", api_key="x")
    pack = SpineContextPackV1.model_validate_json(PACK.read_text())
    approved = build_spineforge_v10_approval(
        evidence=evidence,
        current_context_pack=pack,
        source_run_id=123,
        reviewer_note="approved",
    )
    assert approved["human_review"]["story_writer_authorized"] is True
    assert approved["context_fingerprint"] == pack.context_fingerprint
