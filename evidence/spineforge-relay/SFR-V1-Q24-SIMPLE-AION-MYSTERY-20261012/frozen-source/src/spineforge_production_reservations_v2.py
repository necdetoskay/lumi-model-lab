"""Versioned shared admission with between-call spend thresholds, no output cap.

No checkout-local fallback, implicit grant creation, provider retry or lease
expiry. An uncertain dispatch keeps the entire reservation held. The registry
is a separate branch so unrelated feature commits cannot overwrite its ledger.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
import uuid
from threading import Lock
from decimal import Decimal
from typing import Literal
import requests
from pydantic import Field, field_validator, model_validator
from src.spineforge_relay_v1_contracts import StrictModel, canonical_sha256

REGISTRY_BRANCH = "sfr-paid-reservations"


class ReservationError(RuntimeError):
    pass


def money(value):
    if isinstance(value, bool):
        raise ReservationError("Invalid spend")
    try:
        amount = Decimal(str(value))
    except Exception:
        raise ReservationError("Invalid spend") from None
    if not amount.is_finite() or amount < 0:
        raise ReservationError("Invalid spend")
    return amount


class PaidScopeV2(StrictModel):
    id: str = Field(min_length=1)
    preflight_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_calls: int = Field(gt=0, strict=True)
    max_cost_usd: Decimal = Field(gt=0, allow_inf_nan=False)
    budget_policy: Literal["BETWEEN_CALLS"] = "BETWEEN_CALLS"
    allowed_models: list[str] = Field(min_length=1)

    @field_validator("max_cost_usd", mode="before")
    @classmethod
    def valid_money(cls, value):
        return money(value)


class PaidGrantV2(StrictModel):
    id: str = Field(min_length=1)
    approval_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_calls: int = Field(gt=0, strict=True)
    max_cost_usd: Decimal = Field(gt=0, allow_inf_nan=False)
    scopes: list[PaidScopeV2] = Field(min_length=1)

    @field_validator("max_cost_usd", mode="before")
    @classmethod
    def valid_money(cls, value):
        return money(value)

    @model_validator(mode="after")
    def unique_scopes(self):
        if len({s.id for s in self.scopes}) != len(self.scopes):
            raise ValueError("Duplicate paid scope")
        for scope in self.scopes:
            if scope.max_calls > self.max_calls or scope.max_cost_usd > self.max_cost_usd:
                raise ValueError("Scope exceeds grant")
        return self


class PaidLedgerV2(StrictModel):
    schema_name: Literal["spineforge-relay.paid-ledger.v2"] = "spineforge-relay.paid-ledger.v2"
    grant: PaidGrantV2
    status: Literal["OPEN", "CLOSED"]
    # Reservation keys are approved scope IDs, never per-machine output paths.
    reservations: dict[str, dict] = Field(default_factory=dict)
    closure: dict = Field(default_factory=dict)


class GitHubLedgerStoreV2:
    """Contents API blob-SHA CAS. Any non-success/uncertain write is denial."""
    def __init__(self, *, repository: str, token: str, session=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not token:
            raise ReservationError("Shared repository/credential required")
        self.base = "https://api.github.com/repos/" + repository
        self.session = session or requests.Session()
        self.headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"}

    def _request(self, method, endpoint, **kwargs):
        try:
            response = self.session.request(method, self.base + endpoint, headers=self.headers, timeout=30, **kwargs)
        except Exception:
            raise ReservationError("Shared authority unavailable or write uncertain; no retry") from None
        if response.status_code not in (200, 201):
            raise ReservationError("Shared authority denied operation: HTTP " + str(response.status_code))
        try:
            return response.json()
        except Exception:
            raise ReservationError("Invalid shared authority response") from None

    @staticmethod
    def path(grant_id):
        return "/contents/authorizations/" + hashlib.sha256(grant_id.encode("utf-8")).hexdigest() + ".json"

    def read(self, grant_id):
        raw = self._request("GET", self.path(grant_id), params={"ref": REGISTRY_BRANCH})
        try:
            payload = json.loads(base64.b64decode(raw["content"], validate=False))
            ledger = PaidLedgerV2.model_validate(payload)
            if ledger.grant.id != grant_id or not re.fullmatch(r"[0-9a-f]{40}", raw["sha"]):
                raise ValueError()
            return raw["sha"], ledger
        except Exception:
            raise ReservationError("Invalid shared ledger") from None

    def write(self, grant_id, expected_sha, ledger):
        data = (json.dumps(ledger.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        body = {"branch": REGISTRY_BRANCH, "message": "Reserve/settle approved Relay scope", "content": base64.b64encode(data).decode("ascii")}
        if expected_sha is not None:
            body["sha"] = expected_sha
        raw = self._request("PUT", self.path(grant_id), json=body)
        expected_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if raw.get("content", {}).get("sha") != expected_blob:
            raise ReservationError("Shared write confirmation mismatch; no dispatch")
        return expected_blob


def reserve(store, *, grant_id, scope_id, preflight, executor_id):
    version, ledger = store.read(grant_id)
    if not isinstance(ledger,PaidLedgerV2) or preflight.get('config',{}).get('budget_policy')!='BETWEEN_CALLS':
        raise ReservationError('Fresh v2 authority and between-call policy required')
    if ledger.status != "OPEN" or scope_id in ledger.reservations:
        raise ReservationError("Authorization closed or scope already consumed")
    scopes = {s.id: s for s in ledger.grant.scopes}
    scope = scopes.get(scope_id)
    if scope is None or scope.preflight_sha256 != canonical_sha256(preflight):
        raise ReservationError("Scope/preflight not approved by shared authority")
    cost, calls = Decimal(0), 0
    for key, row in ledger.reservations.items():
        if key not in scopes or row.get("status") not in {"RESERVED", "UNCERTAIN", "SETTLED"}:
            raise ReservationError("Invalid shared reservation")
        if row["status"] == "SETTLED":
            cost += money(row["actual_cost_usd"])
            count = row["actual_calls"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ReservationError("Invalid shared call count")
            calls += count
        else:
            cost += scopes[key].max_cost_usd
            calls += scopes[key].max_calls
    if cost + scope.max_cost_usd > ledger.grant.max_cost_usd or calls + scope.max_calls > ledger.grant.max_calls:
        raise ReservationError("Shared budget/call ceiling exhausted")
    lease = {"token": uuid.uuid4().hex, "executor_id": executor_id, "status": "RESERVED",
             "preflight_sha256": scope.preflight_sha256, "grant_sha256": canonical_sha256(ledger.grant)}
    ledger.reservations[scope_id] = lease
    # The SHA CAS must succeed before returning any dispatch capability.
    store.write(grant_id, version, ledger)
    return scope, lease


def run_reserved(*, store, grant_id, scope_id, preflight, executor_id, invoke, transport):
    """Invoke a bounded runner with its only provider transport centrally gated."""
    scope, lease = reserve(store, grant_id=grant_id, scope_id=scope_id, preflight=preflight, executor_id=executor_id)
    observed, poisoned = [], False
    dispatch_lock = Lock()
    def guarded_call(**kwargs):
        nonlocal poisoned
        if poisoned or len(observed) >= scope.max_calls or kwargs.get("model") not in scope.allowed_models:
            poisoned = True
            raise ReservationError("Reserved transport scope/call ceiling")
        try:
            _, current = store.read(grant_id)
            current_lease = current.reservations.get(scope_id, {})
            if (current.status != "OPEN" or current_lease.get("status") != "RESERVED"
                    or current_lease.get("token") != lease["token"]
                    or canonical_sha256(current.grant) != lease["grant_sha256"]):
                raise ReservationError("Shared authorization revoked or changed")
        except Exception:
            poisoned = True
            raise
        if kwargs.get("max_tokens") is not None:
            raise ReservationError("Between-call policy requires no local output token cap")
        spent = sum((money(r["cost"]) for r in observed if r is not None), Decimal(0))
        if spent >= scope.max_cost_usd:
            raise ReservationError("Between-call budget threshold reached; no dispatch")
        observed.append(None)  # Unknown dispatch spends the full held reservation.
        try:
            from src.spineforge_relay_v1_lease_context import reserved_transport_call
            with reserved_transport_call(kwargs):
                result = transport(**kwargs)
            usage = result[1]["usage"]
            amount = money(usage["cost"])
            for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if isinstance(usage[name], bool) or not isinstance(usage[name], int) or usage[name] < 0:
                    raise ReservationError("Missing/invalid provider usage")
            if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
                raise ReservationError("Inconsistent provider token usage")
            observed[-1] = {"cost": str(amount)}
            return result
        except Exception:
            poisoned = True
            raise
    def call(**kwargs):
        nonlocal poisoned
        if not dispatch_lock.acquire(blocking=False):
            poisoned = True
            raise ReservationError("Concurrent transport on one reservation is denied")
        try:
            return guarded_call(**kwargs)
        finally:
            dispatch_lock.release()
    failure = None
    result = None
    try:
        result = invoke(call)
    except Exception as exc:
        failure = exc
    # Even if a runner caught a transport failure, missing usage cannot free funds.
    version, ledger = store.read(grant_id)
    row = ledger.reservations.get(scope_id, {})
    if row.get("token") != lease["token"] or canonical_sha256(ledger.grant) != lease["grant_sha256"]:
        raise ReservationError("Shared lease identity changed")
    if any(r is None for r in observed):
        row["status"] = "UNCERTAIN"
    else:
        total=sum((money(r["cost"]) for r in observed), Decimal(0))
        row.update(status="SETTLED", actual_calls=len(observed), actual_cost_usd=str(total), budget_threshold_exceeded=total>scope.max_cost_usd, provider_spend_cap_guaranteed=False)
    store.write(grant_id, version, ledger)
    if failure is not None:
        raise failure
    if poisoned and any(r is None for r in observed):
        raise ReservationError("Reserved execution remains uncertain; no retry")
    return result
