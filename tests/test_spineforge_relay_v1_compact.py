import json
from pathlib import Path
import pytest
from src.spineforge_production_compact import CompactStoryPlanV1, compile_compact, compact_planner_input
from src.spineforge_seeded_design import verify_frozen_seed, validate_seeded_design
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_production_story import build_chain
from tests.test_spineforge_relay_v1_production_pipeline import sample
from tests.spineforge_compact_controls import compact_control


def inputs(tmp_path, kind="dialogue"):
    paths, design = sample(tmp_path / "input", kind)
    request = StoryRequestV1.model_validate_json(paths["request"].read_bytes())
    seed = verify_frozen_seed(paths["seed"], paths["freeze"])
    return paths, request, seed, design, compact_control(design)


@pytest.mark.parametrize("kind", ["mosaic", "dialogue"])
def test_compact_planning_preserves_frozen_start_and_projected_story_effects(tmp_path, kind):
    paths, request, seed, original, compact = inputs(tmp_path, kind)
    before = seed.model_dump(mode="json")
    compiled = compile_compact(request, seed, compact)
    new, old = tmp_path / "new.json", tmp_path / "old.json"
    new.write_text(json.dumps(compiled.fixture), encoding="utf8")
    old.write_text(json.dumps(original.fixture), encoding="utf8")
    proof = validate_seeded_design(request, seed, compiled, new)
    assert proof["status"] == "STRUCTURAL_PASS" and proof["semantic_status"] == "REQUIRES_REVIEW"
    assert compiled.fixture["initial_state"] == original.fixture["initial_state"]
    old_end, new_end = build_chain(old)[-1].model_dump(mode="json"), build_chain(new)[-1].model_dump(mode="json")
    # Intent differs by explicit resolution bindings; every state value is preserved.
    old_end.pop("story_intent_sha256"); new_end.pop("story_intent_sha256")
    assert old_end == new_end and seed.model_dump(mode="json") == before
    payload = compact_planner_input(request, seed)
    assert "fixture_schema" not in payload and "initial_state_template" not in payload
    small = json.dumps(compact.model_dump(mode="json", exclude_defaults=True), separators=(",", ":"))
    large = json.dumps(original.model_dump(mode="json"), separators=(",", ":"))
    assert len(small) < .6 * len(large)
    assert compiled.fixture["story_intent"]["resolution_bindings"]


@pytest.mark.parametrize("defect", ["seed", "scene_id", "missing_resolution", "unknown_resolution", "duplicate_resolution", "ungrounded_resolution", "goal", "metadata", "spatial_write", "entity", "rules", "conflict", "overlap", "precondition", "invented_edge"])
def test_compiler_fails_closed_without_inventing_repairs(tmp_path, defect):
    _, request, seed, _, compact = inputs(tmp_path, "mosaic" if defect == "invented_edge" else "dialogue")
    raw = compact.model_dump(mode="json")
    first, last = raw["scenes"][0], raw["scenes"][-1]
    if defect == "seed": raw["seed_sha256"] = "0" * 64
    elif defect == "scene_id": last["scene_id"] = first["scene_id"]
    elif defect == "missing_resolution": last["resolutions"] = []
    elif defect == "unknown_resolution": last["resolutions"][0]["id"] = "invented"
    elif defect == "duplicate_resolution": last["resolutions"].append(last["resolutions"][0])
    elif defect == "ungrounded_resolution": last["resolutions"][0]["evidence"]["predicate_id"] = "missing"
    elif defect == "goal": first["goal_bindings"]["turn"][0]["predicate_id"] = "missing"
    elif defect in {"metadata", "spatial_write", "entity", "rules"}:
        path = {"metadata": "/revision", "spatial_write": "/characters/Reader/location", "entity": "/characters/Invented/knowledge", "rules": "/world/rules"}[defect]
        first["events"][0]["resulting_state"][path] = "unauthorized"
    elif defect == "conflict":
        extra = json.loads(json.dumps(first["events"][0]));extra["id"] = "other"
        extra["resulting_state"]["/characters/Reader/knowledge"] = ["conflict"]
        first["events"].append(extra)
    elif defect == "overlap": first["events"][0]["resulting_state"]["/characters/Reader/knowledge/0"] = "overlap"
    elif defect == "precondition": first["preconditions"]["/characters/Reader/knowledge"] = ["not established"]
    else: raw["scenes"][3]["spatial_operations"][0]["edge_id"] = "invented"
    with pytest.raises((ValueError, RuntimeError)):
        compile_compact(request, seed, CompactStoryPlanV1.model_validate(raw))


def test_closure_status_and_original_details_are_compiler_owned(tmp_path):
    _, request, seed, _, compact = inputs(tmp_path)
    design = compile_compact(request, seed, compact)
    final = design.fixture["scene_plans"][-1]["required_exit_state"]
    assert final["/narrative_obligations"] == [{**o.model_dump(mode="json"), "status": "SATISFIED"} for o in seed.narrative_obligations]
    assert final["/open_threads"] == [] and final["/resolved_threads"] == seed.open_threads
