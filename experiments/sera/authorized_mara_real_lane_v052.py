"""SERA v0.52 isolated, signed-provider Mara S1 qualified scene lane.

This module contains a callable entrypoint, not a CLI or scheduled paid job.
No provider request is made on import or preflight. A trusted runtime must
supply the independently provisioned trusted Ed25519 public key, the signer-
issued per-request approval, and a provider credential. The signed approval
is NOT inferred from credentials. Every unknown response is fail-closed and
no canonical WorldState/G2/production writes are permitted.

The per-request signed grant plan cannot preauthorize as-yet-unknown revised
prose. Such a missing grant will stop safely, NOT automatically charge.
A later bounded delegated-grant design must solve that before 28-sentence
real autonomous rewrite can be considered complete.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker, digest
from experiments.sera.coverage import prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.journaled_provider_bridge_v052 import create_journaled_provider
from experiments.sera.mara_s1_typed_live_v05 import entry_state, REGISTRY
from experiments.sera.openrouter_real_transport_v052 import make_openrouter_transport
from experiments.sera.openrouter_scene_writer_v021 import create_writer
from experiments.sera.provider_grant_journal_v052 import JournalBlocked, ProviderJournal
from experiments.sera.real_blind_benchmark_v040 import (
    prepare as frozen_mara_source, LEXICON, EXPECTED_SHA)
from experiments.sera.scene_qualified_model_lane_v052 import (
    MODEL_KEYS, require)
from experiments.sera.scene_trace_autorepair_v045 import _read, _write
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.signed_paid_approval_v052 import verify_approval
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop

SCHEMA = "sera.v052-mara-signed-provider-noncanonical-lane"
SCENE_KEY = "v052-frozen-mara-s1-28-sentences"


def preflight(*, models, max_rewrites=2):
    """Pure, no-secret/no-network preview for signed paid authorization."""
    if not isinstance(models, dict) or set(models) != MODEL_KEYS or any(
        not isinstance(v, str) or not v or v.startswith("synthetic/")
        for v in models.values()) or len(set(models.values())) != 4:
        raise JournalBlocked("V052_APPROVED_MODELS_INVALID")
    if type(max_rewrites) is not int or not 0 <= max_rewrites <= 2:
        raise JournalBlocked("V052_REWRITE_POLICY_INVALID")
    source=frozen_mara_source()
    prose=source["prose"]
    require(prose_hash(prose) == EXPECTED_SHA and
            len(sentences(prose)) == 28,
            "V052_FROZEN_MARA_SOURCE_DRIFT")
    world=entry_state()
    aliases={k:v for k,v in REGISTRY.items() if k in world["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    typed={"openables":[],"documents":[]}
    policy_sha=digest({
        "schema":SCHEMA, "models":models,
        "registry":aliases,"lexicon":lexicon,"typed_registry":typed,
        "checker":"v0.21+full_scene_qualification_v0.23",
        "writer":"v0.21+source-bound-repair",
        "max_rewrites":max_rewrites,
        "canonical_writes":False,
    })
    return {
        "schema":SCHEMA,
        "source_sha256":EXPECTED_SHA,
        "world_sha256":digest(world),
        "policy_sha256":policy_sha,
        "scene_key":SCENE_KEY,
        "source_sentence_count":28,
        "models":dict(models),
        "max_rewrites":max_rewrites,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
    }


def run_signed_mara(*, models, approval, trusted_public_key, grants,
                    api_key, journal_path, output_root,
                    max_rewrites=2, opener=None):
    """Full v0.22 -> v0.23 -> v0.21 writer -> fresh v0.22/23 loop.

    Does NOT infer paid permission from this function being called.
    A valid separate SERA-specific signed approval and exact grants are
    mandatory. This function is never executed by ordinary offline CI.
    """
    contract=preflight(models=models,max_rewrites=max_rewrites)
    verify_approval(
        approval=approval,trusted_public_key=trusted_public_key,
        source_sha256=contract["source_sha256"],
        world_sha256=contract["world_sha256"],
        policy_sha256=contract["policy_sha256"],
        scene_key=SCENE_KEY,approved_models=models,grants=grants)
    if not isinstance(api_key, str) or not api_key.strip():
        raise JournalBlocked("V052_REAL_PROVIDER_KEY_MISSING")
    journal=ProviderJournal(journal_path)
    transport=make_openrouter_transport(api_key=api_key,opener=opener)
    callback=create_journaled_provider(
        journal=journal,
        source_sha256=EXPECTED_SHA,world_sha256=contract["world_sha256"],
        scene_key=SCENE_KEY,policy_sha256=contract["policy_sha256"],
        approved_models=models,grants=grants,transport=transport,
        approval=approval,trusted_public_key=trusted_public_key,
        auto_register_signed_grants=True)
    root=Path(output_root)
    # Keep the real lane completely isolated from v0.52 synthetic receipts.
    saved=dict(contract,approval_id=approval["manifest"]["approval_id"],
               paid_transport="SIGNED_JOURNALED_OPENROUTER",
               full_independent_qualification_required=True)
    existing=root/"contract.json"
    if existing.exists():
        require(_read(existing)==saved,"V052_REAL_LANE_CONTRACT_DRIFT")
    else:
        root.mkdir(parents=True,exist_ok=True)
        _write(existing,saved)
    final=root/"final.json"
    if final.exists():
        result=_read(final)
        require(result.get("schema")==SCHEMA and
                result.get("canonical_commit_authorized") is False and
                result.get("production_db_writes")==0,
                "V052_REAL_LANE_ARCHIVE_UNSAFE")
        return result

    prose=frozen_mara_source()["prose"]
    world=entry_state()
    registry={k:v for k,v in REGISTRY.items() if k in world["entities"]}
    lexicon=json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    prepare_evidence=create_preparer(
        evidence_root=root/"evidence",work_root=root/"evidence-work",
        scene_key=SCENE_KEY,registry=registry,candidate_lexicon=lexicon,
        typed_registry={"openables":[],"documents":[]},
        api_key="SIGNED_PROVIDER_CALLBACK_KEY_UNUSED",
        extraction_model=models["extraction"],
        semantic_model=models["semantic"],typed_model=models["typed"],
        provider_call=callback,max_model_requests=28,
        observed_spend_guard_usd="0.30")
    writer=create_writer(
        api_key="SIGNED_PROVIDER_CALLBACK_KEY_UNUSED",
        model=models["writer"],provider_call=callback,
        archive_dir=root/"writer-model-receipts",
        observed_spend_guard_usd="0.15",
        story_context={
            "scene_key":SCENE_KEY,
            "entry_world_sha256":contract["world_sha256"],
            "fresh_source_sha_required_after_each_rewrite":True})
    checker=create_checker(evidence_root=root/"evidence",full_qualification=True)
    loop=scene_loop(
        prose=prose,world=deepcopy(world),check_scene=checker,
        rewrite_scene=writer,output_dir=root/"controller",
        prepare_evidence=prepare_evidence,
        evidence_policy_id="v052-signed-real-full-v023-noncanonical",
        max_rewrites=max_rewrites,observed_spend_guard_usd="0.15")
    require(loop.get("canonical_commit_authorized") is False and
            loop.get("world_db_writes")==0 and
            loop.get("requires_manual_intervention") is False,
            "V052_REAL_CONTROLLER_UNSAFE")
    ready=loop["status"]=="SCENE_CANDIDATE_READY_NONCANONICAL"
    result={
        "schema":SCHEMA,
        "status":("LAB_CANDIDATE_NONCANONICAL" if ready else "FAILED_SAFE_FINAL"),
        "source_sha256":EXPECTED_SHA,
        "world_sha256":contract["world_sha256"],
        "policy_sha256":contract["policy_sha256"],
        "source_sentence_count":28,
        "final_source_sha256":loop.get("final_prose_sha256"),
        "controller_status":loop["status"],
        "controller_reason_code":loop.get("reason_code"),
        "automatic_rewrites":loop.get("rewrite_count",0),
        "full_scene_qualification_gate_invoked":True,
        "provider_receipts_require_separate_audit":True,
        "semantic_quality_final_release_approved":False,
        "manual_story_or_json_edits":0,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
        "requires_manual_intervention":False,
    }
    _write(final,result)
    return result
