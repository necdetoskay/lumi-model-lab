"""Data-bound fresh spatial qualification inputs and shared request policy."""
import json
from pathlib import Path
from src.model_registry import normalize_openrouter_request
from src.spineforge_relay_v1_contracts import StoryStateV1, ScenePlanV1, FrozenSpineRouteV1, canonical_sha256
from src.spineforge_relay_v1_compile import compile_scene_contract
from src.spineforge_relay_v1_spatial import SpatialTopologyV1, SpatialOperationV1, SpatialStateV1, compile_spatial_contract
from src.spineforge_relay_v1_q6 import _expected_advance, _sha
from src.spineforge_relay_v1_q6d import request_for as base_request

FIXTURE = Path("tests/fixtures/spineforge_relay_v1/q7d_spatial_chain.json")


def build_chain():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = json.loads(Path(fixture["source_accepted_scene"]).read_text(encoding="utf-8"))
    story = json.loads(Path(fixture["story_fixture"]).read_text(encoding="utf-8"))
    original = StoryStateV1.model_validate(source["state_after"])
    if source["artifact"]["status"] != "ACCEPTED" or canonical_sha256(original) != source["artifact"]["state_after_sha256"]:
        raise ValueError("Unbound accepted predecessor")
    if original.revision != 1 or original.next_spine_beat != "SC02" or original.story_intent_sha256 != canonical_sha256(story["story_intent"]):
        raise ValueError("Source state/intent drift")
    # Explicit metadata migration: no historical bytes or story facts are changed.
    state = original.model_copy(deep=True)
    initial = SpatialStateV1.model_validate(fixture["initial_spatial"])
    if initial.positions != {name: char.location for name, char in state.characters.items()} or any(c.active for c in initial.access_constraints):
        raise ValueError("Spatial migration invents positions or active posture")
    if "spatial" in state.world:
        raise ValueError("Cannot overwrite existing spatial metadata")
    state.world["spatial"] = initial.model_dump(mode="json")
    fixture["migration"] = {"source_state_sha256": canonical_sha256(original), "migrated_state_sha256": canonical_sha256(state),
                            "added_pointer": "/world/spatial", "value": initial.model_dump(mode="json"), "revision_unchanged": True}
    fixture["previous_accepted_scene"] = source
    topology = SpatialTopologyV1.model_validate(fixture["topology"])
    route = FrozenSpineRouteV1(global_spine_sha256=state.global_spine_sha256, beat_ids=story["route"])
    rows = []
    expected = state
    for raw, spatial in zip(fixture["scene_plans"], fixture["spatial_plans"], strict=True):
        plan = ScenePlanV1.model_validate(raw)
        if spatial["scene_id"] != plan.scene_id:
            raise ValueError("Spatial plan attribution drift")
        contract = compile_scene_contract(expected, plan, route)
        compile_spatial_contract(scene=contract, state=expected, topology=topology,
            operations=[SpatialOperationV1.model_validate(o) for o in spatial["operations"]],
            expected_exit=SpatialStateV1.model_validate(spatial["expected_exit"]))
        rows.append((plan, contract, expected))
        expected = _expected_advance(expected, contract)
    return fixture, story["story_intent"], route, state, rows, expected


def request_for(stage, payload):
    kwargs, _ = base_request(stage, payload)
    suffix = Path(f"prompts/spineforge_relay_v1_spatial_{stage}.md").read_text(encoding="utf-8").strip()
    kwargs["system_prompt"] += "\n\n" + suffix
    request = normalize_openrouter_request(kwargs["model"], {"model": kwargs["model"],
        "messages": [{"role": "system", "content": kwargs["system_prompt"]}, {"role": "user", "content": kwargs["user_prompt"]}],
        "temperature": kwargs["temperature"], "max_tokens": kwargs["max_tokens"]},
        request_class=kwargs["request_class"], structured_output=False)
    request["response_format"] = kwargs["response_format"]
    request["provider"] = {**request.get("provider", {}), "require_parameters": True}
    return kwargs, request


def prepare():
    fixture, intent, route, start, rows, expected = build_chain()
    paths = [FIXTURE, Path(fixture["source_accepted_scene"]), Path(fixture["story_fixture"])]
    paths += [Path(p) for p in ("src/spineforge_relay_v1_q7d.py", "src/spineforge_relay_v1_q7d_inputs.py",
        "src/spineforge_relay_v1_spatial.py", "src/spineforge_relay_v1_q6d.py", "src/spineforge_relay_v1_q6.py",
        "src/spineforge_relay_v1_q6b.py", "src/spineforge_relay_v1_q5t.py", "src/spineforge_relay_v1_contracts.py",
        "src/spineforge_relay_v1_compile.py", "src/spineforge_relay_v1_events.py", "src/spineforge_relay_v1_guard.py",
        "src/spineforge_relay_v1_state.py", "src/spineforge_v19_transport.py", "src/model_registry.py",
        "configs/model_runtime_profiles.yaml", "prompts/spineforge_relay_v1_q6d_writer.md", "prompts/spineforge_relay_v1_q6d_guard.md",
        "prompts/spineforge_relay_v1_spatial_writer.md", "prompts/spineforge_relay_v1_spatial_guard.md",
        "tests/fixtures/spineforge_relay_v1/q6b_identity_probe.json", "tests/fixtures/spineforge_relay_v1/q6c_prop_probe.json",
        "docs/experiments/lighthouse-context-and-spine-draft.md")]
    return {"qualification_id": fixture["qualification_id"], "files": [{"path": p.as_posix(), "sha256": _sha(p)} for p in paths],
        "migration": fixture["migration"], "start_state_sha256": canonical_sha256(start),
        "contract_sha256": [canonical_sha256(c) for _, c, _ in rows], "route_sha256": canonical_sha256(route),
        "story_intent_sha256": canonical_sha256(intent), "expected_final_state_sha256": canonical_sha256(expected),
        "max_calls": len(rows)*4, "max_rewrites_per_scene": 1, "automatic_retry": False, "max_total_cost_usd": 0.60,
        "production_write": False}


def authorization_for(preflight):
    return {"preflight_sha256": canonical_sha256(preflight), "paid_execution_authorized": True,
        "destination": "OpenRouter", "scenes": ["SC02", "SC03", "SC04", "SC05", "SC06"], "max_calls": 20,
        "max_rewrites_per_scene": 1, "automatic_retry": False, "state_application_on_accept": True,
        "max_total_cost_usd": 0.60,
        "user_instruction": "User continued the proposed general spatial upgrade and fresh affected-scene qualification; explicit OpenRouter story-data consent persists."}
