from __future__ import annotations

import copy
import json
from pathlib import Path

import src.spineforge_v4 as sf4
import src.spineforge_v5 as sf5
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v3_contract import SpineCreativeDraftV1
from src.spineforge_v5_contract import CreativeSpineSeedV5


PACK = Path("data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json")
RAW_FIXTURE = Path("data/specifications/story_lab/spineforge_v4_replay_fixture.json")
V4_PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v4_normalizer_integrity_frozen.json")


def _raw() -> dict:
    return copy.deepcopy(json.loads(RAW_FIXTURE.read_text())["creative_raw_payload"])


def _valid_spine() -> dict:
    normalized, _ = sf4._normalize_creative_raw(_raw())
    draft = SpineCreativeDraftV1.model_validate(normalized)
    return draft.episode_spine.model_dump(mode="json", by_alias=True)


def _seed() -> dict:
    raw = _raw()
    spine = raw["episode_spine"]
    moments = []
    for beat in spine["beats"][:9]:
        moments.append({
            "key": beat["key"],
            "location_ref": beat["location_ref"],
            "scene_intent": beat["purpose"],
            "protagonist_move": beat["character_action"],
            "pressure_or_event": beat["external_event"],
            "change_or_discovery": beat["new_information"],
        })
    return {
        "schema": "spineforge-creative-seed.v5",
        "creative_model": "model-authored-label",
        "creative_signature": raw["creative_signature"],
        "working_title": spine["title"],
        "story_promise": spine["story_promise"],
        "protagonist_role": spine["protagonist_role"],
        "immediate_objective": spine["immediate_objective"],
        "central_question": spine["central_question"],
        "stakes": spine["stakes"],
        "constraints": spine["constraints"],
        "moments": moments,
        "decision_pressure": spine["decision_point"]["pressure"],
        "decision_options": [row["option"] for row in spine["decision_point"]["branches"]],
        "climax_intent": spine["climax"],
        "local_payoff": spine["local_payoff"],
        "forward_hook": spine["forward_hook"],
        "writer_texture": [
            "Tactile magical cartography.",
            "Professional field craft under pressure.",
        ],
    }


def _compiled() -> dict:
    return {
        "schema": "spineforge-structural-compile.v5",
        "decision": "COMPILED",
        "assessment_summary": "Creative seed compiled into a strict causal spine.",
        "preserved_creative_strengths": [
            "Impossible-road epistemological hook.",
            "Cartographer roleplay under pressure.",
        ],
        "compiler_notes": ["Application-owned authority values preserved."],
        "episode_spine": _valid_spine(),
        "replan_feedback": [],
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
            {"name": name, "score": 4, "blocking_failure": False, "reason": "meets threshold"}
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


def _run_with_sequence(monkeypatch, tmp_path: Path, seq: list[dict]) -> tuple[dict, list[dict]]:
    captured = []

    def fake(**kwargs):
        captured.append(kwargs)
        return copy.deepcopy(seq[len(captured) - 1]), _body(), {}, []

    monkeypatch.setattr(sf5, "call_structured_json_with_retry", fake)
    monkeypatch.setattr(sf5, "require_qualification_runtime_profile", lambda model: None)
    result = sf5.run(context_pack_path=PACK, out_path=tmp_path / "result.json", api_key="x")
    return result, captured


def test_v5_aion_seed_contract_excludes_final_episode_bookkeeping() -> None:
    schema = CreativeSpineSeedV5.model_json_schema(by_alias=True)
    moment = schema["$defs"]["CreativeMomentV5"]["properties"]
    assert "phase" not in moment
    assert "new_information" not in moment
    assert "causal_dependency_keys" not in moment
    assert "movement_constraints" not in json.dumps(schema)

    pack = SpineContextPackV1.model_validate_json(PACK.read_text())
    obligations = sf5.build_structural_obligations(pack)
    assert obligations["mandatory_phases"] == [
        "HOOK", "COMPLICATION", "REVERSAL", "DECISION", "CLIMAX", "PAYOFF"
    ]
    assert "new_information" in obligations["required_beat_fields"]


def test_v5_archived_spine_fixture_reaches_human_stop_without_inference(
    monkeypatch, tmp_path: Path
) -> None:
    result, captured = _run_with_sequence(
        monkeypatch,
        tmp_path,
        [_seed(), _compiled(), _gate_accept()],
    )
    assert result["status"] == "awaiting_human_review"
    assert result["human_review"]["writer_authorized"] is False
    assert result["spine_product"]["schema"] == "spineforge-product.v5"
    assert len(captured) == 3

    payloads = [json.loads(row["user_prompt"]) for row in captured]
    packs = [row["spine_context_pack"] for row in payloads]
    assert {row["context_pack_id"] for row in packs} == {result["context_pack_id"]}
    assert {row["context_fingerprint"] for row in packs} == {result["context_fingerprint"]}


def test_v5_seed_authority_failure_stops_before_sonnet(monkeypatch, tmp_path: Path) -> None:
    seed = _seed()
    seed["moments"][0]["location_ref"] = "hidden_unapproved_location"
    result, captured = _run_with_sequence(monkeypatch, tmp_path, [seed])
    assert result["status"] == "creative_seed_rejected"
    assert len(captured) == 1
    assert result["human_review"]["writer_authorized"] is False


def test_v5_missing_new_information_is_sonnet_boundary_not_aion_boundary(
    monkeypatch, tmp_path: Path
) -> None:
    compiled = _compiled()
    del compiled["episode_spine"]["beats"][1]["new_information"]
    result, captured = _run_with_sequence(monkeypatch, tmp_path, [_seed(), compiled])
    assert result["status"] == "structural_compile_rejected"
    assert len(captured) == 2
    assert "new_information" in result["failure"]["message"]


def test_v5_missing_complication_is_sonnet_boundary_not_aion_boundary(
    monkeypatch, tmp_path: Path
) -> None:
    compiled = _compiled()
    for beat in compiled["episode_spine"]["beats"]:
        if beat["phase"] == "COMPLICATION":
            beat["phase"] = "ESCALATION"
    result, captured = _run_with_sequence(monkeypatch, tmp_path, [_seed(), compiled])
    assert result["status"] == "structural_compile_rejected"
    assert len(captured) == 2
    assert "COMPLICATION" in result["failure"]["message"]


def test_v5_v4_historical_freeze_remains_verifiable() -> None:
    verified = verify_spineforge_runtime(V4_PROFILE)
    assert verified["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v4"
    assert verified["verified_files"] == 26
    assert verified["verified"] is True


def test_v5_runtime_contains_no_case_specific_recovery() -> None:
    text = Path("src/spineforge_v5.py").read_text(encoding="utf-8")
    for token in ("Leyra", "Ashen Gate", "Greyfen", "forbidden_cartographer"):
        assert token not in text
