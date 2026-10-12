"""Versioned plan-to-event coverage, without changing historical serializers.

Planner-authored bindings keep original goals visible to both writer and guard.
Local validation proves coverage and references, not semantic goal entailment.
"""
from typing import Literal
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel, ScenePlanV1, SceneContractV1, canonical_sha256, ValidationFinding
from src.spineforge_relay_v1_events import PredicateEvidenceV1

GOAL_FIELDS = ("narrative_purpose", "objective", "turn")


class GoalPredicateV1(StrictModel):
    event_id: str = Field(min_length=1)
    predicate_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)


class PlanObligationV1(StrictModel):
    id: str = Field(min_length=1)
    source_field: Literal["narrative_purpose", "objective", "turn"]
    source_text: str = Field(min_length=1)
    required_predicates: list[GoalPredicateV1] = Field(min_length=1)


class PredicateOrderV1(StrictModel):
    before: GoalPredicateV1
    after: GoalPredicateV1


class PlanCoverageContractV1(StrictModel):
    schema_name: Literal["spineforge-relay.plan-coverage.v1"] = "spineforge-relay.plan-coverage.v1"
    scene_plan_sha256: str
    scene_contract_sha256: str
    obligations: list[PlanObligationV1] = Field(min_length=1)
    ordered_dependencies: list[PredicateOrderV1] = Field(default_factory=list)


def compile_plan_coverage(*, plan: ScenePlanV1, scene: SceneContractV1,
                          obligations: list[PlanObligationV1],
                          ordered_dependencies: list[PredicateOrderV1]) -> PlanCoverageContractV1:
    if scene.scene_plan_sha256 != canonical_sha256(plan) or scene.scene_id != plan.scene_id:
        raise ValueError("Stale plan/scene coverage binding")
    if len({o.id for o in obligations}) != len(obligations):
        raise ValueError("Duplicate plan obligation")
    if sorted(o.source_field for o in obligations) != sorted(GOAL_FIELDS):
        raise ValueError("Every plan goal field requires exactly one explicit obligation")
    predicates = {(e.id, p.id): p for e in scene.required_events for p in e.predicates}
    def check(ref):
        p = predicates.get((ref.event_id, ref.predicate_id))
        if p is None or (ref.subject, ref.action, ref.target) != (p.subject, p.action, p.target):
            raise ValueError("Goal predicate must exactly match a frozen scene predicate")
    covered = set()
    for obligation in obligations:
        if obligation.source_text != getattr(plan, obligation.source_field):
            raise ValueError("Goal text differs from frozen plan")
        keys = [(r.event_id, r.predicate_id) for r in obligation.required_predicates]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate goal predicate")
        for ref in obligation.required_predicates:
            check(ref)
            covered.add((ref.event_id, ref.predicate_id))
    dependencies = set()
    graph = {}
    for dependency in ordered_dependencies:
        check(dependency.before)
        check(dependency.after)
        before = (dependency.before.event_id, dependency.before.predicate_id)
        after = (dependency.after.event_id, dependency.after.predicate_id)
        if before not in covered or after not in covered or before == after or (before, after) in dependencies:
            raise ValueError("Order dependencies must be unique distinct covered predicates")
        dependencies.add((before, after))
        graph.setdefault(before, []).append(after)
    visiting, done = set(), set()
    def visit(node):
        if node in visiting:
            raise ValueError("Cyclic goal ordering")
        if node in done:
            return
        visiting.add(node)
        for child in graph.get(node, []):
            visit(child)
        visiting.remove(node)
        done.add(node)
    for node in graph:
        visit(node)
    return PlanCoverageContractV1(scene_plan_sha256=canonical_sha256(plan), scene_contract_sha256=canonical_sha256(scene),
                                 obligations=obligations, ordered_dependencies=ordered_dependencies)


def evaluate_plan_coverage(*, coverage: PlanCoverageContractV1, plan: ScenePlanV1,
                           scene: SceneContractV1, prose: str,
                           evidence: list[PredicateEvidenceV1]) -> list[ValidationFinding]:
    findings = []
    def block(message):
        findings.append(ValidationFinding(code="PLAN_OBLIGATION", family="contract", severity="BLOCKING", message=message))
    try:
        rebound = compile_plan_coverage(plan=plan, scene=scene, obligations=coverage.obligations,
                                        ordered_dependencies=coverage.ordered_dependencies)
        if rebound != coverage:
            raise ValueError("Coverage fingerprint drift")
    except ValueError as exc:
        block(str(exc))
        return findings
    grouped = {}
    for row in evidence:
        grouped.setdefault((row.event_id, row.predicate_id), []).append(row)
    def anchor(ref):
        rows = grouped.get((ref.event_id, ref.predicate_id), [])
        if len(rows) != 1:
            block("Missing or duplicate goal evidence")
            return None
        row = rows[0]
        if row.verdict != "SUPPORTED" or (row.subject, row.action, row.target) != (ref.subject, ref.action, ref.target):
            block("Unsupported or misattributed goal evidence")
            return None
        if not row.exact_text.strip() or row.exact_text not in prose:
            block("Ungrounded goal evidence")
            return None
        return row.exact_text
    for obligation in coverage.obligations:
        for ref in obligation.required_predicates:
            anchor(ref)
    for dependency in coverage.ordered_dependencies:
        before, after = anchor(dependency.before), anchor(dependency.after)
        if before is None or after is None:
            continue
        if prose.count(before) != 1 or prose.count(after) != 1 or prose.index(before)+len(before) > prose.index(after):
            block("Goal action must visibly precede its dependent action")
    return findings
