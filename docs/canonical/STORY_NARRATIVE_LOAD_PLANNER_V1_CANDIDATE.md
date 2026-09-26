# LUMI Story Narrative Load Planner v1 — Candidate

Status: **QUALIFICATION CANDIDATE — NOT YET CANONICAL**  
Date: 2026-09-26  
Scope: Story V5 story-architecture / spine construction for exact-age-4 / READ_ALOUD qualification

## 1. Decision

Story length must not be increased by forcing prose expansion or by appending arbitrary beats to an already coherent spine.

The preferred intervention point is the **story architecture / spine planning stage**.

The planner's job is to create enough genuine narrative substance before prose generation. It may use one supporting micro-thread only when that thread naturally belongs to the main story and changes the story's observation, decision, constraint, social shift, or payoff.

This component is therefore named **Narrative Load Planner**, not subplot generator or length expander.

Narrative Load Planner is a logical planning contract. Production should prefer folding these rules into the existing Narrative Architect rather than introducing a mandatory extra LLM call.

## 2. Why this exists

Story V5 experiments showed several distinct behaviors.

### Internal length pressure

Run `36223914525` showed that raising the writer's internal target can increase output length, but quality does not rise with it. The 700-pressure story was longer than the 500-pressure story but materially worse.

The five-family 500-vs-700 probe also did not justify a global multiplier:
- 500-pressure wins: 3;
- 700-pressure wins: 1;
- inconclusive: 1.

Conclusion: no global 700-word or 1.4x production rule.

### Arbitrary B-thread / post-hoc enrichment

B-thread run `36225546379` increased one story from 345 to 372 words, but the baseline won both blind order-swapped comparisons.

Runs `36224984644`, `36225180546`, and `36225224982` showed that adding beats after a spine is already coherent does not reliably increase useful narrative load. The writer often compresses semantically redundant beats back together, and arbitrary micro-events can read as filler.

Conclusion: “add a side event” is not a safe rule.

### Causal micro-arcs

Run `36225591469` showed that setup -> friction -> payoff micro-arcs can add real narrative material in some families:
- mean word delta: +29.33;
- micro-arc wins: 1;
- baseline wins: 1;
- inconclusive: 1.

Conclusion: a real micro-arc can work, but unconditional hand-insertion is not reliable.

## 3. Narrative-load planning evidence

### Single-family probe

Run `36225729794` rebuilt the spine from the premise:
- baseline: 287 words;
- planned: 348 words;
- delta: +61;
- planned story won both order-swapped blind comparisons;
- overall quality: 9/10 vs 7/10.

### Multi-family Cohort A

Run `36225932402`:
- planned wins: 3;
- baseline wins: 0;
- inconclusive: 2;
- mean word delta: +8.8.

### Same fixtures, second seed

Run `36226580056`:
- planned wins: 3;
- baseline wins: 0;
- inconclusive: 2;
- mean word delta: +11.0.

This reproduced the quality advantage without reproducing a large length increase.

### Fresh fixture Cohort B

Run `36226557647` used five new premises:
- planned wins: 3;
- baseline wins: 1;
- inconclusive: 1;
- mean word delta: +25.2.

### Combined evidence

Across the three five-family cohorts:
- family-cases: 15;
- planned wins: **9**;
- baseline wins: **1**;
- inconclusive: **5**;
- combined mean word delta: **+15.0 words**.

Supporting thread was used in 8/15 cases and omitted in 7/15.

This proves two important points:

1. The planner's benefit is primarily **quality and causal structure**, not word count.
2. A supporting thread is genuinely **optional**. The planner can improve a story by restructuring the main arc alone.

## 4. Planner contract

The planner receives:
- exact age;
- reading mode;
- narrative family;
- nominal target length;
- premise;
- canonical constraints available to planning.

It returns an 8–12 beat functional spine.

Each beat carries:
- `density`: brief | develop | anchor;
- `function`: setup | signal | hypothesis | test | complication | observation | decision | social_shift | payoff | closure;
- one concrete event statement.

