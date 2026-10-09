"""Single-use capability for the exact transport call approved by the broker."""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from src.spineforge_relay_v1_contracts import canonical_sha256

_CAPABILITY = ContextVar("relay_paid_transport_capability", default=None)


class UnreservedRelayTransportError(RuntimeError):
    pass


def signature(kwargs):
    return canonical_sha256({k: v for k, v in kwargs.items() if k != "api_key"})


@contextmanager
def reserved_transport_call(kwargs):
    token = _CAPABILITY.set({"signature": signature(kwargs), "used": False, "lock": Lock()})
    try:
        yield
    finally:
        _CAPABILITY.reset(token)


def require_reserved_transport(kwargs):
    capability = _CAPABILITY.get()
    if capability is None:
        raise UnreservedRelayTransportError("Relay inference requires an exact, single-use shared reservation")
    with capability["lock"]:
        if capability["used"] or capability["signature"] != signature(kwargs):
            raise UnreservedRelayTransportError("Relay transport capability consumed or different")
        capability["used"] = True
