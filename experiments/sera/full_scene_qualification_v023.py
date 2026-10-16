"""SERA v0.23 — noncanonical full-scene coverage + authority quarantine.

Deterministic qualification AFTER v0.10/0.18 source-bound extraction,
v0.19 semantic risk projection and v0.20 typed facet simulation.
Prevents a successful *partial* openable/document simulation from being
mistaken for complete physical/causal/epistemic event coverage.

A qualified scene remains NONCANONICAL. No human review dependency, no
WorldState/EventGraph writes, no interpretation of model confidence as truth,
no artificial output token cap or scene-specific Mara condition.
"""
from __future__ import annotations

from collections import Counter

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.world_state_v02 import validate as validate_world
from experiments.sera.artifact_scene_checker_v021 import digest

SCHEMA = "sera.full-scene-qualification.v0.23"
# These are stateful operations v0.13 CANNOT currently simulate safely.
UNSUPPORTED_MUTATIONS = frozenset({
    "MOVE", "TRANSFER", "CHANGE_STATE", "KNOWLEDGE_UPDATE",
    "LEARN_FACT", "DISCOVER",
})
TYPED_EFFECTS = {
    "OPEN": frozenset({"OBSERVE_OPENABLE", "SET_OPENABLE"}),
    "CLOSE": frozenset({"SET_OPENABLE"}),
    "WRITE": frozenset({"APPEND_DOCUMENT_ENTRY"}),
}
NONOBJECTIVE = frozenset({
    "REPORTED_CLAIM", "HYPOTHESIS", "NEGATED", "UNCERTAIN",
})
SERIOUS_FINDING_PREFIXES = (
    "SWEEP_UNACCOUNTED_ACTION_CUE:",
    "SWEEP_MISSING_ENTITY_HINT:",
    "SWEEP_UNRESOLVED_SENTENCE:",
    "SWEEP_UNMAPPED_EVENT:",
    "SWEEP_CLAIM_PROMOTED_TO_WORLD:",
    "SWEEP_DISPOSITION_EVENT_CONFLICT:",
    "SWEEP_EVENT_DISPOSITION_CONFLICT:",
    "SWEEP_EXPECTED_EVENT_NOT_EXTRACTED:",
    "SWEEP_POSSIBLY_MISCLASSIFIED:",
)


def _ensure(ok, code):
    if not ok:
        raise CoverageError(code)


