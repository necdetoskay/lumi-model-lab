"""SERA v0.52 — source-frozen, full-qualified model-transport orchestration.

This module connects ACTUAL SERA v0.22 independent extraction, v0.21 source-
bound model writer, v0.23 full-scene qualification and v0.20 unattended scene
loop. v0.52 deliberately makes NO paid provider request: only an explicitly
injected, scripted offline transport is supported here. The real paid adapter
is a separately authorized future execution boundary, never inferred from an
environment API key or another experiment's grant.

Every changed prose SHA gets NEW independent model evidence. No output-token
ceilings, manual repairs, canonical promotion or database writes.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker, digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_s1_typed_live_v05 import entry_state, REGISTRY
from experiments.sera.openrouter_scene_writer_v021 import create_writer
from experiments.sera.real_blind_benchmark_v040 import (
    prepare as frozen_mara_source, LEXICON, EXPECTED_SHA,
)
from experiments.sera.scene_trace_autorepair_v045 import _read, _write
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop
from experiments.sera.world_state_v02 import validate as validate_world

SCHEMA = "sera.v052-zero-human-qualified-model-lane-shadow"
TRANSPORT = "INJECTED_SCRIPTED_PROVIDER_ONLY_NO_NETWORK"
MODEL_KEYS = frozenset({"extraction", "semantic", "typed", "writer"})
FAKE_KEY = "SERA_V052_OFFLINE_SCRIPTED_NO_REAL_API_KEY"


def require(ok, why):
    if not ok:
        raise CoverageError(why)


def run_offline_lane(*, prose, world, output_root, scene_key,
                     registry, candidate_lexicon, typed_registry,
                     provider_call, models, max_rewrites=2):
    """Prove production-like stage wiring with offline provider callbacks.

    The source-only extractor and source-bound repair Writer are both real
    adapters with synthetic responses. Only the v0.23 full qualifier can
    mark a noncanonical scene structurally ready. An unknown model call
    outcome is terminal-safe without duplicate POSTs.
    """
    require(isinstance(prose, str) and bool(prose.strip()) and
            isinstance(scene_key, str) and bool(scene_key.strip()) and
            isinstance(world, dict), "V052_SOURCE_OR_SCENE_INVALID")
    validate_world(world)
    require(callable(provider_call) and
            isinstance(models, dict) and set(models) == MODEL_KEYS and
            all(isinstance(x, str) and x.startswith("synthetic/v052-")
                for x in models.values()) and
            len(set(models.values())) == len(models),
            "V052_OFFLINE_PROVIDER_MODEL_POLICY_INVALID")
    require(isinstance(registry, dict) and
            isinstance(candidate_lexicon, dict) and
            isinstance(typed_registry, dict) and
            set(typed_registry) == {"openables", "documents"} and
            type(max_rewrites) is int and 0 <= max_rewrites <= 2,
            "V052_SCENE_POLICY_INVALID")
    root = Path(output_root)
    contract = {
        "schema": SCHEMA,
        "source_sha256": prose_hash(prose),
        "world_sha256": digest(world),
        "registry_sha256": digest(registry),
        "candidate_lexicon_sha256": digest(candidate_lexicon),
        "typed_registry_sha256": digest(typed_registry),
        "scene_key": scene_key,
        "models": deepcopy(models),
        "transport": TRANSPORT,
        "max_rewrites": max_rewrites,
        "checker": "v0.21+full_scene_qualification_v0.23",
        "writer": "openrouter_scene_writer_v0.21_adapter_OFFLINE",
        "user_model_output_token_ceiling": "OMITTED",
        "canonical_commit_authorized": False,
    }
    if root.joinpath("contract.json").is_file():
        require(_read(root/"contract.json") == contract,
                "V052_RESTART_SOURCE_WORLD_OR_MODEL_POLICY_DRIFT")
    else:
        root.mkdir(parents=True, exist_ok=True)
        _write(root/"contract.json", contract)
    final = root/"final.json"
    if final.exists():
        prior = _read(final)
        require(isinstance(prior,dict) and
                prior.get("schema") == SCHEMA and
                prior.get("source_sha256") == prose_hash(prose) and
                prior.get("world_sha256") == digest(world) and
                prior.get("canonical_commit_authorized") is False and
                prior.get("production_db_writes") == 0 and
                prior.get("new_paid_model_calls") == 0,
                "V052_SAVED_RESULT_UNSAFE")
        return prior

    prepare_evidence = create_preparer(
        evidence_root=root/"evidence",
        work_root=root/"evidence-work",
        scene_key=scene_key,
        registry=registry,
        candidate_lexicon=candidate_lexicon,
        typed_registry=typed_registry,
        api_key=FAKE_KEY,
        extraction_model=models["extraction"],
        semantic_model=models["semantic"],
        typed_model=models["typed"],
        provider_call=provider_call,
        max_model_requests=28,
        observed_spend_guard_usd="0.30",
    )
    writer = create_writer(
        api_key=FAKE_KEY,
        model=models["writer"],
        provider_call=provider_call,
        archive_dir=root/"writer-model-receipts",
        observed_spend_guard_usd="0.15",
        story_context={
            "scene_key": scene_key,
            "entry_world_sha256": digest(world),
            "all_prose_revisions_require_new_v022_v023_independent_evidence": True,
        },
    )
    checker = create_checker(
        evidence_root=root/"evidence", full_qualification=True,
    )
    loop = scene_loop(
        prose=prose, world=deepcopy(world),
        check_scene=checker,
        rewrite_scene=writer,
        output_dir=root/"controller",
        prepare_evidence=prepare_evidence,
        evidence_policy_id="v052-frozen-source-v022-v023-noncanonical-revision",
        max_rewrites=max_rewrites,
        observed_spend_guard_usd="0.15",
    )
    require(loop.get("canonical_commit_authorized") is False and
            loop.get("world_db_writes") == 0 and
            loop.get("requires_manual_intervention") is False and
            loop.get("original_prose_sha256") == prose_hash(prose),
            "V052_CONTROLLER_RESULT_UNSAFE")
    ready = loop["status"] == "SCENE_CANDIDATE_READY_NONCANONICAL"
    result = {
        "schema": SCHEMA,
        "status": ("FULL_SCENE_QUALIFIED_CANDIDATE_NONCANONICAL"
                   if ready else "FAILED_SAFE_FINAL"),
        "source_sha256": prose_hash(prose),
        "world_sha256": digest(world),
        "final_source_sha256": loop.get("final_prose_sha256"),
        "source_sentence_count": len(sentences(prose)),
        "controller_status": loop["status"],
        "controller_reason_code": loop.get("reason_code"),
        "automatic_rewrites": loop.get("rewrite_count", 0),
        "full_independent_qualification_gate_invoked": True,
        "full_28_sentence_genuine_model_semantics_approved": False,
        "provider_is_real": False,
        "new_paid_model_calls": 0,
        "observed_new_cost_usd": "0",
        "manual_story_or_json_edits": 0,
        "canonical_commit_authorized": False,
        "production_db_writes": 0,
        "requires_manual_intervention": False,
    }
    _write(final, result)
    return result


def frozen_mara_offline(*, output_root, provider_call, models,
                        max_rewrites=2):
    """Operate on EXACT original 28-sentence Mara, not small Ari control."""
    source = frozen_mara_source()
    prose = source["prose"]
    require(prose_hash(prose) == EXPECTED_SHA and
            len(sentences(prose)) == 28,
            "V052_FROZEN_MARA_28_SENTENCE_SOURCE_INVALID")
    world = entry_state()
    aliases = {k: v for k,v in REGISTRY.items() if k in world["entities"]}
    import json
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    result = run_offline_lane(
        prose=prose, world=world,
        output_root=output_root, scene_key="v052-frozen-mara-s1-28-sentences",
        registry=aliases, candidate_lexicon=lexicon,
        typed_registry={"openables": [], "documents": []},
        provider_call=provider_call,
        models=models, max_rewrites=max_rewrites,
    )
    require(result["source_sha256"] == EXPECTED_SHA and
            result["source_sentence_count"] == 28 and
            not result["provider_is_real"],
            "V052_FROZEN_MARA_PROVENANCE_MISMATCH")
    return result
