"""Four genre ROUTING simulations; real paid stories NOT claimed."""
from __future__ import annotations
import copy
import hashlib
import json
import pytest
from pathlib import Path

from experiments import v3_four_genre_autonomy_router as r

MATRIX=r.MATRIX


def ev(router,verdict="PASS",**changes):
    stage=router.stage
    evidence={
        "case_id":router.case_id,"stage":stage,"verdict":verdict,
        "model":r.ROLE_MODEL.get(stage),
        "provider_posts":1,"provider_retries":0,
        "generation_id":"gen-synthetic-"+str(len(router.history))+router.case_id,
        "one_use_grant_id":"SYNTHETIC-STAGE-GRANT-"+str(len(router.history))+router.case_id,
        "human_story_edits":0,
    }
    if stage=="SPINE_HUMAN_APPROVAL":
        evidence["human_spine_approval"]=True
        evidence["approval_artifact_sha256"]="a"*64
    if stage=="AION_WRITER":
        evidence["writer_story_sha256"]="b"*64
    if stage in r.MAX_REPAIR:
        evidence.update({
            "repair_source":"MODEL_PROVIDER_OUTPUT",
            "patch_application":"DETERMINISTIC_EXACT_BOUNDED",
            "repair_proposal_sha256":"c"*64,
            "original_source_sha256":"d"*64,
            "modified_story_sha256":"e"*64,
        })
    evidence.update(changes)
    return evidence


def advance(router,verdict="PASS",**kwargs):
    return router.consume(ev(router,verdict,**kwargs))


def to_english_audit(router):
    for stage in ("SPINE_ARCHITECT","SPINE_GATE","SPINE_HUMAN_APPROVAL","AION_WRITER"):
        assert router.stage==stage
        advance(router)
    assert router.stage=="EN_LUNA_AUDIT"


def to_translation(router,repair=False):
    to_english_audit(router)
    if repair:
        assert advance(router,"LOCAL_DEFECT")=="EN_SOL_REPAIR"
        assert advance(router,"MODEL_PATCHED")=="EN_LUNA_RECHECK"
        assert advance(router)=="TR_GEMINI_TRANSLATE"
    else:
        assert advance(router)=="TR_GEMINI_TRANSLATE"


def test_four_fixtures_are_distinct_data_without_frozen_runtime_edits():
    data=r.load_matrix()
    assert len(data["cases"])==4
    assert data["model_roles"]["writer"]=="aion-labs/aion-3.5-mini"
    assert {case["genre"] for case in data["cases"]}=={
        "DETECTIVE_MYSTERY","SCIENCE_FICTION",
        "POLITICAL_INTRIGUE","FANTASY_ADVENTURE"}
    assert {case["protagonist"] for case in data["cases"]}=={"Mara","Tavi","Sera","Elen"}
    assert data["policy"]["story_text_manual_edits"]==0
    assert data["policy"]["length_is_hard_failure"] is False
    assert data["policy"]["post_repair_independent_reaudit_required"] is True
    assert data["policy"]["human_spine_approval_required_before_writer"] is True


@pytest.mark.parametrize("case_index",range(4))
def test_each_new_case_has_real_validated_world_character_state_and_premise(case_index):
    import json
    from pathlib import Path
    from src.saga_blueprint_contract import NarrativeFixture
    from src.premise_architect_v2_contract import PremiseLabStateV1,PremiseCandidateV2
    case=r.load_matrix()["cases"][case_index]
    inp=case["input_files"]
    fixture=NarrativeFixture.model_validate(json.loads(Path(inp["fixture"]).read_text()))
    state=PremiseLabStateV1.model_validate(json.loads(Path(inp["initial_state"]).read_text()))
    p=json.loads(Path(inp["controlled_premise"]).read_text())
    premise=PremiseCandidateV2.model_validate(p["premise"])
    assert fixture.character.age==18
    assert fixture.character.name==case["protagonist"]
    assert premise.title==case["title"]
    assert len(state.world_access)>=3
    assert premise.constraints==case["rules"]
    assert p["human_creative_approval_required_before_writer"] is True
    from src.saga_spine_v2_contract import CharacterSagaSpineV2
    saga=CharacterSagaSpineV2.model_validate(json.loads(
        Path(inp["saga_spine"]).read_text()))
    assert case["protagonist"] in saga.origin.summary
    assert saga.main_saga.milestones[0].key in premise.target_refs
    assert case["saga_input_status"]=="CREATED_SCHEMA_VALID"
    assert case["real_spine_eligible"] is True


