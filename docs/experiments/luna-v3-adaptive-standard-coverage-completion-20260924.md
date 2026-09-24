# Luna v3 Adaptive STANDARD Coverage Completion Wave — 2026-09-24

Status: **EVIDENCE COMPLETE — 8/8 ACCEPTED**
Workflow run: `35985914923`
Generator: `openai/gpt-5.6-luna`
Generation protocol: `english-story-production.v3`
Continuity evaluator implementation: `typesafe/jev-1.13`
Semantic judge implementation: `anthropic/claude-haiku-4.5`

## Purpose

This wave closed the remaining fixture-backed STANDARD coverage gaps while
repeating the highest-priority sentinel from the previous wave.

The batch contained:

- sentinel repeat: `EARLY_CHILD × exploration_mystery`;
- four previously UNKNOWN cells;
- three age-balanced depth repeats.

## Results

| Lane | Age tier | Family | Target | Actual | Attempts | Semantic repairs | Judge avg | Judge min | Seconds |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| SENTINEL | EARLY_CHILD | exploration_mystery | 500 | 543 | 6 | 0 | 4.000 | 4 | 107.9 |
| DEPTH | CHILD | exploration_mystery | 1,500 | 1,625 | 6 | 0 | 4.000 | 4 | 122.1 |
| NEW | MIDDLE_CHILD | puzzle_problem_solving | 2,800 | 2,758 | 10 | 4 | 4.000 | 4 | 216.5 |
| DEPTH | TEEN | exploration_mystery | 3,800 | 3,599 | 6 | 0 | 4.000 | 4 | 161.9 |
| NEW | YOUNG_ADULT | exploration_mystery | 4,200 | 3,824 | 6 | 0 | 4.000 | 4 | 175.8 |
| DEPTH | ADULT | exploration_mystery | 4,200 | 3,855 | 7 | 0 | 4.000 | 4 | 190.1 |
| NEW | MATURE_ADULT | exploration_mystery | 4,200 | 4,027 | 6 | 0 | 4.000 | 4 | 174.5 |
| NEW | SENIOR | exploration_mystery | 4,200 | 3,967 | 7 | 0 | 4.000 | 4 | 195.2 |

All eight cases were accepted and every final semantic-judge minimum criterion
was 4.

## Sentinel result

The first EARLY_CHILD exploration observation required 12 attempts and
2 semantic repairs. The sentinel repeat completed in 6 attempts with zero
semantic repairs.

Across the two v3 observations the cell therefore averages 1.0 semantic
repair/run. The original repair-heavy run is not sufficient evidence of a
persistent model-specific weakness.

No prompt fork or runtime-policy override is justified.

## New uncertainty signal

The newly covered `MIDDLE_CHILD × puzzle_problem_solving` cell completed
successfully but required 10 attempts and 4 semantic repairs.

The repairs were concentrated in Scenes 4 and 5 and primarily reflected
continuity-evaluator `no_contradiction` concerns. Final semantic judging still
accepted the story at 4/4.

This is therefore a high-priority repeat signal, not a tuning conclusion. A
single-case sentinel repeat is the next governed action.

## Coverage milestone

After promotion of this wave, the current executable STANDARD scope is:

- observed: **24 / 24**;
- UNKNOWN: **0**;
- THIN: **18**;
- PROVISIONAL: **6**;
- ESTABLISHED: **0**.

The broader canonical STANDARD space remains 80 cells because seven additional
narrative families do not yet have fixture-backed executable cases. Those
56 cells remain `OUT_OF_SCOPE_FIXTURE_MISSING`, not failed or unqualified
cells.

## Decision

The coverage-expansion phase for the current 24-cell executable STANDARD wave
is complete.

Future paid runs should now be targeted depth/repeat work driven by evidence,
not blind Cartesian expansion. The immediate next run is a one-case sentinel
repeat of `MIDDLE_CHILD × puzzle_problem_solving`.
