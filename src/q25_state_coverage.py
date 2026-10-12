"""Q25 conservative, deterministic terminal-state coverage audit.

The input story claims are annotations, not machine-verified truth.
No seed mutation, provider dispatch, state commit or narrative acceptance.
"""
import copy
import json

from src.q25_entity_candidates import fingerprint
from src.q25_state_admission import build_draft
from src.q25_story_evidence import extend_draft
from src.q25_terminal_properties import property_candidates


def ptr(*parts):
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)



def compare_seed_to_candidates(*, seed, draft, property_claims, coverage_rows, entity_proposal):
    """Read-only seed-to-terminal-candidate diff; no claim is a verified state write."""
    object_changes = []
    relations = entity_proposal.get("terminal_relations", [])
    def relation_quotes(subject):
        return [r["evidence"] for r in relations
                if r["subject"] == "object:" + subject and r["kind"] == "IN_CONTAINER"]

    for object_id, original in sorted(seed["objects"].items()):
        state = original.get("state", {})
        candidate = draft["objects"][object_id]
        for field in ("container", "contains"):
            if field not in state:
                continue
            before = state[field]
            after = (candidate["container"]["ref"] if candidate["container"]["status"] == "KNOWN"
                     else None) if field == "container" else candidate["contains"]
            if before != after:
                quotes = relation_quotes(object_id)
                if field == "contains":
                    quotes = [q for nested in state[field] + after for q in relation_quotes(nested)]
                object_changes.append(dict(
                    path=ptr("objects", object_id, field), seed_value=before,
                    candidate_terminal_value=after, evidence=quotes,
                    disposition="STRUCTURAL_CANDIDATE_NOT_SEMANTICALLY_CERTIFIED"))
    for key, claim in sorted(property_claims.items()):
        object_id, field = key
        object_changes.append(dict(
            path=ptr("objects", object_id, "properties", field),
            seed_value=seed["objects"][object_id]["state"][field],
            candidate_terminal_value=claim["proposed_terminal_value"],
            evidence=claim["evidence"],
            disposition="SOURCE_BOUND_CANDIDATE_NOT_SEMANTICALLY_CERTIFIED"))
    character_changes = []
    for claim in draft["proposed_character_changes"]:
        actor, field = claim["actor"], claim["field"]
        initial = seed["characters"][actor]
        if field == "knowledge":
            before = list(initial["knowledge"])
        elif field in ("emotion", "health"):
            before = initial["condition"][field]
        elif field == "relationship_trust":
            before = initial["relationships"][claim["other_actor"]]["trust"]
        else:
            before = initial["location"]
        character_changes.append(dict(
            actor=actor, field=field, other_actor=claim.get("other_actor"),
            seed_value=before, candidate_terminal_value=claim["value"],
            epistemic_type=claim.get("epistemic_type"),
            evidence=[claim["evidence"]],
            disposition="PARTIAL_KNOWLEDGE_CANDIDATE" if field == "knowledge"
                        else "SOURCE_BOUND_CANDIDATE_NOT_SEMANTICALLY_CERTIFIED"))

    goal_changes = []
    for claim in draft["proposed_goal_outcomes"]:
        goal_changes.append(dict(
            actor=claim["actor"],
            seed_goal=seed["characters"][claim["actor"]]["condition"]["goal"],
            proposed_outcome=claim["outcome"], evidence=claim["evidence"],
            disposition="CANDIDATE_NOT_SEMANTICALLY_CERTIFIED"))

    obligation_by_id = {c["obligation_id"]: c for c in draft["proposed_narrative_obligations"]}
    obligations = []
    for item in seed.get("narrative_obligations", []):
        proposal = obligation_by_id.get(item["id"])
        obligations.append(dict(
            obligation_id=item["id"], seed_status=item["status"],
            proposed_outcome=proposal["outcome"] if proposal else None,
            evidence=proposal["evidence"] if proposal else [],
            disposition="PENDING_INDEPENDENT_SEMANTIC_REVIEW" if proposal else "UNASSESSED"))

    thread_by_id = {c["thread_id"]: c for c in draft["proposed_thread_outcomes"]}
    threads = []
    for item in seed.get("open_threads", []):
        proposal = thread_by_id.get(item)
        threads.append(dict(
            thread_id=item, seed_status="OPEN",
            proposed_outcome=proposal["outcome"] if proposal else None,
            evidence=proposal["evidence"] if proposal else [],
            disposition="PENDING_INDEPENDENT_SEMANTIC_REVIEW" if proposal else "UNASSESSED"))

    missing = [dict(path=r["path"], status=r["status"], note=r["note"])
               for r in coverage_rows if r["status"] in ("UNKNOWN", "UNASSESSED", "PARTIAL_CANDIDATES")]
    proposed_new = [dict(object_id=k, owner=v["owner"], location=v["location"],
                         identity_status="PROPOSED")
                    for k, v in sorted(draft["objects"].items()) if v["identity_status"] == "PROPOSED"]
    return dict(
        schema="q25.seed-candidate-comparison.v1",
        acceptance="NOT_ACCEPTED_INCOMPLETE",
        object_changes=object_changes,
        new_object_candidates=proposed_new,
        character_changes=character_changes,
        goal_outcomes=goal_changes,
        narrative_obligations=obligations,
        proposed_closed_obligations=[o["obligation_id"] for o in obligations
                                      if o["proposed_outcome"] == "SATISFIED"],
        independently_certified_closed_obligations=[],
        contested_or_unverified_obligations=[o["obligation_id"] for o in obligations],
        open_threads=threads,
        explicit_gaps=missing,
        world_time=dict(seed_value=seed.get("world", {}).get("time"),
                        candidate_terminal_value=None, disposition="UNASSESSED"),
        state_commit_authorized=False,
    )