def test_offline_plan_does_not_claim_real_model_generation(tmp_path):
    a=r.write_plan(tmp_path/"one")
    assert a["case_count"]==4 and a["new_paid_provider_posts"]==0
    assert a["allowed_manual_prose_repairs"]==0
    assert all(x["next_stage"]=="SPINE_ARCHITECT" for x in a["cases"])
    assert all(x["actual_story_generated"] is False for x in a["cases"])
    assert all(x["actual_model_repair_performed"] is False for x in a["cases"])
    assert all(x["requires_stage_scoped_paid_grant"] for x in a["cases"])
    with pytest.raises(r.RouterStop,match="PLAN_OUTPUT_EXISTS"):
        r.write_plan(tmp_path/"one")


def test_detective_synthetic_english_sol_repairs_and_luna_reaudits():
    c=r.RepairRouter.for_case("age18.closed-platform.mystery.stress-01")
    to_translation(c,repair=True)
    assert c.model_repair_attempts["EN_SOL_REPAIR"]==1
    assert [x["stage"] for x in c.history][-3:]==[
        "EN_LUNA_AUDIT","EN_SOL_REPAIR","EN_LUNA_RECHECK"]
    assert advance(c)=="TR_LUNA_FIDELITY"
    assert advance(c)=="WORLD_LUNA_OUTCOME"
    assert advance(c)=="COMPLETE_UNPUBLISHED"
    assert c.snapshot()["human_story_edits"]==0
    assert c.snapshot()["published"] is False


def test_scifi_unresolved_semantic_recheck_stops_no_manual_second_repair():
    c=r.RepairRouter.for_case("age18.orbit-rescue.scifi.stress-02")
    to_english_audit(c)
    assert advance(c,"LOCAL_DEFECT")=="EN_SOL_REPAIR"
    assert advance(c,"MODEL_PATCHED")=="EN_LUNA_RECHECK"
    assert advance(c,"STRUCTURAL_DEFECT")=="STOPPED"
    assert c.model_repair_attempts["EN_SOL_REPAIR"]==1
    with pytest.raises(r.RouterStop,match="ROUTER_NOT_WAITING_FOR_STAGE"):
        advance(c,"MODEL_PATCHED")
    assert c.snapshot()["world_state_committed"] is False


def test_intrigue_translation_fidelity_sol_rejects_false_positive_without_patch():
    c=r.RepairRouter.for_case("age18.council-seal.intrigue.stress-03")
    to_translation(c)
    assert advance(c)=="TR_LUNA_FIDELITY"
    assert advance(c,"LOCAL_DEFECT")=="TR_SOL_ADJUDICATION"
    assert advance(c,"DISMISSED")=="WORLD_LUNA_OUTCOME"
    assert advance(c)=="COMPLETE_UNPUBLISHED"
    assert c.model_repair_attempts["TR_GEMINI_REPAIR"]==0
    assert c.snapshot()["human_story_edits"]==0


def test_fantasy_model_confirms_translation_defect_gemini_repairs_luna_rechecks():
    c=r.RepairRouter.for_case("age18.mirror-marsh.fantasy.stress-04")
    to_translation(c)
    assert advance(c)=="TR_LUNA_FIDELITY"
    assert advance(c,"LOCAL_DEFECT")=="TR_SOL_ADJUDICATION"
    assert advance(c,"CONFIRMED")=="TR_GEMINI_REPAIR"
    assert advance(c,"MODEL_PATCHED")=="TR_LUNA_RECHECK"
    assert advance(c)=="WORLD_LUNA_OUTCOME"
    assert advance(c)=="COMPLETE_UNPUBLISHED"
    assert c.model_repair_attempts["TR_GEMINI_REPAIR"]==1
    assert c.snapshot()["published"] is False


def test_gemini_deterministic_semantic_defect_uses_model_not_human():
    c=r.RepairRouter.for_case("age18.mirror-marsh.fantasy.stress-04")
    to_translation(c)
    assert advance(c,"LOCAL_DEFECT")=="TR_GEMINI_REPAIR"
    assert advance(c,"MODEL_PATCHED")=="TR_LUNA_RECHECK"
    assert advance(c)=="WORLD_LUNA_OUTCOME"


