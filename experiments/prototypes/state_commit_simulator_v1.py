from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

PROTOCOL = "state-commit-simulator.v1"

SET_MUTATIONS = {
    "WORLD_HYPOTHESIS_SET",
    "WORLD_FACT_SET",
    "CHARACTER_GOAL_COMPLETE",
    "OPPORTUNITY_CONSUME",
}
APPEND_MUTATIONS = {
    "CHARACTER_KNOWLEDGE_ADD",
    "THREAD_RESOLVE",
    "THREAD_OPEN",
    "MEMORY_CANDIDATE_ADD",
}


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def state_hash(state: dict[str, Any]) -> str:
    return canonical_hash(state)


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fingerprint_entity(entity_ref: str, entity: dict[str, Any]) -> str:
    payload = {
        "entity_ref": entity_ref,
        "entity_kind": entity.get("entity_kind"),
        "revision": entity.get("revision"),
        "values": entity.get("values") or {},
    }
    return canonical_hash(payload)


def allowed_contract(
    authority: dict[str, Any],
) -> tuple[dict[tuple[str, str, str], dict[str, Any]], list[str]]:
    errors: list[str] = []
    allowed: dict[tuple[str, str, str], dict[str, Any]] = {}

    for index, row in enumerate(authority.get("allowed_mutations") or []):
        if not isinstance(row, dict):
            errors.append(f"authority_allowed_{index}_not_object")
            continue
        key = (
            str(row.get("mutation_type") or ""),
            str(row.get("entity_ref") or ""),
            str(row.get("field_key") or ""),
        )
        if not all(key):
            errors.append(f"authority_allowed_{index}_invalid")
            continue
        allowed[key] = row

    return allowed, errors


def validate_commit(
    *,
    state: dict[str, Any],
    authority: dict[str, Any],
    outcome: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    errors: list[str] = []
    conflicts: list[str] = []

    if not idempotency_key.strip():
        errors.append("idempotency_key_missing")

    authority_revision = str(authority.get("revision") or "")
    if outcome.get("authority_revision") != authority_revision:
        errors.append("authority_revision_mismatch")

    allowed, authority_errors = allowed_contract(authority)
    errors.extend(authority_errors)

    authority_entities = {
        str(row.get("entity_ref")): row
        for row in authority.get("entities") or []
        if isinstance(row, dict) and row.get("entity_ref")
    }

    entities = state.get("entities")
    if not isinstance(entities, dict):
        errors.append("state_entities_missing")
        entities = {}

    mutations = outcome.get("mutations")
    if not isinstance(mutations, list):
        errors.append("outcome_mutations_missing")
        mutations = []

    for index, mutation in enumerate(mutations):
        if not isinstance(mutation, dict):
            errors.append(f"mutation_{index}_not_object")
            continue

        mutation_type = str(mutation.get("mutation_type") or "")
        entity_ref = str(mutation.get("entity_ref") or "")
        field_key = str(mutation.get("field_key") or "")
        key = (mutation_type, entity_ref, field_key)

        contract = allowed.get(key)
        if contract is None:
            errors.append(f"mutation_{index}_not_authorized")
            continue

        expected_epistemic = contract.get("epistemic_class")
        if expected_epistemic and mutation.get("epistemic_class") != expected_epistemic:
            errors.append(f"mutation_{index}_epistemic_class_mismatch")

        auth_entity = authority_entities.get(entity_ref)
        state_entity = entities.get(entity_ref)
        if not isinstance(auth_entity, dict):
            errors.append(f"mutation_{index}_authority_entity_missing")
            continue
        if not isinstance(state_entity, dict):
            conflicts.append(f"mutation_{index}_state_entity_missing")
            continue

        auth_revision = auth_entity.get("expected_revision")
        auth_fingerprint = auth_entity.get("expected_fingerprint")
        base_revision = mutation.get("base_revision")
        base_fingerprint = mutation.get("base_fingerprint")

        if base_revision != auth_revision:
            errors.append(f"mutation_{index}_base_revision_authority_mismatch")
        if base_fingerprint != auth_fingerprint:
            errors.append(f"mutation_{index}_base_fingerprint_authority_mismatch")

        if state_entity.get("revision") != base_revision:
            conflicts.append(
                f"mutation_{index}_stale_revision:"
                f"{state_entity.get('revision')}!={base_revision}"
            )
        if state_entity.get("fingerprint") != base_fingerprint:
            conflicts.append(f"mutation_{index}_stale_fingerprint")

        evidence = mutation.get("evidence_scenes")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"mutation_{index}_evidence_missing")

        if mutation_type not in SET_MUTATIONS | APPEND_MUTATIONS:
            errors.append(f"mutation_{index}_unsupported_operation:{mutation_type}")

    return {
        "valid": not errors and not conflicts,
        "errors": errors,
        "conflicts": conflicts,
    }


