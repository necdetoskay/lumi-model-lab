# LUMI Story Narrative Load Planner v1 — Candidate

Status: **QUALIFICATION-COMPLETE CANDIDATE — NOT YET CANONICAL**  
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

Targeted guard run `36227255937` then tested three everyday-fantastical fixtures, including the previously losing glass-color fixture:
- guarded-planner wins: **3/3**;
- baseline wins: **0/3**;
- inconclusive: **0/3**;
- mean word delta: **-49 words**.

The known causal-rule failure was therefore corrected without using extra length as the mechanism.

## 6.1. Additional continuity guards

Qualification exposed three more failure classes that are now explicit contract rules:

- **Epistemic order:** decisive explanatory evidence must not be shown before the misunderstanding/uncertainty it resolves.
- **Perception vs response:** being busy, holding something, or being unable to answer immediately does not itself mean a character could not hear or see.
- **Physical affordance preservation:** the planner may not invent an unstated inability such as being too short, too weak, or unable to reach merely to create friction.
- **Terminal closure:** once the final closure action is realized, the writer may not append a second payoff, prop-placement action, joke, or symbolic epilogue.

Emotional guard run `36228047493` demonstrated that the perception/response fix corrected the previously failing `blocks_no_reply` case. A separate `watering_can_busy` failure then revealed the physical-affordance and post-closure-action risks, which were promoted into the deterministic candidate contract.

## 6.2. Existing Narrative Architect integration evidence

The preferred production shape is to fold Narrative Load into the existing Narrative Architect rather than create a permanent extra planner model hop.

Initial integration run `36227676063`:
- narrative-load-aware architect wins: **2/3**;
- baseline architect wins: **1/3**;
- no additional planner hop;
- mean word delta: **+3.33 words**.

The losing emotional case exposed repetition/economy issues rather than a need for more words. The architect/writer contract was tightened around epistemic order, response causality, immutable causal state, terminal closure, and physical affordances.

Because the OpenRouter key approached its monthly limit, later full reruns were replaced with frozen-baseline targeted qualification rather than paying again for already-recorded baseline generations.

Targeted integration run `36228645350` reused the successful baseline evidence from `36227676063` and retested only the two unresolved families:
- `everyday_fantastical_discovery`: narrative-load-aware architect won **both** order-swapped comparisons;
- `emotional_development`: **inconclusive** (one judge each way), with no serious defect;
- frozen baseline wins: **0/2**;
- candidate wins: **1/2**;
- inconclusive: **1/2**;
- candidate outputs were shorter by 20 and 76 words respectively;
- semantic architect replans used: **0**;
- total targeted run cost: **$0.165884**.

Combining the already-clean exploration result from the initial run with the targeted rerun gives the latest family resolution:
- narrative-load-aware architect wins: **2/3**;
- baseline wins: **0/3**;
- inconclusive: **1/3**.

This qualifies the **integration direction**: Narrative Load belongs inside the existing Narrative Architect contract. It does not justify a mandatory extra NarrativeLoadPlanner LLM call.

The architect path may perform at most **one bounded semantic replan**, and only when deterministic plan validation fails. On the normal valid path, extra model hops remain zero.

Provider token caps used in targeted qualification (architect 8192, writer 16384, judge 8192) are request/output reservation caps only; they are not story-length targets. They prevent oversized 65K token reservations from causing avoidable OpenRouter 402 failures.

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
- causal-rule and committed-state guards are qualified on the known risky family — **complete**;
- integration into the existing Narrative Architect is compared against the current architect without adding a mandatory extra LLM call — **complete**;
- no canon/safety regression appears;
- cost/latency implications are recorded;
- production promotion is explicit and versioned.

Current state:
- deterministic contract suite: green;
- second seed: complete;
- fresh fixture Cohort B: complete;
- targeted causal/state guard qualification: complete (run `36227255937`, 3/3 wins);
- architect-integration qualification: **complete** (initial run `36227676063`; targeted V2 run `36228645350`; latest resolved family view 2 wins / 0 baseline losses / 1 inconclusive);\n- mandatory extra planner hop: **not required**;\n- bounded semantic replan: **max 1, invalid-plan only**;\n- production promotion: **still requires explicit versioned decision**.

## 10. Current conclusion

The evidence supports:

> Design sufficient story substance before writing; do not repair thinness by padding prose.

It also supports:

> A natural supporting micro-thread can be useful, but only when the premise needs it and it preserves the main causal/state rules.

It does **not** support:

> Always add a subplot, always add more beats, or force every story toward 500 words.
