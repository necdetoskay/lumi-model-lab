# Dynamic Scene Narrative Architect v4 — Canonical Experiment Record

Date: 2026-09-24  
Status: EXPERIMENTAL / NOT PROMOTED  
Risk class: AEGIS L3  
Supersedes no production protocol. `english-story-production.v3` remains historical evidence identity.

## Why this experiment exists

The v3 story pipeline hardcoded exactly six scenes and also encoded positional semantics:

- fixed six-element scene budget allocation;
- Scene 5 = decisive payoff;
- Scene 6 = resolution/aftermath;
- scene-level and whole-story JEV prompts referenced those positions;
- planner validator required exactly six scenes;
- benchmark fixtures included `Preserve continuity across all six scenes`.

The product requirement never required six scenes. The desired rule is:

> The Narrative Architect chooses the minimum sufficient scene decomposition that best protects coherence, pacing, age fit, causal progression and requested length.

Application code owns validity. The model owns the proposed scene count and narrative decomposition.

## Candidate v4 role split

- Narrative Architect: `anthropic/claude-sonnet-5`
- Scene writer: `openai/gpt-5.6-luna`
- Continuity evaluator: `typesafe/jev-1.13`
- Semantic judge: `anthropic/claude-haiku-4.5`

Scene count range in the experiment: 2–12.

Each scene carries:

- `narrative_role`;
- `relative_weight`;
- purpose;
- entry state;
- beats;
- prior evidence;
- handoff;
- open threads.

Exactly one scene must be `PAYOFF`. The final scene must be `RESOLUTION`. PAYOFF must precede RESOLUTION. No numeric scene position owns those semantics.

## Experiment fixture

Primary cell:

- age: 10 / MIDDLE_CHILD;
- family: `puzzle_problem_solving`;
- reading mode: `INDEPENDENT_READER`;
- target: 2,800 words.

This cell was chosen because historical v3 evidence includes both clean and repair-heavy runs, so it is suitable for observing structural and continuity burden.

## Run 1 — 36008607397 — diagnostic, not valid dynamic-scene evidence

Source SHA:

`484382782c379f13a4e2a13202722b20760d1b1e`

Evidence branch:

`evidence/dynamic-sonnet-v4-36008607397`

Observed:

- Sonnet chose 6 scenes;
- plan Haiku average: 4.857;
- final story: 2,692 words;
- deterministic errors: none;
- final semantic judge: 3.875 average, continuity 3;
- pipeline accepted: false;
- total pipeline cost: USD 0.16752763;
- total time: 285.235 s.

### Why Run 1 does not answer the dynamic-scene question

The inherited fixture still contained:

`Preserve continuity across all six scenes.`

Sonnet explicitly cited that constraint as the reason it had to choose six scenes.

Therefore Run 1 is retained as diagnostic evidence but is not evidence that Sonnet independently preferred six scenes.

### Important defect discovered in Run 1

The SceneGraph itself contained an ambiguous pattern statement. Scene 4 prose repair then attempted to solve the downstream contradiction while the plan remained immutable.

Two scene semantic repairs plus two final targeted polish cycles were attempted. The final story no longer contained the exact phrase the final judge complained about, but the immutable SceneGraph still carried the ambiguous rule and the judge continued to target Scene 4.

Canonical lesson:

> Repair ownership must follow defect ownership.

If the defect originates in StoryContract/SceneGraph, prose repair is the wrong layer. The pipeline must escalate to plan repair/regeneration or reject the plan before prose.

A second related issue was observed: historical repair evidence can anchor the final judge on an already-fixed phrase. Final judgment must prioritize the current artifact and must not re-emit a stale defect solely from repair history.

## Run 2 — 36009516596 — first valid dynamic-scene evidence

The experiment fixture was copied to a scene-count-neutral version. The only semantic governance change was replacing the fixed-six continuity requirement with continuity across the complete story and the Narrative Architect's chosen SceneGraph.

Source SHA:

`e2cfbd524da8549b4c56578c28ae2be691ad546e`

Evidence branch:

`evidence/dynamic-sonnet-v4-36009516596`

Provider preflight:

- access available: true;
- key limit remaining before run: USD 9.33783092;
- monthly usage before run: USD 10.66216908.

### Sonnet decision

Sonnet selected **5 scenes**, with rationale:

- setup;
- two distinct evidence/testing stages;
- one payoff;
- one resolution;
- merging scenes would blur evidence steps or leak the solution;
- adding scenes would pad a 2,800-word independent-reader story.

Roles:

