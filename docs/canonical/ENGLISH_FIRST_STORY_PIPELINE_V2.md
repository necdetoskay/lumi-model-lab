# English-First Story Production Pipeline v2 — Word-Budget Gate Retrofit

Status: **Candidate pending live regression qualification**
Date: 2026-09-24
Base: `ENGLISH_FIRST_STORY_PIPELINE_V1.md`
Generation protocol version: `english-story-production.v2`

## Purpose

v2 is a deliberately narrow generation-protocol change.

It does **not** change:

- StoryContract semantics;
- six-scene SceneGraph structure;
- scene allocation weights;
- continuity evaluator model/questions/thresholds;
- semantic judge model/rubric/thresholds;
- total-story word-budget gate;
- repair-count limits;
- model runtime profile or production policy.

It changes only the local scene word-budget hard bound used before continuity
evaluation and local repair.

## Evidence motivating the change

Capability Cube v2 age-relative STANDARD qualification produced:

- 24 / 24 accepted first-wave stories;
- 7 / 7 accepted targeted repeats;
- 32 total v2 evidence runs when the independent EARLY_CHILD smoke is included.

Across those 32 runs, **16 initial scene word-budget misses** occurred before
continuity evaluation.

The current v1 local scene gate uses ±20%.

Of those 16 misses:

- 10 were already inside ±25%;
- multiple retries were caused by only a few words beyond the v1 boundary;
- the assembled-story gate already uses ±25%.

Representative v1 friction:

- target 255, actual 311, v1 max 306;
- target 255, actual 309, v1 max 306;
- target 255, actual 315, v1 max 306;
- target 714, actual 867, v1 max 857.

For short EARLY_CHILD scenes, percentage-only bounds are additionally brittle.
A target of 65 words with 84 actual words is only 19 words over target but
looks like a 29% overshoot.

## v2 scene hard bound

For a scene target `T`:

`slack = max(round(T × 0.25), 20)`

`minimum = max(1, T - slack)`

`maximum = T + slack`

Examples:

| Target | v1 hard range | v2 hard range |
|---:|---:|---:|
| 65 | 52–78 | 45–85 |
| 78 | 62–94 | 58–98 |
| 100 | 80–120 | 75–125 |
| 255 | 204–306 | 191–319 |
| 714 | 571–857 | 536–892 |

The minimum absolute slack exists only to avoid pathological percentage
behavior for very short scenes.

## Total-story authority remains unchanged

The assembled English master remains a deterministic hard gate at:

- minimum: 75% of configured target;
- maximum: 125% of configured target.

v2 does not weaken the whole-story acceptance budget.

## Repair behavior

The specialized word-budget repair path uses the same v2 hard bounds.

Its preferred range remains narrower than the hard bound so a repair still
tries to move prose toward the target rather than merely touching the outer
limit.

A story or scene that fails schema, state, continuity, repetition, or semantic
quality gates receives no benefit from this change.

## Evidence isolation

The protocol version is bumped:

- v1: `english-story-production.v1`
- v2: `english-story-production.v2`

Capability Cube groups by generation-protocol identity. v2 runs therefore
cannot silently aggregate with v1 evidence even when the StorySpec, model and
evaluation stack are otherwise identical.

## Live regression set before promotion

Before v2 can supersede v1, run the unchanged Luna/JEV/Haiku stack on a compact
cross-age regression set:

1. EARLY_CHILD × puzzle_problem_solving × 500 words;
2. CHILD × exploration_mystery × 1,500 words;
3. MIDDLE_CHILD × exploration_mystery × 2,800 words;
4. TEEN × puzzle_problem_solving × 3,800 words;
5. ADULT × exploration_mystery × 4,200 words.

Promotion requires:

- all five stories accepted;
- final semantic-judge minimum criterion >= 4 in the observed regression set;
- no new deterministic or continuity failure pattern;
- no evidence-integrity failure;
- scene retry burden should not materially worsen relative to v1 reference runs.

The purpose is not to prove v2 globally superior from five runs. It is to
verify that the shared gate retrofit removes known technical friction without
regressing story quality before broader qualification.
