"""SERA v0.21 — durable evidence-bound actual v0.19/v0.20 scene checker.

This is the nonbillable side of the unattended v0.20 control loop.
It consumes already-archived, SOURCE-AND-WORLD-keyed extraction and
semantic model receipts and actually executes the v0.19 independent
source binding + v0.20 typed-world simulation. The source archive
MUST be independently re-created for every revised prose by a future
durable extraction worker; a missing archive fails safely, never
reuses old model conclusions for new text.

No human approval, magic scene-specific rules, DB writes, provider
calls, model output token limits or canonical authorization.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.event_candidate_projection_v019 import project
from experiments.sera.typed_aspect_recovery_v020 import recover
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.recheck-evidence-bundle.v0.21"
KEYS = frozenset({
    "schema", "prose_sha256", "world_sha256",
    "extraction_report", "semantic_summary",
    "typed_registry", "typed_candidates", "temporal_case",
    "relation_case",
})


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def build_bundle(*, prose, world, extraction_report, semantic_summary,
                 typed_registry, typed_candidates, temporal_case=None,
                 relation_case=None):
    """Produce a *non-authorizing* versioned archive from existing evidence."""
    validate_world(world)
    return {
        "schema": SCHEMA,
        "prose_sha256": prose_hash(prose),
        "world_sha256": digest(world),
        "extraction_report": deepcopy(extraction_report),
        "semantic_summary": deepcopy(semantic_summary),
        "typed_registry": deepcopy(typed_registry),
        "typed_candidates": deepcopy(typed_candidates),
        "temporal_case": deepcopy(temporal_case),
        "relation_case": deepcopy(relation_case),
    }


def create_checker(*, evidence_root, full_qualification=False):
    """Set full_qualification=True for v0.23 scene-worker qualification.

    The v0.21 two-gate mode is kept only for historical lab replays.
    """
    if type(full_qualification) is not bool:
        raise CoverageError("V023_QUALIFICATION_POLICY_INVALID")
    root = Path(evidence_root)
    def check_scene(*, prose, world):
        validate_world(world)
        fingerprint = prose_hash(prose)
        # Hash derived from actual prose, not provider output or user path.
        path = root / (fingerprint + ".json")
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CoverageError("V021_EVIDENCE_FOR_PROSE_NOT_AVAILABLE") from exc
        if (not isinstance(bundle, dict) or set(bundle) != KEYS or
            bundle["schema"] != SCHEMA or
            bundle["prose_sha256"] != fingerprint or
            bundle["world_sha256"] != digest(world)):
            raise CoverageError("V021_EVIDENCE_WORLD_OR_SOURCE_MISMATCH")
        # Actually run source-bound independent semantic recheck and typed
        # guarded state simulation, not a stubbed READY or "review" label.
        projected = project(
            prose=prose,
            extraction_report=bundle["extraction_report"],
            semantic_summary=bundle["semantic_summary"],
            temporal_case=bundle["temporal_case"],
        )
        roles = bundle["typed_registry"]
        if (isinstance(roles,dict) and
            set(roles)=={"openables","documents"} and
            isinstance(roles["openables"],list) and
            isinstance(roles["documents"],list) and
            set(roles["openables"]) & set(roles["documents"]) and
            bundle["typed_candidates"]):
            # Multi-capability OBJECTS: never let legacy v0.13's single
            # role-per-object simulator silently drop OPEN or WRITE.
            from experiments.sera.multifacet_physical_preview_v054 import preview
            typed=preview(
                prose=prose,world=world,registry=roles,
                candidates=bundle["typed_candidates"],
                extraction_report=bundle["extraction_report"])
        elif (isinstance(roles, dict) and
            set(roles) == {"openables", "documents"} and
            roles["openables"] == [] and roles["documents"] == [] and
            bundle["typed_candidates"] == []):
            # No phantom watch or notebook: the empty facet registry is
            # acceptable ONLY with the full v0.23 all-event gate, which
            # still detects unsupported MOVE/TRANSFER/state effects.
            if not full_qualification:
                raise CoverageError("V024_EMPTY_FACETS_REQUIRE_FULL_GATE")
            typed = {
                "schema": "sera.typed-aspect-candidate-recovery.v0.20",
                "status": "NO_APPLICABLE_TYPED_FACETS_NONCANONICAL",
                "prose_sha256": prose_hash(prose),
                "world_sha256": digest(world),
                "original_candidates_sha256": digest([]),
                "blocker_codes": [],
                "requires_manual_intervention": False,
                "canonical_commit_authorized": False,
                "world_db_writes": 0,
                "empty_facet_scope_requires_full_gate": True,
            }
        elif (full_qualification and bundle["typed_candidates"] and
              bundle["temporal_case"] is not None and
              bundle["relation_case"] is not None and
              any(isinstance(e, dict) and e.get("kind") == "MOVE"
                  for e in bundle["extraction_report"].get(
                      "candidate_events", [])) and
              any(isinstance(e, dict) and e.get("kind") in (
                  "TRANSFER", "LEARN_FACT", "KNOWLEDGE_UPDATE")
                  for e in bundle["extraction_report"].get(
                      "candidate_events", []))):
            # v0.13 independently validates at ORIGINAL entry location,
            # which is incorrect when an object is used AFTER movement.
            # Defer ONLY with v0.27 full gate; no independently approved
            # result or model claim grants final scene readiness.
            typed = {
                "schema": "sera.typed-aspect-candidate-recovery.v0.20",
                "status": "DEFERRED_TO_V027_ORDERED_FACETS_NONCANONICAL",
                "prose_sha256": prose_hash(prose),
                "world_sha256": digest(world),
                "original_candidates_sha256": digest(
                    bundle["typed_candidates"]),
                "blocker_codes": [],
                "requires_manual_intervention": False,
                "canonical_commit_authorized": False,
                "world_db_writes": 0,
                "ordered_facet_scope_requires_full_gate": True,
            }
        else:
            typed = recover(
                prose=prose, world=world,
                registry=roles, candidates=bundle["typed_candidates"],
                projection=projected,
            )
        if (projected["canonical_commit_authorized"] is not False or
            typed["canonical_commit_authorized"] is not False or
            projected["world_db_writes"] != 0 or
            typed["world_db_writes"] != 0):
            raise CoverageError("V021_EVIDENCE_UNAUTHORIZED_WORLD_CHANGE")
        result = {"projection": projected, "typed": typed}
        if full_qualification:
            # No recursive dependency: import after the v0.21 module is
            # loaded so the v0.23 qualifier may reuse its SHA digest.
            from experiments.sera.full_scene_qualification_v023 import qualify
            result["qualification"] = qualify(
                prose=prose, world=world, bundle=bundle,
                projection=projected, typed=typed,
            )
        return result
    return check_scene
