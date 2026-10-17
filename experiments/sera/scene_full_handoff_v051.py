"""SERA v0.51 — safe, source-bound handoff from v0.50 into real v0.22/v0.21/v0.20.

NO manual story repair, NO new real LLM calls, NO canonical/production writes.
This deliberately does NOT treat 26 v0.50 scripted advisories as semantic truth:
the ENTIRE original scene must be re-extracted using independent prompts and
qualified by the original v0.22 worker, v0.21 checker, v0.20 rewrite loop.
If full extraction is incomplete, terminate FAILED_SAFE_FINAL. Never promote
partial synthetic repair candidates or 'next_action' flags to world events.

v0.51 has two complementary experiments:
- real 14-paid-receipt Mara provenance + v0.50 automatic row repair +
  actual v0.22/v0.20 full 28-sentence safe stop (offline provider doubles);
- separately a 2-sentence Ari control case proving v0.51 handoff can route
  through existing v0.22/v0.21/v0.20 automatic rewrite and replay. This is
  NOT evidence of a complete, real-model repaired Mara S1.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.automated_row_recovery_v050 import (
    execute as repair_rows, STATUS_SOURCE, STATUS_REVIEW,
)
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state
from experiments.sera.real_blind_benchmark_v040 import LEXICON, EXPECTED_SHA
from experiments.sera.real_mara_recovery_queue_v049 import (
    verified_real_receipts, build_work_orders,
)
from experiments.sera.scene_trace_autorepair_v045 import digest, _read, _write
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop

SCHEMA = "sera.v051-source-repair-to-full-scene-handoff"
MARA_MODEL = "synthetic/v051-mara-incomplete-full-source"
MARA_FALLBACK = "synthetic/v051-mara-incomplete-independent-fallback"
MARA_TYPED = "synthetic/v051-typed-not-reached"
MARA_SEMANTIC = "synthetic/v051-semantic-not-reached"


def require(flag,code):
    if not flag:
        raise CoverageError(code)


def _stage_contract(stage, prose, *, expected_tasks=None):
    """Source and noncanonical authority must match BEFORE full worker runs."""
    require(isinstance(stage,dict) and
            stage.get("schema")=="sera.v050-unattended-source-bound-repair-controller" and
            stage.get("source_sha256")==prose_hash(prose) and
            stage.get("world_commit_authorized") is False and
            stage.get("world_db_writes")==0 and
            stage.get("repair_model_was_real") is False and
            stage.get("full_scene_semantic_qualification_proven") is False and
            stage.get("requires_manual_intervention") is False and
            stage.get("status") in (
                "SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL",
                "REPLAN_REQUIRED_NONCANONICAL",
                "FAILED_SAFE_FINAL",
            ),
            "V051_ROW_STAGE_AUTHORITY_OR_SOURCE_INVALID")
    if expected_tasks is not None:
        completed=stage.get("tasks_accounted_for")
        rows=stage.get("task_results")
        require(type(completed) is int and
                isinstance(rows,list) and
                len(rows)==completed and
                (0<=completed<=expected_tasks if
                 stage["status"]=="FAILED_SAFE_FINAL" else
                 completed==expected_tasks),
                "V051_INCOMPLETE_ROW_REPAIR_ACCOUNTING")
    if stage["status"]=="SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL":
        require(all(r.get("status") in (STATUS_SOURCE,STATUS_REVIEW) and
                    r.get("semantic_truth_verified") is False and
                    r.get("canonical_commit_authorized") is False
                    for r in stage["task_results"]),
                "V051_ROW_REPAIR_SOURCE_OR_TRUTH_MISMATCH")
    return True


def handoff(*,stage,prose,world,output_root,scene_key,registry,
            candidate_lexicon,typed_registry,full_provider,writer,
            extraction_model,semantic_model,typed_model,fallback_model=None,
            max_rewrites=2,expected_tasks=None):
    """Runs genuine v0.22 evidence + v0.21 checker + v0.20 scene loop.

    The entire source must be re-extracted. The v0.50 candidate rows cannot
    masquerade as v0.10 full-scene coverage. No real provider is connected.
    A row-stage failed safe, ambiguous, or hard unbound row may not fake
    completion; a noncanonical 'REPLAN_REQUIRED' may only try the actual
    v0.20/v0.22 gates and cannot bypass source evidence on its way to rewrite.
    """
    _stage_contract(stage,prose,expected_tasks=expected_tasks)
    require(callable(full_provider) and callable(writer) and
            isinstance(prose,str) and prose.strip() and
            isinstance(scene_key,str) and scene_key and
            isinstance(world,dict) and
            type(max_rewrites) is int and 0<=max_rewrites<=2,
            "V051_SCENE_HANDOFF_CONFIGURATION_INVALID")
    root=Path(output_root)
    contract={
        "schema":SCHEMA,
        "source_sha256":prose_hash(prose),
        "world_sha256":digest(world),
        "repair_stage_sha256":digest(stage),
        "scene_key":scene_key,
        "registry_sha256":digest(registry),
        "lexicon_sha256":digest(candidate_lexicon),
        "typed_roles_sha256":digest(typed_registry),
        "models":[extraction_model,semantic_model,typed_model,fallback_model],
        "max_rewrites":max_rewrites,
        "transport":"SYNTHETIC_SCRIPTED_NO_OPENROUTER_API",
    }
    if (root/"contract.json").exists():
        require(_read(root/"contract.json")==contract,
                "V051_RESTART_SOURCE_WORLD_OR_REPAIR_STAGE_DRIFT")
    else:
        _write(root/"contract.json",contract)
    final=root/"final.json"
    if final.exists():
        previous=_read(final)
        require(previous.get("schema")==SCHEMA and
                previous.get("source_sha256")==prose_hash(prose) and
                previous.get("canonical_commit_authorized") is False and
                previous.get("production_world_db_writes")==0,
                "V051_FINAL_SNAPSHOT_NOT_SAFE")
        return previous
    if stage["status"]=="FAILED_SAFE_FINAL":
        result=_final(stage,None,prose,
                      "V051_UPSTREAM_REPAIR_FAILED_SAFE")
        _write(final,result)
        return result
    evidence=create_preparer(
        evidence_root=root/"evidence",
        work_root=root/"evidence-work",
        scene_key=scene_key,
        registry=registry,
        candidate_lexicon=candidate_lexicon,
        typed_registry=typed_registry,
        api_key="SYNTHETIC_NO_EXTERNAL_KEY_FOR_V051",
        extraction_model=extraction_model,
        semantic_model=semantic_model,
        typed_model=typed_model,
        fallback_model=fallback_model,
        provider_call=full_provider,
        max_model_requests=28,
        observed_spend_guard_usd="0.30",
    )
    checker=create_checker(evidence_root=root/"evidence")
    result=scene_loop(
        prose=prose,world=deepcopy(world),
        check_scene=checker,rewrite_scene=writer,
        output_dir=root/"controller",
        prepare_evidence=evidence,
        evidence_policy_id="v051-original-source-full-recheck-no-partial-promotion",
        max_rewrites=max_rewrites,
    )
    require(result.get("canonical_commit_authorized") is False and
            result.get("world_db_writes")==0 and
            result.get("original_prose_sha256")==prose_hash(prose) and
            result.get("requires_manual_intervention") is False,
            "V051_SCENE_CONTROLLER_WORLD_OR_SOURCE_UNSAFE")
    code=("V051_FULL_SCENE_STRUCTURAL_CANDIDATE_NONCANONICAL"
          if result["status"]=="SCENE_CANDIDATE_READY_NONCANONICAL"
          else "V051_FULL_SCENE_INDEPENDENT_EVIDENCE_FAILED_SAFE")
    out=_final(stage,result,prose,code)
    _write(final,out)
    return out


def _final(stage,scene,prose,reason):
    done=(scene is not None and
          scene["status"]=="SCENE_CANDIDATE_READY_NONCANONICAL")
    return {
        "schema":SCHEMA,
        "status":("FULL_SCENE_STRUCTURAL_CANDIDATE_NONCANONICAL"
                  if done else "FAILED_SAFE_FINAL"),
        "reason_code":reason,
        "source_sha256":prose_hash(prose),
        "row_stage_status":stage["status"],
        "row_stage_task_count":stage.get("tasks_accounted_for",0),
        "scene_status":scene["status"] if scene else "NOT_STARTED",
        "scene_reason_code":scene.get("reason_code") if scene else None,
        "scene_final_source_sha256":(
            scene.get("final_prose_sha256") if scene else None
        ),
        "automatic_rewrites":scene.get("rewrite_count",0) if scene else 0,
        "stage_reached_actual_v020_v021_v022":scene is not None,
        "independent_semantic_gold_verified":False,
        "new_real_provider_calls":0,
        "new_real_provider_cost_usd":"0",
        "canonical_commit_authorized":False,
        "production_world_db_writes":0,
        "sqlite_lab_world_db_writes":0,
        "requires_manual_intervention":False,
        "next_automatic_action":(
            "CONTINUE_FURTHER_INDEPENDENT_STORY_QUALIFICATION"
            if done else "TERMINAL_SAFE_FAILURE"
        ),
    }


def run_real_mara_shadow(*,receipt_root,output_root,
                          row_provider,full_provider,writer):
    """Bind actual 14 real receipts to v0.50 then full original 28-source gate.

    The injected providers MUST be deterministic OFFLINE test doubles.
    A 28-row Mara real-model semantic success is NOT a plausible result
    without new independent real provider calls + separate authorization.
    """
    source,receipts,coverage,old=verified_real_receipts(receipt_root)
    require(prose_hash(source["prose"])==EXPECTED_SHA and
            old["attempts_started"]==14,
            "V051_NOT_ORIGINAL_FROZEN_REAL_MARA")
    audit,tasks=build_work_orders(source=source,receipts=receipts,
                                   coverage=coverage)
    root=Path(output_root)
    repair=repair_rows(
        source=source,audit=audit,tasks=tasks,
        output_root=root/"v050-row-stage",
        scripted_provider=row_provider,
    )
    world=entry_state()
    aliases={name:value for name,value in REGISTRY.items()
             if name in world["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    full=handoff(
        stage=repair,prose=source["prose"],world=world,
        output_root=root/"v051-full",
        scene_key="v051-frozen-real-mara-shadow",
        registry=aliases,candidate_lexicon=lexicon,
        typed_registry={"openables":[],"documents":[]},
        full_provider=full_provider,writer=writer,
        extraction_model=MARA_MODEL,
        semantic_model=MARA_SEMANTIC,typed_model=MARA_TYPED,
        fallback_model=MARA_FALLBACK,
        expected_tasks=26,max_rewrites=2,
    )
    return {"row_stage":repair,"full_stage":full,
            "original_real_receipts_verified":14,
            "original_real_spend_usd":old["observed_spend_usd"],
            "new_real_provider_calls":0,
            "canonical_commit_authorized":False}