1. SETUP
2. RISING_ACTION
3. RISING_ACTION
4. PAYOFF
5. RESOLUTION

Relative weights:

`15 / 20 / 20 / 25 / 20`

Allocated word budgets:

`420 / 560 / 560 / 700 / 560`

### Result

- accepted: **true**;
- final words: **2,607 / 2,800**;
- repeated 8-gram ratio: **0.0**;
- deterministic errors: none;
- total scene attempts: **8**;
- semantic scene repairs: **3**;
- final targeted repairs: **0**;
- final Haiku: **4.0 average, minimum 4, no critical failures**;
- whole-story JEV: all metrics above threshold;
- total time: **277.160 s**;
- total cost: **USD 0.131251818**.

Plan stage:

- plan Haiku average: 4.714;
- plan deterministic validation: pass;
- JEV decomposition fitness: 0.88;
- JEV plan warnings:
  - constraint_coverage: 0.65;
  - no_unexplained_dependencies: 0.79.

The plan still proceeded because the current plan acceptance gate is deterministic validation + Haiku acceptance; JEV plan signals are advisory.

### Scene-level warning that remains after PASS

Scene 4 PAYOFF required two semantic repairs.

Final scene-level JEV still reported:

`no_contradiction = 0.77 < 0.80`

and:

`continuity_escalation_required = true`.

However the assembled whole-story JEV later reported:

`no_contradictions = 0.85`

and the final Haiku accepted every criterion at 4.

This is not automatically wrong: local uncertainty can disappear when the entire story is visible. But the authority rule is currently underspecified.

## New architecture requirements discovered

### V4-R1 — Variable scene count

No production prompt, validator, budget allocator, continuity evaluator or final judge may encode six scenes or Scene 5/6 semantics.

Narrative semantics belong to roles, not numeric positions.

### V4-R2 — Scene-count-neutral fixtures

Qualification fixtures must not contain a scene-count constraint unless scene count itself is an explicit product requirement of that fixture.

### V4-R3 — Repair ownership routing

Classify each detected defect before repair:

- StoryContract defect -> contract/plan escalation;
- SceneGraph defect -> plan repair/regeneration;
- scene prose defect -> local prose repair;
- state_delta defect -> structured scene regeneration under immutable prior state;
- final style-only defect -> bounded prose polish.

Do not try to repair an immutable plan defect by rewriting prose.

### V4-R4 — Stale-evidence isolation

Final semantic judgment must judge the current assembled artifact. Historical repair attempts may be retained for audit but must not cause a defect to be repeated when the current prose no longer contains it.

### V4-R5 — Cross-level continuity authority

Define an explicit rule for a scene-level JEV warning that remains after bounded repairs while whole-story JEV and final Haiku pass.

Until this is defined, a story with `continuity_escalation_required=true` must be considered accepted-with-warning evidence, not proof of production readiness.

### V4-R6 — Plan JEV governance

The plan stage currently allows Haiku acceptance to override below-threshold JEV advisory signals.

Before promotion, define whether:

- specific plan-JEV dimensions are blocking;
- warnings must be explicitly resolved by prose contracts;
- or a stronger plan repair/escalation is required.

## Cost observation

The valid dynamic v4 run cost USD 0.131251818. At the 2026-09-24 observed USD/TRY rate around 48.84, this is approximately **6.41 TL per story** for this sample.

Historical v3 MIDDLE_CHILD × puzzle runs cost approximately USD 0.0478–0.0684, roughly **2.34–3.34 TL** at the same rate.

Therefore Sonnet planning is materially more expensive and must earn its cost through reduced failure/retry burden, higher narrative quality, or better cross-cell robustness.

One run is not enough to establish that benefit.

## Decision after the first valid run

Do **not** resume the 32/80 -> 80/80 v3 campaign.

Do **not** promote v4 from one successful story.

Next controlled work:

1. implement/verify repair-ownership routing and cross-level gate semantics;
2. keep scene-count-neutral fixtures;
3. run a small v4 validation set across materially different lengths/ages/families;
4. compare Luna-planned v4 vs Sonnet-planned v4 under the same dynamic protocol;
5. promote a planner strategy only if the evidence justifies the added cost;
6. only then restart broad Capability Cube qualification under the promoted protocol identity.

## Evidence classification

- v3 evidence remains valid historical evidence for `english-story-production.v3`;
- v4 experimental runs must never be mixed into the v3 Capability Cube;
- Run 1 is diagnostic because the fixture still forced six scenes;
- Run 2 is the first valid dynamic-scene observation;
- v4 remains EXPERIMENTAL until governed promotion criteria are met.
