"""Q25 conservative, deterministic terminal-state coverage audit.

The input story claims are annotations, not machine-verified truth.
No seed mutation, provider dispatch, state commit or narrative acceptance.
"""
import copy
import json

from src.q25_entity_candidates import fingerprint
from src.q25_state_admission import build_draft
from src.q25_story_evidence import extend_draft


def ptr(*parts):
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def coverage_report(*, seed, prose, entity_proposal, policy, story_proposal):
    """Rebuild the full Q25 candidate lineage and identify every unresolved slot."""
    original = copy.deepcopy(seed)
    admission = build_draft(seed=seed, prose=prose, proposal=entity_proposal, policy=policy)
    extension = extend_draft(
        seed=seed, prose=prose, admission_result=admission,
        entity_proposal=entity_proposal, policy=policy,
        story_proposal=story_proposal,
    )
    draft = extension["draft_state"]
    rows = []
    seen = set()

    def row(path, category, status, note, evidence=None):
        if path in seen:
            raise ValueError("Duplicate coverage field")
        seen.add(path)
        rows.append(dict(path=path, category=category, status=status,
                         note=note, evidence=evidence or []))

    objects = draft["objects"]
    for object_id, obj in sorted(objects.items()):
        base = ("objects", object_id)
        for field in ("owner", "location"):
            state = obj[field]["status"]
            if state == "UNKNOWN":
                row(ptr(*base, field), "OBJECT", "UNKNOWN",
                    "Explicitly unresolved; no owner/location inferred")
            else:
                row(ptr(*base, field), "OBJECT", "STRUCTURAL_ONLY",
                    "Copied/derived relationship; not semantically certified at story end")
        for field in ("container", "held_by", "contains"):
            row(ptr(*base, field), "OBJECT", "STRUCTURAL_ONLY",
                "Relation consistency only, not independent semantic verification")
        for field in sorted(obj.get("properties", {})):
            row(ptr(*base, "properties", field), "OBJECT_PROPERTY", "UNASSESSED",
                "Initial property copied from seed; terminal value is unverified")
        if obj["identity_status"] == "PROPOSED":
            row(ptr(*base, "identity_status"), "ENTITY_ADMISSION", "CANDIDATE",
                "New ordinary object structurally eligible only; semantic role unresolved")

    character_claims = draft["proposed_character_changes"]
    goal_claims = {c["actor"]: c for c in draft["proposed_goal_outcomes"]}
    for actor, raw in sorted(draft["characters"].items()):
        actor_claims = [c for c in character_claims if c["actor"] == actor]
        for field, path in (
            ("health", ptr("characters", actor, "condition", "health")),
            ("emotion", ptr("characters", actor, "condition", "emotion")),
            ("location", ptr("characters", actor, "location")),
        ):
            claims = [c for c in actor_claims if c["field"] == field]
            row(path, "CHARACTER", "CANDIDATE" if claims else "UNASSESSED",
                "Cited but not independently adjudicated" if claims else "Seed value only; terminal state not extracted",
                [c["evidence"] for c in claims])
        know = [c for c in actor_claims if c["field"] == "knowledge"]
        row(ptr("characters", actor, "knowledge"), "CHARACTER_KNOWLEDGE",
            "PARTIAL_CANDIDATES" if know else "UNASSESSED",
            "These citations cannot prove exhaustive terminal character knowledge",
            [c["evidence"] for c in know])
        for other in sorted(raw.get("relationships", {})):
            claims = [c for c in actor_claims
                      if c["field"] == "relationship_trust" and c.get("other_actor") == other]
            row(ptr("characters", actor, "relationships", other, "trust"),
                "RELATIONSHIP", "CANDIDATE" if claims else "UNASSESSED",
                "Relationship state requires semantic evaluation",
                [c["evidence"] for c in claims])
        goal = goal_claims.get(actor)
        row(ptr("characters", actor, "condition", "goal"), "GOAL",
            "CANDIDATE" if goal else "UNASSESSED",
            "Proposed completion does not certify true achievement",
            goal["evidence"] if goal else [])

    obligations = {c["obligation_id"]: c for c in draft["proposed_narrative_obligations"]}
    for obligation in seed.get("narrative_obligations", []):
        claim = obligations.get(obligation["id"])
        row(ptr("narrative_obligations", obligation["id"], "status"), "NARRATIVE_OBLIGATION",
            "CANDIDATE" if claim else "UNASSESSED",
            "Cited obligation completion is not independently adjudicated",
            claim["evidence"] if claim else [])
    threads = {c["thread_id"]: c for c in draft["proposed_thread_outcomes"]}
    for thread in seed.get("open_threads", []):
        claim = threads.get(thread)
        row(ptr("open_threads", thread), "OPEN_THREAD",
            "CANDIDATE" if claim else "UNASSESSED",
            "Cited thread closure is not independently adjudicated",
            claim["evidence"] if claim else [])

    if "time" in seed.get("world", {}):
        row(ptr("world", "time"), "WORLD_TIME", "UNASSESSED",
            "No inferred elapsed minutes or free time reset")
    counts = {k: sum(1 for r in rows if r["status"] == k)
              for k in ("CANDIDATE", "PARTIAL_CANDIDATES", "STRUCTURAL_ONLY", "UNASSESSED", "UNKNOWN")}
    assert seed == original
    return dict(
        schema="q25.story-state-coverage.v1",
        seed_sha256=fingerprint(seed),
        source_sha256=draft["source_sha256"],
        story_proposal_sha256=extension["story_proposal_sha256"],
        coverage="INCOMPLETE_REQUIRES_SEMANTIC_ADJUDICATION_AND_EXTRACTION",
        fields=rows, counts=counts,
        blocking_field_count=len(rows),
        state_commit_authorized=False,
        full_story_state_qualified=False,
        narrative_acceptance="UNVERIFIED",
        semantic_support_certified=False,
        required_next_checks=[
            "Independent semantic evidence/role adjudication",
            "Terminal generic object-property extraction",
            "Exhaustive character/knowledge/relationship assessment",
            "World time and location consistency",
            "Canonical authority integration",
        ],
        provider_calls=0,
    )


def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("seed", "prose-record", "entity-proposal", "policy", "story-proposal"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding="utf8"))
    result = coverage_report(
        seed=read(args.seed), prose=read(args.prose_record)["text"],
        entity_proposal=read(args.entity_proposal), policy=read(args.policy),
        story_proposal=read(args.story_proposal),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
