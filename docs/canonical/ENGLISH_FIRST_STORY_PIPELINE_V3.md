# English-First Story Production Pipeline v3 — Asymmetric Word-Budget Gate

Status: **Candidate pending live regression qualification**  
Date: 2026-09-24  
Supersedes candidate: `ENGLISH_FIRST_STORY_PIPELINE_V2.md`  
Generation protocol version: `english-story-production.v3`

## Purpose

v3 narrows the v2 experiment after live evidence showed that symmetric relaxation
can admit materially under-length scenes before continuity evaluation.

The production authority remains model-independent. This change does not alter
the Luna runtime profile, StoryContract semantics, scene allocation weights,
continuity-evaluator questions/thresholds, semantic-judge rubric/thresholds,
whole-story word-budget gate, or repair-count limits.

## Evidence

Age-relative v1 qualification produced 16 initial scene word-budget misses:

- 11 over the upper bound;
- 5 below the lower bound.

The main friction was therefore over-length output.

Protocol v2 changed both sides from the v1 ±20% scene gate to
`target ± max(25%, 20 words)`. Five cross-age regression cases passed, but the
TEEN × puzzle cell showed continuity-repair variance:

- v1 reference: 7 attempts / 0 semantic repairs;
- v2 repeat A: 8 / 1;
- v2 repeat B: 11 / 5;
- v2 repeat C: 7 / 1.

In repeat B, three scenes were shorter than the v1 80% minimum but were admitted
by v2. Two of those scenes later required continuity repair. This is not proof of
causation, but it provides a plausible failure mechanism: a too-short scene can
omit explanatory material that a local word-budget repair might otherwise
restore.

## v3 rule

For scene target `T`:

`minimum = round(T × 0.80)`

`upper_slack = max(round(T × 0.25), 20)`

`maximum = T + upper_slack`

Examples:

| Target | v1 range | v2 range | v3 range |
|---:|---:|---:|---:|
| 65 | 52–78 | 45–85 | 52–85 |
| 78 | 62–94 | 58–98 | 62–98 |
| 100 | 80–120 | 75–125 | 80–125 |
| 255 | 204–306 | 191–319 | 204–319 |
| 714 | 571–857 | 536–892 | 571–892 |

v3 therefore keeps the v1 under-length protection while relaxing only the
historically dominant overshoot side.

## Whole-story authority

The completed English master remains a hard deterministic gate at 75%–125% of
the configured story target. v3 does not weaken that authority.

## Evaluation roles

The governed roles are model-independent:

- `generator`
- `continuity_evaluator`
- `semantic_judge`

JEV is the current continuity-evaluator implementation, not the schema or
architecture name. Replacing it later must create a new evaluation-stack
identity, so evidence from different evaluator stacks cannot silently merge.

## Evidence isolation

v3 uses `english-story-production.v3`. Capability Cube groups evidence by
generation-protocol SHA, so v1, v2 and v3 results remain separate cohorts.

## Qualification before promotion

Use the unchanged Luna / current continuity evaluator / current semantic judge
stack on a compact cross-age set:

1. EARLY_CHILD × puzzle_problem_solving × 500 words
2. CHILD × exploration_mystery × 1,500 words
3. MIDDLE_CHILD × exploration_mystery × 2,800 words
4. TEEN × puzzle_problem_solving × 3,800 words
5. ADULT × exploration_mystery × 4,200 words

Promotion requires all five accepted, minimum semantic-judge criterion >= 4,
no new deterministic failure signature, and no persistent continuity-repair
regression in the TEEN control cell.

The v2 evidence remains immutable experimental evidence even if v2 is not
promoted.