Required:
- setup;
- at least one meaningful progression function;
- payoff;
- terminal closure;
- payoff before closure;
- no duplicate beat text.

Beat count is not a word-count proxy. Splitting one semantic event into several beats only to increase length is forbidden.

## 5. Supporting micro-thread

A supporting thread is optional and there may be at most one for this profile.

When used, it must satisfy all of the following:

1. **Belongs to the same story.** It intersects with the main arc through the same environment, existing object, existing relationship, or natural condition.
2. **Has causal shape.** It has setup -> friction/change -> convergence/payoff.
3. **Changes something.** It changes an observation, decision, constraint, social state, or payoff. If removing it changes nothing, it is filler.
4. **Rejoins the main arc.** It does not survive as a separate mini-story or detached epilogue.
5. **Preserves the main causal rule.** Once the story establishes “X causes Y under condition Z,” the supporting thread may test or expose that rule but must not silently replace it, weaken it, or invent a hidden extra condition merely to delay payoff.
6. **Preserves committed state.** A completed action or item state may not be undone merely to reuse the prop later.
7. **Does not create durable canon.** No new named character, family/relationship fact, durable world fact, important persistent item, or independent solution may be invented merely to support it.
8. **Remains age-appropriate.** No complex subplot logic, adult-style inference chain, or unsafe child behavior.

The planner may explicitly decide **not** to use a supporting thread. That is a valid and often preferable outcome.

## 6. Known risk discovered in qualification

The only baseline consensus win across the 15 family-cases occurred in fresh-fixture `everyday_fantastical_discovery`.

The planner created an otherwise plausible supporting thread around toy cleanup, but the resulting prose weakened the already-established light condition:
- the light path was cleared;
- the expected visual effect did not return immediately;
- an implied/late extra condition was introduced to explain the delay.

The defect was not “too many words.” It was **causal-rule drift**.

Therefore causal-rule preservation and committed-state preservation are explicit candidate requirements before promotion.

## 7. Length policy

For this candidate:
- nominal writer target remains 500 words;
- target is soft;
- quality is primary;
- length is secondary;
- the planner is not instructed to hit 500 by adding content;
- no automatic 700-word or 1.4x multiplier is used;
- no post-hoc expansion is triggered solely because a strong story is short.

A 250–350 word story can still be the better story. Narrative load and prose length are only loosely correlated.

## 8. Pipeline position

Logical flow:

`Premise / StoryIntent -> Narrative-load-aware Story Architecture -> deterministic plan validation -> Writer -> defect locator / bounded repair -> final acceptance`

Implementation preference:

`Existing Narrative Architect + Narrative Load contract -> Writer`

rather than:

`NarrativeLoadPlanner model call -> Narrative Architect model call -> Writer`.

The goal is to improve planning without adding an unnecessary permanent model hop.

A short final story is not automatically sent back for expansion. Replanning is justified only when the architecture itself is diagnosed as thin or causally weak, not merely because prose is below a numeric target.

## 9. Promotion gate

This candidate must not become canonical production policy until:
- deterministic planner-contract tests are green;
- second-seed evidence is green;
- fresh-fixture evidence is recorded;
- causal-rule and committed-state guards are qualified on the known risky family;
- integration into the existing Narrative Architect is compared against the current architect without adding a mandatory extra LLM call;
- no canon/safety regression appears;
- cost/latency implications are recorded;
- production promotion is explicit and versioned.

Current state:
- deterministic contract suite: green;
- second seed: complete;
- fresh fixture Cohort B: complete;
- architect-integration qualification: **next**.

## 10. Current conclusion

The evidence supports:

> Design sufficient story substance before writing; do not repair thinness by padding prose.

It also supports:

> A natural supporting micro-thread can be useful, but only when the premise needs it and it preserves the main causal/state rules.

It does **not** support:

> Always add a subplot, always add more beats, or force every story toward 500 words.
