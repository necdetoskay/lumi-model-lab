# Dynamic Scene v4 — Sonnet Architect / Luna Writer — One-Story Experiment

Date: 2026-09-24  
Status: EXPERIMENTAL — NOT PROMOTED  
Branch: `experiment/dynamic-scene-sonnet-v4-one-story-20260924`

## Question

Can a stronger Narrative Architect choose the scene count and StoryContract/SceneGraph, while a cheaper model writes scene prose, with better structural flexibility than the fixed-six-scene v3 pipeline?

Test cell:
- age tier: MIDDLE_CHILD
- exact age: 10
- narrative family: puzzle_problem_solving
- target: 2800 words
- planner: `anthropic/claude-sonnet-5`
- writer: `openai/gpt-5.6-luna`
- continuity evaluator: `typesafe/jev-1.13`
- semantic judge: `anthropic/claude-haiku-4.5`

## Run 1 — invalid scene-count experiment, useful failure evidence

Run: `36008607397`

The v4 planner was dynamic, but the inherited v3 fixture still contained:

> Preserve continuity across all six scenes.

Sonnet therefore chose six scenes and explicitly cited that constraint. This run MUST NOT be used as evidence that Sonnet independently preferred six scenes.

Result:
- story accepted: false
- scenes: 6
- words: 2692 / 2800
- deterministic errors: none
- final judge: 3.875 average; continuity 3
- cost: USD 0.167527630
- total time: 285.235 s

### New repair deadlock found

Scene 4 originally encoded an ambiguous rule using `every third number is skipped`.
The final prose-only repair successfully removed that phrase from the prose and replaced it with explicit wording: two numbers are listed, then one is skipped.

However, immutable `state_delta` still contained:
- `The sequence skips every third number...`
- `The Pattern Wall follows a repeating rule in which every third number is skipped.`

The final judge receives both prose and ContinuityLedger, so it continued to flag the stale canonical-state wording. The prose-only repair verifier reported success while the whole-story judge continued to fail.

Conclusion: prose-only repair cannot resolve a defect whose source is already committed into immutable state. The pipeline needs an explicit distinction between prose defect and canonical-state defect. A state defect must be repaired/regenerated before the scene is committed, or downstream scenes must be revalidated after a governed state correction.

## Fixture repair

A scene-count-neutral fixture was introduced for v4. The old fixed-six constraint is not valid input for dynamic SceneGraph qualification. A guard was also added so dynamic qualification can reject legacy fixed-scene constraints before paid generation.

## Corrected run A

Run: `36009516596`

Result:
- accepted: true
- Sonnet-selected scenes: 5
- rationale: five scenes were the minimum sufficient decomposition; adding more would pad the 2800-word independent-reader story
- roles: SETUP → RISING_ACTION → RISING_ACTION → PAYOFF → RESOLUTION
- budgets: 420 / 560 / 560 / 700 / 560
- actual words: 2607
- repetition ratio: 0
- deterministic errors: none
- final Haiku: all criteria 4, average 4.0, accepted
- whole-story JEV: all checks above threshold
- plan Haiku: 4.714 average, min 4
- scene attempts: 1 / 2 / 1 / 3 / 1
- semantic repairs: 0 / 1 / 0 / 2 / 0
- Scene 4 ended with scene-level `no_contradiction=0.77` and escalation flag, while whole-story JEV later scored no_contradictions=0.85 and final Haiku accepted. This evaluator disagreement remains an open governance question.
- total cost: USD 0.131251818
- total time: 277.160 s
- Sonnet planner alone: USD 0.080706

## Corrected replication B

Run: `36009842023`

Result:
- accepted: true
- Sonnet-selected scenes: 6
- rationale: setup + false-hypothesis test + two clue-gathering steps + payoff + resolution were minimally sufficient
- roles: SETUP → COMPLICATION → RISING → CLIMAX_BUILD → PAYOFF → RESOLUTION
- budgets: 420 / 420 / 420 / 560 / 560 / 420
- actual words: 2435
- repetition ratio: 0
- deterministic errors: none
- final Haiku: all criteria 4, average 4.0, accepted
- whole-story JEV: all checks above threshold
- no semantic repairs
- one extra scene attempt occurred in Scene 5
- total cost: USD 0.131849230
- total time: 221.556 s
- Sonnet planner alone: USD 0.089336

Important judge inconsistency:
- deterministic actual word count was 2435
- Haiku summary claimed approximately 2835 words
The deterministic count remained authoritative and the story still passed the current total-word hard gate (75%-125%). Judge prose summaries must never be used as numeric authority.

## v3 comparison

Comparable accepted v3 run `35987414041`:
- fixed scenes: 6
- accepted: true
- words: 2724
- scene attempts: 6 total
- semantic repairs: 0
- final Haiku: 4.0 average
- total cost: USD 0.047813598
- total time: 147.189 s
- Luna planner cost: USD 0.005465600
- plan Haiku: 4.857 average

Other v3 repeats in the same cell reached 10 scene attempts and 4 semantic repairs while still passing, at USD 0.065478006–0.068435044.

## What was learned

1. Dynamic scene count works technically. Once the legacy fixture leak was removed, Sonnet independently selected five scenes in one accepted run and six in another accepted run.
2. Scene count is not yet stable. The same cell/spec can lead Sonnet to defensibly choose five or six scenes. This may be healthy creative variance, but production routing must not assume scene count is deterministic.
3. Sonnet has not yet demonstrated superior plan quality versus Luna. In the comparable clean v3 run, Luna's plan also scored 4.857/5. Sonnet plan scores were 4.714 and 4.857.
4. Sonnet is materially more expensive as configured. High-reasoning Sonnet planner alone cost USD 0.080706–0.089336 in corrected runs, versus USD 0.0054656 for the comparable Luna planner.
5. Stronger planning did not eliminate repair burden. One corrected run needed three semantic repairs total; the replication needed none.
6. Immutable-state repair has a real deadlock mode. Prose-only repair can be correct while stale state_delta keeps the final judge failing.
7. Evaluator hierarchy needs clarification. A scene can remain below JEV threshold with an escalation flag while whole-story JEV and Haiku later accept.
8. Semantic judge narrative text is not numerical evidence. Haiku can misstate word count; deterministic metrics must remain authoritative.

## Decision

Do not promote v4 and do not resume the 80-cell qualification yet.

Before additional broad paid testing:
1. separate prose defects from canonical-state defects;
2. prevent unresolved canonical-state defects from being committed into the ledger;
3. define authority for scene-level JEV escalation vs whole-story acceptance;
4. make the v4 scene-neutral fixture/protocol identity explicit;
5. reduce Sonnet planning token burden (test lower reasoning / tighter output contract) before deciding whether the stronger planner is economically justified;
6. then run a small controlled Luna-Architect vs Sonnet-Architect comparison using the same dynamic-scene protocol.

No result from this experiment should be mixed into the existing v3 Capability Cube.
