# LUMI Story Narrative Load Planner v1 — Candidate

Status: **QUALIFICATION CANDIDATE — NOT YET CANONICAL**  
Date: 2026-09-26  
Scope: Story V5 spine construction for exact-age-4 / READ_ALOUD qualification

## 1. Decision

Story length must not be increased by forcing prose expansion or by appending arbitrary beats to an already coherent spine.

The preferred intervention point is the **spine planning stage**.

The planner's job is to produce enough genuine narrative load before prose generation. It may use one supporting micro-thread only when that thread naturally belongs to the main story and changes the story's observation, decision, constraint, social shift, or payoff.

This component is therefore named **Narrative Load Planner**, not subplot generator or length expander.

## 2. Why this exists

Story V5 experiments showed three distinct behaviors.

### Internal length pressure

Run `36223914525` showed that raising the writer's internal target can increase output length, but quality does not rise with it. The 700-pressure story was longer than the 500-pressure story but materially worse.

### Post-hoc spine enrichment

Runs `36224984644`, `36225180546`, and `36225224982` showed that adding beats after a spine is already coherent does not reliably increase useful narrative load. The writer often compresses semantically redundant beats back together, and arbitrary micro-events can read as filler.

### Causal micro-arcs

Run `36225591469` showed that setup -> friction -> payoff micro-arcs can add real narrative material in some families, but hand-authored insertion is not uniformly better. The idea is valid; unconditional insertion is not.

### Narrative-load planning from the start

Run `36225729794` rebuilt the spine from the premise. The planned story increased from 287 to 348 words and won both order-swapped blind comparisons, 9/10 versus 7/10.

Run `36225932402` extended the same method across five narrative families:

- planned: 3 consensus wins;
- baseline: 0 consensus wins;
- inconclusive: 2;
- planned never lost a family;
- mean word-count change: +8.8 words.

The last point is important: the planner is **not** validated as a universal word-count expander. It is validated as a quality-oriented spine planner that sometimes increases length when the premise genuinely supports more narrative load.

## 3. Planner contract

The planner receives:

- exact age;
- reading mode;
- narrative family;
- nominal target length;
- premise;
- canonical constraints available to planning.

It returns an 8–12 beat spine.

Each beat carries:

- `density`: brief | develop | anchor;
- `function`: setup | signal | hypothesis | test | complication | observation | decision | social_shift | payoff | closure;
- one concrete event statement.

Beat count is not a word-count proxy. Splitting one semantic event into several beats only to increase length is forbidden.

## 4. Supporting micro-thread

A supporting thread is optional and there may be at most one for this profile.

When used, it must satisfy all of the following:

1. **Belongs to the same story.** It intersects with the main arc through the same environment, existing object, existing relationship, or natural condition.
2. **Has causal shape.** It has setup -> friction/change -> convergence/payoff.
3. **Changes something.** It changes an observation, decision, constraint, social state, or payoff. If removing it changes nothing, it is filler.
4. **Rejoins the main arc.** It does not survive as a separate mini-story or detached epilogue.
5. **Does not create durable canon.** No new named character, family/relationship fact, durable world fact, important persistent item, or independent solution may be invented merely to support it.
6. **Remains age-appropriate.** No complex subplot logic, adult-style inference chain, or unsafe child behavior.

The planner may explicitly decide **not** to use a supporting thread. That is a valid outcome.

## 5. Length policy

For this candidate:

- nominal writer target remains 500 words;
- target is soft;
- quality is primary;
- length is secondary;
- the planner is not instructed to hit 500 by adding content;
- no automatic 700-word or 1.4x pressure multiplier is used;
- no post-hoc expansion is triggered solely because a strong story is short.

A 250–350 word story can still be the better story. Narrative load and prose length are correlated only loosely.

## 6. Pipeline position

Candidate flow:

`Premise / StoryIntent -> NarrativeLoadPlanner -> Spine validation -> Writer -> defect locator / bounded repair -> final acceptance`

The planner runs **before** prose.

A short final story is not automatically sent back for expansion. Replanning is justified only when the spine itself is diagnosed as underloaded, not merely because the prose is below a numeric target.

## 7. Promotion gate

This candidate must not become canonical production policy until:

- deterministic planner-contract tests are green;
- the five-family evidence remains reproducible on at least one fresh fixture cohort;
- no canon/safety regression appears;
- planner cost is accepted as a deliberate quality tradeoff;
- the production architecture explicitly replaces any conflicting fixed-spine assumptions.

## 8. Current conclusion

The evidence supports:

> Design sufficient story substance before writing; do not repair thinness by padding prose.

It does **not** support:

> Always add a subplot or always add more beats to make the story longer.
