# Luna v3 Adaptive Density Wave 35991944331

Date: 2026-09-24
Status: **EVIDENCE COMPLETE**
Generator: `openai/gpt-5.6-luna`
Generation protocol: `english-story-production.v3`

## Purpose

After full executable STANDARD coverage was achieved, the adaptive planner
shifted from filling UNKNOWN cells to increasing evidence density while
reserving one sentinel-repeat lane for suspicious cells.

This wave executed one sentinel repeat plus seven density-expansion cases.
Acceptance thresholds, runtime profile, continuity evaluator and semantic judge
were unchanged.

## Results

| Lane | Age tier | Family | Target | Actual | Attempts | Semantic repairs | Judge avg | Judge min |
|---|---|---|---:|---:|---:|---:|---:|---:|
| COVERAGE_EXPANSION | CHILD | emotional_development | 1,500 | 1,662 | 6 | 0 | 4.000 | 4 |
| SENTINEL_REPEAT | MIDDLE_CHILD | puzzle_problem_solving | 2,800 | 2,698 | 10 | 4 | 4.000 | 4 |
| COVERAGE_EXPANSION | MATURE_ADULT | emotional_development | 4,200 | 4,398 | 6 | 0 | 4.000 | 4 |
| COVERAGE_EXPANSION | SENIOR | puzzle_problem_solving | 4,200 | 3,774 | 7 | 0 | 4.875 | 4 |
| COVERAGE_EXPANSION | ADULT | emotional_development | 4,200 | 4,411 | 7 | 1 | 4.000 | 4 |
| COVERAGE_EXPANSION | EARLY_CHILD | puzzle_problem_solving | 500 | 524 | 7 | 1 | 4.000 | 4 |
| COVERAGE_EXPANSION | TEEN | emotional_development | 3,800 | 3,818 | 6 | 0 | 4.000 | 4 |
| COVERAGE_EXPANSION | YOUNG_ADULT | puzzle_problem_solving | 4,200 | 3,848 | 11 | 4 | 4.000 | 4 |

All eight stories were accepted. Every final semantic-judge minimum criterion
was at least 4.

## MIDDLE_CHILD puzzle decision

The current v3 cohort on the same frozen fixture is now:

- `35985914923-middle-child--puzzle-problem-solving`: 10 attempts / 4 semantic repairs;
- `35987414041-middle-child--puzzle-problem-solving`: 6 / 0;
- `35991944331-middle-child--puzzle-problem-solving`: 10 / 4.

The newest heavy run required repeated continuity repair in Scene 2 for
`no_contradiction` and Scene 5 for `no_unexplained_dependency`.

Two independent anomalous runs now exist on one spec fingerprint. Per the
fixture-diversity guard, the cell is `DIAGNOSTIC_FIXTURE_REQUIRED`.

Do not repeat the same fixture again and do not add model-specific tuning yet.
The next MIDDLE_CHILD puzzle evidence must come from a second frozen premise
with the same governed axes.

## YOUNG_ADULT puzzle decision

The current v3 cohort is:

- first run: 6 attempts / 0 semantic repairs;
- `35991944331-young-adult--puzzle-problem-solving`: 11 / 4.

The new heavy run required two repairs in Scene 2 and two in Scene 4, dominated
by `no_contradiction` and one `no_unexplained_dependency` transition.

Because only one of the two current runs is anomalous, fixture diversity is not
yet required. The canonical planner selects this cell for one bounded sentinel
repeat.

## Planner outcome after the wave

Inside the 24 fixture-backed STANDARD cells:

- observed: 24;
- UNKNOWN: 0;
- THIN: 9;
- PROVISIONAL: 15;
- ESTABLISHED: 0.

Escalation state:

- diagnostic fixture required: `middle-child--puzzle-problem-solving`;
- targeted intervention candidates: none;
- next sentinel repeat: `young-adult--puzzle-problem-solving`.

No evidence in this wave justifies weaker continuity thresholds, weaker judge
thresholds, or a Luna-specific production-policy override.
