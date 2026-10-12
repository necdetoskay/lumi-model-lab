"""Read-only Q25 character, goal, thread and obligation evidence projection.

This validates *annotated proposals*, not automatic semantic extraction or final
StoryState. Literal citations are necessary but cannot certify factual support.
"""
import copy
import json
from typing import Literal

from pydantic import Field

from src.q25_entity_candidates import fingerprint
from src.q25_offline_diagnostic import Strict, Span, digest, valid_span
from src.q25_state_admission import build_draft


class CharacterClaim(Strict):
    actor: str = Field(min_length=1)
    field: Literal["emotion", "health", "location", "knowledge", "relationship_trust"]
    value: str = Field(min_length=1)
    evidence: Span
    epistemic_type: Literal["OBSERVED", "REPORTED", "BELIEF", "INFERRED"] | None = None
    other_actor: str | None = None


class GoalClaim(Strict):
    actor: str = Field(min_length=1)
    goal_id: str = Field(min_length=1)
    outcome: Literal["ACHIEVED", "ABANDONED", "BLOCKED"]
    evidence: list[Span] = Field(min_length=1)


class ObligationClaim(Strict):
    obligation_id: str = Field(min_length=1)
    outcome: Literal["SATISFIED", "UNSATISFIED"]
    evidence: list[Span] = Field(min_length=1)


class ThreadClaim(Strict):
    thread_id: str = Field(min_length=1)
    outcome: Literal["RESOLVED", "UNRESOLVED"]
    evidence: list[Span] = Field(min_length=1)


class StoryEvidenceProposal(Strict):
    schema_name: Literal["q25.story-evidence-proposal.v1"] = "q25.story-evidence-proposal.v1"
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    character_claims: list[CharacterClaim] = Field(default_factory=list)
    goal_claims: list[GoalClaim] = Field(default_factory=list)
    obligation_claims: list[ObligationClaim] = Field(default_factory=list)
    thread_claims: list[ThreadClaim] = Field(default_factory=list)


