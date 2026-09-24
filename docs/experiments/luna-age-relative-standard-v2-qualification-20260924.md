# GPT-5.6 Luna — Age-Relative STANDARD Qualification Wave v2

Status: **Completed / first-pass sparse qualification**
Date: 2026-09-24
Canonical generator: `openai/gpt-5.6-luna`
Continuity evaluator: `typesafe/jev-1.13`
Semantic judge: `anthropic/claude-haiku-4.5`
Generation/evaluation base SHA: `0381ef9139cf862c1e647286a8980516ba3061e4`
Wave run: `35964336473`
Independent EARLY_CHILD smoke: `35964292345`

## Purpose

This wave replaces the invalid global-2000-word age sweep with the canonical
Capability Cube v2 age-relative STANDARD policy.

It tests one exact representative age from every NarrativeAgeTier across three
narrative families while keeping the model, model policy, generation protocol,
evaluation stack and relative length class fixed.

## STANDARD targets

| Tier | Exact age | Reading mode | Target words |
|---|---:|---|---:|
| EARLY_CHILD | 4 | READ_ALOUD | 500 |
| CHILD | 7 | EARLY_READER | 1,500 |
| MIDDLE_CHILD | 10 | INDEPENDENT_READER | 2,800 |
| TEEN | 15 | INDEPENDENT_READER | 3,800 |
| YOUNG_ADULT | 21 | INDEPENDENT_READER | 4,200 |
| ADULT | 32 | INDEPENDENT_READER | 4,200 |
| MATURE_ADULT | 50 | INDEPENDENT_READER | 4,200 |
| SENIOR | 70 | INDEPENDENT_READER | 4,200 |

Families:

- `exploration_mystery`
- `emotional_development`
- `puzzle_problem_solving`

## First-pass results

All 24 wave cases were accepted by the unchanged deterministic, continuity and
semantic-judge gates.

| Tier | Family | Target | Actual | Judge | Min | Attempts | Repairs | Seconds |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| EARLY_CHILD | exploration_mystery | 500 | 558 | 4.000 | 4 | 6 | 0 | 129.9 |
| EARLY_CHILD | emotional_development | 500 | 540 | 4.000 | 4 | 7 | 0 | 157.5 |
| EARLY_CHILD | puzzle_problem_solving | 500 | 570 | 4.000 | 4 | 13 | 4 | 197.1 |
| CHILD | exploration_mystery | 1,500 | 1,650 | 4.000 | 4 | 9 | 1 | 170.7 |
| CHILD | emotional_development | 1,500 | 1,583 | 4.000 | 4 | 8 | 2 | 192.5 |
| CHILD | puzzle_problem_solving | 1,500 | 1,579 | 4.750 | 4 | 8 | 0 | 221.5 |
| MIDDLE_CHILD | exploration_mystery | 2,800 | 2,643 | 4.000 | 4 | 6 | 0 | 173.6 |
| MIDDLE_CHILD | emotional_development | 2,800 | 2,816 | 4.000 | 4 | 7 | 1 | 204.0 |
| MIDDLE_CHILD | puzzle_problem_solving | 2,800 | 2,689 | 4.000 | 4 | 6 | 0 | 177.6 |
| TEEN | exploration_mystery | 3,800 | 3,567 | 4.000 | 4 | 7 | 1 | 253.8 |
| TEEN | emotional_development | 3,800 | 3,843 | 4.000 | 4 | 6 | 0 | 213.3 |
| TEEN | puzzle_problem_solving | 3,800 | 3,396 | 4.875 | 4 | 7 | 0 | 196.2 |
| YOUNG_ADULT | exploration_mystery | 4,200 | 3,802 | 4.000 | 4 | 6 | 0 | 205.4 |
| YOUNG_ADULT | emotional_development | 4,200 | 4,288 | 4.000 | 4 | 6 | 0 | 217.7 |
| YOUNG_ADULT | puzzle_problem_solving | 4,200 | 3,838 | 4.000 | 4 | 8 | 2 | 260.6 |
| ADULT | exploration_mystery | 4,200 | 3,881 | 4.000 | 4 | 8 | 2 | 238.9 |
| ADULT | emotional_development | 4,200 | 4,094 | 4.000 | 4 | 6 | 0 | 196.8 |
| ADULT | puzzle_problem_solving | 4,200 | 3,897 | 4.000 | 4 | 6 | 0 | 207.1 |
| MATURE_ADULT | exploration_mystery | 4,200 | 4,021 | 4.000 | 4 | 6 | 0 | 189.0 |
| MATURE_ADULT | emotional_development | 4,200 | 4,399 | 4.000 | 4 | 7 | 1 | 243.2 |
| MATURE_ADULT | puzzle_problem_solving | 4,200 | 3,666 | 4.000 | 4 | 9 | 1 | 251.7 |
| SENIOR | exploration_mystery | 4,200 | 3,825 | 4.000 | 4 | 7 | 1 | 229.0 |
| SENIOR | emotional_development | 4,200 | 4,023 | 4.000 | 4 | 8 | 1 | 274.2 |
| SENIOR | puzzle_problem_solving | 4,200 | 3,757 | 4.000 | 4 | 8 | 1 | 221.6 |

