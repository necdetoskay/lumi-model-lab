# Luna v3 Adaptive Emotional-Development Wave — 2026-09-24

Status: **EVIDENCE COMPLETE — 8/8 ACCEPTED**
Workflow run: `35982224237`
Generator: `openai/gpt-5.6-luna`
Generation protocol: `english-story-production.v3`
Continuity evaluator implementation: `typesafe/jev-1.13`
Semantic judge implementation: `anthropic/claude-haiku-4.5`

## Purpose

This was the first live batch selected by Adaptive Capability Coverage Planner v1.

The planner selected `emotional_development` across all eight canonical
NarrativeAgeTiers because the family had zero active-v3 age coverage while
remaining fully fixture-backed.

The batch was selected for evidence coverage, not because the family was
assumed to be more important or more popular in production.

## Results

| Age tier | Target | Actual | Scene attempts | Semantic repairs | Judge avg | Judge min | Seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| EARLY_CHILD | 500 | 548 | 7 | 0 | 4.000 | 4 | 113.9 |
| CHILD | 1,500 | 1,703 | 6 | 0 | 4.000 | 4 | 135.9 |
| MIDDLE_CHILD | 2,800 | 2,889 | 9 | 3 | 4.000 | 4 | 225.1 |
| TEEN | 3,800 | 3,854 | 7 | 1 | 4.000 | 4 | 210.6 |
| YOUNG_ADULT | 4,200 | 4,249 | 6 | 0 | 4.000 | 4 | 243.3 |
| ADULT | 4,200 | 3,994 | 6 | 0 | 4.000 | 4 | 197.0 |
| MATURE_ADULT | 4,200 | 4,188 | 7 | 1 | 4.000 | 4 | 217.5 |
| SENIOR | 4,200 | 4,133 | 6 | 0 | 4.000 | 4 | 204.5 |

All eight cases were accepted and every final semantic-judge minimum criterion
was 4.

## Continuity-repair observations

MIDDLE_CHILD was the only materially high-repair cell:

- Scene 3 required two bounded repairs for `no_unexplained_dependency`
  (0.78 then 0.75 against the 0.80 threshold);
- Scene 5 required one bounded repair for `no_future_leakage` (0.56).

TEEN required one bounded Scene 5 `no_future_leakage` repair at 0.75.

MATURE_ADULT required one bounded Scene 2 `no_unexplained_dependency` repair
at 0.74.

All listed repairs subsequently cleared the relevant continuity gate. No
terminal failure or final quality-gate failure remained.

## Interpretation

The batch does not justify a model-specific prompt or runtime-policy override.

MIDDLE_CHILD × emotional_development is a THIN cell with one successful but
repair-heavy observation. It requires a repeat before any tuning conclusion.

This result motivated a planner hardening: a bounded sentinel-repeat lane
should reserve at most one slot in an adaptive batch for a THIN/PROVISIONAL
cell with a real failure, low final criterion, or materially high semantic
repair burden. The remaining batch continues coverage expansion.

## Evidence identity

Each run is archived independently under `evidence/model_qualification/` and
is bound to the exact generator profile/policy, v3 generation-protocol SHA and
evaluation-stack SHA.

Exact run ids:

- `35982224237-early-child--emotional-development`
- `35982224237-child--emotional-development`
- `35982224237-middle-child--emotional-development`
- `35982224237-teen--emotional-development`
- `35982224237-young-adult--emotional-development`
- `35982224237-adult--emotional-development`
- `35982224237-mature-adult--emotional-development`
- `35982224237-senior--emotional-development`
