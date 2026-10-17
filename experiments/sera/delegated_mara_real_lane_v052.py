"""SERA v0.52 dynamic delegated Mara full-scene qualified lane (shadow only).

No paid request on import or preflight. Valid signed SERA-only delegated approval,
a trusted deployment-pinned verifier key, an approved API credential and a
SINGLE shared durable journal are all mandatory. This module is not a CLI.
No human story repair, manual stage approval, output-token caps or G2 writes.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker, digest
from experiments.sera.authorized_mara_real_lane_v052 import preflight
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.delegated_scene_budget_v052 import DelegatedSceneBudget
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_s1_typed_live_v05 import entry_state, REGISTRY
from experiments.sera.openrouter_real_transport_v052 import make_openrouter_transport
from experiments.sera.openrouter_scene_writer_v021 import create_writer, make_request
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _hash
from experiments.sera.real_blind_benchmark_v040 import (
    prepare as frozen_mara_source, LEXICON, EXPECTED_SHA)
from experiments.sera.scene_trace_autorepair_v045 import _read, _write
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop

SCHEMA = "sera.v052-mara-delegated-noncanonical-shadow"
SCENE_KEY = "v052-frozen-mara-s1-28-sentences"


def run_delegated_mara(*, models, approval, trusted_public_key,
                       api_key, journal_path, output_root,
                       max_rewrites=2, opener=None):
    """Execute existing full v0.22/v0.23/0.21/0.20 scene pipeline.

    Explicit real paid approval is mandatory. Dynamic rewritten source SHA
    is accepted ONLY after a RECEIPTED source-bound writer generation.
    """
    contract = preflight(models=models, max_rewrites=max_rewrites)
    # No network, credentials or journal writes until signature and source
    # are validated by the DelegatedSceneBudget constructor.
    budget = DelegatedSceneBudget(
        db_path=journal_path,approval=approval,trusted_public_key=trusted_public_key,
        source_sha256=contract["source_sha256"],
        world_sha256=contract["world_sha256"],
        scene_key=contract["scene_key"],policy_sha256=contract["policy_sha256"],
        models=models)
    if budget.manifest["max_rewrites"] != max_rewrites:
        raise JournalBlocked("V052_DELEGATED_REWRITE_POLICY_DRIFT")
    if not isinstance(api_key,str) or not api_key.strip():
        raise JournalBlocked("V052_DELEGATED_PROVIDER_KEY_REQUIRED")
    transport = make_openrouter_transport(api_key=api_key,opener=opener)
    root = Path(output_root)
    saved = dict(contract,
                 signed_approval_sha256=_hash(approval),
                 signed_delegated_max_calls=budget.manifest["max_calls"],
                 signed_delegated_max_rewrites=max_rewrites,
                 signed_delegated_observed_spend_guard_usd=budget.manifest[
                     "observed_spend_guard_usd"],
                 transport="SIGNED_BOUND_DYNAMIC_JOURNAL_OPENROUTER",
                 canonical_commit_authorized=False)
    if root.joinpath("contract.json").exists():
        if _read(root/"contract.json") != saved:
            raise CoverageError("V052_DELEGATED_SCENE_CONTRACT_DRIFT")
    else:
        root.mkdir(parents=True,exist_ok=True)
        _write(root/"contract.json",saved)
    # Mutable only within this synchronous single-scene controller invocation.
    # Durable journal independently proves every source revision and request.
    active_source = [EXPECTED_SHA]
    role_for_model = {model:role for role,model in models.items()}

    def callback(*, key, model, prepared):
        try:
            role = role_for_model.get(model)
            if role is None:
                raise JournalBlocked("V052_DELEGATED_MODEL_UNAPPROVED")
            return budget.call(
                source_sha=active_source[0],role=role,model=model,
                request=prepared["request"],transport=transport)
        except Exception as exc:
            raise CoverageError("V052_DELEGATED_SOURCE_SAFE_STOP:"+
                                type(exc).__name__) from exc

    def reconcile(*, model, request, request_sha256):
        from hashlib import sha256
        from experiments.sera.world_state_v02 import canonical
        expected=sha256(canonical({"model":model,"request":request})
                        .encode("utf-8")).hexdigest()
        if request_sha256 != expected:
            raise CoverageError("V052_DELEGATED_RECOVERY_REQUEST_SHA_DRIFT")
        role=role_for_model.get(model)
        if role is None:
            raise CoverageError("V052_DELEGATED_RECOVERY_MODEL_UNAPPROVED")
        try:
            return budget.recover_completed(
                source_sha=active_source[0],role=role,
                model=model,request=request)
        except Exception as exc:
            raise CoverageError("V052_DELEGATED_GET_ONLY_RECOVERY_STOP:"+
                                type(exc).__name__) from exc

    world = entry_state()
    aliases = {k:v for k,v in REGISTRY.items() if k in world["entities"]}
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    original_preparer = create_preparer(
        evidence_root=root/"evidence",work_root=root/"evidence-work",
        scene_key=SCENE_KEY,registry=aliases,candidate_lexicon=lexicon,
        typed_registry={"openables":[],"documents":[]},
        api_key="DELEGATED_PROVIDER_CALLBACK_KEY_UNUSED",
        extraction_model=models["extraction"],
        semantic_model=models["semantic"],typed_model=models["typed"],
        provider_call=callback,max_model_requests=28,
        observed_spend_guard_usd="0.30",reconciler=reconcile)

    def preparer(*, prose, world):
        active_source[0] = prose_hash(prose)
        return original_preparer(prose=prose,world=world)

    writer_context = {
        "scene_key":SCENE_KEY,
        "entry_world_sha256":contract["world_sha256"],
        "fresh_source_sha_required_after_each_rewrite":True}
    original_writer=create_writer(
        api_key="DELEGATED_PROVIDER_CALLBACK_KEY_UNUSED",
        model=models["writer"],provider_call=callback,
        archive_dir=root/"writer-model-receipts",
        observed_spend_guard_usd="0.15",reconciler=reconcile,
        story_context=writer_context)

    def _write_proven_revision(*, source, defects, recovery=False):
        active_source[0] = prose_hash(source)
        answer=(original_writer.recover_existing(source=source,defects=defects)
                if recovery else original_writer(source=source,defects=defects))
        # Only model-generated full prose with immutable source evidence can
        # become the next source; this is NOT canonical WorldState authority.
        writer_request=make_request(
            source=source, defects=defects, story_context=writer_context)
        budget.accept_writer_revision(
            parent_sha=active_source[0],revised_prose=answer["prose"],
            writer_request=writer_request,
            generation_id=answer["receipt"]["response_id"])
        return answer

    def writer(*, source, defects):
        return _write_proven_revision(source=source,defects=defects)

    def recover_writer(*, source, defects):
        return _write_proven_revision(source=source,defects=defects,recovery=True)

    writer.recover_existing=recover_writer
    checker=create_checker(evidence_root=root/"evidence",full_qualification=True)
    original=frozen_mara_source()["prose"]
    if prose_hash(original)!=EXPECTED_SHA or len(sentences(original))!=28:
        raise CoverageError("V052_DELEGATED_FROZEN_MARA_SOURCE_INVALID")
    loop=scene_loop(
        prose=original,world=deepcopy(world),check_scene=checker,
        rewrite_scene=writer,output_dir=root/"controller",
        prepare_evidence=preparer,
        evidence_policy_id="v052-delegated-fresh-v022-v023-noncanonical",
        max_rewrites=max_rewrites,observed_spend_guard_usd="0.15",
        resume_reconciled_evidence=True,
        recover_rewrite_scene=writer.recover_existing)
    if (loop.get("canonical_commit_authorized") is not False or
        loop.get("world_db_writes")!=0 or
        loop.get("requires_manual_intervention") is not False):
        raise CoverageError("V052_DELEGATED_CONTROLLER_UNSAFE")
    ready = loop["status"]=="SCENE_CANDIDATE_READY_NONCANONICAL"
    result={
        "schema":SCHEMA,
        "status":"LAB_CANDIDATE_NONCANONICAL" if ready else "FAILED_SAFE_FINAL",
        "source_sha256":EXPECTED_SHA,
        "world_sha256":contract["world_sha256"],
        "source_sentence_count":28,
        "final_source_sha256":loop.get("final_prose_sha256"),
        "controller_status":loop["status"],
        "controller_reason_code":loop.get("reason_code"),
        "automatic_rewrites":loop.get("rewrite_count",0),
        "full_v023_scene_qualification_invoked":True,
        "semantic_quality_approved":False,
        "manual_story_or_json_edits":0,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "requires_manual_intervention":False,
        "paid_receipts_in_shared_journal":True}
    _write(root/"final.json",result)
    return result