def qualify(*, prose, world, bundle, projection, typed):
    validate_world(world)
    _ensure(isinstance(bundle, dict) and
            bundle.get("schema") == "sera.recheck-evidence-bundle.v0.21" and
            bundle.get("prose_sha256") == prose_hash(prose) and
            bundle.get("world_sha256") == digest(world),
            "V023_BUNDLE_SOURCE_OR_WORLD_MISMATCH")
    report = bundle.get("extraction_report")
    _ensure(isinstance(report, dict) and
            report.get("schema") == "sera.blind-sweep-bound.v0.10" and
            report.get("source_prose_sha256") == prose_hash(prose) and
            report.get("canonical_commit_authorized") is False and
            report.get("world_state_writes") == 0 and
            report.get("sentences_accounted_for") == len(sentences(prose)),
            "V023_SOURCE_SWEEP_INCOMPLETE")
    _ensure(isinstance(projection, dict) and
            projection.get("schema") == "sera.event-candidate-repair.v0.19" and
            projection.get("prose_sha256") == prose_hash(prose) and
            projection.get("original_report_sha256") == digest(report) and
            projection.get("canonical_commit_authorized") is False and
            projection.get("world_db_writes") == 0 and
            isinstance(typed, dict) and
            typed.get("schema") == "sera.typed-aspect-candidate-recovery.v0.20" and
            typed.get("prose_sha256") == prose_hash(prose) and
            typed.get("world_sha256") == digest(world) and
            typed.get("original_candidates_sha256") ==
                digest(bundle.get("typed_candidates")) and
            typed.get("canonical_commit_authorized") is False and
            typed.get("world_db_writes") == 0,
            "V023_UPSTREAM_CHECK_SOURCE_OR_AUTHORITY_MISMATCH")
    events = report.get("candidate_events")
    candidates = bundle.get("typed_candidates")
    _ensure(isinstance(events, list) and isinstance(candidates, list),
            "V023_EVENTS_MISSING")
    sid_set = {s["id"] for s in sentences(prose)}
    known = world["entities"]
    defects = []
    counters = Counter()

    def flag(code, *, event_id=None, sentence_id=None):
        row = {"code": code}
        if event_id is not None:
            row["event_id"] = event_id
        if sentence_id is not None:
            row["sentence_id"] = sentence_id
        defects.append(row)
        counters[code] += 1

    # v0.26 takes priority over independent v0.24/v0.25 previews
    # only when both families occur, no typed facets are involved, and
    # application-owned full temporal + relation policies exist.
    spatial = None
    spatial_failure = None
    relation_preview = None
    relation_failure = None
    ordered_preview = None
    ordered_failure = None
    ordered_facet_preview = None
    ordered_facet_failure = None
    moving = [e for e in events if isinstance(e, dict) and
              e.get("kind") == "MOVE" and
              e.get("effect") in ("WORLD", "OBJECT")]
    relational = [e for e in events if isinstance(e, dict) and
                  e.get("kind") in ("TRANSFER", "LEARN_FACT",
                                   "KNOWLEDGE_UPDATE") and
                  e.get("effect") in (
                      "WORLD", "OBJECT", "CHARACTER_KNOWLEDGE",
                  )]
    joint_facets = bool(moving and relational and candidates and
                        bundle.get("temporal_case") is not None and
                        bundle.get("relation_case") is not None)
    joint = bool(moving and relational and
                 bundle.get("temporal_case") is not None and
                 bundle.get("relation_case") is not None)
    if joint_facets:
        from experiments.sera.ordered_facet_preview_v027 import preview
        try:
            ordered_facet_preview = preview(
                prose=prose, world=world,
                extraction_report=report,
                temporal_case=bundle["temporal_case"],
                relation_case=bundle["relation_case"],
                typed_candidates=candidates,
                typed_registry=bundle.get("typed_registry"),
                typed_registry=bundle["typed_registry"],
            )
        except CoverageError as exc:
            ordered_facet_failure = str(exc)
            flag("ORDERED_FACET_CAUSAL_REPLAY_UNQUALIFIED")
    elif joint:
        from experiments.sera.ordered_causal_preview_v026 import preview
        try:
            ordered_preview = preview(
                prose=prose, world=world, extraction_report=report,
                temporal_case=bundle["temporal_case"],
                relation_case=bundle["relation_case"],
                typed_candidates=candidates,
            )
        except CoverageError as exc:
            ordered_failure = str(exc)
            flag("ORDERED_CAUSAL_REPLAY_UNQUALIFIED")
    else:
        if moving and bundle.get("temporal_case") is not None:
            from experiments.sera.spatial_preview_v024 import preview
            try:
                spatial = preview(
                    prose=prose, world=world, extraction_report=report,
                    temporal_case=bundle["temporal_case"],
                )
            except CoverageError as exc:
                spatial_failure = str(exc)
                flag("SPATIAL_SOURCE_OR_ROUTE_UNQUALIFIED")
        if relational and bundle.get("relation_case") is not None:
            from experiments.sera.relation_knowledge_preview_v025 import preview
            try:
                relation_preview = preview(
                    prose=prose, world=world, extraction_report=report,
                    relation_case=bundle["relation_case"],
                )
            except CoverageError as exc:
                relation_failure = str(exc)
                flag("RELATION_OR_KNOWLEDGE_SOURCE_UNQUALIFIED")
    covered_relations = (
        set(ordered_facet_preview["covered_relation_ids"])
        if ordered_facet_preview is not None else
        set(ordered_preview["covered_relation_ids"])
        if ordered_preview is not None else
        {x["event_id"] for x in relation_preview["transitions"]}
        if relation_preview is not None else set()
    )
    covered_movements = (
        set(ordered_facet_preview["covered_movement_ids"])
        if ordered_facet_preview is not None else
        set(ordered_preview["covered_movement_ids"])
        if ordered_preview is not None else
        {x["source_event_id"] for x in spatial["transitions"]}
        if spatial is not None else set()
    )
    seen = set()
    for event in events:
        _ensure(isinstance(event, dict) and
                isinstance(event.get("event_id"), str) and
                event["event_id"] not in seen and
                event.get("sentence_id") in sid_set and
                type(event.get("start")) is int and
                type(event.get("end")) is int and
                0 <= event["start"] < event["end"] <= len(prose) and
                prose[event["start"]:event["end"]] == event.get("quote") and
                isinstance(event.get("entity_refs"), list),
                "V023_EVENT_SOURCE_BINDING_INVALID")
        seen.add(event["event_id"])
        ident, sid = event["event_id"], event["sentence_id"]
        kind, effect = event.get("kind"), event.get("effect")
        refs = event["entity_refs"]
        _ensure(all(isinstance(x, str) and x for x in refs),
                "V023_EVENT_ENTITY_REF_INVALID")
        if kind == "UNMAPPED" or effect == "UNKNOWN":
            flag("UNMAPPED_OR_UNKNOWN_EFFECT", event_id=ident, sentence_id=sid)
        if event.get("epistemic") in NONOBJECTIVE and effect in (
            "WORLD", "OBJECT", "DOCUMENT",
        ):
            flag("NONOBJECTIVE_CLAIM_HAS_PHYSICAL_EFFECT",
                 event_id=ident, sentence_id=sid)
        if (kind in UNSUPPORTED_MUTATIONS and effect not in (
            "NONE", "UNKNOWN",
        ) and not (kind == "MOVE" and ident in covered_movements)
          and not (kind in ("TRANSFER", "LEARN_FACT",
                            "KNOWLEDGE_UPDATE") and
                   ident in covered_relations)
          and not (kind == "CHANGE_STATE" and
                   ordered_facet_preview is not None and
                   any(step["source_event_id"] == ident and
                       step["kind"] == "SET_OPENABLE"
                       for step in ordered_facet_preview["steps"]))):
            flag("STATE_EFFECT_WITHOUT_QUALIFIED_REDUCER",
                 event_id=ident, sentence_id=sid)
        # A physical event must have a known, active, registered object /
        # character. Mentions such as new:train never become world truth.
        if effect in ("OBJECT", "WORLD", "DOCUMENT"):
            if not refs or any(
                ref not in known or
                known[ref].get("lifecycle") != "ACTIVE"
                for ref in refs
            ):
                flag("PHYSICAL_EFFECT_UNREGISTERED_OR_PROVISIONAL_REF",
                     event_id=ident, sentence_id=sid)
        if kind in TYPED_EFFECTS and effect in ("OBJECT", "DOCUMENT"):
            if not any(
                typed_row.get("type") in TYPED_EFFECTS[kind] and
                typed_row.get("sentence_id") == sid and
                isinstance(typed_row.get("evidence"), dict) and
                type(typed_row["evidence"].get("start")) is int and
                type(typed_row["evidence"].get("end")) is int and
                typed_row["evidence"]["start"] < event["end"] and
                event["start"] < typed_row["evidence"]["end"]
                for typed_row in candidates if isinstance(typed_row, dict)
            ):
                flag("PHYSICAL_EFFECT_NOT_REDUCER_COVERED",
                     event_id=ident, sentence_id=sid)

    # The separately prompted typed-facet model must never create an
    # actual state effect omitted by the independent sentence sweep.
    # Evidence overlap and known object role alone cannot prove that a
    # physical operation happened; missing cross-model event coverage is
    # an automatic re-extraction/replan blocker, not a human adjudication.
    acceptable_kinds = {
        "OBSERVE_OPENABLE": frozenset({"OBSERVE", "OPEN"}),
        "SET_OPENABLE": frozenset({"CLOSE", "OPEN", "CHANGE_STATE"}),
        "APPEND_DOCUMENT_ENTRY": frozenset({"WRITE"}),
    }
    for item in candidates:
        _ensure(isinstance(item, dict) and
                item.get("type") in acceptable_kinds and
                isinstance(item.get("evidence"), dict),
                "V023_TYPED_CANDIDATE_INVALID")
        source_evidence = item["evidence"]
        _ensure(type(source_evidence.get("start")) is int and
                type(source_evidence.get("end")) is int and
                0 <= source_evidence["start"] <
                source_evidence["end"] <= len(prose) and
                prose[source_evidence["start"]:source_evidence["end"]] ==
                    source_evidence.get("quote"),
                "V023_TYPED_CANDIDATE_SOURCE_INVALID")
        if not any(
            row["sentence_id"] == item["sentence_id"] and
            row["kind"] in acceptable_kinds[item["type"]] and
            row["start"] < source_evidence["end"] and
            source_evidence["start"] < row["end"]
            for row in events
        ):
            flag("TYPED_OPERATION_NOT_BACKED_BY_INDEPENDENT_SWEEP",
                 event_id=item["event_id"],
                 sentence_id=item.get("sentence_id"))

    # v0.10 already validates source provenance and lexical cues. A
    # suspicious source finding cannot disappear because v0.19 only
    # audits targeted semantic risks.
    for issue in report.get("findings", []):
        _ensure(isinstance(issue, str), "V023_SWEEP_FINDINGS_INVALID")
        if issue.startswith(SERIOUS_FINDING_PREFIXES):
            flag("SOURCE_COMPLETENESS_OR_DISPOSITION_DEFECT")
    if projection.get("remaining_semantic_task_codes") or \
       projection.get("unsupported_semantic_tasks") or \
       projection.get("temporal_failure"):
        flag("UNRESOLVED_SOURCE_SEMANTIC_OR_TIME_DEFECT")
    facet_status = typed.get("status")
    if facet_status == "NO_APPLICABLE_TYPED_FACETS_NONCANONICAL":
        roles = bundle.get("typed_registry")
        _ensure(isinstance(roles, dict) and
                roles == {"openables": [], "documents": []} and
                candidates == [] and
                typed.get("empty_facet_scope_requires_full_gate") is True,
                "V024_EMPTY_FACET_COVERAGE_FORGED")
    if facet_status == "DEFERRED_TO_V027_ORDERED_FACETS_NONCANONICAL":
        _ensure(typed.get("ordered_facet_scope_requires_full_gate") is True,
                "V027_DEFERRED_FACET_AUTHORITY_INVALID")
        if ordered_facet_preview is None:
            flag("DEFERRED_TYPED_FACETS_NOT_ORDERED")
    if typed.get("blocker_codes") or facet_status not in (
        "TYPED_FACETS_SIMULATED_NONCANONICAL",
        "NO_APPLICABLE_TYPED_FACETS_NONCANONICAL",
        "DEFERRED_TO_V027_ORDERED_FACETS_NONCANONICAL",
    ):
        flag("UNRESOLVED_TYPED_REDUCER_DEFECT")

    # If v0.26 already proved one evolving-state motion+relation replay,
    # it counts as ONE coherent family. Independent v0.13 facets still
    # require a future common reducer and must remain a blocker.
    active_families = (
        1 if ordered_facet_preview is not None else
        1 + bool(candidates) if ordered_preview is not None else
        sum((bool(spatial is not None),
             bool(relation_preview is not None), bool(candidates)))
    )
    if active_families > 1 or (joint_facets and
                                ordered_facet_preview is None):
        flag("CROSS_FAMILY_STATE_ORDER_UNQUALIFIED")

    # Do not invent a trusted temporal schedule. If this source contains
    # movement, a separate location/travel/time reducer is needed.
    # The v0.13 openable/document facet check does not qualify movement.
    status = ("REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL" if defects
              else "FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL")
    return {
        "schema": SCHEMA,
        "prose_sha256": prose_hash(prose),
        "world_sha256": digest(world),
        "status": status,
        "source_sentence_count": len(sentences(prose)),
        "source_event_count": len(events),
        "typed_candidate_count": len(candidates),
        "spatial_preview": spatial,
        "spatial_failure": spatial_failure,
        "relation_preview": relation_preview,
        "relation_failure": relation_failure,
        "ordered_preview": ordered_preview,
        "ordered_failure": ordered_failure,
        "ordered_facet_preview": ordered_facet_preview,
        "ordered_facet_failure": ordered_facet_failure,
        "defects": defects,
        "defect_frequency": dict(sorted(counters.items())),
        "next_automatic_action": (
            "AUTO_REEXTRACT_OR_REPLAN_SCENE" if defects else
            "CONTINUE_INDEPENDENT_CANON_QUALIFICATION"
        ),
        "semantic_truth_proven": False,
        "all_state_types_implemented": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "requires_manual_intervention": False,
    }
