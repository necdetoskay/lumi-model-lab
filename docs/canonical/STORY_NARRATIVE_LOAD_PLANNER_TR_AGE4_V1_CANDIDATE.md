# Story Narrative Load Planner — TR Age 4 v1 Candidate

Status: **QUALIFICATION CANDIDATE — NOT CANONICAL**

## Purpose

This candidate defines how LUMI should create a Story Spine that has enough genuine narrative substance before prose generation.

The goal is **not** to force a 500-word output. The goal is to prevent an under-developed spine from making the writer either finish too early or invent filler while trying to satisfy a length target.

## Core decision

Do not solve short stories by:
- raising the writer target globally to 700/800;
- adding arbitrary extra beats after the spine is already complete;
- expanding prose after generation merely to satisfy word count.

Instead, improve the spine **before writing**.

A valid spine contains one main arc and may contain at most one supporting micro-thread when the premise naturally supports it.

The supporting thread is not a conventional subplot. It must:
1. arise from the same context, object, relationship, or environmental condition as the main story;
2. have a small setup -> friction/change -> convergence/payoff shape;
3. change an observation, action, decision, constraint, or result in the main arc;
4. naturally rejoin the main arc;
5. add no named character, relationship canon, durable world fact, or independent solution;
6. disappear entirely when it is not useful.

If removing the supporting thread changes nothing except word count, it is filler and must not exist.

## Evidence

### Length-pressure experiments

Increasing internal writer pressure from 500 to 700/800 increased length in some runs but did not reliably improve quality. Across five story families, 500-pressure won three comparisons, 700-pressure won one, and one was inconclusive.

Conclusion: a global length multiplier is not justified.

### Post-hoc spine enrichment

Adding two extra develop beats across five families did not create reliable extra narrative volume:
- average word delta: -10 words;
- baseline won 3 families;
- enriched won 2.

Conclusion: beat count is not narrative load.

### Manual causal micro-arcs

Three-beat setup -> complication -> payoff additions produced an average +29.33 words across three families, but quality was mixed:
- 1 micro-arc win;
- 1 baseline win;
- 1 inconclusive.

Conclusion: a real micro-arc can increase volume, but hand-inserting one is not a safe universal rule.

### Narrative Load Planner

Single-family probe run **36225729794**:
- baseline: 287 words;
- planned: 348 words;
- +61 words;
- planned story won both blind order-swapped comparisons, 9/10 vs 7/10.

Five-family probe run **36225932402**:
- planned: 3 wins;
- baseline: 0 wins;
- inconclusive: 2;
- mean word delta: +8.8 words.

Most importantly, the planner improved quality even when it produced a **shorter** story:
- exploration/mystery: 343 -> 329, planned won;
- emotional development: 292 -> 246, planned won.

Conclusion: Narrative Load Planner is supported as a **quality and causal-structure mechanism**, not as a word-count mechanism.

## Candidate flow

1. Load premise / StoryIntent / StoryContract constraints.
2. Narrative Load Planner creates an 8–12 beat functional spine.
3. Planner decides whether one supporting thread is genuinely useful.
4. Deterministic spine-contract validation runs.
5. Invalid spine receives at most one bounded replan.
6. Writer receives the accepted spine plus a soft nominal length target.
7. Writer realizes the spine without inventing new plot events or canon.
8. Normal locator / repair / final acceptance continues.
9. Publication is determined by story quality; length deviation remains evidence, not an automatic defect.

## Functional beat model

Each beat carries:
- density: brief | develop | anchor
- function: setup | signal | hypothesis | test | complication | observation | decision | social_shift | payoff | closure
- one concrete beat event.

Required:
- 8–12 beats;
- setup;
- payoff;
- closure;
- at least one meaningful progression function between setup and payoff;
- no duplicate beat text.

This schema does **not** assign a word quota to each beat.

## Why supporting thread is optional

The five-family planner correctly chose no supporting thread for several stories and still improved them.

Therefore:
- no global requirement to create a side event;
- no fixed B-thread;
- no rule such as “500 words requires 10 beats”;
- no forced side character.

The planner must be allowed to conclude that the main arc already contains sufficient narrative load.

## Known failure mode

The everyday-fantastical sample showed that a supporting thread can create state continuity risk when a prop is completed/put away and then reintroduced merely for payoff.

Before promotion, the planner/writer contract must explicitly preserve committed item state and forbid undoing a completed action solely to reuse a prop.

## Promotion gate

This candidate must not become canonical until:
- deterministic spine-contract tests pass;
- a second-seed five-family repeat is recorded;
- no baseline consensus win appears across the combined planner qualification unless analyzed and accepted;
- supporting-thread state continuity is explicitly covered;
- the existing publication-quality regression remains green.

## North-star rule

**Narrative load means meaningful story change, not more words.**

Length is an observed consequence. Quality, causality, age fit, agency, rhythm, and closure remain the product goals.
