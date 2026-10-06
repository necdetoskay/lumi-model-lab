"""Deterministic state transition engine for SpineForge Relay v1."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.spineforge_relay_v1_contracts import (
    SceneContractV1,
    SceneDeltaV1,
    StateMutation,
    StoryStateV1,
    canonical_sha256,
)


class RelayStateError(RuntimeError):
    """Base class for fail-closed relay state failures."""


class StaleRelayInput(RelayStateError):
    """Raised when an artifact is not bound to the exact current upstream state."""


class InvalidRelayTransition(RelayStateError):
    """Raised when a requested state mutation cannot be applied exactly."""


_PROTECTED_ROOTS = {
    "schema_name",
    "story_id",
    "revision",
    "global_spine_sha256",
    "story_intent_sha256",
}


def _tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise InvalidRelayTransition("State path must be an absolute JSON pointer")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def _index(token: str, *, size: int, allow_end: bool = False) -> int:
    if token == "-" and allow_end:
        return size
    try:
        value = int(token)
    except ValueError as exc:
        raise InvalidRelayTransition(f"Invalid list index: {token}") from exc
    upper = size if allow_end else size - 1
    if value < 0 or value > upper:
        raise InvalidRelayTransition(f"List index out of range: {token}")
    return value


def _parent(root: Any, parts: list[str]) -> tuple[Any, str]:
    if not parts:
        raise InvalidRelayTransition("Root replacement is forbidden")
    current = root
    for token in parts[:-1]:
        if isinstance(current, dict):
            if token not in current:
                raise InvalidRelayTransition(f"Missing state path component: {token}")
            current = current[token]
        elif isinstance(current, list):
            current = current[_index(token, size=len(current))]
        else:
            raise InvalidRelayTransition(f"Cannot traverse scalar state at: {token}")
    return current, parts[-1]


def _read(parent: Any, token: str) -> tuple[bool, Any]:
    if isinstance(parent, dict):
        return token in parent, parent.get(token)
    if isinstance(parent, list):
        if token == "-":
            return False, None
        idx = _index(token, size=len(parent))
        return True, parent[idx]
    raise InvalidRelayTransition("Mutation parent must be a dict or list")


def _apply(parent: Any, token: str, mutation: StateMutation) -> None:
    exists, current = _read(parent, token)

    if mutation.op == "SET":
        if not exists:
            raise InvalidRelayTransition(f"SET target does not exist: {mutation.path}")
        if current != mutation.before:
            raise InvalidRelayTransition(f"SET before-value mismatch: {mutation.path}")
        if isinstance(parent, dict):
            parent[token] = deepcopy(mutation.after)
        else:
            parent[_index(token, size=len(parent))] = deepcopy(mutation.after)
        return

    if mutation.op == "ADD":
        if isinstance(parent, dict):
            if exists:
                raise InvalidRelayTransition(f"ADD target already exists: {mutation.path}")
            parent[token] = deepcopy(mutation.after)
        else:
            idx = _index(token, size=len(parent), allow_end=True)
            parent.insert(idx, deepcopy(mutation.after))
        return

    if mutation.op == "REMOVE":
        if not exists:
            raise InvalidRelayTransition(f"REMOVE target does not exist: {mutation.path}")
        if current != mutation.before:
            raise InvalidRelayTransition(f"REMOVE before-value mismatch: {mutation.path}")
        if isinstance(parent, dict):
            del parent[token]
        else:
            del parent[_index(token, size=len(parent))]
        return

    raise InvalidRelayTransition(f"Unsupported mutation op: {mutation.op}")


def _assert_binding(state: StoryStateV1, delta: SceneDeltaV1, contract: SceneContractV1) -> None:
    current_sha = canonical_sha256(state)
    contract_sha = canonical_sha256(contract)

    if delta.scene_id != contract.scene_id:
        raise StaleRelayInput("Delta/contract scene mismatch")
    if delta.source_state_revision != state.revision:
        raise StaleRelayInput("Delta source revision is stale")
    if delta.source_state_sha256 != current_sha:
        raise StaleRelayInput("Delta source state fingerprint is stale")
    if delta.contract_sha256 != contract_sha:
        raise StaleRelayInput("Delta contract fingerprint is stale")
    if contract.story_state_revision != state.revision:
        raise StaleRelayInput("Contract state revision is stale")
    if contract.story_state_sha256 != current_sha:
        raise StaleRelayInput("Contract state fingerprint is stale")
    if contract.global_spine_sha256 != state.global_spine_sha256:
        raise StaleRelayInput("Contract global spine fingerprint is stale")
    if contract.story_intent_sha256 != state.story_intent_sha256:
        raise StaleRelayInput("Contract story intent fingerprint is stale")


def apply_scene_delta(
    state: StoryStateV1,
    delta: SceneDeltaV1,
    contract: SceneContractV1,
) -> StoryStateV1:
    """Apply one validated scene delta to the exact bound StoryState.

    The function is deliberately strict:
    - exact state/contract fingerprint binding is mandatory;
    - canonical identity fields cannot be mutated;
    - each before-value must match;
    - output is revalidated as StoryStateV1;
    - successful application increments revision exactly once.
    """
    _assert_binding(state, delta, contract)

    payload = deepcopy(state.model_dump(mode="json"))

    for mutation in delta.mutations:
        parts = _tokens(mutation.path)
        if not parts or parts[0] in _PROTECTED_ROOTS:
            raise InvalidRelayTransition(f"Protected state path: {mutation.path}")
        parent, token = _parent(payload, parts)
        _apply(parent, token, mutation)

    payload["revision"] = state.revision + 1

    try:
        return StoryStateV1.model_validate(payload)
    except Exception as exc:
        raise InvalidRelayTransition("Resulting StoryState violates the v1 contract") from exc
