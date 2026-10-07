"""Explicit structured fixtures for existing reducer/compiler regression tests."""
from src.spineforge_relay_v1_contracts import RequiredEventSpecV1, EventPredicateV1


def event(actor, action, target):
    return RequiredEventSpecV1(id="E1", actor=actor, action=action, target=target,
        required_observer=None, evidence_mode="DIRECT_OBSERVATION",
        predicates=[EventPredicateV1(id="P1", subject=actor, action=action, target=target)],
        allowed_provenance=["DIRECT_OBSERVATION"],
        forbidden_provenance=["INVENTED_CLUE", "INVENTED_WORLD_RULE", "UNESTABLISHED_LORE"])
