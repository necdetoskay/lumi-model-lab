"""SERA v0.52 experimental bounded delegated real-model Mara scene lane.

Unlike the exact-request lane, the *signed* finite budget can authorize
new source SHA requests AFTER a receipted model-writer scene revision. No
human repair and no manual restart gates. The run is inert until invoked with
a separately signed SERA-specific delegated approval and trusted key.

All provider posts have a durable single-use journal; unknown in-flight,
unpriced, malformed or unproven revisions fail closed. Not production/G2.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker, digest
from experiments.sera.authorized_mara_real_lane_v052 import preflight, SCENE_KEY
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.delegated_paid_budget_v052 import (
    DelegatedBudget, verify_delegated_approval)
from experiments.sera.delegated_provider_bridge_v052 import create_delegated_provider
from experiments.sera.delegated_receipt_audit_v052 import audit_delegated_receipts
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_s1_typed_live_v05 import entry_state, REGISTRY
from experiments.sera.openrouter_real_transport_v052 import make_openrouter_transport
from experiments.sera.openrouter_scene_writer_v021 import create_writer, make_request
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, ProviderJournal, _hash
from experiments.sera.real_blind_benchmark_v040 import (
    prepare as frozen_mara_source, LEXICON, EXPECTED_SHA)
from experiments.sera.scene_qualified_model_lane_v052 import require
from experiments.sera.scene_trace_autorepair_v045 import _read, _write
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop

import json

SCHEMA="sera.v052-mara-delegated-model-shadow"


def run_delegated_mara(*, models, approval, trusted_public_key, api_key,
                       journal_path, output_root, max_rewrites=2, opener=None):
    """Entry is intentionally not registered as a CI-paid workflow/CLI."""
    contract=preflight(models=models,max_rewrites=max_rewrites)
    verify_delegated_approval(
        approval=approval,trusted_public_key=trusted_public_key,
        source_sha256=contract["source_sha256"],
        world_sha256=contract["world_sha256"],
        scene_key=SCENE_KEY,policy_sha256=contract["policy_sha256"],
        approved_models=models,max_rewrites=max_rewrites)
    if not isinstance(api_key,str) or not api_key.strip():
        raise JournalBlocked("V052_DELEGATED_PROVIDER_KEY_MISSING")
    journal=ProviderJournal(journal_path)
    budget=DelegatedBudget(
        journal,approval=approval,trusted_public_key=trusted_public_key,
        source_sha256=EXPECTED_SHA,world_sha256=contract["world_sha256"],
        scene_key=SCENE_KEY,policy_sha256=contract["policy_sha256"],
        approved_models=models,max_rewrites=max_rewrites)
    callback=create_delegated_provider(
        budget=budget,transport=make_openrouter_transport(
            api_key=api_key,opener=opener))
    root=Path(output_root)
    saved=dict(contract,schema=SCHEMA,
               approval_id=budget.approval_id,
               approval_manifest_sha256=budget.digest,
               paid_transport="SIGNED_BOUNDED_DELEGATED_OPENROUTER",
               canonical_commit_authorized=False,
               production_db_writes=0)
    manifest_file=root/"contract.json"
    if manifest_file.exists():
        require(_read(manifest_file)==saved,
                "V052_DELEGATED_LANE_CONTRACT_DRIFT")
    else:
        root.mkdir(parents=True,exist_ok=True)
        _write(manifest_file,saved)
    final=root/"final.json"
    if final.exists():
        previous=_read(final)
        require(previous.get("schema")==SCHEMA and
                previous.get("approval_id")==budget.approval_id and
                previous.get("canonical_commit_authorized") is False and
                previous.get("production_db_writes")==0,
                "V052_DELEGATED_PREVIOUS_FINAL_UNSAFE")
        if previous["status"]=="LAB_CANDIDATE_NONCANONICAL":
            return previous
        # Failed terminal records may only resume from already receipted
        # work through the v0.20/v0.22 GET-only recovery path.

    world=entry_state()
    registry={k:v for k,v in REGISTRY.items() if k in world["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    def safe_provider(*,key,model,prepared):
        try:
            return callback(key=key,model=model,prepared=prepared)
        except Exception as exc:
            raise CoverageError("V052_DELEGATED_PROVIDER_FAILED_SAFE:"
                                +type(exc).__name__) from exc
    def safe_reconciler(*,model,request,request_sha256):
        try:
            return callback.recover_completed(
                model=model,request=request,request_sha256=request_sha256)
        except Exception as exc:
            raise CoverageError("V052_DELEGATED_READ_ONLY_RECOVERY_FAILED_SAFE:"
                                +type(exc).__name__) from exc

    preparer=create_preparer(
        evidence_root=root/"evidence",work_root=root/"evidence-work",
        scene_key=SCENE_KEY,registry=registry,candidate_lexicon=lexicon,
        typed_registry={"openables":[],"documents":[]},
        api_key="DELEGATED_CALLBACK_KEY_UNUSED",
        extraction_model=models["extraction"],
        semantic_model=models["semantic"],typed_model=models["typed"],
        provider_call=safe_provider,reconciler=safe_reconciler,
        max_model_requests=28,observed_spend_guard_usd="0.30")

    def proven_preparer(*,prose,world):
        if digest(world)!=contract["world_sha256"]:
            raise CoverageError("V052_DELEGATED_WORLD_DRIFT")
        try:
            callback.use_source(prose)
        except JournalBlocked as exc:
            raise CoverageError("V052_DELEGATED_UNPROVEN_SOURCE") from exc
        return preparer(prose=prose,world=world)

    story_context={
        "scene_key":SCENE_KEY,
        "entry_world_sha256":contract["world_sha256"],
        "fresh_source_sha_required_after_each_rewrite":True}
    writer=create_writer(
        api_key="DELEGATED_CALLBACK_KEY_UNUSED",
        model=models["writer"],provider_call=safe_provider,
        archive_dir=root/"writer-model-receipts",
        observed_spend_guard_usd="0.15",reconciler=safe_reconciler,
        story_context=story_context)

    def proven_writer(*,source,defects,recovery=False):
        try:
            callback.use_source(source)
        except JournalBlocked as exc:
            raise CoverageError("V052_DELEGATED_UNKNOWN_WRITER_SOURCE") from exc
        answer=(writer.recover_existing(source=source,defects=defects)
                if recovery else writer(source=source,defects=defects))
        # Parse the exact v0.21 request used for the paid Writer. The new
        # SHA is registered ONLY when the archived raw writer response proves
        # the same full prose and the exact writer generation ID.
        request=make_request(source=source,defects=defects,
                             story_context=story_context)
        try:
            budget.register_model_revision(
                parent_prose=source,revised_prose=answer["prose"],
                writer_payload=request,
                writer_response_id=answer["receipt"]["response_id"])
        except JournalBlocked as exc:
            raise CoverageError("V052_DELEGATED_WRITER_REVISION_UNPROVEN") from exc
        return answer

    def rewrite(*,source,defects):
        return proven_writer(source=source,defects=defects)
    def recovery(*,source,defects):
        return proven_writer(source=source,defects=defects,recovery=True)

    checker=create_checker(evidence_root=root/"evidence",full_qualification=True)
    frozen_prose=frozen_mara_source()["prose"]
    if prose_hash(frozen_prose)!=EXPECTED_SHA:
        raise CoverageError("V052_DELEGATED_ORIGINAL_MARA_SHA_DRIFT")
    loop=scene_loop(
        prose=frozen_prose,world=deepcopy(world),
        check_scene=checker,rewrite_scene=rewrite,
        output_dir=root/"controller",prepare_evidence=proven_preparer,
        evidence_policy_id="v052-delegated-v022-v023-source-lineage",
        max_rewrites=max_rewrites,observed_spend_guard_usd="0.15",
        resume_reconciled_evidence=True,recover_rewrite_scene=recovery)
    require(loop.get("canonical_commit_authorized") is False and
            loop.get("world_db_writes")==0 and
            loop.get("requires_manual_intervention") is False,
            "V052_DELEGATED_CONTROLLER_UNSAFE")
    receipt_audit=audit_delegated_receipts(
        journal=journal,approval_id=budget.approval_id)
    _write(root/"provider_receipt_audit.json",receipt_audit)
    ready=(loop["status"]=="SCENE_CANDIDATE_READY_NONCANONICAL"
           and receipt_audit["all_provider_receipts_qualified"])
    with journal._connect() as db:
        posts=db.execute(
            "SELECT COUNT(*) FROM delegated_requests WHERE approval_id=?",
            (budget.approval_id,)).fetchone()[0]
    result={
        "schema":SCHEMA,"approval_id":budget.approval_id,
        "status":"LAB_CANDIDATE_NONCANONICAL" if ready else "FAILED_SAFE_FINAL",
        "source_sha256":EXPECTED_SHA,"world_sha256":contract["world_sha256"],
        "policy_sha256":contract["policy_sha256"],
        "source_sentence_count":28,
        "final_source_sha256":loop.get("final_prose_sha256"),
        "controller_status":loop["status"],
        "controller_reason_code":loop.get("reason_code"),
        "receipt_gate_failure":(None if qualified_receipts else
                                "V052_DELEGATED_UNQUALIFIED_PROVIDER_RECEIPTS"),
        "automatic_rewrites":loop.get("rewrite_count",0),
        "allocated_provider_requests":posts,
        "provider_receipts":receipts,
        "all_billable_requests_receipted_and_priced":qualified_receipts,
        "provider_receipt_audit_status":receipt_audit["status"],
        "provider_receipts_qualified":receipt_audit["all_provider_receipts_qualified"],
        "observed_provider_spend_usd":receipt_audit["total_observed_usd"],
        "provider_receipts_require_independent_audit":True,
        "full_scene_qualification_gate_invoked":True,
        "semantic_quality_final_release_approved":False,
        "manual_story_or_json_edits":0,"canonical_commit_authorized":False,
        "production_db_writes":0,"requires_manual_intervention":False,
    }
    _write(final,result)
    return result
