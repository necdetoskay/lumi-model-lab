# Story Word-Budget Protocol v3 Qualification — 2026-09-24

Status: **PROMOTION EVIDENCE COMPLETE**
Generator: `openai/gpt-5.6-luna`
Continuity evaluator implementation: `typesafe/jev-1.13`
Semantic judge implementation: `anthropic/claude-haiku-4.5`
Promoted protocol: `english-story-production.v3`

## Question

Can the shared scene word-budget gate remove unnecessary overshoot repair
without weakening under-length protection or increasing continuity-repair
burden?

## Protocols compared

- v1: symmetric ±20% local scene gate.
- v2: symmetric `target ± max(25%, 20 words)`.
- v3: lower bound kept at 80% of target; upper bound changed to
  `target + max(25%, 20 words)`.

All compared qualification runs used the same generator profile/policy and the
same evaluation stack. Capability Cube isolates the protocols by generation
protocol SHA.

## Historical v1 miss distribution

Across the age-relative v1 qualification evidence there were 16 initial local
word-budget misses:

- 11 above the upper bound;
- 5 below the lower bound.

A deterministic replay of those 16 misses through v3 shows:

- 7 of 11 over-length misses would be accepted locally;
- all 5 under-length misses would still require repair;
- 4 larger overshoots would still require repair.

This is the intended selectivity: relax the dominant overshoot friction without
relaxing under-length protection.

## v2 non-promotion control

The five v2 cross-age smoke cases all passed final quality gates, but the TEEN
× puzzle control cohort showed a material retry regression.

| Protocol | TEEN × puzzle runs | Attempts | Semantic repairs |
|---|---|---:|---:|
| v1 | historical + two controls | 7, 6, 7 | 0, 0, 1 |
| v2 | initial + two repeats | 8, 11, 7 | 1, 5, 1 |

Mean burden:

- v1: 6.67 attempts / 0.33 semantic repairs;
- v2: 8.67 attempts / 2.33 semantic repairs.

In the worst v2 run, three scenes were admitted below the old v1 80% lower
bound; two later needed continuity repair. This does not prove a universal
causal relationship, but it is sufficient evidence not to promote symmetric
lower-bound relaxation.

Exact v1 control runs:

- `35976623010` — accepted, 6 attempts / 0 semantic repairs;
- `35976625872` — accepted, 7 / 1.

Exact v2 TEEN runs:

- `35968474673` — accepted, 8 / 1;
- `35968897380` — accepted, 11 / 5;
- `35976077823` — accepted, 7 / 1.

## v3 cross-age qualification

| Run | Age tier | Family | Target | Actual | Attempts | Semantic repairs | Judge avg | Judge min |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `35977020122` | EARLY_CHILD | puzzle_problem_solving | 500 | 542 | 7 | 1 | 4.000 | 4 |
| `35977023267` | CHILD | exploration_mystery | 1,500 | 1,574 | 6 | 0 | 4.000 | 4 |
| `35977026503` | MIDDLE_CHILD | exploration_mystery | 2,800 | 2,820 | 6 | 0 | 4.000 | 4 |
| `35977029260` | TEEN | puzzle_problem_solving | 3,800 | 3,403 | 6 | 0 | 4.000 | 4 |
| `35977032780` | ADULT | exploration_mystery | 4,200 | 3,758 | 8 | 0 | 4.000 | 4 |

Result: 5 / 5 accepted; every final semantic-judge minimum criterion was 4.

The ADULT run's two extra retries were bounded under-length technical repair in
Scene 6: 483 → 559 → 576 words against a 571-word lower bound. This is expected
v3 behavior: under-length protection remains active.

The EARLY_CHILD run's single semantic repair was a bounded
`goal_preserved` continuity repair in Scene 6 and did not reproduce as a
cross-age failure pattern.

## v3 TEEN control repeats

Two additional TEEN × puzzle runs were performed after the initial v3 smoke:

- `35977570919` — accepted, 6 attempts / 0 semantic repairs;
- `35977574454` — accepted, 7 attempts / 0 semantic repairs.

Across the three v3 TEEN runs:

- attempts: 6, 6, 7;
- semantic repairs: 0, 0, 0;
- all three final semantic-judge averages: 4.000;
- all three final minimum criteria: 4.

This restores the clean retry profile seen under v1 while keeping the targeted
upper-bound relaxation.

## Decision

Promote `english-story-production.v3` as the active shared Model Lab story
generation protocol.

Do not promote v2.

Do not add a Luna-specific prompt or runtime-policy overlay from this evidence.
The improvement belongs to the shared pipeline because the defect was a shared
local validation rule.

The governed evaluation roles remain model-independent:

- `continuity_evaluator`;
- `semantic_judge`.

JEV and Haiku are the current implementations recorded in evidence, not the
schema names.

## Change control

Any future change to the scene-budget rule, scene structure, prompts,
continuity-evaluator protocol, semantic-judge protocol, generator runtime
profile, or production policy creates a new governed evidence cohort and
requires qualification before promotion.
