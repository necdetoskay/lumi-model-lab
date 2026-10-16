"""SERA v0.17: unattended, restart-aware scene identity recovery supervisor.

This is a laboratory boundary, NOT production story authorization.
Complete identities are source-bound model proposals, never world truth.

The supervisor re-extracts after fully receipted incomplete responses, and
automatically terminates on exhausted recovery. An in-flight request with no
durable provider receipt is NOT repeated: the provider might have charged it.
That case ends FAILED_SAFE_FINAL until idempotent provider recovery exists.
No human review, manual JSON patch, approval, resume action or token ceiling.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.blind_identity_v015 import make_request
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.identity_stage_v016 import execute as identity_stage
from experiments.sera.identity_auto_repair_v016 import repair as replay_identity
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.scene-identity-recovery.v0.17"
MAX_SCENE_ATTEMPTS = 4


def _hash(obj):
    return sha256(canonical(obj).encode("utf-8")).hexdigest()


def _persist(path, value):
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageError("V017_DURABLE_RECORD_UNREADABLE") from exc


def _receipts_complete(attempt_dir):
    """Fail closed if ANY dispatched billable request lacks a durable receipt."""
    ledger_path = attempt_dir / "ledger.json"
    if not ledger_path.is_file():
        return False, "V017_MISSING_PROVIDER_LEDGER"
    ledger = _read(ledger_path)
    if not isinstance(ledger, list):
        return False, "V017_PROVIDER_LEDGER_INVALID"
    started = Counter(x.get("ref") for x in ledger
                      if isinstance(x, dict) and
                      x.get("stage") == "REQUEST_STARTED")
    saved = Counter(x.get("ref") for x in ledger
                    if isinstance(x, dict) and
                    x.get("stage") == "RAW_RESPONSE_SAVED")
    if started != saved or not started:
        return False, "V017_UNCONFIRMED_IN_FLIGHT_PROVIDER_ATTEMPT"
    for ref in saved:
        filename = ("primary.json" if ref == "ALL" else
                    "targeted_" + sha256(ref.encode("utf-8")).hexdigest()[:24]
                    + ".json")
        path = attempt_dir / filename
        if not path.is_file():
            return False, "V017_PROVIDER_RECEIPT_MISSING"
        receipt = _read(path)
        usage = receipt.get("usage") if isinstance(receipt, dict) else None
        if not isinstance(usage, dict) or usage.get("cost") is None:
            return False, "V017_PROVIDER_CHARGE_UNKNOWN"
        try:
            charge = Decimal(str(usage["cost"]))
        except (ValueError, TypeError, InvalidOperation):
            return False, "V017_PROVIDER_CHARGE_INVALID"
        if not charge.is_finite() or charge < 0:
            return False, "V017_PROVIDER_CHARGE_INVALID"
    return True, None



def _recover_completed_provider_receipts(*, attempt_dir, prose, world, census):
    """Rebind durable paid evidence after a worker crash; ZERO new model calls.

    Any in-flight unreceipted request is rejected before entering here.
    Previously paid targeted replies remain archived; their interpretations
    are conservatively NOT reconstructed as authority by this recovery.
    """
    receipts_ok, error = _receipts_complete(attempt_dir)
    if not receipts_ok:
        raise CoverageError(error)
    primary = _read(attempt_dir / "primary.json")
    original = primary.get("raw_content")
    if not isinstance(original, str) or not original.strip():
        raise CoverageError("V017_ARCHIVED_PRIMARY_CONTENT_INVALID")
    ledger = _read(attempt_dir / "ledger.json")
    saved = [item["ref"] for item in ledger
             if isinstance(item, dict) and
             item.get("stage") == "RAW_RESPONSE_SAVED"]
    charges = Decimal("0")
    for ref in saved:
        name = ("primary.json" if ref == "ALL" else
                "targeted_" + sha256(ref.encode("utf-8")).hexdigest()[:24]
                + ".json")
        charges += Decimal(str(_read(attempt_dir / name)["usage"]["cost"]))
    # Recompute source-bound proposals with no external model callback.
    # If a previously paid targeted answer is omitted, the supervisor
    # automatically proceeds to a new full-scene attempt only when safe.
    result = replay_identity(
        prose=prose, world=world, census=census,
        raw_provider_content=original, max_targeted_calls=0,
    )
    summary = {
        "schema": "sera.identity-stage.v0.16",
        "status": "AUTO_REPAIR_FINISHED_NONCANONICAL_HOLD",
        "primary_calls": saved.count("ALL"),
        "targeted_calls": len(saved) - saved.count("ALL"),
        "provider_reported_total_spend_usd": float(charges),
        "result": result, "error": None,
        "recovered_from_archived_provider_receipts": True,
        "canonical_commit_authorized": False, "world_db_writes": 0,
    }
    _persist(attempt_dir / "result.json", summary)
    return summary


def _ready(stage):
    result = stage.get("result")
    return (
        stage.get("status") == "AUTO_REPAIR_FINISHED_NONCANONICAL_HOLD"
        and isinstance(result, dict)
        and result.get("all_reference_slots_accounted_for") is True
        and type(result.get("requested_entity_count")) is int
        and result.get("accepted_source_bound_count")
            == result["requested_entity_count"]
        and result.get("automatic_abstain_count") == 0
        and result.get("model_declared_abstain_count") == 0
        and result.get("canonical_commit_authorized") is False
        and result.get("world_db_writes") == 0
    )


def execute(*, prose, world, census, call_model, output_dir,
            primary_model="anthropic/claude-haiku-4.5",
            repair_model="anthropic/claude-haiku-4.5",
            max_scene_attempts=3, repair_calls_allowed=4,
            observed_spend_guard_usd="0.15"):
    """Automatically attempt source-bound identity coverage, no manual gate.

    call_model(model=..., prepared={"request": ...}) is an injected provider
    adapter. This function does not itself make a network request.
    It cannot qualify semantic gold, update WorldState or approve events.
    """
    if type(max_scene_attempts) is not int or not (
        1 <= max_scene_attempts <= MAX_SCENE_ATTEMPTS
    ):
        raise CoverageError("V017_SCENE_ATTEMPT_POLICY_INVALID")
    if type(repair_calls_allowed) is not int or not 0 <= repair_calls_allowed <= 4:
        raise CoverageError("V017_REPAIR_ATTEMPT_POLICY_INVALID")
    try:
        cost_limit = Decimal(str(observed_spend_guard_usd))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CoverageError("V017_SPEND_POLICY_INVALID") from exc
    if not cost_limit.is_finite() or cost_limit <= 0:
        raise CoverageError("V017_SPEND_POLICY_INVALID")

    # Verify input/source before establishing an attempt directory.
    request = make_request(prose=prose, world=world, census=census)
    contract = {
        "schema": SCHEMA, "prose_sha256": prose_hash(prose),
        "world_sha256": _hash(world), "census_sha256": _hash(census),
        "request_sha256": request["request_sha256"],
        "primary_model": primary_model, "repair_model": repair_model,
        "max_scene_attempts": max_scene_attempts,
        "repair_calls_allowed": repair_calls_allowed,
        "observed_spend_guard_usd": str(cost_limit),
    }
    output_dir = Path(output_dir)
    if output_dir.exists():
        if _read(output_dir / "contract.json") != contract:
            raise CoverageError("V017_REPLAY_CONTRACT_MISMATCH")
    else:
        output_dir.mkdir(parents=True, exist_ok=False)
        _persist(output_dir / "contract.json", contract)
    final_file = output_dir / "final.json"
    if final_file.is_file():
        return _read(final_file)

    trace = []
    observed_spend = Decimal("0")
    reason = "V017_RECOVERY_ATTEMPTS_EXHAUSTED"
    next_refs = []
    prior_attempt_count = 0

    def finish(status, reason_code):
        output = {
            "schema": SCHEMA, "status": status, "reason_code": reason_code,
            "prose_sha256": contract["prose_sha256"],
            "attempt_count": prior_attempt_count,
            "attempts": deepcopy(trace),
            "provider_reported_total_spend_usd": str(observed_spend),
            "canonical_commit_authorized": False,
            "world_db_writes": 0,
            "requires_manual_intervention": False,
        }
        _persist(final_file, output)
        return output

    for index in range(max_scene_attempts):
        attempt_dir = output_dir / ("attempt_%02d" % (index + 1))
        if observed_spend >= cost_limit:
            reason = "V017_OBSERVED_SPEND_GUARD"
            break
        if attempt_dir.exists():
            if not (attempt_dir / "result.json").is_file():
                reason = "V017_INCOMPLETE_ATTEMPT_AFTER_CRASH"
                break
            stage = _read(attempt_dir / "result.json")
            if stage.get("status") == "STARTED":
                receipts_ok, receipt_error = _receipts_complete(attempt_dir)
                if not receipts_ok:
                    reason = receipt_error
                    break
                try:
                    stage = _recover_completed_provider_receipts(
                        attempt_dir=attempt_dir, prose=prose,
                        world=world, census=census,
                    )
                except (CoverageError, ValueError, TypeError, KeyError):
                    reason = "V017_ARCHIVED_REBIND_FAILED_SAFE"
                    break
        else:
            def provider(*, model, prepared):
                # Only for a fresh full-scene re-extraction: prior judgments
                # are hints, NOT ground truth or a manual Mara rules table.
                prepared = deepcopy(prepared)
                payload = prepared["request"]
                if index and next_refs and (
                    payload["messages"] == request["messages"]
                ):
                    payload["messages"].append({
                        "role": "system",
                        "content": (
                            "Automatic source-grounded re-extraction. "
                            "Prior attempt left provisional refs unresolved: "
                            + ", ".join(sorted(next_refs)) +
                            ". Reassess ALL requested refs from the original "
                            "source. Do not copy previous judgments, omit rows, "
                            "invent facts, or claim canonical authority. "
                            "Return one valid JSON object."
                        ),
                    })
                enforce_no_output_token_limit(payload)
                return call_model(model=model, prepared=prepared)
            stage = identity_stage(
                prose=prose, world=world, census=census, call_model=provider,
                output_dir=attempt_dir, primary_model=primary_model,
                repair_model=repair_model,
                repair_calls_allowed=repair_calls_allowed,
            )
        prior_attempt_count = index + 1
        if not isinstance(stage, dict):
            reason = "V017_STAGE_SUMMARY_INVALID"
            break
        receipts_ok, receipt_error = _receipts_complete(attempt_dir)
        if not receipts_ok:
            reason = receipt_error
            trace.append({"attempt": index + 1, "status": stage.get("status"),
                          "receipt_verified": False, "reason": reason})
            break
        try:
            amount = Decimal(str(stage["provider_reported_total_spend_usd"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            reason = "V017_STAGE_SPEND_UNKNOWN"
            break
        if not amount.is_finite() or amount < 0:
            reason = "V017_STAGE_SPEND_INVALID"
            break
        observed_spend += amount
        result = stage.get("result")
        if isinstance(result, dict):
            next_refs = [row.get("entity_ref") for row in
                         result.get("quarantined_proposals", [])
                         if isinstance(row, dict) and
                         isinstance(row.get("entity_ref"), str)]
            if not next_refs and not _ready(stage):
                next_refs = ["UNQUALIFIED_COVERAGE"]
        else:
            next_refs = ["INVALID_PRIMARY_EXTRACTION"]
        trace.append({
            "attempt": index + 1, "status": stage.get("status"),
            "receipt_verified": True,
            "accepted_source_bound_count": (
                result.get("accepted_source_bound_count")
                if isinstance(result, dict) else None),
            "automatic_abstain_count": (
                result.get("automatic_abstain_count")
                if isinstance(result, dict) else None),
            "next_unresolved_refs": sorted(next_refs),
            "provider_reported_spend_usd": str(amount),
            "canonical_commit_authorized": False,
        })
        _persist(output_dir / "progress.json", trace)
        if _ready(stage):
            return finish("IDENTITY_CANDIDATES_READY_NONCANONICAL",
                          "V017_FULL_SOURCE_BOUND_COVERAGE_ONLY")
        # Every completed, receipted failed/partial attempt is automatically
        # routed to a fresh full extraction; never a reviewer queue.

    return finish("FAILED_SAFE_FINAL", reason)
