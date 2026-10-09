import json
from pathlib import Path
import pytest
from src.spineforge_production_config import RunConfigV1
from src.spineforge_production_pipeline import prepare,execute,request_for,validate_review
from src.spineforge_production_range_story import runner_request_for
from src.spineforge_seeded_design import StorySeedV1,freeze_seed,SeededStoryDesignV2
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_spatial import SpatialTopologyV1
from src.spineforge_production_source_ranges import range_table as source_table
from tests.test_spineforge_relay_v1_joint_movement import fake as scene_fake
from tests.spineforge_compact_controls import compact_control_v3


def write(path,value):path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode())


def sample(tmp_path,kind="mosaic"):
    tmp_path.mkdir(parents=True,exist_ok=True)
    if kind=="mosaic":
        raw=json.loads(Path("tests/fixtures/story_design_v1/mosaic-adapter-proposal.json").read_text())
        f=raw["fixture"]
        request=StoryRequestV1.model_validate_json(Path("tests/fixtures/story_design_v1/mosaic-request.json").read_bytes())
        bindings=raw["request_bindings"]
    else:
        topo=SpatialTopologyV1(locations=["reading_room"],edges=[],position_state_paths={"Reader":"/characters/Reader/location"})
        spatial=dict(topology_sha256=canonical_sha256(topo),positions={"Reader":"reading_room"},access_constraints=[])
        initial=dict(revision=0,characters={"Reader":dict(location="reading_room",condition={},inventory={},knowledge=[],relationships={})},
            world={"spatial":spatial},objects={},open_threads=["question"],resolved_threads=[],completed_spine_beats=[],next_spine_beat="S01",
            narrative_obligations=[dict(id="answer",detail="Find and acknowledge an honest answer",status="OPEN",target_scene_id=None)])
        f=dict(schema="spineforge-relay.repeatability-fixture.v5",story_id="quiet-decision",story_intent=dict(language="en",reader_age=12,tone=["quiet"],premise="A reader notices a question and chooses an honest answer."),route=["S01","S02"],initial_state=initial,relevant_character_canon={"Reader":dict(age=12)},prop_authorization_policy=dict(authorized_actionable_props=[],rule="No physical props required"),topology=topo.model_dump(mode="json"),carry_groups=[],scene_plans=[],coverage_plans=[],spatial_plans=[])
        for i,action in enumerate(["NOTICE_QUESTION","CHOOSE_ANSWER"],1):
            sid=f"S{i:02}";eid=sid+"-E01"
            changes={"/characters/Reader/knowledge":["question"] if i==1 else ["question","answer"],"/world/spatial":spatial}
            if i==2:changes.update({"/open_threads":[],"/resolved_threads":["question"],"/narrative_obligations":[{**initial["narrative_obligations"][0],"status":"SATISFIED"}]})
            predicate=dict(id="P1",subject="Reader",action=action,target="question" if i==1 else "answer")
            event=dict(id=eid,actor="Reader",action=action,target=predicate["target"],required_observer=None,evidence_mode="DIRECT_OBSERVATION",predicates=[predicate],allowed_provenance=["DIRECT_OBSERVATION"],forbidden_provenance=["INVENTED_WORLD_RULE","INVENTED_CLUE","UNESTABLISHED_LORE"],resulting_state={"/characters/Reader/knowledge":changes["/characters/Reader/knowledge"]})
            plan=dict(scene_id=sid,spine_beats=[sid],narrative_purpose=action,objective=action,turn=action,location="reading_room",required_events=[event],entry_state={},required_exit_state=changes,allowed_state_paths=list(changes),next_spine_beat="S02" if i==1 else None,target_words_min=120,target_words_max=260)
            ref=dict(event_id=eid,predicate_id="P1",subject="Reader",action=action,target=predicate["target"])
            f["scene_plans"].append(plan)
            f["coverage_plans"].append(dict(scene_id=sid,ordered_dependencies=[],obligations=[dict(id=sid+"-"+field,source_field=field,source_text=action,required_predicates=[ref]) for field in ["narrative_purpose","objective","turn"]]))
            f["spatial_plans"].append(dict(scene_id=sid,operations=[],expected_exit=spatial))
        request=StoryRequestV1(original_prompt="A reader chooses an honest answer.",language="en",reader_age=12,genre="reflection",tone=["quiet"],scene_count=2,requirements=[dict(id="R1",source_text="chooses an honest answer",meaning="Choose honestly")])
        bindings=[dict(requirement_id="R1",scene_id="S02",event_id="S02-E01",predicate_id="P1",rationale="Honest answer decision")]
    seed=StorySeedV1(story_id=f["story_id"],scenario_id=kind,characters=f["initial_state"]["characters"],world=f["initial_state"]["world"],objects=f["initial_state"]["objects"],topology=f["topology"],relevant_character_canon=f["relevant_character_canon"],prop_authorization_policy=f["prop_authorization_policy"],open_threads=f["initial_state"]["open_threads"],narrative_obligations=f["initial_state"]["narrative_obligations"])
    design=SeededStoryDesignV2(request_sha256=canonical_sha256(request),seed_sha256=canonical_sha256(seed),fixture=f,request_bindings=bindings)
    paths={k:tmp_path/(k+".json") for k in ["request","seed","freeze","config"]}
    write(paths["request"],request.model_dump(mode="json"));write(paths["seed"],seed.model_dump(mode="json"))
    write(paths["config"],RunConfigV1().model_dump(mode="json"));freeze_seed(paths["seed"],paths["freeze"])
    return paths,design


