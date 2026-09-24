# Luna v3 Adaptive Sentinel + Expansion Wave — 2026-09-24

Status: **EVIDENCE COMPLETE — 8/8 ACCEPTED**
Workflow run: `35984545658`
Generator: `openai/gpt-5.6-luna`
Generation protocol: `english-story-production.v3`
Continuity evaluator implementation: `typesafe/jev-1.13`
Semantic judge implementation: `anthropic/claude-haiku-4.5`

## Purpose

This was the first live wave after adding the bounded sentinel-repeat lane to
Adaptive Capability Coverage Planner v1.

The batch contained:

- one sentinel repeat: `MIDDLE_CHILD × emotional_development`;
- seven age-balanced coverage-expansion cases.

## Results

| Lane | Age tier | Family | Target | Actual | Attempts | Semantic repairs | Judge avg | Judge min | Seconds |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| SENTINEL | MIDDLE_CHILD | emotional_development | 2,800 | 2,807 | 6 | 0 | 4.000 | 4 | 151.1 |
| EXPANSION | EARLY_CHILD | exploration_mystery | 500 | 583 | 12 | 2 | 4.000 | 4 | 142.6 |
| EXPANSION | CHILD | puzzle_problem_solving | 1,500 | 1,517 | 6 | 0 | 4.000 | 4 | 160.5 |
| EXPANSION | TEEN | exploration_mystery | 3,800 | 3,684 | 7 | 0 | 4.000 | 4 | 207.4 |
| EXPANSION | YOUNG_ADULT | puzzle_problem_solving | 4,200 | 3,671 | 6 | 0 | 4.000 | 4 | 180.2 |
| EXPANSION | ADULT | puzzle_problem_solving | 4,200 | 3,649 | 9 | 2 | 4.000 | 4 | 300.9 |
| EXPANSION | MATURE_ADULT | puzzle_problem_solving | 4,200 | 3,688 | 7 | 0 | 4.000 | 4 | 194.5 |
| EXPANSION | SENIOR | puzzle_problem_solving | 4,200 | 3,593 | 8 | 0 | 4.000 | 4 | 212.4 |

All eight cases were accepted and every final semantic-judge minimum criterion
was 4.

## Sentinel result

The first MIDDLE_CHILD emotional-development observation required 9 attempts
and 3 semantic repairs. Its sentinel repeat required exactly 6 attempts and
zero semantic repairs.

Across the two v3 observations the cell therefore averages 1.5 semantic
repairs/run, below the planner sentinel threshold of 2.0.

Conclusion: the original 3-repair observation is not sufficient evidence of a
persistent model-specific weakness. No prompt fork or runtime-policy override
is justified.

## New uncertainty signals

EARLY_CHILD × exploration_mystery completed successfully but required
12 attempts and 2 semantic repairs. It therefore becomes sentinel-eligible.

ADULT × puzzle_problem_solving also completed successfully with 9 attempts and
2 semantic repairs. It is sentinel-eligible, but deterministic sentinel
priority selects EARLY_CHILD exploration first because its semantic-repair
burden is equal and its scene-attempt burden is higher.

These are repeat signals, not tuning decisions.

## Local scene-budget authority clarification

One EARLY_CHILD exploration semantic repair finished slightly above the local
scene-budget bound after a prior bounded word-budget repair.

Review of the canonical implementation and regression tests confirms that this
is expected current behavior:

- local scene bounds trigger bounded repair work;
- residual scene-only length misses may become advisory after bounded repair;
- non-length schema/state errors remain blocking;
- the assembled whole-story 75%–125% budget remains the hard deterministic
  length authority.

Therefore this observation is not a protocol-v3 invariant failure and does not
require a new generation-protocol version.

## Coverage after promotion

After this wave is promoted, the active-v3 executable scope becomes:

- observed: 20 / 24 cells;
- UNKNOWN: 4;
- THIN: 18;
- PROVISIONAL: 2;
- ESTABLISHED: 0.

The next adaptive plan can cover all four remaining UNKNOWN cells while
retaining one sentinel repeat and three age-balanced depth/repeat slots.
