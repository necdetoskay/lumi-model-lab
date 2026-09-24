# GPT-5.6 Luna — Age-Relative STANDARD Targeted Repeats

Status: **Completed**
Date: 2026-09-24
Generator: `openai/gpt-5.6-luna`
Continuity evaluator: `typesafe/jev-1.13`
Semantic judge: `anthropic/claude-haiku-4.5`
Generation protocol: `english-story-production.v1`
Canonical repeat base SHA: `b0c79856a82f955cc3f751291ceb6774082da605`

## Purpose

The first age-relative STANDARD wave accepted all 24 cases, but six cells met
an objective retry-watch threshold:

- at least 2 semantic repairs in one run; or
- at least 9 total scene-generation attempts in one run.

`EARLY_CHILD × exploration_mystery` was added as a control because its two
prior v2 runs had materially different retry burden.

No prompt, model policy, judge threshold, continuity threshold, or StorySpec
was changed for this repeat round.

## Repeat results

| Cell | First observed burden | Repeat burden | Repeat judge | Interpretation |
|---|---|---|---:|---|
| EARLY_CHILD × puzzle_problem_solving | 13 attempts / 4 repairs | 6 / 0 | 4.000 | first outlier did not reproduce |
| CHILD × emotional_development | 8 / 2 | 7 / 1 | 4.000 | burden reduced; no persistent failure |
| CHILD × exploration_mystery | 9 / 1 | 9 / 1 | 4.000 | retry burden reproduced |
| YOUNG_ADULT × puzzle_problem_solving | 8 / 2 | 6 / 0 | 4.000 | first burden did not reproduce |
| ADULT × exploration_mystery | 8 / 2 | 6 / 0 | 4.000 | first burden did not reproduce |
| MATURE_ADULT × puzzle_problem_solving | 9 / 1 | 7 / 0 | 4.000 | first burden did not reproduce |
| EARLY_CHILD × exploration_mystery control | prior: 13/2 and 6/0 | 6 / 0 | 4.000 | high-retry smoke did not reproduce twice |

All seven repeat stories passed final semantic quality gates with minimum
criterion 4.

## CHILD exploration deep comparison

`CHILD × exploration_mystery` is the only watch cell whose aggregate retry
count reproduced exactly: 9 attempts / 1 semantic repair in both qualification
runs.

However, the internal failure signature was not identical.

First wave run:

- Scene 4 exceeded its 255-word target with 311 words and required two
  technical repair attempts before acceptance;
- Scene 5 required one continuity/semantic repair.

Repeat run:

- Scene 3 exceeded its 255-word target with 334 words and required a technical
  repair followed by one continuity/semantic repair;
- Scene 4 exceeded its 255-word target with 309 words and required one
  technical repair.

Thus the repeated aggregate burden is a mixture of tight per-scene word-budget
validation and non-identical continuity repairs. It is not evidence of one
stable narrative defect in Luna.

## Shared word-budget gate finding

Across the 24 first-wave runs, the independent EARLY_CHILD smoke, and the seven
targeted repeats (32 v2 runs total), there were **16 initial scene word-budget
misses**.

Of those 16 misses:

- **10** would have been inside a ±25% relative scene tolerance;
- the current scene validator uses ±20%;
- the completed-story validator already uses ±25%.

Examples of retries caused by very small boundary misses include:

- CHILD exploration: 311 words where the current maximum was 306;
- CHILD exploration repeat: 309 where the maximum was 306;
- CHILD puzzle: 315 where the maximum was 306;
- SENIOR emotional: 867 where the maximum was 857.

For very short EARLY_CHILD scenes, percentage-only thresholds are additionally
brittle because a difference of roughly 15–25 words can look like a very large
percentage despite the complete 500-word story remaining inside its accepted
whole-story budget.

## Decision

Do **not** add a Luna-specific CHILD/exploration prompt or production-policy
overlay from this evidence.

The next experiment should address the shared generation protocol instead:

1. preserve the existing total-story ±25% acceptance gate;
2. test a less brittle per-scene word-budget rule;
3. keep all continuity and semantic quality gates unchanged;
4. bump the generation-protocol version so new evidence cannot aggregate with
   `english-story-production.v1`;
5. re-run a compact regression set spanning short, child, teen, and adult
   targets before any broader promotion.

This is a pipeline-efficiency hypothesis, not a claim that the current accepted
stories are low quality.
