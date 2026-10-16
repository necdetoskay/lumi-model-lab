"""SERA v0.28 — real StoryForge contract → isolated SERA scene qualification.

The bridge consumes StoryForge's published English master and immutable
request/result envelopes. StoryForge publication_ready means editorial
acceptance ONLY; it is NEVER WorldState/EventGraph commit authority.

No SERA provider call without explicit paid authorization, independent
trusted-world scope verification and exact qualification-ready model
runtime profile attestations. No API credential, model token output
ceiling, model-generated trusted route/fact, manual operator queue, or
canonical world write is persisted. All StoryForge inputs and model
profiles are content-addressed to the durable scene work contract.

This is an integration adapter for a laboratory story job, not a
production LUMI story-worker deployment or authenticated canon committer.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.sera.composed_scene_runner_v023 import run as run_scene
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.storyforge-scene-bridge.v0.28"
MODEL_ROLES = ("writer", "sweep", "semantic", "facet")
INPUT_SCHEMA = "storyforge-request.v1"
OUTPUT_SCHEMA = "storyforge-result.v1"


def need(condition, code):
    if not condition:
        raise CoverageError(code)


def sha(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def normalize(value, *, kind):
    if isinstance(value, dict):
        return deepcopy(value)
    if hasattr(value, "model_dump") and callable(value.model_dump):
        obj = value.model_dump(mode="json")
        need(isinstance(obj, dict), "V028_INVALID_" + kind)
        return deepcopy(obj)
    raise CoverageError("V028_INVALID_" + kind)


def real_profile_attestor(model):
    """Read actual LUMI runtime registry only when explicitly invoked.

    Exact/qualification-ready metadata is an application prerequisite;
    this never makes a billable provider call or relaxes token policy.
    """
    from src.model_registry import (
        require_qualification_runtime_profile, runtime_profile_identity,
    )
    profile = require_qualification_runtime_profile(model)
    identity = runtime_profile_identity(model)
    return {
        **identity, "qualification_ready":
            profile["qualification"]["ready"] is True,
    }


def _attested_models(models, attestor):
    need(isinstance(models, dict) and
         all(isinstance(models.get(k), str) and models[k].strip()
             for k in MODEL_ROLES) and
         (models.get("repair") is None or
          isinstance(models["repair"], str) and models["repair"].strip()),
         "V028_MODEL_ROLES_INCOMPLETE")
    need(callable(attestor), "V028_MODEL_ATTESTOR_REQUIRED")
    requested = list(MODEL_ROLES) + (["repair"] if models.get("repair") else [])
    verified = {}
    for role in requested:
        model = models[role]
        proof = attestor(model)
        need(isinstance(proof, dict) and proof.get("model_id") == model and
             proof.get("provider") == "openrouter" and
             isinstance(proof.get("match"), dict) and
             proof["match"].get("type") == "exact" and
             proof.get("qualification_ready") is True and
             all(isinstance(proof.get(k), str) and
                 len(proof[k]) == 64 and
                 all(c in "0123456789abcdef" for c in proof[k])
                 for k in ("profile_sha256", "runtime_contract_sha256",
                           "production_policy_sha256")),
             "V028_UNQUALIFIED_OR_UNPINNED_MODEL_PROFILE")
        verified[role] = {
            "model_id": model, "provider": "openrouter",
            "profile_sha256": proof["profile_sha256"],
            "runtime_contract_sha256": proof["runtime_contract_sha256"],
            "production_policy_sha256": proof["production_policy_sha256"],
        }
    return verified


def _persist_if_absent(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CoverageError("V028_CONTRACT_JOURNAL_CORRUPT") from exc
        need(old == content, "V028_IMMUTABLE_JOB_CONTRACT_CHANGED")
        return
    tmp = path.with_suffix(".tmp")
    # An existing abandoned journal must not silently replace a paid job.
    try:
        with tmp.open("x", encoding="utf-8") as file:
            file.write(json.dumps(
                content, sort_keys=True, ensure_ascii=False,
                allow_nan=False,
            ) + "\n")
            file.flush()
            os.fsync(file.fileno())
        tmp.replace(path)
    except FileExistsError as exc:
        raise CoverageError("V028_UNKNOWN_CONTRACT_JOURNAL_STATE") from exc


def prepare(*, request, result, world, trusted_scope,
            verify_scope, scene_span, models, model_attestor,
            scene_key, job_id):
    req = normalize(request, kind="STORYFORGE_REQUEST")
    res = normalize(result, kind="STORYFORGE_RESULT")
    validate_world(world)
    need(req.get("schema_version") == INPUT_SCHEMA and
         res.get("schema_version") == OUTPUT_SCHEMA and
         isinstance(req.get("request_id"), str) and req["request_id"] and
         req.get("request_id") == res.get("request_id") and
         isinstance(req.get("active_world_id"), str) and
         req["active_world_id"] and
         isinstance(req.get("profile_id"), str) and
         req.get("profile_id") == res.get("profile_id"),
         "V028_STORYFORGE_REQUEST_RESULT_MISMATCH")
    need(res.get("status") == "publication_ready" and
         res.get("publication_ready") is True and
         isinstance(res.get("english_story"), str) and
         res["english_story"].strip() and
         isinstance(res.get("plan"), dict) and
         isinstance(res.get("context_packet"), dict) and
         isinstance(res.get("evidence"), dict),
         "V028_STORYFORGE_EDITORIAL_GATE_NOT_ACCEPTED")
    need(isinstance(req.get("story_intent"), dict) and
         isinstance(req.get("generation_profile"), dict) and
         req["generation_profile"].get("language_of_generation") == "en" and
         isinstance(req.get("always_required"), list) and
         isinstance(req.get("candidate_facts"), list),
         "V028_STORYFORGE_REQUEST_CONTRACT_INVALID")
    editorial = res["evidence"]
    # Explicitly require the old independent editorial gates, not
    # merely a possibly model-influenced publication_ready flag.
    need(isinstance(editorial.get("story_gate"), dict) and
         editorial["story_gate"].get("pass") is True and
         isinstance(editorial.get("fidelity_gate"), dict) and
         editorial["fidelity_gate"].get("pass") is True,
         "V028_UNVERIFIED_STORYFORGE_EDITORIAL_EVIDENCE")
    need(isinstance(scene_key, str) and bool(scene_key.strip()) and
         isinstance(job_id, str) and bool(job_id.strip()) and
         all(c.isalnum() or c in "-_." for c in job_id) and
         not job_id.startswith(".") and len(job_id) <= 128,
         "V028_INVALID_SCENE_OR_JOB_ID")
    master = res["english_story"]
    need(isinstance(scene_span, dict) and
         set(scene_span) == {"start", "end"} and
         type(scene_span["start"]) is int and
         type(scene_span["end"]) is int and
         0 <= scene_span["start"] < scene_span["end"] <= len(master),
         "V028_SOURCE_SLICE_OUT_OF_BOUNDS")
    prose = master[scene_span["start"]:scene_span["end"]]
    need(prose.strip() and prose == prose.strip(),
         "V028_SOURCE_SLICE_NOT_EXACT_SCENE")
    need(isinstance(trusted_scope, dict) and
         trusted_scope.get("active_world_id") == req["active_world_id"] and
         trusted_scope.get("entry_world_sha256") == sha(world) and
         trusted_scope.get("storyforge_request_id") == req["request_id"] and
         isinstance(trusted_scope.get("policy_version"), str) and
         bool(trusted_scope["policy_version"]) and
         callable(verify_scope) and
         verify_scope(deepcopy(trusted_scope)) is True,
         "V028_TRUSTED_WORLD_SCOPE_NOT_VERIFIED")
    qualified = _attested_models(models, model_attestor)
    context = {
        "schema": SCHEMA,
        "request_id": req["request_id"],
        "active_world_id": req["active_world_id"],
        "storyforge_profile_id": req["profile_id"],
        "storyforge_request_sha256": sha(req),
        "storyforge_result_sha256": sha(res),
        "english_master_sha256": prose_hash(master),
        "scene_span": deepcopy(scene_span),
        "scene_source_sha256": prose_hash(prose),
        "trusted_world_scope_sha256": sha(trusted_scope),
        "verified_model_profiles": qualified,
        "story_intent": deepcopy(req["story_intent"]),
        "storyforge_validated_plan": deepcopy(res["plan"]),
        "storyforge_context_packet": deepcopy(res["context_packet"]),
    }
    contract = {
        "schema": SCHEMA, "job_id": job_id, "scene_key": scene_key,
        "prose_sha256": prose_hash(prose), "world_sha256": sha(world),
        "request_sha256": sha(req), "result_sha256": sha(res),
        "trusted_scope_sha256": sha(trusted_scope),
        "model_profile_sha256": sha(qualified),
        "context_sha256": sha(context),
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }
    return prose, context, contract


def run(*, request, result, world, trusted_scope,
        verify_scope, scene_span, models, model_attestor,
        scene_key, job_id, work_root,
        registry, candidate_lexicon, typed_registry,
        trusted_temporal_builder=None, temporal_policy_id=None,
        trusted_relation_builder=None, relation_policy_id=None,
        paid_authorized=False, paid_grant=None, verify_paid_grant=None,
        api_key=None, provider_call=None,
        max_rewrites=2):
    """Make dry-run default; run SERA only on explicit paid authorization.

    For production the app MUST inject a real authenticated verify_scope,
    real registered identity/fact/route policies and a durable per-job
    storage mount. The returned outcome NEVER signals canon authority.
    """
    prose, context, contract = prepare(
        request=request, result=result, world=world,
        trusted_scope=trusted_scope, verify_scope=verify_scope,
        scene_span=scene_span, models=models,
        model_attestor=model_attestor,
        scene_key=scene_key, job_id=job_id,
    )
    need(isinstance(work_root, (str, Path)) and
         type(paid_authorized) is bool,
         "V028_JOB_ROOT_OR_BILLING_POLICY_INVALID")
    root = Path(work_root) / job_id
    # Application, not the provider, owns these registered facts/routes.
    for mapping in (registry, candidate_lexicon, typed_registry):
        need(isinstance(mapping, dict),
             "V028_REGISTERED_WORLD_POLICY_REQUIRED")
    need(isinstance(typed_registry.get("openables"), list) and
         isinstance(typed_registry.get("documents"), list),
         "V028_TYPED_REGISTRY_INVALID")
    # The worker must not be allowed to inherit a differently-scoped
    # entry world or a changed profile on resume.
    contract = {
        **contract,
        "trusted_temporal_policy_id": temporal_policy_id,
        "trusted_relation_policy_id": relation_policy_id,
        "registered_entities_sha256": sha(registry),
        "candidate_lexicon_sha256": sha(candidate_lexicon),
        "typed_registry_sha256": sha(typed_registry),
        "max_rewrites": max_rewrites,
    }
    _persist_if_absent(root / "v028_immutable_contract.json", contract)
    if not paid_authorized:
        return {
            "schema": SCHEMA,
            "status": "DRY_RUN_READY_NO_MODEL_CALLS_NONCANONICAL",
            "job_id": job_id, "scene_key": scene_key,
            "scene_sha256": prose_hash(prose),
            "world_sha256": sha(world),
            "model_profile_sha256": contract["model_profile_sha256"],
            "provider_calls": 0, "model_cost_usd": "0",
            "requires_manual_intervention": False,
            "canonical_commit_authorized": False, "world_db_writes": 0,
            "next_automatic_action": "AWAIT_EXPLICIT_BILLING_AUTHORIZATION",
        }
    # Billing is granted by an independent authenticated application
    # authority, not by an untrusted caller flipping a boolean or by
    # StoryForge's publication_ready. This is a signed-job policy seam,
    # not an interactive human approval step for normal production.
    need(isinstance(paid_grant, dict) and
         paid_grant.get("approved") is True and
         paid_grant.get("job_id") == job_id and
         paid_grant.get("scene_key") == scene_key and
         paid_grant.get("request_sha256") == contract["request_sha256"] and
         paid_grant.get("result_sha256") == contract["result_sha256"] and
         paid_grant.get("world_sha256") == contract["world_sha256"] and
         paid_grant.get("model_profile_sha256") ==
             contract["model_profile_sha256"] and
         isinstance(paid_grant.get("budget_policy_id"), str) and
         bool(paid_grant["budget_policy_id"].strip()) and
         callable(verify_paid_grant) and
         verify_paid_grant(deepcopy(paid_grant)) is True,
         "V028_PAID_GRANT_NOT_AUTHENTICATED_OR_SCOPE_MISMATCH")
    _persist_if_absent(root / "v028_verified_paid_grant_digest.json", {
        "schema": "sera.verified-paid-grant-digest.v0.28",
        "contract_sha256": sha(contract),
        "billing_grant_sha256": sha(paid_grant),
    })
    need(isinstance(api_key, str) and api_key.strip() and
         callable(provider_call),
         "V028_PAID_PROVIDER_NOT_CONFIGURED")
    models = deepcopy(models)
    result = run_scene(
        prose=prose, world=world, scene_key=scene_key,
        work_root=root / "sera_noncanonical",
        api_key=api_key, registry=deepcopy(registry),
        candidate_lexicon=deepcopy(candidate_lexicon),
        typed_registry=deepcopy(typed_registry),
        writer_model=models["writer"], sweep_model=models["sweep"],
        semantic_model=models["semantic"], facet_model=models["facet"],
        repair_model=models.get("repair"),
        immutable_story_context=context,
        trusted_temporal_builder=trusted_temporal_builder,
        temporal_policy_id=temporal_policy_id,
        trusted_relation_builder=trusted_relation_builder,
        relation_policy_id=relation_policy_id,
        provider_call=provider_call,
        max_rewrites=max_rewrites,
    )
    need(isinstance(result, dict) and
         result.get("canonical_commit_authorized") is False and
         result.get("world_db_writes") == 0 and
         result.get("requires_manual_intervention") is False,
         "V028_SCENE_WORKER_AUTHORITY_INVALID")
    return {
        "schema": SCHEMA, "job_id": job_id, "scene_key": scene_key,
        "status": ("SCENE_EVIDENCE_QUALIFIED_NONCANONICAL" if
                   result.get("status") ==
                       "SCENE_CANDIDATE_READY_NONCANONICAL" else
                   "FAILED_SAFE_FINAL"),
        "scene_sha256": prose_hash(prose),
        "world_sha256": sha(world),
        "storyforge_editorial_ready": True,
        "sera_scene_result": result,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
        "next_automatic_action": (
            "CONTINUE_OTHER_INDEPENDENT_STORY_GATES" if
            result.get("status") == "SCENE_CANDIDATE_READY_NONCANONICAL"
            else "FAILED_SAFE_FINAL"
        ),
    }