@pytest.mark.parametrize("mutate,error",[
    ({"human_story_edits":1},"SINGLE_AUTHORIZED_PROVIDER_EVIDENCE_REQUIRED"),
    ({"provider_posts":2},"SINGLE_AUTHORIZED_PROVIDER_EVIDENCE_REQUIRED"),
    ({"provider_retries":1},"SINGLE_AUTHORIZED_PROVIDER_EVIDENCE_REQUIRED"),
    ({"model":"openai/gpt-5.6-luna"},"FROZEN_MODEL_ROLE_SUBSTITUTION"),
    ({"one_use_grant_id":None},"SINGLE_AUTHORIZED_PROVIDER_EVIDENCE_REQUIRED"),
    ({"generation_id":"not-real"},"SINGLE_AUTHORIZED_PROVIDER_EVIDENCE_REQUIRED"),
])
def test_manual_story_edit_retry_model_swap_or_missing_grant_forbidden(mutate,error):
    c=r.RepairRouter.for_case("age18.closed-platform.mystery.stress-01")
    with pytest.raises(r.RouterStop,match=error):
        advance(c,**mutate)
    assert c.stage=="SPINE_ARCHITECT"
    assert c.history==[]


def test_spine_gate_and_human_approval_cannot_be_skipped_or_faked():
    c=r.RepairRouter.for_case("age18.council-seal.intrigue.stress-03")
    with pytest.raises(r.RouterStop,match="CROSS_CASE_OR_OUT_OF_ORDER"):
        c.consume({**ev(c),"stage":"AION_WRITER"})
    advance(c)
    advance(c)
    assert c.stage=="SPINE_HUMAN_APPROVAL"
    with pytest.raises(r.RouterStop,match="SPINE_HUMAN_APPROVAL_NOT_VERIFIED"):
        advance(c,human_spine_approval=False)
    assert c.stage=="SPINE_HUMAN_APPROVAL"
    assert advance(c)=="AION_WRITER"


def test_paid_stage_grant_and_generation_replay_are_rejected():
    c=r.RepairRouter.for_case("age18.orbit-rescue.scifi.stress-02")
    first=ev(c);advance(c)
    with pytest.raises(r.RouterStop,match="PROVIDER_GRANT_OR_GENERATION_REPLAY"):
        advance(c,one_use_grant_id=first["one_use_grant_id"])
    with pytest.raises(r.RouterStop,match="PROVIDER_GRANT_OR_GENERATION_REPLAY"):
        advance(c,generation_id=first["generation_id"])


def test_model_repair_must_be_model_authored_bounded_and_proven():
    c=r.RepairRouter.for_case("age18.closed-platform.mystery.stress-01")
    to_english_audit(c)
    advance(c,"LOCAL_DEFECT")
    for item in (
        {"repair_source":"HUMAN_EDITOR"},
        {"patch_application":"DIRECT_USER_TEXT_REPLACEMENT"},
        {"original_source_sha256":"e"*64},
        {"repair_proposal_sha256":None},
    ):
        with pytest.raises(r.RouterStop,match="MANUAL_OR_UNPROVEN_REPAIR_FORBIDDEN"):
            advance(c,"MODEL_PATCHED",**item)
    assert c.stage=="EN_SOL_REPAIR"


def test_no_repair_without_model_finding_and_one_pass_only():
    c=r.RepairRouter.for_case("age18.orbit-rescue.scifi.stress-02")
    to_english_audit(c)
    assert advance(c)=="TR_GEMINI_TRANSLATE"
    with pytest.raises(r.RouterStop,match="CROSS_CASE_OR_OUT_OF_ORDER"):
        c.consume({**ev(c),"stage":"EN_SOL_REPAIR","verdict":"MODEL_PATCHED"})
    assert c.model_repair_attempts["EN_SOL_REPAIR"]==0


def test_no_automatic_spine_rewrite_on_structural_error():
    c=r.RepairRouter.for_case("age18.council-seal.intrigue.stress-03")
    advance(c)
    assert advance(c,"STRUCTURAL_DEFECT")=="STOPPED"
    assert len(c.history)==2
    assert all(h["human_story_edits"]==0 for h in c.history)


def test_case_scoping_never_leaks_between_worlds():
    c=r.RepairRouter.for_case("age18.mirror-marsh.fantasy.stress-04")
    payload=ev(c)
    payload["case_id"]="age18.orbit-rescue.scifi.stress-02"
    with pytest.raises(r.RouterStop,match="CROSS_CASE_OR_OUT_OF_ORDER"):
        c.consume(payload)


def test_length_warning_never_is_a_route_reject_reason():
    c=r.RepairRouter.for_case("age18.closed-platform.mystery.stress-01")
    to_english_audit(c)
    assert advance(c,"PASS",word_count=2950,length_warning=True)=="TR_GEMINI_TRANSLATE"
    assert c.snapshot()["story_length_nonblocking"] is True
