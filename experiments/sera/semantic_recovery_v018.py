"""SERA v0.18 — unattended semantic-risk probe and recovery stage.

Runs independent, exact-source-bound semantic probes with automatic format
fallback, durable per-task paid receipts and machine-only dispositions.
The stage NEVER treats agreement as truth, patches prose, registers entities
or authorizes WorldState/EventGraph commits. No output token ceilings.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.semantic_risks_v011 import (
    audit_risks, make_task_request, bind_task_response,
)
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.unattended-semantic-recovery.v0.18"


def _digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def _save(path, value):
    temp = path.with_suffix(".pending")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CoverageError("V018_SAVED_PROOF_UNREADABLE") from exc


def _cost(raw):
    usage = raw.get("usage") if isinstance(raw, dict) else None
    if not isinstance(usage, dict) or usage.get("cost") is None:
        raise CoverageError("V018_PROVIDER_COST_MISSING")
    try:
        result = Decimal(str(usage["cost"]))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise CoverageError("V018_PROVIDER_COST_INVALID") from exc
    if not result.is_finite() or result < 0:
        raise CoverageError("V018_PROVIDER_COST_INVALID")
    return result


def _verify_receipt(data, *, model, request_digest):
    if not isinstance(data, dict) or (
        data.get("request_sha256") != request_digest
        or data.get("model_requested") != model
    ):
        raise CoverageError("V018_RECEIPT_REQUEST_MISMATCH")
    body = data.get("response")
    if not isinstance(body, dict):
        raise CoverageError("V018_RECEIPT_PROVIDER_BODY_MISSING")
    _cost(body)
    return body


def _bind(*, audit, request, response):
    if response.get("choices") is None or not isinstance(
        response["choices"], list
    ) or len(response["choices"]) != 1:
        raise CoverageError("V018_PROVIDER_CHOICES_INVALID")
    choice = response["choices"][0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise CoverageError("V018_PROVIDER_INCOMPLETE")
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise CoverageError("V018_PROVIDER_TEXT_MISSING")
    raw_text = message["content"].strip()
    if raw_text.startswith("```"):
        fence = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```", raw_text)
        if fence is None:
            raise CoverageError("V018_PROVIDER_JSON_FENCE_INVALID")
        raw_text = fence.group(1)
    try:
        parsed = json.loads(raw_text)
    except ValueError as exc:
        raise CoverageError("V018_PROVIDER_JSON_INVALID") from exc
    return bind_task_response(audit=audit, request=request, raw=parsed)


def execute(*, prose, extraction_report, call_model, output_dir,
            primary_model="anthropic/claude-haiku-4.5",
            fallback_model="anthropic/claude-haiku-4.5",
            max_provider_calls=12, observed_spend_guard_usd="0.10",
            reconciler=None):
    """call_model(model=..., prepared={'request': ...}) -> provider envelope."""
    if reconciler is not None and not callable(reconciler):
        raise CoverageError("V030_SEMANTIC_RECONCILER_INVALID")
    if type(max_provider_calls) is not int or not 0 <= max_provider_calls <= 20:
        raise CoverageError("V018_CALL_POLICY_INVALID")
    try:
        limit = Decimal(str(observed_spend_guard_usd))
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise CoverageError("V018_SPEND_POLICY_INVALID") from exc
    if not limit.is_finite() or limit <= 0:
        raise CoverageError("V018_SPEND_POLICY_INVALID")
    audit = audit_risks(prose=prose, report=extraction_report)
    tasks = audit["targeted_tasks"]
    # Demand complete task IDs and prevent filename traversal or duplication.
    task_ids = [x["task_id"] for x in tasks]
    if len(set(task_ids)) != len(task_ids) or any(
        not isinstance(t, str) or not t.startswith("task_") or
        not t[5:].isdigit() for t in task_ids
    ):
        raise CoverageError("V018_TASK_SET_INVALID")
    contract = {
        "schema": SCHEMA, "source_prose_sha256": prose_hash(prose),
        "report_sha256": _digest(extraction_report),
        "audit_sha256": _digest(audit),
        "models": [primary_model, fallback_model],
        "max_provider_calls": max_provider_calls,
        "observed_spend_guard_usd": str(limit),
    }
    root = Path(output_dir)
    if root.exists():
        if _load(root / "contract.json") != contract:
            raise CoverageError("V018_INPUT_OR_POLICY_CHANGED")
    else:
        root.mkdir(parents=True, exist_ok=False)
        _save(root / "contract.json", contract)
    final = root / "final.json"
    if final.is_file():
        return _load(final)

    entries = []
    spent = Decimal("0")
    calls = 0
    reason = None
    def finish(status, failure=None):
        result = {
            "schema": SCHEMA, "status": status, "failure_code": failure,
            "source_prose_sha256": contract["source_prose_sha256"],
            "source_event_count": audit["candidate_event_count"],
            "semantic_risk_count": audit["targeted_task_count"],
            "completed_advisory_tasks": len(entries),
            "provider_calls": calls,
            "observed_spend_usd": str(spent),
            "independent_advisories": deepcopy(entries),
            "advisory_sha256": _digest(entries),
            "unresolved_tasks": task_ids[len(entries):],
            "next_automatic_action": (
                "AUTO_EVENT_REEXTRACTION_OR_SCENE_REPLAN"
                if status == "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL"
                else "NO_AUTOMATIC_ACTION_REQUIRED_AT_THIS_RISK_GATE"
                if status == "NO_TARGETED_RISKS_FOUND_NONCANONICAL"
                else "TERMINAL_SAFE_FAILURE"
            ),
            "requires_manual_intervention": False,
            "canonical_commit_authorized": False,
            "world_db_writes": 0,
        }
        _save(final, result)
        return result

    for task in tasks:
        task_id = task["task_id"]
        request = make_task_request(audit=audit, task_id=task_id)
        digest = request["request_sha256"]
        # Blind review is based on source context, never prior model opinion.
        payload = {
            "messages": request["messages"],
            "response_format": {"type": "json_object"},
        }
        enforce_no_output_token_limit(payload)
        bound = None
        for round_index, model in enumerate((primary_model, fallback_model)):
            suffix = sha256(task_id.encode("utf-8")).hexdigest()[:24]
            receipt_path = root / f"receipt_{suffix}_{round_index}.json"
            started_path = root / f"started_{suffix}_{round_index}.json"
            if receipt_path.is_file():
                # Replayed paid attempts still consume the original budget.
                # Never reset counted provider calls after worker restart.
                calls += 1
                try:
                    body = _verify_receipt(
                        _load(receipt_path), model=model, request_digest=digest,
                    )
                except CoverageError as exc:
                    reason = str(exc)
                    break
                spent += _cost(body)
            elif started_path.exists():
                calls += 1
                # Zero replayed POSTs: only independently attested OpenRouter
                # known-generation GETs can recover charged model text.
                if reconciler is None:
                    reason = "V018_UNCONFIRMED_IN_FLIGHT_CALL"
                    break
                from experiments.sera.openrouter_reconciliation_v030 import fingerprint
                try:
                    envelope = reconciler(
                        model=model, request=payload,
                        request_sha256=fingerprint(model=model, request=payload),
                    )
                    body = envelope.get("raw") if isinstance(envelope, dict) else None
                    if not isinstance(body, dict):
                        raise CoverageError("V030_SEMANTIC_RECOVERY_BODY_INVALID")
                    _save(receipt_path, {
                        "model_requested": model,
                        "request_sha256": digest, "response": body,
                    })
                    spent += _cost(body)
                except CoverageError as exc:
                    reason = str(exc)
                    break
            else:
                if calls >= max_provider_calls or spent >= limit:
                    reason = "V018_CALL_OR_SPEND_GUARD"
                    break
                _save(started_path, {
                    "task_id": task_id, "request_sha256": digest,
                    "model": model,
                })
                calls += 1
                try:
                    envelope = call_model(
                        model=model, prepared={"request": deepcopy(payload)},
                    )
                except Exception:
                    reason = "V018_PROVIDER_FAILED_UNRECEIPTED"
                    break
                body = envelope.get("raw") if isinstance(envelope, dict) else None
                if not isinstance(body, dict):
                    reason = "V018_PROVIDER_FAILED_UNRECEIPTED"
                    break
                # Archive the provider envelope BEFORE schema binding.
                _save(receipt_path, {
                    "model_requested": model,
                    "request_sha256": digest, "response": body,
                })
                try:
                    spent += _cost(body)
                except CoverageError as exc:
                    reason = str(exc)
                    break
            if body.get("model") != model:
                reason = "V018_PROVIDER_MODEL_MISMATCH"
                break
            try:
                bound = _bind(audit=audit, request=request, response=body)
                break
            except (CoverageError, TypeError, ValueError):
                # A completed paid but malformed response can receive an
                # automatically routed independent fallback. Never invent
                # evidence or silently accept its opinion as canon.
                if round_index == 1:
                    reason = "V018_BOTH_RESPONSES_UNQUALIFIED"
        if reason:
            break
        if bound is None:
            reason = "V018_TASK_UNBOUND"
            break
        entries.append(bound)
        _save(root / "progress.json", entries)

    if reason is not None:
        return finish("FAILED_SAFE_FINAL", reason)
    if not tasks:
        return finish("NO_TARGETED_RISKS_FOUND_NONCANONICAL")
    return finish("SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL")