def provider(config,design,calls,defect=None):
    scenes=scene_fake([])
    def fake(**kwargs):
        payload=json.loads(kwargs["user_prompt"]);stage=kwargs["request_class"].split("production_")[-1]
        calls.append(stage)
        if stage=="planner":
            raw=compact_control_v3(design).model_dump(mode="json",exclude_defaults=True)
            if defect=="structural" and calls.count("planner")==1:raw["request_bindings"]=[]
            if defect=="nonconvergent":raw["request_bindings"]=[]
            if defect=="unsafe_id":raw["scenes"][0]["scene_id"]="../outside"
            text=json.dumps(raw)
            expected=request_for(stage,payload,config)[1]
        elif stage=="plan_guard":
            raw=dict(review_id=payload["review_id"],decision="PASS",findings=[],summary="Synthetic control")
            if defect=="stale_review":raw["review_id"]="0"*64
            if defect=="semantic" and calls.count("plan_guard")==1:
                raw.update(decision="REWRITE",findings=[dict(field_id=payload["source_fields"][0]["id"],category="CAUSALITY",reason="Synthetic review blocker",repair_instruction="Reconsider plan")])
            text=json.dumps(raw);expected=request_for(stage,payload,config)[1]
        else:
            stage="guard" if "candidate_prose" in payload else "writer"
            delegated={**kwargs,"model":"openai/gpt-5.6-sol" if stage=="writer" else "anthropic/claude-sonnet-5.5"}
            text,body,_=scenes(**delegated)
            if stage=="guard":
                report=json.loads(text);table=payload["source_range_table"];report["source_sha256"]=table["source_sha256"]
                for row in report["event_evidence"]:
                    quote=row.pop("exact_text");index=next(i for i,s in enumerate(table["spans"]) if s["text"]==quote);row["source_range_id"]=next(r[0] for r in table["ranges"] if r[1:]==[index,index])
                text=json.dumps(report)
            expected=runner_request_for(stage,payload,config)[1]
        if defect=="transport":raise RuntimeError("Synthetic transport failure")
        body=dict(id="synthetic-"+str(len(calls)),model=kwargs["model"],choices=[dict(finish_reason="stop",message=dict(content=text))],usage=dict(prompt_tokens=1200,completion_tokens=450,total_tokens=1650,cost=.01))
        if defect=="usage":body["usage"]["total_tokens"]=2
        if defect=="truncated":body["choices"][0]["finish_reason"]="length"
        return text,body,expected
    return fake


def run(tmp_path,kind="mosaic",defect=None):
    paths,design=sample(tmp_path/"inputs",kind);config=RunConfigV1()
    pf=prepare(paths["request"],paths["seed"],paths["freeze"],paths["config"])
    calls=[]
    result=execute(request_path=paths["request"],seed_path=paths["seed"],freeze_path=paths["freeze"],config_path=paths["config"],preflight=pf,output=tmp_path/"run",api_key="synthetic",call_fn=provider(config,design,calls,defect))
    return result,calls

@pytest.mark.parametrize("kind,expected",[("mosaic",14),("dialogue",6)])
def test_same_pipeline_handles_joint_delivery_and_nonspatial_decision(tmp_path,kind,expected):
    result,calls=run(tmp_path,kind)
    assert result["status"]=="ACCEPT" and len(calls)==expected
    assert result["provider_calls"]==expected and result["usage_complete"] is True
    assert (tmp_path/"run/state-comparison.json").exists() and (tmp_path/"run/assembled-story.md").exists()
    assert result["editorial_status"]=="REQUIRES_SEPARATE_REVIEW"

@pytest.mark.parametrize("defect",["structural","semantic"])
def test_one_bounded_plan_rewrite_then_story(tmp_path,defect):
    result,calls=run(tmp_path,"dialogue",defect)
    assert result["status"]=="ACCEPT" and calls.count("planner")==2
    assert calls.count("plan_guard")== (1 if defect=="structural" else 2)

@pytest.mark.parametrize("defect",["nonconvergent","stale_review","transport","usage","truncated","unsafe_id"])
def test_failed_plan_never_dispatches_scene_writer(tmp_path,defect):
    result,calls=run(tmp_path,"dialogue",defect)
    assert result["status"]=="REJECT_NON_CONVERGENT"
    assert calls.count("planner")<=2 and not (tmp_path/"run/story").exists()
    if defect=="transport":assert len(calls)==1 and result["usage_complete"] is False


