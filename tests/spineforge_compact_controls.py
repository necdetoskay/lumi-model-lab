"""Test-only conversion of authored controls, never used by real inference."""
from src.spineforge_production_compact import CompactStoryPlanV1


def compact_control(design):
    f = design.fixture
    scenes = []
    initial = f["initial_state"]
    open_threads = set(initial["open_threads"])
    open_obligations = {o["id"] for o in initial["narrative_obligations"] if o["status"] == "OPEN"}
    def ref(value):
        return {k:value[k] for k in ["event_id", "predicate_id"]}
    for s, cov, spatial in zip(f["scene_plans"], f["coverage_plans"], f["spatial_plans"]):
        row = {k:s[k] for k in ["scene_id", "narrative_purpose", "objective", "turn"]}
        row.update({k:s[k] for k in ["location", "entry_requirements", "exit_requirements", "immutable_facts", "forbidden", "emotional_transition", "target_words_min", "target_words_max"] if k in s})
        row["events"] = []
        for e in s["required_events"]:
            event = {k:e[k] for k in ["id", "predicates", "required_observer", "evidence_mode", "separate_physical_clue_required", "forbidden_evidence_subjects"] if k in e}
            event["resulting_state"] = {p:v for p,v in e.get("resulting_state",{}).items() if p not in {"/world/spatial", "/open_threads", "/resolved_threads", "/narrative_obligations"} and not p.endswith("/location")}
            row["events"].append(event)
        row["goal_bindings"] = {o["source_field"]:[ref(r) for r in o["required_predicates"]] for o in cov["obligations"]}
        row["ordered_dependencies"] = [dict(before=ref(o["before"]), after=ref(o["after"])) for o in cov["ordered_dependencies"]]
        row["spatial_operations"] = spatial["operations"]
        row["preconditions"] = s.get("entry_state",{})
        row["resolutions"] = []
        end = s["required_exit_state"]
        anchor = dict(event_id=s["required_events"][-1]["id"], predicate_id=s["required_events"][-1]["predicates"][0]["id"])
        for thread in end.get("/resolved_threads",[]):
            if thread in open_threads:
                row["resolutions"].append(dict(kind="THREAD", id=thread, evidence=anchor));open_threads.remove(thread)
        for o in end.get("/narrative_obligations",[]):
            if o["status"] == "SATISFIED" and o["id"] in open_obligations:
                row["resolutions"].append(dict(kind="OBLIGATION", id=o["id"], evidence=anchor));open_obligations.remove(o["id"])
        scenes.append(row)
    return CompactStoryPlanV1(request_sha256=design.request_sha256, seed_sha256=design.seed_sha256,
        premise=f["story_intent"]["premise"], character_arc=f["story_intent"].get("character_arc", f["story_intent"]["premise"]),
        resolution="Explicit authored control resolution; synthetic, not a quality verdict.",
        scenes=scenes, carry_groups=f["carry_groups"], request_bindings=design.request_bindings)


def upgrade_plan_control(plan):
    """Offline test migration only. Real inference never falls back to v1 output."""
    from src.spineforge_production_compact_v2 import CompactStoryPlanV2
    raw = plan.model_dump(mode="json")
    raw["schema_name"] = "spineforge.compact-story-plan.v2"
    for scene in raw["scenes"]:
        scene["goal_bindings"] = {field:list(dict.fromkeys(r["event_id"] for r in refs)) for field,refs in scene["goal_bindings"].items()}
        for op in scene["spatial_operations"]: op.pop("predicate_id")
    return CompactStoryPlanV2.model_validate(raw)


def compact_control_v2(design):
    return upgrade_plan_control(compact_control(design))


def upgrade_v2_control(plan):
    from src.spineforge_production_compact_v3 import CompactStoryPlanV3
    raw=plan.model_dump(mode="json");raw["schema_name"]="spineforge.compact-story-plan.v3"
    for scene in raw["scenes"]:
        for event in scene["events"]:
            clue=event.pop("separate_physical_clue_required")
            if clue:
                p=next((p for p in event["predicates"] if p["action"]=="SHOW_PHYSICAL_CLUE"),event["predicates"][0])
                event["physical_clue"]={"subject":p["subject"],"target":p["target"]}
    return CompactStoryPlanV3.model_validate(raw)


def compact_control_v3(design):
    return upgrade_v2_control(compact_control_v2(design))
