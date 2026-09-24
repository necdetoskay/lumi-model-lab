# Luna v3 All-Narrative-Families STANDARD Wave Expansion — 2026-09-24

Status: **FIXTURE EXPANSION READY FOR QUALIFICATION**

## Purpose

The original age-relative STANDARD qualification program covered all eight
canonical age tiers but only three of ten canonical narrative families.

That 24-cell executable space is now fully observed under
`english-story-production.v3`, and the suspicious cells discovered during
that phase have already been handled through bounded sentinel repeats and,
where required, second frozen diagnostic fixtures.

The next information bottleneck is therefore family coverage, not another blind
round of repeats over the same three families.

## New active wave

`configs/qualification_waves/age-relative-standard-v3-all-families.yaml`

Dimensions:

- 8 NarrativeAgeTiers;
- 10 canonical NarrativeFamilies;
- STANDARD relative length only;
- canonical reading mode per age tier;
- total: **80 executable cases**.

## Preserved fixtures

The existing v2 fixtures for these families are intentionally unchanged:

- `exploration_mystery`
- `emotional_development`
- `puzzle_problem_solving`

Tests require the 24 corresponding materialized specs to be byte-equivalent
between v2 and v3. Existing evidence therefore retains the same governed
fixture meaning instead of being silently migrated to a new benchmark.

## Newly fixture-backed families

Seven canonical families become executable:

1. `friendship_social_problem`
2. `nature_environment`
3. `scientific_curiosity`
4. `adventure_journey`
5. `cooperation_teamwork`
6. `everyday_fantastical_discovery`
7. `world_lore_discovery`

The friendship and adventure fixtures are grounded in the earlier frozen
English benchmark concepts. The remaining fixtures are purpose-built
qualification fixtures aligned to the canonical LUMI narrative-family
taxonomy.

They are synthetic Model Lab fixtures, not training-corpus examples and not
production user stories.

## What each new family is intended to measure

- `friendship_social_problem`: perspective-taking, non-villainized social
  disagreement, concrete collaborative repair.
- `nature_environment`: multi-observation ecological reasoning, cause vs
  correlation, proportionate low-impact action.
- `scientific_curiosity`: hypothesis formation, controlled comparison,
  confound recognition, evidence-driven revision.
- `adventure_journey`: preparation, stable fantasy rules, route planning,
  bounded adaptation without deus ex machina.
- `cooperation_teamwork`: task dependencies, role revision, distributed
  contribution, coordination rather than single-hero rescue.
- `everyday_fantastical_discovery`: stable fantastical rules embedded in
  ordinary life, with human judgment still required.
- `world_lore_discovery`: source comparison, known/inferred/remembered
  distinctions, preserved uncertainty.

## Guardrails

The all-family expansion does not change:

- Luna runtime profile or production policy;
- generation protocol v3;
- continuity-evaluator questions or thresholds;
- semantic-judge rubric or thresholds;
- StoryContract authority;
- STANDARD age-relative word targets;
- self-hosted runner requirement.

No model-specific tuning is authorized by this fixture expansion.

## Planner state at activation

Before the new fixtures are used for paid qualification:

- executable STANDARD scope: **80**;
- observed active-protocol cells: **24**;
- UNKNOWN cells: **56**;
- fixture-missing cells: **0**.

The deterministic age-balanced planner selects
`world_lore_discovery` across all eight age tiers as the first batch because
that family has zero active-protocol age coverage.

This is a coverage decision only. It is not a quality ranking between
narrative families.

## Promotion criteria for the wave definition

The wave definition is acceptable for execution only when:

- exactly 80 cases materialize;
- all specs validate;
- all ten canonical narrative families are represented;
- all eight canonical age tiers are represented;
- the original 24 v2 family specs remain byte-equivalent;
- the adaptive planner resolves 80 executable / 24 observed / 56 UNKNOWN
  before any new paid run;
- the repository test suite remains green.

Live story outcomes from the new families remain separate qualification
evidence and will be promoted only after their immutable evidence packs are
reviewed.