def extend_draft(*, seed, prose, admission_result, entity_proposal, policy, story_proposal):
    """Add explicitly sourced *candidate* terminal story claims to an eligible draft.

    Existing/unknown state remains untouched. No inferred completion, new actor,
    production commit, semantic approval or canonical schema conversion.
    """
    original_seed = copy.deepcopy(seed)
    original_admission = copy.deepcopy(admission_result)
    # Never trust a caller-supplied partial state without replaying the exact
    # structural admission from its frozen source and explicit policy.
    recomputed = build_draft(seed=seed, prose=prose, proposal=entity_proposal, policy=policy)
    if admission_result != recomputed:
        raise ValueError("Admission result differs from deterministic replay")
    proposal = StoryEvidenceProposal.model_validate(story_proposal)
    if proposal.seed_sha256 != fingerprint(seed) or proposal.source_sha256 != digest(prose):
        raise ValueError("Story evidence binding differs from frozen seed/prose")
    draft = admission_result.get("draft_state")
    if admission_result.get("structural_admission") != "ELIGIBLE_DRAFT" or not isinstance(draft, dict):
        raise ValueError("Cannot extend a structurally blocked or missing draft")
    if admission_result.get("state_commit_authorized") is not False:
        raise ValueError("Draft unexpectedly has commit authority")
    if (draft.get("base_seed_sha256") != proposal.seed_sha256
            or draft.get("source_sha256") != proposal.source_sha256
            or draft.get("schema") != "q25.draft-state.v1"):
        raise ValueError("Draft lineage/schema mismatch")
    if draft.get("characters") != seed.get("characters") and not _only_inventory_changed(seed, draft):
        raise ValueError("Draft character seed fields unexpectedly changed")

    characters = seed["characters"]
    obligations = {o["id"]: o for o in seed.get("narrative_obligations", [])}
    if len(obligations) != len(seed.get("narrative_obligations", [])):
        raise ValueError("Duplicate seed narrative obligation")
    threads = seed.get("open_threads", [])
    if len(set(threads)) != len(threads):
        raise ValueError("Duplicate seed thread")

    def check_evidence(spans):
        pairs = set()
        last_start = -1
        for span in spans:
            if not valid_span(prose, proposal.source_sha256, span):
                raise ValueError("Invalid cited prose span")
            pair = (span.start, span.end)
            if pair in pairs or span.start <= last_start:
                raise ValueError("Duplicate or out-of-order supporting evidence")
            pairs.add(pair)
            last_start = span.start

    char_candidates, goal_candidates, obligation_candidates, thread_candidates = [], [], [], []
    scalar_seen, knowledge_seen, goal_seen, obligation_seen, thread_seen = set(), set(), set(), set(), set()
    for item in proposal.character_claims:
        if item.actor not in characters:
            raise ValueError("Unrecognized character; new actors require separate admission")
        check_evidence([item.evidence])
        if item.field == "relationship_trust":
            if item.other_actor not in characters[item.actor].get("relationships", {}):
                raise ValueError("Unrecognized established relationship")
        elif item.other_actor is not None:
            raise ValueError("Unexpected relationship target")
        if item.field == "knowledge":
            if item.epistemic_type is None:
                raise ValueError("Knowledge needs explicit epistemic classification")
            if item.value in characters[item.actor].get("knowledge", []):
                raise ValueError("Cannot relabel seed knowledge as story-acquired")
            key = (item.actor, item.value)
            if key in knowledge_seen:
                raise ValueError("Duplicate knowledge claim")
            knowledge_seen.add(key)
        else:
            if item.epistemic_type is not None:
                raise ValueError("Epistemic classification is only for knowledge claims")
            key = (item.actor, item.field, item.other_actor)
            if key in scalar_seen:
                raise ValueError("Conflicting/multiple terminal character claims")
            scalar_seen.add(key)
            if item.field == "location" and item.value not in seed["topology"]["locations"]:
                raise ValueError("Unapproved location/topology")
        char_candidates.append(item.model_dump(mode="json"))

    for item in proposal.goal_claims:
        if item.actor not in characters or characters[item.actor].get("condition", {}).get("goal") != item.goal_id:
            raise ValueError("Goal must match a known character seed goal")
        if item.actor in goal_seen:
            raise ValueError("Duplicate terminal goal outcome")
        goal_seen.add(item.actor)
        check_evidence(item.evidence)
        goal_candidates.append(item.model_dump(mode="json"))

    for item in proposal.obligation_claims:
        if item.obligation_id not in obligations or obligations[item.obligation_id]["status"] != "OPEN":
            raise ValueError("Only known open obligations may be assessed")
        if item.obligation_id in obligation_seen:
            raise ValueError("Duplicate narrative obligation outcome")
        obligation_seen.add(item.obligation_id)
        check_evidence(item.evidence)
        obligation_candidates.append(item.model_dump(mode="json"))

    for item in proposal.thread_claims:
        if item.thread_id not in threads:
            raise ValueError("Unknown open narrative thread")
        if item.thread_id in thread_seen:
            raise ValueError("Duplicate thread outcome")
        thread_seen.add(item.thread_id)
        check_evidence(item.evidence)
        thread_candidates.append(item.model_dump(mode="json"))

    extended = copy.deepcopy(draft)
    extended["proposed_character_changes"] = char_candidates
    extended["proposed_goal_outcomes"] = goal_candidates
    extended["proposed_narrative_obligations"] = obligation_candidates
    extended["proposed_thread_outcomes"] = thread_candidates
    extended["narrative_coverage"] = "ANNOTATED_CANDIDATES_ONLY_NOT_COMPLETE"
    extended["full_story_state_qualified"] = False
    extended["semantic_support_certified"] = False
    assert seed == original_seed and admission_result == original_admission
    return dict(
        schema="q25.evidence-extended-draft.v1",
        draft_state=extended,
        story_proposal_sha256=fingerprint(proposal.model_dump(mode="json")),
        structural_admission="ELIGIBLE_DRAFT",
        semantic_support_certified=False,
        full_story_state_qualified=False,
        state_commit_authorized=False,
        independent_semantic_review_required=True,
        unresolved_coverage=[
            "Object terminal properties",
            "All character terminal fields not explicitly annotated",
            "Evidence/epistemic and obligation semantic adjudication",
            "Canonical authority integration",
        ],
        provider_calls=0,
    )


def _only_inventory_changed(seed, draft):
    if set(seed["characters"]) != set(draft["characters"]):
        return False
    return all(
        {k: v for k, v in draft["characters"][name].items() if k != "inventory"}
        == {k: v for k, v in raw.items() if k != "inventory"}
        for name, raw in seed["characters"].items()
    )


def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("seed", "prose-record", "entity-proposal", "policy", "story-proposal"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding="utf8"))
    seed = read(args.seed)
    prose = read(args.prose_record)["text"]
    admission = build_draft(seed=seed, prose=prose,
                            proposal=read(args.entity_proposal), policy=read(args.policy))
    result = extend_draft(seed=seed, prose=prose, admission_result=admission,
                          entity_proposal=read(args.entity_proposal), policy=read(args.policy),
                          story_proposal=read(args.story_proposal))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
