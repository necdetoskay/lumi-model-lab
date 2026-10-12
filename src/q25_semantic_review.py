"""Offline, evidence-bound Q25 semantic review packet.

Untrusted extractor candidates are never accepted as canon. A reviewer's
self-reported answers are recorded only: identity and independence cannot be
verified from a JSON document. No provider calls, production writes or grants.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from src.q25_entity_candidates import fingerprint
from src.q25_extractor_adapter import materialize_quotes, offline_replay
from src.q25_offline_diagnostic import Strict


CLAIM_GROUPS = (
    ("objects", "entity_proposal", "objects", "mention"),
    ("terminal_relations", "entity_proposal", "terminal_relations", "evidence"),
    ("character_claims", "story_proposal", "character_claims", "evidence"),
    ("goal_claims", "story_proposal", "goal_claims", "evidence"),
    ("obligation_claims", "story_proposal", "obligation_claims", "evidence"),
    ("thread_claims", "story_proposal", "thread_claims", "evidence"),
    ("property_claims", "property_proposal", "claims", "evidence"),
)


class ItemVerdict(Strict):
    claim_id: str = Field(min_length=3)
    semantic_support: Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT", "UNCERTAIN"]
    temporal_scope: Literal["TERMINAL", "EARLIER_ONLY", "UNDETERMINED"]
    epistemic_status: Literal["OBSERVED", "REPORTED", "BELIEF_ONLY", "UNDETERMINED"]
    note: str = Field(min_length=12, max_length=1200)


class ReviewResponse(Strict):
    schema_name: Literal["q25.semantic-review-response.v1"]
    packet_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_label: str = Field(min_length=3, max_length=120)
    verdicts: list[ItemVerdict]


def build_review_packet(*, seed, prose, raw_output, policy):
    """Build an ordered, deterministic review of structurally valid proposals."""
    inputs_before = copy.deepcopy((seed, raw_output, policy))
    result = offline_replay(seed=seed, prose=prose, raw_output=raw_output, policy=policy)
    if result["status"] != "SOURCE_BOUND_CANDIDATES_ONLY":
        raise ValueError("Only source-bound candidate replays can become review packets")
    materialized = materialize_quotes(seed=seed, prose=prose, raw_output=raw_output)
    items = []
    for group, proposal_name, member, evidence_field in CLAIM_GROUPS:
        for idx, claim in enumerate(materialized[proposal_name][member], start=1):
            citations = claim[evidence_field]
            if isinstance(citations, dict):
                citations = [citations]
            identity = dict(group=group, ordinal=idx, claim=claim)
            claim_sha = fingerprint(identity)
            items.append({
                "claim_id": f"{group}:{idx}:{claim_sha[:12]}",
                "group": group,
                "candidate": copy.deepcopy(claim),
                "citations": copy.deepcopy(citations),
                "claim_sha256": claim_sha,
                "status": "PENDING_INDEPENDENT_SEMANTIC_REVIEW",
            })
    assert (seed, raw_output, policy) == inputs_before
    return dict(
        schema="q25.semantic-review-packet.v1",
        seed_sha256=result["coverage"]["seed_sha256"],
        source_sha256=result["coverage"]["source_sha256"],
        raw_output_sha256=result["raw_output_sha256"],
        coverage_counts=result["coverage"]["counts"],
        unresolved_terminal_fields=result["coverage"]["blocking_field_count"],
        candidates=items,
        candidate_count=len(items),
        review_questions=[
            "Does the cited story text semantically entail the proposed claim?",
            "Is this claim true at the END of the story rather than an earlier scene?",
            "Is the cited information observed fact, report or character belief?",
            "Is there contradictory context elsewhere in the full story?",
        ],
        review_status="AWAITING_EXTERNAL_REVIEW",
        semantic_support_certified=False,
        full_story_state_qualified=False,
        state_commit_authorized=False,
        provider_calls=0,
    )


def review_packet_digest(packet):
    if packet.get("schema") != "q25.semantic-review-packet.v1":
        raise ValueError("Unknown review packet")
    return fingerprint(packet)


def record_review(*, packet, response):
    """Record user-supplied judgments, WITHOUT certifying human identity or truth.

    Rejected/missing judgments are not silently interpreted as acceptance.
    Neither full review completion nor every SUPPORTED vote grants state write.
    """
    digest = review_packet_digest(packet)
    review = ReviewResponse.model_validate(response)
    if digest != review.packet_sha256:
        raise ValueError("Review response does not bind the exact packet")
    expected = [x["claim_id"] for x in packet["candidates"]]
    supplied = [v.claim_id for v in review.verdicts]
    if len(supplied) != len(set(supplied)):
        raise ValueError("Duplicate claim review")
    if set(supplied) != set(expected):
        raise ValueError("Missing or unknown claim reviews")
    verdicts = {v.claim_id: v.model_dump(mode="json") for v in review.verdicts}
    counts = {status: sum(1 for r in verdicts.values() if r["semantic_support"] == status)
              for status in ("SUPPORTED", "CONTRADICTED", "INSUFFICIENT", "UNCERTAIN")}
    return {
        "schema": "q25.semantic-review-record.v1",
        "packet_sha256": digest,
        "review_response_sha256": fingerprint(review.model_dump(mode="json")),
        "reviewer_label_unverified": review.reviewer_label,
        "item_count": len(expected),
        "verdicts": [verdicts[x] for x in expected],
        "support_counts": counts,
        "status": "SELF_REPORTED_REVIEW_LABELS_UNVERIFIED",
        "independent_reviewer_authenticated": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "provider_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("seed", "prose-record", "raw-response", "policy"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--review-response", type=Path)
    args = parser.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf8"))
    packet = build_review_packet(
        seed=load(args.seed),
        prose=load(args.prose_record)["text"],
        raw_output=load(args.raw_response),
        policy=load(args.policy),
    )
    output = (record_review(packet=packet, response=load(args.review_response))
              if args.review_response else packet)
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
