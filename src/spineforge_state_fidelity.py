"""Offline comparison of reviewer-observed end-state facts with recorded state.

Observations are semantic assertions supplied by a reviewer, not extracted or
proved by this module. Source binding proves provenance, not interpretation or
completeness. This audit never edits state or overrides historical acceptance.
"""
import re
from typing import Any, Literal
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel, canonical_sha256
from src.spineforge_production_source_ranges import range_table


class EndStateObservation(StrictModel):
    state_pointer: str = Field(pattern=r"^/(characters|objects|world)/.+")
    observed_value: Any
    source_range_id: str = Field(min_length=1)


class StateFidelityReview(StrictModel):
    schema_name: Literal["spineforge.state-fidelity-review.v1"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1)
    observations: list[EndStateObservation]


def _read(root, pointer):
    if re.search(r"~(?![01])", pointer):
        raise ValueError("Malformed state pointer")
    current = root
    for encoded in pointer[1:].split("/"):
        # Reject malformed RFC 6901 escapes and ambiguous list indexes.
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                return False, None
            current = current[token]
        elif isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ValueError("Invalid state list index")
            index = int(token)
            if index >= len(current):
                return False, None
            current = current[index]
        else:
            return False, None
    return True, current


def audit_state_fidelity(*, prose, state, review):
    review = StateFidelityReview.model_validate(review)
    table = range_table(prose)
    if review.source_sha256 != table["source_sha256"]:
        raise ValueError("Stale prose binding")
    if review.state_sha256 != canonical_sha256(state):
        raise ValueError("Stale state binding")
    choices = {row[0]: row[1:] for row in table["ranges"]}
    findings, seen = [], set()
    for observation in review.observations:
        pointer = observation.state_pointer
        if pointer in seen:
            raise ValueError("Duplicate end-state observation")
        seen.add(pointer)
        if observation.source_range_id not in choices:
            raise ValueError("Unknown source range")
        first, last = choices[observation.source_range_id]
        quote = prose[table["spans"][first]["start"]:table["spans"][last]["end"]]
        exists, actual = _read(state, pointer)
        if not exists or canonical_sha256(actual) != canonical_sha256(observation.observed_value):
            findings.append(dict(code="PROSE_STATE_DIVERGENCE",state_pointer=pointer,
                recorded_exists=exists,recorded_value=actual,
                observed_value=observation.observed_value,exact_text=quote,
                source_range_id=observation.source_range_id))
    return dict(schema="spineforge.state-fidelity-audit.v1",
        status="FINDINGS_PRESENT" if findings else "NO_OBSERVED_DIVERGENCE",
        source_sha256=review.source_sha256,state_sha256=review.state_sha256,
        reviewer=review.reviewer,observation_count=len(review.observations),
        findings=findings,semantic_completeness_verified=False,
        retrospective_repair=False)