## Aggregate observations

- accepted: **24 / 24**;
- average final semantic-judge score: **4.0677 / 5**;
- lowest observed final criterion: **4**;
- average scene-generation attempts per story: **7.29**;
- average semantic repairs per story: **0.75**;
- average total pipeline time: **209.3 s**;
- average absolute target-word error: **6.89%**.

By family:

| Family | Judge avg | Attempts/story | Total repairs | Avg seconds | Avg abs word error |
|---|---:|---:|---:|---:|---:|
| exploration_mystery | 4.000 | 6.88 | 5 | 198.8 | 8.0% |
| emotional_development | 4.000 | 6.88 | 5 | 212.4 | 3.6% |
| puzzle_problem_solving | 4.203 | 8.12 | 8 | 216.7 | 9.1% |

## Important interpretation

This first pass shows that the age-relative STANDARD targets are operationally
viable across all eight age tiers with the current six-scene protocol.

It does **not** establish that all 24 cells are equally reliable. With one wave
observation per cell, 23 cells remain THIN. The independent EARLY_CHILD
exploration smoke provides a second observation for that one cell once both
records are promoted.

The clearest first-pass outlier is:

`EARLY_CHILD × puzzle_problem_solving × STANDARD`

It still passed every final quality gate, but required 13 generation attempts
and 4 semantic repairs. That is a reliability/efficiency signal, not a quality
failure.

Other cells worth repeat attention because they required at least two semantic
repairs or nine total attempts are:

- `CHILD × exploration_mystery` — 9 attempts / 1 repair;
- `CHILD × emotional_development` — 8 attempts / 2 repairs;
- `YOUNG_ADULT × puzzle_problem_solving` — 8 attempts / 2 repairs;
- `ADULT × exploration_mystery` — 8 attempts / 2 repairs;
- `MATURE_ADULT × puzzle_problem_solving` — 9 attempts / 1 repair.

No model-specific prompt/policy tuning is justified from one observation.
These cells should be repeated under the exact same protocol first.

## Independent EARLY_CHILD exploration smoke

Run `35964292345` was executed before the full wave using the same v2 spec and
protocol identity:

- target: 500 words;
- actual: 563 words;
- accepted: yes;
- final judge: 4.000 / 5, minimum 4;
- total attempts: 13;
- semantic repairs: 2;
- pipeline time: 187.3 s.

Together with the wave exploration run (6 attempts / 0 repairs), this already
shows why repeat evidence matters: the same governed cell can vary materially
in retry burden while both outputs pass the final quality gate.

## Next qualification rule

Before defining SHORT/LONG/extreme policies or introducing model-specific
execution overlays:

1. promote this immutable evidence into Capability Cube v2;
2. run a targeted repeat wave for reliability outliers;
3. use already-clean cells as regression controls;
4. only treat a weakness as systematic if it reproduces under the exact same
   model/profile/generation/evaluation identities.
