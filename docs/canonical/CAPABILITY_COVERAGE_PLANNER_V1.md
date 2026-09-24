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

Provider-access and provider-transport failures are retained as operational evidence but are excluded from both current and historical capability density. A quota/auth/rate-limit/network failure therefore does not make a cell THIN, PROVISIONAL, failed, anomalous, or sentinel-eligible. Unknown terminal failures remain fail-closed capability failures.

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

## Sentinel repeat lane

A pure `UNKNOWN > THIN` expansion rule can leave a suspicious successful cell
unrepeated for too long. v1 therefore reserves **at most one** sentinel-repeat
slot per batch.

A THIN or PROVISIONAL current-protocol cell is sentinel-eligible only when
its **latest** governed run is anomalous. A run is anomalous when any of these
is true:

- the run failed;
- its final semantic-judge minimum is `<= 3`;
- it required at least 2 semantic repairs.

Aggregate failure, judge and repair history remains visible in the candidate
record and priority diagnostics, but an older anomaly does not keep a cell in
the sentinel lane forever. When a single anomalous run is followed by a clean
governed repeat, the planner records `SENTINEL_RESOLVED_BY_CLEAN_REPEAT` and
releases the sentinel slot unless the fixture-diversity escalation rules below
still apply.

The sentinel occupies its age-tier slot in the age-balanced first pass. This
keeps total age coverage balanced while allowing one bounded repeat to resolve
uncertainty. All other slots remain normal coverage expansion.

The sentinel lane is diagnostic only. It cannot change acceptance thresholds,
trigger model-specific tuning, or promote a route by itself.

The first real sentinel selected by this rule is
`MIDDLE_CHILD × emotional_development` after its initial v3 run passed final
quality gates but required 3 semantic repairs across 9 scene attempts.

## Fixture-diversity escalation guard

Repeating one frozen benchmark fixture is useful for separating stochastic
variance from a one-off bad run, but repeated sampling of the same fixture can
become benchmark overfitting.

A current-protocol run is anomalous for this guard when any of the existing
sentinel conditions is true at run level:

- the run is not accepted;
- final semantic-judge minimum is `<= 3`;
- the run required at least 2 semantic repairs.

The planner tracks both distinct current spec fingerprints and distinct
anomalous spec fingerprints.

Escalation rules:

1. two or more anomalous runs with only one distinct current spec fingerprint
   -> `DIAGNOSTIC_FIXTURE_REQUIRED`;
2. anomalous runs observed on two or more distinct spec fingerprints
   -> `TARGETED_INTERVENTION_CANDIDATE`.

Cells in either escalation state are excluded from automatic same-fixture
qualification matrices. The planner reports them separately instead.

`DIAGNOSTIC_FIXTURE_REQUIRED` means the next evidence must come from a second
frozen premise with the same governed axes. It does **not** authorize a prompt
or runtime-policy change.

`TARGETED_INTERVENTION_CANDIDATE` means the anomaly generalized across
fixtures and a controlled intervention experiment may be designed. It still
does not authorize direct production tuning; the intervention must pass the
same-cell diagnostic set and regression controls before promotion.

The first real cell to exercise this guard is
`ADULT × puzzle_problem_solving`: two independent v3 runs on the same frozen
spec both passed final judge 4/4 but each required two semantic repairs. The
planner therefore requests a second diagnostic fixture rather than repeating
that benchmark again.

The `MIDDLE_CHILD × puzzle_problem_solving` sequence demonstrates the clean
repeat release rule: its first v3 observation required four semantic repairs,
while the next governed repeat required zero. The earlier anomaly remains in
the Capability Cube, but that clean latest repeat closes automatic sentinel
eligibility unless a new anomalous run appears.

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