def apply_mutation(entity: dict[str, Any], mutation: dict[str, Any]) -> None:
    mutation_type = str(mutation["mutation_type"])
    field_key = str(mutation["field_key"])
    value = copy.deepcopy(mutation.get("value"))
    values = entity.setdefault("values", {})

    if mutation_type in SET_MUTATIONS:
        values[field_key] = value
        return

    if mutation_type in APPEND_MUTATIONS:
        current = values.get(field_key)
        if current is None:
            current = []
            values[field_key] = current
        if not isinstance(current, list):
            raise RuntimeError(f"append_target_not_list:{field_key}")
        if value not in current:
            current.append(value)
        return

    raise RuntimeError(f"unsupported_mutation_type:{mutation_type}")


def commit(
    *,
    state: dict[str, Any],
    authority: dict[str, Any],
    outcome: dict[str, Any],
    idempotency_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    before = copy.deepcopy(state)
    before_hash = state_hash(before)
    outcome_hash = canonical_hash(outcome)

    journal = state.setdefault("commit_journal", {})
    prior = journal.get(idempotency_key)
    if isinstance(prior, dict):
        if prior.get("outcome_hash") == outcome_hash:
            return state, {
                "protocol": PROTOCOL,
                "status": "IDEMPOTENT_REPLAY",
                "idempotency_key": idempotency_key,
                "outcome_hash": outcome_hash,
                "state_hash_before": before_hash,
                "state_hash_after": before_hash,
                "mutated_entities": [],
                "errors": [],
                "conflicts": [],
            }
        return state, {
            "protocol": PROTOCOL,
            "status": "IDEMPOTENCY_COLLISION",
            "idempotency_key": idempotency_key,
            "outcome_hash": outcome_hash,
            "state_hash_before": before_hash,
            "state_hash_after": before_hash,
            "mutated_entities": [],
            "errors": ["idempotency_key_reused_with_different_outcome"],
            "conflicts": [],
        }

    validation = validate_commit(
        state=state,
        authority=authority,
        outcome=outcome,
        idempotency_key=idempotency_key,
    )
    if not validation["valid"]:
        return state, {
            "protocol": PROTOCOL,
            "status": "CONFLICT" if validation["conflicts"] else "REJECTED",
            "idempotency_key": idempotency_key,
            "outcome_hash": outcome_hash,
            "state_hash_before": before_hash,
            "state_hash_after": before_hash,
            "mutated_entities": [],
            "errors": validation["errors"],
            "conflicts": validation["conflicts"],
        }

    working = copy.deepcopy(state)
    touched: set[str] = set()

    try:
        for mutation in outcome["mutations"]:
            entity_ref = str(mutation["entity_ref"])
            entity = working["entities"][entity_ref]
            apply_mutation(entity, mutation)
            touched.add(entity_ref)

        for entity_ref in sorted(touched):
            entity = working["entities"][entity_ref]
            entity["revision"] = int(entity["revision"]) + 1
            entity["fingerprint"] = fingerprint_entity(entity_ref, entity)

        after_without_journal = copy.deepcopy(working)
        after_without_journal.setdefault("commit_journal", {}).pop(idempotency_key, None)
        commit_state_hash = state_hash(after_without_journal)

        working.setdefault("commit_journal", {})[idempotency_key] = {
            "outcome_hash": outcome_hash,
            "mutated_entities": sorted(touched),
            "post_commit_state_hash": commit_state_hash,
        }
    except Exception as exc:
        return before, {
            "protocol": PROTOCOL,
            "status": "ABORTED",
            "idempotency_key": idempotency_key,
            "outcome_hash": outcome_hash,
            "state_hash_before": before_hash,
            "state_hash_after": before_hash,
            "mutated_entities": [],
            "errors": [f"apply_failed:{type(exc).__name__}:{exc}"],
            "conflicts": [],
        }

    after_hash = state_hash(working)
    return working, {
        "protocol": PROTOCOL,
        "status": "COMMITTED",
        "idempotency_key": idempotency_key,
        "outcome_hash": outcome_hash,
        "state_hash_before": before_hash,
        "state_hash_after": after_hash,
        "mutated_entities": sorted(touched),
        "errors": [],
        "conflicts": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--authority", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--output-state", required=True)
    parser.add_argument("--output-result", required=True)
    args = parser.parse_args()

    state = load_json(args.state)
    authority = load_json(args.authority)
    outcome = load_json(args.outcome)

    committed_state, result = commit(
        state=state,
        authority=authority,
        outcome=outcome,
        idempotency_key=args.idempotency_key,
    )

    Path(args.output_state).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_state).write_text(
        json.dumps(committed_state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_result).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
