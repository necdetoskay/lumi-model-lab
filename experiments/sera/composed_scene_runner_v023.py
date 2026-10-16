"""SERA v0.23 — composed unattended lab runner, real transport-capable.

Binds v0.21 provider writer, v0.22 paid per-draft independent evidence,
v0.21 actual source checker + v0.23 cross-family qualification and v0.20
durable rewriting. The callable has the same provider injection seam as
SERA's real OpenRouter transport; no app output-token limit, human action
or canonical commit.

NOT wired to production LUMI user/character worker or authenticated
WorldStore commit. A successful scene is a candidate ONLY.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.mara_s1_typed_live_v05 import one_provider_call
from experiments.sera.openrouter_scene_writer_v021 import create_writer
from experiments.sera.unattended_scene_rewrite_v020 import execute
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.composed-unattended-lab-runner.v0.23"


def _sha(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def run(*, prose, world, scene_key, work_root, api_key, registry,
        candidate_lexicon, typed_registry,
        writer_model, sweep_model, semantic_model, facet_model,
        provider_call=one_provider_call, repair_model=None,
        immutable_story_context=None, max_rewrites=2,
        writer_spend_guard_usd="0.15",
        extraction_spend_guard_usd="0.30",
        max_extraction_requests=24,
        trusted_temporal_builder=None,
        temporal_policy_id=None,
        trusted_relation_builder=None, relation_policy_id=None,
        reconciler=None, reconciliation_policy_id=None):
    """Run the actual staged v0.23 LAB workflow, no canon writes.

    Store work_root separately per authorized story job. The caller,
    not a model answer, chooses the session, world, provider credentials,
    registered entities, and immutable scene policy.
    """
    if ((reconciler is None) != (reconciliation_policy_id is None) or
        (reconciler is not None and
         (not callable(reconciler) or
          not isinstance(reconciliation_policy_id, str) or
          not reconciliation_policy_id.strip()))):
        raise CoverageError("V030_RECONCILER_POLICY_INVALID")
    validate_world(world)
    if not isinstance(prose, str) or not prose.strip():
        raise CoverageError("V023_RUN_SOURCE_REQUIRED")
    if not isinstance(scene_key, str) or not scene_key.strip():
        raise CoverageError("V023_RUN_SCENE_ID_REQUIRED")
    if not isinstance(work_root, (str, Path)):
        raise CoverageError("V023_RUN_ROOT_REQUIRED")
    if type(max_rewrites) is not int or not 0 <= max_rewrites <= 4:
        raise CoverageError("V023_RUN_REWRITE_POLICY_INVALID")
    context = deepcopy(immutable_story_context or {})
    if not isinstance(context, dict):
        raise CoverageError("V023_RUN_IMMUTABLE_CONTEXT_INVALID")
    for name in (writer_model, sweep_model, semantic_model, facet_model):
        if not isinstance(name, str) or not name.strip():
            raise CoverageError("V023_RUN_MODEL_REQUIRED")

    policy = {
        "schema": SCHEMA, "scene_key": scene_key,
        "original_prose_sha256": prose_hash(prose),
        "world_sha256": _sha(world),
        "models": [writer_model, sweep_model, semantic_model,
                   facet_model, repair_model],
        "registry_sha256": _sha(registry),
        "candidate_lexicon_sha256": _sha(candidate_lexicon),
        "typed_registry_sha256": _sha(typed_registry),
        "story_context_sha256": _sha(context),
        "max_rewrites": max_rewrites,
        "writer_spend_guard_usd": str(writer_spend_guard_usd),
        "extraction_spend_guard_usd": str(extraction_spend_guard_usd),
        "max_extraction_requests": max_extraction_requests,
        "full_scene_gate_required": True,
        "temporal_policy_id": temporal_policy_id,
        "relation_policy_id": relation_policy_id,
        "reconciliation_policy_id": reconciliation_policy_id,
        "production_canon_authority": False,
    }
    root = Path(work_root)
    worker = create_preparer(
        evidence_root=root/"evidence",
        work_root=root/"extraction_jobs",
        scene_key=scene_key,
        registry=registry,
        candidate_lexicon=candidate_lexicon,
        typed_registry=typed_registry,
        api_key=api_key,
        extraction_model=sweep_model,
        semantic_model=semantic_model,
        typed_model=facet_model,
        provider_call=provider_call,
        fallback_model=repair_model,
        max_model_requests=max_extraction_requests,
        observed_spend_guard_usd=extraction_spend_guard_usd,
        trusted_temporal_builder=trusted_temporal_builder,
        temporal_policy_id=temporal_policy_id,
        trusted_relation_builder=trusted_relation_builder,
        relation_policy_id=relation_policy_id,
        reconciler=reconciler,
    )
    writer = create_writer(
        api_key=api_key,
        model=writer_model, story_context=context,
        provider_call=provider_call,
        fallback_model=repair_model,
        archive_dir=root/"writer_paid_receipts",
        observed_spend_guard_usd=writer_spend_guard_usd,
        reconciler=reconciler,
    )
    return execute(
        prose=prose, world=world,
        prepare_evidence=worker,
        evidence_policy_id=_sha(policy),
        check_scene=create_checker(
            evidence_root=root/"evidence", full_qualification=True,
        ),
        rewrite_scene=writer,
        output_dir=root/"scene_controller",
        max_rewrites=max_rewrites,
        observed_spend_guard_usd=writer_spend_guard_usd,
    )
