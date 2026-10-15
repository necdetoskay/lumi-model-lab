"""Generic model-authored repair router for four V3 stress cases.

This module is an OFFLINE routing/qualification contract, not a text
generator or provider client. Its events are evidence descriptions, not
a claim that real models ran. A separate, single-use-paid-stage runner
must execute model calls and supply authenticated result artifacts.

No manual story repair or user-authored patch endpoint exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass,field
from pathlib import Path

from src.frozen_lane_verify import verify_frozen_lane
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2
from src.premise_architect_v2_contract import PremiseLabStateV1, PremiseCandidateV2

MATRIX=Path("data/specifications/story_lab/v3_four_genre_stress_matrix_20261015.json")
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v3_uncapped.json")
FROZEN_SHA="63e1e3ce82c244bc5bb02b0463a9a1a6715c941b"
STAGES=(
    "SPINE_ARCHITECT","SPINE_GATE","SPINE_HUMAN_APPROVAL",
    "AION_WRITER","EN_LUNA_AUDIT","EN_SOL_REPAIR","EN_LUNA_RECHECK",
    "TR_GEMINI_TRANSLATE","TR_LUNA_FIDELITY","TR_SOL_ADJUDICATION",
    "TR_GEMINI_REPAIR","TR_LUNA_RECHECK","WORLD_LUNA_OUTCOME",
)
ROLE_MODEL={
    "SPINE_ARCHITECT":"anthropic/claude-sonnet-5.5",
    "SPINE_GATE":"openai/gpt-5.6-luna",
    "AION_WRITER":"aion-labs/aion-3.5-mini",
    "EN_LUNA_AUDIT":"openai/gpt-5.6-luna",
    "EN_SOL_REPAIR":"openai/gpt-5.6-sol",
    "EN_LUNA_RECHECK":"openai/gpt-5.6-luna",
    "TR_GEMINI_TRANSLATE":"google/gemini-3.8-flash",
    "TR_LUNA_FIDELITY":"openai/gpt-5.6-luna",
    "TR_SOL_ADJUDICATION":"openai/gpt-5.6-sol",
    "TR_GEMINI_REPAIR":"google/gemini-3.8-flash",
    "TR_LUNA_RECHECK":"openai/gpt-5.6-luna",
    "WORLD_LUNA_OUTCOME":"openai/gpt-5.6-luna",
}
NEXT_QUALITY={
    "SPINE_ARCHITECT":"SPINE_GATE",
    "SPINE_GATE":"SPINE_HUMAN_APPROVAL",
    "SPINE_HUMAN_APPROVAL":"AION_WRITER",
    "AION_WRITER":"EN_LUNA_AUDIT",
    "EN_SOL_REPAIR":"EN_LUNA_RECHECK",
    "EN_LUNA_RECHECK":"TR_GEMINI_TRANSLATE",
    "TR_GEMINI_TRANSLATE":"TR_LUNA_FIDELITY",
    "TR_GEMINI_REPAIR":"TR_LUNA_RECHECK",
    "TR_LUNA_RECHECK":"WORLD_LUNA_OUTCOME",
    "WORLD_LUNA_OUTCOME":"COMPLETE_UNPUBLISHED",
}
AUDITS={
    "EN_LUNA_AUDIT":"EN_SOL_REPAIR",
    "TR_LUNA_FIDELITY":"TR_SOL_ADJUDICATION",
}
HUMAN_APPROVAL_STAGE="SPINE_HUMAN_APPROVAL"
MAX_REPAIR={
    "EN_SOL_REPAIR":1,
    "TR_GEMINI_REPAIR":1,
}
ALLOWED_VERDICTS={"PASS","LOCAL_DEFECT","STRUCTURAL_DEFECT","CONFIRMED",
                  "DISMISSED","REJECT","MODEL_PATCHED"}


class RouterStop(RuntimeError):
    pass


def _check(condition:bool,reason:str):
    if not condition:
        raise RouterStop(reason)


def load_matrix()->dict:
    data=json.loads(MATRIX.read_text(encoding="utf-8"))
    _check(data.get("schema")=="lumi.v3.four-genre-stress-matrix.v1",
           "CASE_MATRIX_SCHEMA_INVALID")
    frozen=verify_frozen_lane(PROFILE)
    _check(frozen.get("verified_files")==43,"FROZEN_V3_FAILED")
    _check(data.get("frozen_sha")==FROZEN_SHA,"FROZEN_SOURCE_PIN_MISMATCH")
    p=json.loads(PROFILE.read_text(encoding="utf-8"))
    expected={
        "spine_architect":p["runtime"]["spine"]["architect_model"],
        "spine_gate":p["runtime"]["spine"]["gate_model"],
        "writer":p["runtime"]["writer"]["model"],
        "english_quality":p["runtime"]["authority"]["semantic_gate_model"],
        "english_repair":p["runtime"]["repair"]["model"],
        "translation":p["runtime"]["translation"]["model"],
        "translation_fidelity":p["runtime"]["fidelity"]["model"],
        "fidelity_adjudication":p["runtime"]["fidelity"]["adjudicator_model"],
        "translation_repair":p["runtime"]["translation"]["model"],
        "world_outcome":"openai/gpt-5.6-luna",
    }
    _check(data["model_roles"]==expected,"FROZEN_MODEL_ROLES_DRIFT")
    policy=data["policy"]
    for key in ("story_text_manual_edits","max_english_model_repair_attempts"):
        _check(policy.get(key)==(0 if key=="story_text_manual_edits" else 1),
               "MANUAL_EDIT_OR_REPAIR_POLICY_INVALID")
    _check(policy.get("max_translation_model_repair_attempts")==1
           and policy.get("model_repair_application")=="DETERMINISTIC_EXACT_SOURCE_BOUNDED"
           and policy.get("repair_authorship")=="MODEL_ONLY"
           and policy.get("length_is_hard_failure") is False
           and policy.get("human_spine_approval_required_before_writer") is True
           and policy.get("paid_stage_requires_separate_grant") is True
           and policy.get("no_world_state_commit") is True
           and policy.get("no_publication") is True
           and policy.get("same_case_prompt_hotfix") is False,
           "IMMUTABLE_V3_STRESS_POLICY_CONFLICT")
    cases=data.get("cases")
    _check(isinstance(cases,list) and len(cases)==4,
           "STRESS_REQUIRES_EXACTLY_FOUR_CASES")
    ids=set()
    genres=set()
    for row in cases:
        _check(isinstance(row,dict) and
               row.get("protagonist_age")==18
               and row.get("case_id","").startswith("age18.")
               and all(isinstance(row.get(k),str) and len(row[k].strip())>12
                       for k in ("logline","inciting_incident","core_question",
                                 "stakes","adversarial_seed","repair_expectation"))
               and len(row.get("rules",[]))==4
               and len(row.get("required_continuity",[]))==3
               and row.get("choice_a")!=row.get("choice_b"),
               "STRESS_CASE_UNDERDEFINED")
        source_files=row.get("input_files") or {}
        _check(set(source_files)=={"fixture","initial_state","controlled_premise","saga_spine"}
               and row.get("saga_input_status") in {
                   "CREATED_PENDING_SCHEMA_VERIFICATION","CREATED_SCHEMA_VALID"
               }
               and row.get("real_spine_eligible") is (
                   row.get("saga_input_status")=="CREATED_SCHEMA_VALID"
               ),
               "CASE_INPUTS_UNDERDEFINED_OR_SPINE_ELIGIBILITY_FAKED")
        for source in source_files.values():
            _check(isinstance(source,str) and
                   source.startswith("data/specifications/story_lab/four_genre_v3_inputs/")
                   and ".." not in source and Path(source).is_file(),
                   "CASE_INPUT_PATH_INVALID")
        saga=CharacterSagaSpineV2.model_validate(json.loads(
            Path(source_files["saga_spine"]).read_text(encoding="utf-8")))
        fixture=NarrativeFixture.model_validate(json.loads(
            Path(source_files["fixture"]).read_text(encoding="utf-8")))
        state=PremiseLabStateV1.model_validate(json.loads(
            Path(source_files["initial_state"]).read_text(encoding="utf-8")))
        wrapper=json.loads(Path(source_files["controlled_premise"]).read_text(encoding="utf-8"))
        premise=PremiseCandidateV2.model_validate(wrapper["premise"])
        _check(fixture.character.name==row["protagonist"]
               and row["protagonist"] in saga.origin.summary
               and saga.main_saga.milestones[0].key in premise.target_refs
               and all(truth.mode=="UNRESOLVED_BY_DESIGN"
                       for truth in saga.main_saga.hidden_truths)
               and fixture.character.age==18
               and premise.title==row["title"]
               and premise.logline==row["logline"]
               and premise.constraints==row["rules"]
               and set(premise.location_refs).issubset(
                   {e.key for e in state.world_access})
               and wrapper.get("human_creative_approval_required_before_writer") is True,
               "CASE_AUTHORITY_INPUT_MISMATCH")
        ids.add(row["case_id"]);genres.add(row["genre"])
    _check(len(ids)==4 and genres=={
        "DETECTIVE_MYSTERY","SCIENCE_FICTION","POLITICAL_INTRIGUE","FANTASY_ADVENTURE"
    },"CASE_IDENTITIES_OR_GENRES_NOT_DIVERSE")
    return data


def sha_bytes(content:bytes)->str:
    return hashlib.sha256(content).hexdigest()


@dataclass
class RepairRouter:
    """Strict evidence-driven transition router, no prose mutation methods."""
    case_id:str
    stage:str="SPINE_ARCHITECT"
    history:list[dict]=field(default_factory=list)
    model_repair_attempts:dict=field(default_factory=lambda:{
        "EN_SOL_REPAIR":0,"TR_GEMINI_REPAIR":0,
    })
    original_writer_sha:str|None=None
    accepted_english_sha:str|None=None
    accepted_turkish_sha:str|None=None
    last_repair_proposal_sha:str|None=None
    terminal_reason:str|None=None
    used_grants:set[str]=field(default_factory=set)
    used_model_generations:set[str]=field(default_factory=set)

    @classmethod
    def for_case(cls,case_id:str):
        _check(case_id in {r["case_id"] for r in load_matrix()["cases"]},
               "UNKNOWN_STRESS_CASE")
        return cls(case_id=case_id)

    def stop(self,reason:str)->None:
        self.stage="STOPPED"
        self.terminal_reason=reason

    def consume(self,evidence:dict)->str:
        _check(self.stage in STAGES and self.stage!="STOPPED",
               "ROUTER_NOT_WAITING_FOR_STAGE")
        _check(isinstance(evidence,dict)
               and evidence.get("case_id")==self.case_id
               and evidence.get("stage")==self.stage,
               "CROSS_CASE_OR_OUT_OF_ORDER_STAGE_EVIDENCE")
        stage=self.stage
        verdict=evidence.get("verdict")
        _check(isinstance(verdict,str) and verdict in ALLOWED_VERDICTS,
               "VERDICT_INVALID")
        if stage==HUMAN_APPROVAL_STAGE:
            # A real human approval is required by FROZEN V3. This is
            # eligibility ONLY, never permission to change story prose.
            _check(verdict=="PASS"
                   and evidence.get("human_spine_approval") is True
                   and isinstance(evidence.get("approval_artifact_sha256"),str)
                   and len(evidence["approval_artifact_sha256"])==64
                   and evidence.get("human_story_edits")==0,
                   "SPINE_HUMAN_APPROVAL_NOT_VERIFIED")
        else:
            _check(evidence.get("model")==ROLE_MODEL[stage],
                   "FROZEN_MODEL_ROLE_SUBSTITUTION")
            _check(evidence.get("one_use_grant_id") not in self.used_grants
                   and evidence.get("generation_id") not in self.used_model_generations,
                   "PROVIDER_GRANT_OR_GENERATION_REPLAY")
            _check(evidence.get("provider_posts")==1
                   and evidence.get("provider_retries")==0
                   and isinstance(evidence.get("generation_id"),str)
                   and evidence["generation_id"].startswith("gen-")
                   and isinstance(evidence.get("one_use_grant_id"),str)
                   and bool(evidence["one_use_grant_id"])
                   and evidence.get("human_story_edits")==0,
                   "SINGLE_AUTHORIZED_PROVIDER_EVIDENCE_REQUIRED")
        # Exactly one stage evidence per transition; never silently run
        # missing audit, repair or re-audit.
        _check(len(self.history)<20,"STRESS_UNBOUNDED_ROUTING_DETECTED")
        if verdict=="REJECT":
            self.stop("MODEL_GATE_REJECTED")
        elif verdict=="STRUCTURAL_DEFECT":
            self.stop("STRUCTURAL_DEFECT_REQUIRES_NEW_PLAN_NOT_MANUAL_REWRITE")
        elif stage in AUDITS:
            if verdict=="LOCAL_DEFECT":
                self.stage=AUDITS[stage]
            elif verdict=="PASS":
                self.stage=("TR_GEMINI_TRANSLATE" if stage=="EN_LUNA_AUDIT"
                            else "WORLD_LUNA_OUTCOME")
            else:
                self.stop("AUDIT_VERDICT_NOT_ROUTABLE")
        elif stage=="TR_GEMINI_TRANSLATE":
            if verdict=="PASS":
                self.stage="TR_LUNA_FIDELITY"
            elif verdict=="LOCAL_DEFECT":
                self.stage="TR_GEMINI_REPAIR"
            else:
                self.stop("TRANSLATION_DETERMINISTIC_SEMANTIC_DEFECT_BLOCKED")
        elif stage=="TR_SOL_ADJUDICATION":
            if verdict=="DISMISSED":
                self.stage="WORLD_LUNA_OUTCOME"
            elif verdict=="CONFIRMED":
                self.stage="TR_GEMINI_REPAIR"
            else:
                self.stop("ADJUDICATION_VERDICT_NOT_ROUTABLE")
        elif stage in MAX_REPAIR:
            _check(self.model_repair_attempts[stage]<MAX_REPAIR[stage],
                   "PAID_REPAIR_RETRY_FORBIDDEN")
            _check(verdict=="MODEL_PATCHED"
                   and evidence.get("repair_source")=="MODEL_PROVIDER_OUTPUT"
                   and evidence.get("patch_application")=="DETERMINISTIC_EXACT_BOUNDED"
                   and evidence.get("repair_proposal_sha256") is not None
                   and evidence.get("original_source_sha256") is not None
                   and evidence.get("modified_story_sha256") is not None
                   and evidence["original_source_sha256"]!=evidence["modified_story_sha256"],
                   "MANUAL_OR_UNPROVEN_REPAIR_FORBIDDEN")
            self.last_repair_proposal_sha=evidence["repair_proposal_sha256"]
            self.model_repair_attempts[stage]+=1
            self.stage=NEXT_QUALITY[stage]
        elif stage in ("EN_LUNA_RECHECK","TR_LUNA_RECHECK"):
            if verdict!="PASS":
                self.stop("POST_REPAIR_RECHECK_NOT_CLEAN")
            else:
                self.stage=NEXT_QUALITY[stage]
        elif stage=="AION_WRITER":
            _check(verdict=="PASS"
                   and isinstance(evidence.get("writer_story_sha256"),str)
                   and len(evidence["writer_story_sha256"])==64,
                   "WRITER_STORY_EVIDENCE_MISSING")
            self.original_writer_sha=evidence["writer_story_sha256"]
            self.stage=NEXT_QUALITY[stage]
        elif stage in NEXT_QUALITY:
            if verdict!="PASS":
                self.stop("REQUIRED_STAGE_FAILED")
            else:
                self.stage=NEXT_QUALITY[stage]
        else:
            self.stop("UNSUPPORTED_STAGE")
        # Only after ALL source, paid-call and repair assertions succeed
        # can an event consume a grant / mutate routing state.
        if stage!=HUMAN_APPROVAL_STAGE:
            self.used_grants.add(evidence["one_use_grant_id"])
            self.used_model_generations.add(evidence["generation_id"])
        self.history.append({
            "stage":stage,"verdict":verdict,
            "model":evidence.get("model"),
            "provider_posts":evidence.get("provider_posts",0),
            "human_story_edits":0,
        })
        # All downstream consent and publish boundaries remain closed.
        return self.stage

    def snapshot(self)->dict:
        return {
            "schema":"lumi.v3.four-genre-stress-router-snapshot.v1",
            "case_id":self.case_id,"next_required_stage":self.stage,
            "status":("OFFLINE_PLAN_NOT_EXECUTED" if not self.history else
                       "SIMULATED_STAGE_EVIDENCE_ONLY"),
            "terminal_reason":self.terminal_reason,
            "stage_evidence":list(self.history),
            "model_repairs":dict(self.model_repair_attempts),
            "human_story_edits":0,
            "story_length_nonblocking":True,
            "published":False,
            "world_state_committed":False,
            "paid_model_calls_from_planner":0,
        }


def plan()->dict:
    matrix=load_matrix()
    return {
        "schema":"lumi.v3.four-genre-stress-preflight.v1",
        "status":"FOUR_SAGA_INPUTS_SCHEMA_VALID_NO_PROVIDER_RUNS",
        "frozen_v3_sha":FROZEN_SHA,
        "cases":[{
            "case_id":c["case_id"],
            "genre":c["genre"],
            "title":c["title"],
            "next_stage":RepairRouter.for_case(c["case_id"]).stage,
            "validated_input_files":c["input_files"],
            "fixture_initial_state_premise_schema_valid":True,
            "saga_spine_input_created":True,
            "saga_spine_schema_valid":True,
            "real_spine_eligible":c["real_spine_eligible"],
            "actual_story_generated":False,
            "actual_spine_approved":False,
            "actual_model_repair_performed":False,
            "requires_stage_scoped_paid_grant":True,
        } for c in matrix["cases"]],
        "case_count":4,
        "allowed_manual_prose_repairs":0,
        "all_repair_model_only":True,
        "writer_model":ROLE_MODEL["AION_WRITER"],
        "human_spine_approval_is_separate_from_story_repair":True,
        "target_word_count_is_advisory":True,
        "new_paid_provider_posts":0,
        "published":False,
        "world_state_committed":False,
    }


def write_plan(out_dir:Path)->dict:
    if out_dir.exists():
        raise RouterStop("PLAN_OUTPUT_EXISTS")
    payload=plan()
    out_dir.mkdir(parents=True,mode=0o700)
    with (out_dir/"qualification-preflight.json").open("x",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)
        f.write("\n");f.flush();os.fsync(f.fileno())
    return payload


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir",required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(write_plan(args.out_dir),ensure_ascii=False,indent=2))
