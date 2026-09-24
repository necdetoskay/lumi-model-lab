# Adaptive Capability Coverage Planner v1

Status: **Canonical**
Date: 2026-09-24
AEGIS risk: **L2**
Scope: Model Lab qualification scheduling only

## Purpose

The Capability Cube is intentionally larger than the set of cases that should
be executed at once. The planner chooses the next small qualification batch
from existing executable benchmark fixtures without pretending that untested
cells are good, bad, popular, or production-critical.

The planner does not route production traffic and does not change model
runtime policy, prompts, continuity thresholds, semantic-judge thresholds, or
StoryContract rules.

## Canonical coverage spaces

Capability Cube v2 currently defines a canonical STANDARD space of:

`8 NarrativeAgeTiers × 10 NarrativeFamilies = 80 cells`

The executable age-relative wave currently has complete synthetic fixtures for
three families:

- `exploration_mystery`
- `emotional_development`
- `puzzle_problem_solving`

Therefore the current executable scope is:

`8 ages × 3 fixture-backed families = 24 cells`

The remaining 56 canonical STANDARD cells are **OUT_OF_SCOPE_FIXTURE_MISSING**,
not failed qualification cells. The planner must never synthesize an arbitrary
benchmark premise merely to make those cells executable.

## Governed identity

A run only counts as current evidence when all of these match the planner's
current identity:

- generator model id;
- generator runtime-profile SHA;
- generator production-policy SHA;
- generation-protocol SHA;
- continuity-evaluator model;
- semantic-judge model;
- evaluation-protocol version;
- evaluation-stack SHA;
- exact age, reading mode, narrative family, relative length class and target words.

Evidence from an older generation protocol may be used only as historical
burden evidence. It does not increase current coverage.

## Selection order

v1 uses deterministic lexicographic priority rather than an opaque numerical score.

First, current evidence density:

1. `UNKNOWN`
2. `THIN`
3. `PROVISIONAL`
4. `ESTABLISHED`

An `ESTABLISHED` cell is excluded from normal expansion batches.

Second, the first pass protects age balance: at most one case is selected from
each age tier until every eligible age tier has had an opportunity to enter
the batch.

Within an age tier, ties are resolved by:

1. lower active-protocol family age coverage;
2. historical terminal failure presence;
3. higher historical semantic-repair burden;
4. higher historical scene-attempt burden;
5. lower current run count;
6. stable deterministic identifiers.

If the requested batch is larger than the number of represented age tiers,
remaining slots are filled by the same deterministic priority order.

## No invented production-frequency signal

v1 deliberately has no production-frequency weighting.

Real LUMI usage telemetry may later become a separate governed signal, but
until that data exists the planner records:

`production_frequency_weighting = DISABLED_NO_TELEMETRY`

Guessing that one age or story family is “more popular” would distort the
evidence program.

## Outputs

CLI:

`python -m src.capability_coverage plan`

produces:

- `reports/next_qualification_plan.json`
- `reports/next_qualification_plan.md`

The JSON report contains the complete executable candidate set plus the
selected batch and exact governed identity.

`python -m src.capability_coverage matrix`

emits a GitHub Actions matrix containing only the selected cases.

## Self-hosted workflow integration

`Capability Qualification Wave` supports two selection modes:

- `manifest`: execute the entire configured wave;
- `adaptive`: compile the next batch through this planner.

Both modes run only on the self-hosted runner pool. The wave manifest remains
the authority for `max_parallel`.

The adaptive workflow writes the plan into the GitHub step summary before paid
case execution.

## Initial v1 planning result

With `english-story-production.v3` evidence after protocol promotion:

- executable scope: 24 cells;
- observed under active protocol: 5;
- unknown: 19;
- thin: 4;
- provisional: 1;
- established: 0;
- canonical fixture-missing out-of-scope: 56.

The first age-balanced batch selected `emotional_development` across all eight
age tiers because that family had zero active-v3 age coverage while remaining
fully fixture-backed.

This is a coverage decision, not a claim that emotional-development stories
are more important than other families.

## Change control

A planner change requires tests showing deterministic selection and preserved
identity isolation.

The planner must never:

- weaken story acceptance thresholds;
- mutate model runtime profiles;
- merge evidence from different protocol/evaluation identities;
- treat fixture-missing cells as tested;
- infer production popularity without telemetry;
- automatically promote a model or production route.
