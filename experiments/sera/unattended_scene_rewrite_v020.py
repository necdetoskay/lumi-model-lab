"""SERA v0.20 — unattended, lab-only source-to-rewrite scene controller.

This is a reusable state-machine integration seam, not a production model
adapter or authorization gate. The caller supplies a deterministic
check_scene(prose=..., world=...) that runs ALL required nonbillable gates
and a rewrite_scene(source=..., defects=...) callback that returns a
COMPLETED, receipted model answer. There is no manual retry or approval.
Every rewritten scene must be checked again from scratch. Unknown in-flight
calls are never blindly resent; no model output token ceiling exists.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.unattended-scene-rewrite-controller.v0.20"
MAX_REWRITES = 4


def _digest(obj):
    return sha256(canonical(obj).encode("utf-8")).hexdigest()


def _read(file):
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CoverageError("V020_REWRITE_DURABLE_RECORD_INVALID") from exc


def _write(file, obj):
    temp = file.with_suffix(file.suffix + ".pending")
    temp.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temp.replace(file)


def _receipt(payload, expected_source_hash):
    if (not isinstance(payload, dict) or set(payload) != {"prose", "receipt"}
        or not isinstance(payload["prose"], str)
        or not payload["prose"].strip()):
        raise CoverageError("V020_REWRITE_REPLY_SCHEMA_INVALID")
    proof = payload["receipt"]
    if (not isinstance(proof, dict) or
        set(proof) != {"source_prose_sha256", "response_id", "model",
                       "finish_reason", "cost_usd"} or
        proof["source_prose_sha256"] != expected_source_hash or
        not isinstance(proof["response_id"], str) or
        not proof["response_id"].strip() or
        not isinstance(proof["model"], str) or not proof["model"] or
        proof["finish_reason"] != "stop"):
        raise CoverageError("V020_REWRITE_PROVIDER_RECEIPT_INVALID")
    try:
        charge = Decimal(str(proof["cost_usd"]))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise CoverageError("V020_REWRITE_COST_INVALID") from exc
    if not charge.is_finite() or charge < 0:
        raise CoverageError("V020_REWRITE_COST_INVALID")
    return charge


def _assess(result, prose, world):
    if not isinstance(result, dict) or set(result) not in (
        {"projection", "typed"},
        {"projection", "typed", "qualification"},
    ):
        raise CoverageError("V020_REWRITE_ASSESSMENT_INVALID")
    projection, typed = result["projection"], result["typed"]
    if (not isinstance(projection, dict) or not isinstance(typed, dict) or
        projection.get("schema") != "sera.event-candidate-repair.v0.19" or
        typed.get("schema") != "sera.typed-aspect-candidate-recovery.v0.20" or
        projection.get("prose_sha256") != prose_hash(prose) or
        typed.get("prose_sha256") != prose_hash(prose) or
        typed.get("world_sha256") != _digest(world) or
        projection.get("canonical_commit_authorized") is not False or
        typed.get("canonical_commit_authorized") is not False or
        projection.get("world_db_writes") != 0 or
        typed.get("world_db_writes") != 0 or
        typed.get("requires_manual_intervention") is not False):
        raise CoverageError("V020_REWRITE_ASSESSMENT_SOURCE_OR_AUTHORITY_INVALID")
    ready = (
        projection.get("next_automatic_action") ==
        "CONTINUE_FULL_SCENE_GATES" and
        projection.get("status") ==
        "CANDIDATES_STRUCTURALLY_CLEAN_NONCANONICAL" and
        (
            (typed.get("status") == "TYPED_FACETS_SIMULATED_NONCANONICAL"
             and typed.get("next_automatic_action") ==
                "CONTINUE_INDEPENDENT_SCENE_QUALIFICATION")
            or (typed.get("status") ==
                "NO_APPLICABLE_TYPED_FACETS_NONCANONICAL" and
                "qualification" in result and
                typed.get("empty_facet_scope_requires_full_gate") is True)
            or (typed.get("status") ==
                "DEFERRED_TO_V027_ORDERED_FACETS_NONCANONICAL" and
                "qualification" in result and
                typed.get("ordered_facet_scope_requires_full_gate") is True
                and isinstance(result["qualification"], dict) and
                result["qualification"].get("ordered_facet_preview") is not None)
        )
    )
    failures = (projection.get("remaining_semantic_task_codes", []) +
                projection.get("unsupported_semantic_tasks", []) +
                typed.get("blocker_codes", []))
    # v0.23 full-scene qualification is REQUIRED for the new v0.23
    # composed worker, but old experimental two-gate v0.20 replays remain
    # explicitly NONCANONICAL and backward-compatible.
    if "qualification" in result:
        q = result["qualification"]
        if (not isinstance(q, dict) or
            q.get("schema") != "sera.full-scene-qualification.v0.23" or
            q.get("prose_sha256") != prose_hash(prose) or
            q.get("world_sha256") != _digest(world) or
            q.get("canonical_commit_authorized") is not False or
            q.get("world_db_writes") != 0 or
            q.get("requires_manual_intervention") is not False or
            not isinstance(q.get("defects"), list)):
            raise CoverageError("V023_FULL_GATE_INVALID_OR_FORGED")
        complete = (
            q.get("status") == "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL"
            and q.get("next_automatic_action") ==
                "CONTINUE_INDEPENDENT_CANON_QUALIFICATION"
            and q["defects"] == []
        )
        ready = ready and complete
        failures += deepcopy(q["defects"])
        if not complete and not q["defects"]:
            raise CoverageError("V023_FULL_GATE_MISSING_DEFECT_EVIDENCE")
    if (not isinstance(failures, list) or not all(
        isinstance(item, (str, dict)) and bool(item) for item in failures
    )):
        raise CoverageError("V020_REWRITE_DEFECTS_SCHEMA_INVALID")
    if not ready and not failures:
        raise CoverageError("V020_REWRITE_MISSING_DEFECT_EVIDENCE")
    return ready, failures


def _recover_existing_paid_rewrite(*, source, world, output_dir,
                                   max_rewrites, recover_rewrite_scene):
    """Rehydrate only a previously started paid writer request.

    All earlier source checks and rewrites are read from immutable
    journals; the callback must be the writer's GET-only recovery path.
    """
    current = source
    for idx in range(max_rewrites):
        check = output_dir / f"check_{idx:02d}.json"
        if not check.is_file():
            return False
        row = _read(check)
        if not isinstance(row, dict) or (
            row.get("prose_sha256") != prose_hash(current)
        ):
            raise CoverageError("V031_REWRITE_CHECKPOINT_SOURCE_MISMATCH")
        ready, defects = _assess(row.get("assessment"), current, world)
        if ready:
            return False
        saved = output_dir / f"rewrite_{idx:02d}.json"
        pending = output_dir / f"rewrite_{idx:02d}.started"
        if saved.is_file():
            old_answer = _read(saved)
            _receipt(old_answer, prose_hash(current))
            if prose_hash(old_answer["prose"]) == prose_hash(current):
                raise CoverageError("V031_PREVIOUS_REWRITE_NO_SOURCE_CHANGE")
            current = old_answer["prose"]
            continue
        if not pending.is_file():
            return False
        if _read(pending) != {
            "prose_sha256": prose_hash(current),
            "defects_sha256": _digest(defects),
        }:
            raise CoverageError("V031_PENDING_REWRITE_PROOF_MISMATCH")
        try:
            answer = recover_rewrite_scene(
                source=current, defects=deepcopy(defects),
            )
            _receipt(answer, prose_hash(current))
            if prose_hash(answer["prose"]) == prose_hash(current):
                return False
        except (CoverageError, OSError, TypeError, ValueError):
            # Unknown generation ID: leave terminal failure intact.
            return False
        _write(saved, answer)
        return True
    return False


def execute(*, prose, world, check_scene, rewrite_scene,
            output_dir, max_rewrites=2,
            observed_spend_guard_usd="0.15",
            prepare_evidence=None, evidence_policy_id=None,
            resume_reconciled_evidence=False,
            recover_rewrite_scene=None):
    """Automatically rewrite affected scene until source-bound gates pass.

    check_scene MUST be deterministic and without a new billed provider
    request; a future durable worker will orchestrate the actual paid
    extraction outside this controller. rewrite_scene may be paid, but
    its response MUST have provider/cost receipt and source fingerprint.
    A crash before receipt is a terminal-safe exception, not a human queue.
    """
    validate_world(world)
    if (type(max_rewrites) is not int or
        not 0 <= max_rewrites <= MAX_REWRITES or
        not isinstance(prose, str) or not prose.strip()):
        raise CoverageError("V020_REWRITE_POLICY_INVALID")
    try:
        spend_guard = Decimal(str(observed_spend_guard_usd))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CoverageError("V020_REWRITE_SPEND_POLICY_INVALID") from exc
    if not spend_guard.is_finite() or spend_guard <= 0:
        raise CoverageError("V020_REWRITE_SPEND_POLICY_INVALID")
    if prepare_evidence is not None and (
        not callable(prepare_evidence) or
        not isinstance(evidence_policy_id, str) or
        not evidence_policy_id.strip()
    ):
        raise CoverageError("V022_EVIDENCE_POLICY_ID_REQUIRED")
    if prepare_evidence is None and evidence_policy_id is not None:
        raise CoverageError("V022_UNUSED_EVIDENCE_POLICY_ID")
    if (type(resume_reconciled_evidence) is not bool or
        (resume_reconciled_evidence and prepare_evidence is None)):
        raise CoverageError("V030_SCENE_RECONCILIATION_POLICY_INVALID")
    if recover_rewrite_scene is not None and not callable(recover_rewrite_scene):
        raise CoverageError("V031_REWRITE_RECOVERY_CALLBACK_INVALID")
    output_dir = Path(output_dir)
    contract = {
        "schema": SCHEMA, "original_prose_sha256": prose_hash(prose),
        "world_sha256": _digest(world),
        "max_rewrites": max_rewrites,
        "observed_spend_guard_usd": str(spend_guard),
    }
    if prepare_evidence is not None:
        contract["evidence_policy_id"] = evidence_policy_id
    if output_dir.exists():
        if _read(output_dir / "contract.json") != contract:
            raise CoverageError("V020_REWRITE_RESUME_CONTRACT_MISMATCH")
    else:
        output_dir.mkdir(parents=True, exist_ok=False)
        _write(output_dir / "contract.json", contract)
    final = output_dir / "final.json"
    if final.exists():
        previous = _read(final)
        if (recover_rewrite_scene is not None and
            isinstance(previous, dict) and
            previous.get("status") == "FAILED_SAFE_FINAL" and
            previous.get("reason_code") in (
                "V020_REWRITE_PROVIDER_FAILED_SAFE",
                "V020_UNKNOWN_IN_FLIGHT_REWRITE_NO_AUTO_RESEND",
            )):
            recovered = _recover_existing_paid_rewrite(
                source=prose, world=world, output_dir=output_dir,
                max_rewrites=max_rewrites,
                recover_rewrite_scene=recover_rewrite_scene,
            )
            if not recovered:
                return previous
            prior = output_dir / "pre_reconciled_writer_safe_stop.json"
            if prior.exists():
                if _read(prior) != previous:
                    raise CoverageError("V031_PRIOR_WRITER_FAILURE_DRIFT")
            else:
                _write(prior, previous)
            final.unlink()
        elif (not resume_reconciled_evidence or
              not isinstance(previous, dict) or
              previous.get("status") != "FAILED_SAFE_FINAL" or
              previous.get("reason_code") !=
                  "V022_EVIDENCE_GENERATION_FAILED_SAFE"):
            return previous
        else:
            # One noncanonical evidence replay may verify an orphaned
            # generation via authenticated GET; the v0.22 journal ensures
            # existing STARTED signatures are NEVER billed a second time.
            # If recovery cannot complete, preserve the prior terminal result.
            try:
                recovered = prepare_evidence(
                    prose=prose, world=deepcopy(world),
                )
            except Exception:
                return previous
            if (not isinstance(recovered, dict) or
                recovered.get("status") != "EVIDENCE_READY_NONCANONICAL" or
                recovered.get("prose_sha256") != prose_hash(prose) or
                recovered.get("world_sha256") != _digest(world) or
                recovered.get("canonical_commit_authorized") is not False or
                recovered.get("world_db_writes") != 0):
                return previous
            prior = output_dir / "pre_reconciliation_safe_stop.json"
            if prior.exists():
                if _read(prior) != previous:
                    raise CoverageError("V030_SCENE_PRIOR_FAILURE_DRIFT")
            else:
                _write(prior, previous)
            final.unlink()

    original_world = _digest(world)
    current = prose
    audit = []
    spent = Decimal("0")
    status = "FAILED_SAFE_FINAL"
    reason = "V020_REWRITE_ATTEMPTS_EXHAUSTED"

    def finish():
        out = {
            "schema": SCHEMA, "status": status,
            "reason_code": reason,
            "original_prose_sha256": contract["original_prose_sha256"],
            "final_prose_sha256": prose_hash(current),
            "candidate_prose_noncanonical": current,
            "attempts": deepcopy(audit),
            "rewrite_count": sum(1 for a in audit if "rewrite_response_id" in a),
            "provider_reported_spend_usd": str(spent),
            "next_automatic_action": (
                "CONTINUE_OTHER_FULL_STORY_GATES" if status ==
                "SCENE_CANDIDATE_READY_NONCANONICAL" else
                "TERMINAL_SAFE_NO_WORLD_WRITE"
            ),
            "canonical_commit_authorized": False,
            "world_db_writes": 0,
            "requires_manual_intervention": False,
        }
        if _digest(world) != original_world:
            raise CoverageError("V020_REWRITE_WORLD_MUTATED")
        _write(final, out)
        return out

    for idx in range(max_rewrites + 1):
        if prepare_evidence is not None:
            # v0.22 paid extraction owns per-source model request/receipt
            # checkpoints. Never try to redo a paid call from this controller.
            try:
                prepared = prepare_evidence(
                    prose=current, world=deepcopy(world),
                )
                if (not isinstance(prepared, dict) or
                    prepared.get("status") != "EVIDENCE_READY_NONCANONICAL" or
                    prepared.get("prose_sha256") != prose_hash(current) or
                    prepared.get("world_sha256") != _digest(world) or
                    prepared.get("canonical_commit_authorized") is not False or
                    prepared.get("world_db_writes") != 0):
                    reason = "V022_EVIDENCE_GENERATION_FAILED_SAFE"
                    break
            except Exception:
                reason = "V022_EVIDENCE_GENERATION_FAILED_SAFE"
                break
        scan = output_dir / f"check_{idx:02d}.json"
        started = output_dir / f"check_{idx:02d}.started"
        if scan.is_file():
            row = _read(scan)
            if row.get("prose_sha256") != prose_hash(current):
                reason = "V020_CHECKPOINT_SOURCE_MISMATCH"
                break
            assessment = row["assessment"]
        else:
            # check_scene is contractually nonbillable and deterministic.
            # An interrupted check is safe to recompute from the same
            # frozen source. Only an unknown in-flight *provider* rewrite
            # must remain fail-closed to avoid double billing.
            if started.exists():
                if _read(started) != {"prose_sha256": prose_hash(current)}:
                    reason = "V020_CHECKPOINT_SOURCE_MISMATCH"
                    break
            else:
                _write(started, {"prose_sha256": prose_hash(current)})
            try:
                assessment = check_scene(prose=current, world=deepcopy(world))
                _assess(assessment, current, world)
                _write(scan, {
                    "prose_sha256": prose_hash(current),
                    "assessment": assessment,
                })
            except Exception:
                reason = "V020_SCENE_CHECK_FAILED_SAFE"
                break
        try:
            ready, defects = _assess(assessment, current, world)
        except (CoverageError, TypeError):
            reason = "V020_SCENE_CHECK_INVALID"
            break
        audit.append({"attempt": idx, "prose_sha256": prose_hash(current),
                      "structurally_ready_noncanonical": ready,
                      "defects": deepcopy(defects)})
        if ready:
            status = "SCENE_CANDIDATE_READY_NONCANONICAL"
            reason = "V020_ONLY_STRUCTURAL_GATES_QUALIFIED"
            break
        if idx == max_rewrites:
            break
        if spent >= spend_guard:
            reason = "V020_REWRITE_OBSERVED_SPEND_GUARD"
            break
        before = prose_hash(current)
        saved = output_dir / f"rewrite_{idx:02d}.json"
        pending = output_dir / f"rewrite_{idx:02d}.started"
        if saved.is_file():
            answer = _read(saved)
        elif pending.exists():
            reason = "V020_UNKNOWN_IN_FLIGHT_REWRITE_NO_AUTO_RESEND"
            break
        else:
            _write(pending, {
                "prose_sha256": before, "defects_sha256": _digest(defects),
            })
            try:
                answer = rewrite_scene(
                    source=current,
                    defects=deepcopy(defects),
                )
                _receipt(answer, before)
                _write(saved, answer)
            except Exception:
                reason = "V020_REWRITE_PROVIDER_FAILED_SAFE"
                break
        try:
            cost = _receipt(answer, before)
            if prose_hash(answer["prose"]) == before:
                reason = "V020_REWRITE_NO_SOURCE_CHANGE"
                break
            spent += cost
            audit[-1]["rewrite_response_id"] = answer["receipt"]["response_id"]
            current = answer["prose"]
        except (CoverageError, ValueError, TypeError):
            reason = "V020_REWRITE_RECEIPT_OR_SOURCE_INVALID"
            break
    return finish()