def coverage_report(*, seed, prose, entity_proposal, policy, story_proposal, property_proposal=None):
    """Rebuild the full Q25 candidate lineage and identify every unresolved slot."""
    original = copy.deepcopy(seed)
    admission = build_draft(seed=seed, prose=prose, proposal=entity_proposal, policy=policy)
    extension = extend_draft(
        seed=seed, prose=prose, admission_result=admission,
        entity_proposal=entity_proposal, policy=policy,
        story_proposal=story_proposal,
    )
    draft = extension["draft_state"]
    property_view = (property_candidates(seed=seed, prose=prose,
        entity_proposal=entity_proposal, policy=policy, proposal=property_proposal)
        if property_proposal is not None else None)
    property_claims = ({(c['object_id'], c['property_name']): c
        for c in property_view['proposed_properties']} if property_view else {})
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
            property_claim = property_claims.get((object_id, field))
            row(ptr(*base, "properties", field), "OBJECT_PROPERTY",
                "CANDIDATE" if property_claim else "UNASSESSED",
                "Source-bound terminal change is only a candidate; initial property remains unchanged"
                if property_claim else "Initial property copied from seed; terminal value is unverified",
                property_claim["evidence"] if property_claim else [])
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
        **({"property_proposal_sha256": property_view["proposal_sha256"]} if property_view else {}),
        coverage="INCOMPLETE_REQUIRES_SEMANTIC_ADJUDICATION_AND_EXTRACTION",
        fields=rows, counts=counts,
        initial_to_candidate_comparison=compare_seed_to_candidates(
            seed=seed, draft=draft, property_claims=property_claims,
            coverage_rows=rows, entity_proposal=entity_proposal),
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
    parser.add_argument("--property-proposal", type=Path)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding="utf8"))
    result = coverage_report(
        seed=read(args.seed), prose=read(args.prose_record)["text"],
        entity_proposal=read(args.entity_proposal), policy=read(args.policy),
        story_proposal=read(args.story_proposal),
        property_proposal=read(args.property_proposal) if args.property_proposal else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
