"""Q25 read-only source-bound terminal *property* candidates.

Literal source support is necessary but not sufficient for semantic truth.
This adapter never mutates StoryState, authorizes persistence, or certifies a claim.
"""
import copy
import json
from typing import Literal

from pydantic import Field

from src.q25_entity_candidates import fingerprint
from src.q25_offline_diagnostic import Strict, Span, digest, valid_span
from src.q25_state_admission import build_draft


class PropertyClaim(Strict):
    object_id: str = Field(min_length=1)
    property_name: str = Field(min_length=1)
    expected_seed_value: bool | int | float | str | None
    proposed_terminal_value: bool | int | float | str | None
    evidence_kind: Literal["OBSERVED_ACTION", "REPORTED", "INFERRED"]
    evidence: list[Span] = Field(min_length=1)


class TerminalPropertyProposal(Strict):
    schema_name: Literal["q25.terminal-property-proposal.v1"] = "q25.terminal-property-proposal.v1"
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    claims: list[PropertyClaim]


def property_candidates(*, seed, prose, entity_proposal, policy, proposal):
    """Validate candidate property assignments against seed and cited source.

    Existing *seed-defined scalar* properties only; new properties, container,
    identity, ownership, locations and non-scalar schema changes are excluded.
    """
    before_seed = copy.deepcopy(seed)
    before_entities = copy.deepcopy(entity_proposal)
    before_policy = copy.deepcopy(policy)
    parsed = TerminalPropertyProposal.model_validate(proposal)
    if parsed.seed_sha256 != fingerprint(seed) or parsed.source_sha256 != digest(prose):
        raise ValueError("Terminal property proposal does not bind frozen seed/prose")
    admitted = build_draft(seed=seed, prose=prose, proposal=entity_proposal, policy=policy)
    if admitted["structural_admission"] != "ELIGIBLE_DRAFT" or admitted["draft_state"] is None:
        raise ValueError("Cannot propose terminal attributes on blocked entity graph")
    objects = seed.get("objects", {})
    proposed = []
    seen = set()
    for claim in parsed.claims:
        ident = (claim.object_id, claim.property_name)
        if ident in seen:
            raise ValueError("Multiple terminal values for the same object property")
        seen.add(ident)
        if claim.object_id not in objects:
            raise ValueError("New or unknown object property needs independent admission")
        raw = objects[claim.object_id].get("state", {})
        if claim.property_name not in raw or claim.property_name in ("container", "contains"):
            raise ValueError("Only existing non-relational properties are eligible")
        old = raw[claim.property_name]
        new = claim.proposed_terminal_value
        expected = claim.expected_seed_value
        scalars = (str, int, float, bool, type(None))
        if (type(old) not in scalars or type(expected) is not type(old)
                or type(new) is not type(old)):
            raise ValueError("Unsupported property type, or unsafe type conversion")
        if expected != old:
            raise ValueError("Property precondition contradicts immutable seed")
        if new == old:
            raise ValueError("No-op terminal claim cannot certify a preserved value")
        previous_start = -1
        occupied = set()
        for span in claim.evidence:
            if not valid_span(prose, parsed.source_sha256, span):
                raise ValueError("Invalid terminal property evidence")
            if span.start <= previous_start or (span.start, span.end) in occupied:
                raise ValueError("Duplicate or unordered terminal property citations")
            occupied.add((span.start, span.end))
            previous_start = span.start
        # No semantic adjudication: claims remain proposals even if citations match.
        proposed.append(claim.model_dump(mode="json"))
    assert seed == before_seed and entity_proposal == before_entities and policy == before_policy
    return {
        "schema": "q25.terminal-property-candidates.v1",
        "base_seed_sha256": parsed.seed_sha256,
        "source_sha256": parsed.source_sha256,
        "proposal_sha256": fingerprint(parsed.model_dump(mode="json")),
        "status": "SOURCE_BOUND_CANDIDATES_NOT_SEMANTICALLY_VERIFIED",
        "proposed_properties": proposed,
        "state_commit_authorized": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "provider_calls": 0,
    }


def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("seed", "prose-record", "entity-proposal", "policy", "property-proposal"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding="utf8"))
    result = property_candidates(
        seed=read(args.seed), prose=read(args.prose_record)["text"],
        entity_proposal=read(args.entity_proposal), policy=read(args.policy),
        proposal=read(args.property_proposal),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
