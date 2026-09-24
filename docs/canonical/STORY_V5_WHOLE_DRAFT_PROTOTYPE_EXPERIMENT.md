# Story v5 Whole-Draft Prototype — Canonical Experiment Record

Date: 2026-09-24  
Status: EXPERIMENTAL / NOT PROMOTED  
Risk class: AEGIS L3

## Goal

Test a simpler story-production architecture:

`Dynamic Architect -> Whole Story Draft -> Deterministic Gates -> JEV -> Semantic Judge -> StoryOutcome -> Application Commit`

The default prototype intentionally does **not** generate each scene in a separate model call.

## Prototype role split

- Narrative Architect: `openai/gpt-5.6-luna`
- Whole-story writer: `openai/gpt-5.6-luna`
- Continuity evaluator: `typesafe/jev-1.13`
- Semantic judge: `anthropic/claude-haiku-4.5`
- StoryOutcome extractor: `openai/gpt-5.6-luna`

The implementation lives on experimental branch:

`experiment/story-v5-whole-draft-prototype-20260924`

Prototype file:

`experiments/prototypes/story_v5_whole_draft_prototype.py`

The prototype never writes to the real LUMI database. It emits a validated dry-run `StoryOutcome` proposal only.

## Built-in fixture

- age: 9
- narrative family: `exploration_mystery`
- reading mode: `INDEPENDENT_READER`
- target: 1,500 words
- scene count: model-owned
- theme: careful observation turns uncertainty into understanding

The fixture is scene-count-neutral.

## Non-billable launch-path diagnostics

Two initial workflow runs failed before any model request because the standalone prototype was executed from a subdirectory without the repository root on `PYTHONPATH`.

No paid model tokens were consumed by those launch-path failures.

The workflow was corrected to run the prototype with repository-root module visibility.

## First real whole-draft run — 36016223639

Evidence branch:

`evidence/story-v5-whole-draft-36016223639`

### Architect decision

Luna selected 5 scenes:

1. SETUP
2. DISCOVERY
3. INVESTIGATION
4. PAYOFF
5. RESOLUTION

The selected decomposition was coherent, but the first whole draft produced 2,119 words for a 1,500-word target.

Result:

- deterministic FAIL only because `2119 > 1875` hard maximum;
- repeated 8-gram ratio: 0.0;
- JEV: all dimensions above threshold;
- final Haiku: 4.875 average, minimum 4, no critical failures;
- no semantic repair requested;
- state extraction correctly did not run because deterministic acceptance failed.

Important lesson:

> A whole-story writer can preserve excellent narrative quality while still missing the application-owned length contract.

Word budget is therefore an application constraint, not a model-trust assumption.

## Word-budget hardening

The prototype now provides:

- target total word count;
- hard total range;
- application-normalized per-scene word targets derived from planner relative weights.

If the draft is otherwise structurally valid and the only deterministic defect is total length, the prototype allows exactly one bounded `length normalization` pass.

That pass must preserve:

- StoryContract;
- SceneGraph;
- scene roles;
- facts;
- clue order;
- protagonist decisions;
- payoff;
- resolution;
- ending state.

It may remove redundant description, recap and repeated explanation. It may not invent new events.

## Successful v5 run — 36017226649

Evidence branch:

`evidence/story-v5-whole-draft-36017226649`

### Scene plan

Luna selected 5 scenes:

1. SETUP
2. INVESTIGATION
3. COMPLICATION
4. PAYOFF
5. RESOLUTION

Application-owned scene targets:

- Scene 1: 270 words
- Scene 2: 360 words
- Scene 3: 330 words
- Scene 4: 360 words
- Scene 5: 180 words

### Draft and normalization

Initial whole draft:

- 1,898 words.

Single bounded normalization:

- 1,410 words;
- target: 1,500;
- accepted range: 1,125–1,875;
- repetition ratio: 0.0;
- schema errors: none.

No additional prose repair was required.

### Continuity evidence

Whole-story JEV:

- causal_chain: 0.95
- goal_continuity: 0.97
- evidence_progression: 0.96
- no_contradictions: 0.89
- no_redundant_events: 0.94
- payoff_resolution: 0.96
- decomposition_fitness: 0.89
- below threshold: none
- next action: CONTINUE

### Semantic judge

Haiku:

- instruction_following: 5
- coherence: 5
- character_consistency: 5
- age_appropriateness: 5
- creativity: 4
- style_quality: 5
- continuity: 5
- ending_quality: 5
- average: 4.875
- minimum: 4
- critical failures: none
- repair targets: none

Result: semantic PASS.

### StoryOutcome

Outcome extraction ran only after deterministic + JEV + semantic acceptance.

Produced:

- world-state changes;
- character knowledge changes;
- rejected hypothesis knowledge;
- resolved threads;
- one opened thread for the permanent map redraw;
- one high-importance memory candidate;
- current opportunity consumed;
- no invented inventory or relationship change.

Outcome validation errors: none.

`commit_ready=true`

Database write:

`false`

This is intentional. The LUMI application remains the only authority allowed to perform an atomic/idempotent state commit.

## Cost and latency

Successful run:

- plan: USD 0.003590
- whole draft: USD 0.0039355
- one length normalization: USD 0.0033833
- final Haiku judge: USD 0.007519
- outcome extraction: USD 0.00266395
- JEV: USD 0.00022491
- approximate complete run total: USD 0.02131666
- elapsed pipeline time: 101.795 seconds

At the observed 2026-09-24 USD/TRY rate of about 48.79, this sample is approximately 1.04 TL.

This is not yet a generalized production cost. It is one 1,500-word fixture and uses Luna rather than a stronger architect.

## Comparison to the current scene-by-scene direction

The successful v5 sample used:

- one planning generation;
- one whole-story draft generation;
- one bounded length normalization;
- one whole-story JEV evaluation;
- one final judge;
- one outcome extraction.

There were no per-scene writer/JEV loops and no semantic prose repair.

This materially reduces orchestration surface compared with a default scene-by-scene pipeline.

However, one sample is not sufficient for promotion.

## State extraction authority issue discovered

The prototype currently permits the extractor to emit free-form field paths such as:

`lantern_loop.map_status`

This is suitable only for prototype inspection.

Production must not allow the model to invent database/state field names.

Required production rule:

> The application provides the current typed state snapshot, entity identifiers, allowed mutation schema and legal operations. The model may only propose mutations inside that closed contract.

Future output should therefore be closer to:

`StateMutationProposal[]`

with:

- canonical entity ID;
- mutation type;
- allowed field/contract key;
- old revision/fingerprint;
- proposed value;
- story evidence scenes;
- confidence/validation metadata.

The application validates and commits. The model never writes the database.

## Current architectural assessment

This experiment provides strong evidence that the simpler whole-draft direction is viable:

- model-owned dynamic scene count worked;
- a coherent complete story was produced;
- continuity remained high;
- semantic judge strongly accepted the result;
- bounded normalization corrected word length without a narrative repair loop;
- validated state outcome extraction worked;
- total latency and cost were materially lower than the earlier Sonnet-planner scene-by-scene sample.

The comparison is not apples-to-apples because fixture length and architect model differ.

## Decision

Do not promote v5 yet.

Do not resume broad 80-cell qualification yet.

Next controlled work:

1. close the typed `StateMutationProposal` contract;
2. validate the whole-draft architecture across short, medium and long stories;
3. test whether one bounded length-normalization pass remains exceptional rather than normal;
4. compare Luna vs Haiku vs stronger architect candidates under the same v5 protocol;
5. measure first-draft acceptance rate, repair rate, latency and TL cost;
6. only then choose the production-candidate protocol.

## Promotion intent

The desired production default is:

`Context Compiler -> Narrative Architect -> Whole Draft Writer -> Deterministic/JEV/Judge Acceptance -> StoryOutcome -> Atomic State Commit -> DELIVERED`

Repair remains an exception and must be routed by defect ownership.