def test_run_config_changes_requests_and_rejects_unknown_profiles(tmp_path):
    paths,design=sample(tmp_path/"input")
    cfg=RunConfigV1(writer="anthropic/claude-sonnet-5.5",scene_guard="openai/gpt-5.6-sol")
    payload=dict(plan_coverage_contract={},source_range_table=source_table("A fact."))
    assert runner_request_for("writer",payload,cfg)[0]["model"]==cfg.writer
    assert runner_request_for("guard",payload,cfg)[1]["model"]==cfg.scene_guard
    write(paths["config"],RunConfigV1(planner="unknown/model").model_dump(mode="json"))
    with pytest.raises(RuntimeError,match="MODEL_RUNTIME_PROFILE_MISSING"):
        prepare(paths["request"],paths["seed"],paths["freeze"],paths["config"])


def test_one_shared_reservation_covers_planner_review_and_scene_calls(tmp_path):
    from tests.test_spineforge_relay_v1_reservations import MemoryAuthority
    from src.spineforge_relay_v1_reservations import PaidGrantV1,PaidLedgerV1,run_reserved,ReservationError
    paths,design=sample(tmp_path/"inputs","dialogue");cfg=RunConfigV1()
    pf=prepare(paths["request"],paths["seed"],paths["freeze"],paths["config"])
    grant=PaidGrantV1(id="synthetic",approval_evidence_sha256="a"*64,max_calls=pf["max_calls"],max_cost_usd="1.20",
        scopes=[dict(id="whole-chain",preflight_sha256=canonical_sha256(pf),max_calls=pf["max_calls"],max_cost_usd="1.20",max_call_cost_usd="0.30",allowed_models=cfg.models())])
    store=MemoryAuthority(PaidLedgerV1(grant=grant,status="OPEN"));calls=[]
    def invoke(call):return execute(request_path=paths["request"],seed_path=paths["seed"],freeze_path=paths["freeze"],config_path=paths["config"],preflight=pf,output=tmp_path/"run",api_key="synthetic",call_fn=call)
    result=run_reserved(store=store,grant_id="synthetic",scope_id="whole-chain",preflight=pf,executor_id="test",invoke=invoke,transport=provider(cfg,design,calls))
    assert result["status"]=="ACCEPT" and len(calls)==6
    row=store.ledger.reservations["whole-chain"]
    assert row["status"]=="SETTLED" and row["actual_calls"]==6 and float(row["actual_cost_usd"])==.06
    with pytest.raises(ReservationError,match="consumed"):
        run_reserved(store=store,grant_id="synthetic",scope_id="whole-chain",preflight=pf,executor_id="duplicate",invoke=invoke,transport=provider(cfg,design,calls))
    assert len(calls)==6


def test_plan_finding_must_reference_real_design_value(tmp_path):
    paths,design=sample(tmp_path/"inputs","dialogue")
    request=StoryRequestV1.model_validate_json(paths["request"].read_bytes())
    from src.spineforge_seeded_design import verify_frozen_seed
    seed=verify_frozen_seed(paths["seed"],paths["freeze"])
    raw=dict(request_sha256=canonical_sha256(request),seed_sha256=canonical_sha256(seed),design_sha256=canonical_sha256(design),decision="REWRITE",summary="block",
        findings=[dict(design_pointer="/fixture/story_id",source_value="invented",reason="block",repair_instruction="fix")])
    with pytest.raises(ValueError,match="Ungrounded"):validate_review(raw,request,seed,design)


def test_real_transport_refuses_unreserved_generic_planner(tmp_path):
    from src.spineforge_v19_transport import _request_once
    from src.spineforge_relay_v1_lease_context import UnreservedRelayTransportError
    from src.spineforge_seeded_design import seeded_planner_input,verify_frozen_seed
    paths,design=sample(tmp_path/"inputs","dialogue")
    request=StoryRequestV1.model_validate_json(paths["request"].read_bytes())
    seed=verify_frozen_seed(paths["seed"],paths["freeze"])
    kwargs,_=request_for("planner",seeded_planner_input(request,seed),RunConfigV1())
    with pytest.raises(UnreservedRelayTransportError):_request_once(api_key="synthetic",**kwargs)


@pytest.mark.parametrize("stage",["planner","plan_guard"])
def test_json_mode_always_includes_explicit_json_instruction(stage):
    kwargs,expected=request_for(stage,{"instructions":"Plan a story"},RunConfigV1())
    assert "valid JSON object" in kwargs["system_prompt"]
    assert expected["response_format"]=={"type":"json_object"}
    assert any("JSON" in m["content"] for m in expected["messages"])


def test_transport_failure_retains_http_diagnostics_without_credentials():
    from src.generate import OpenRouterCallError
    from src.spineforge_production_paid_entry import sanitized_failure
    secret="synthetic-private-credential"
    exc=OpenRouterCallError("never print",dict(stage="http_response",status_code=400,attempts=1,
        error_body={"error":{"message":"JSON required "+secret,"code":400},"headers":{"Authorization":"Bearer "+secret},"api_key":secret},
        request={"private":secret}))
    record=sanitized_failure(exc,secret)
    assert record["diagnostics"]["status_code"]==400
    assert record["diagnostics"]["error_body"]["error"]["code"]==400
    assert secret not in json.dumps(record) and "Authorization" not in json.dumps(record)
    assert "request" not in record["diagnostics"]
