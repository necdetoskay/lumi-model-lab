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


## Four-length validation sweep — 36018357054

Evidence branch:

`evidence/story-v5-length-sweep-36018357054`

Purpose:

Test the same v5 whole-draft protocol across materially different story lengths, ages, and narrative families without changing model roles or acceptance thresholds.

Cases:

| Case | Target | Final | Scenes | Normalization | Repair | Haiku | Outcome |
| --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| age 5 / nature | 500 | 564 | 4 | no | no | 4.875 | commit-ready |
| age 9 / exploration | 1500 | 1783 | 5 | no | no | 4.875 | commit-ready |
| age 12 / puzzle | 2800 | 2994 | 5 | no | no | 4.875 | commit-ready |
| adult / world-lore | 4200 | 5001 | 7 | no | no | 4.875 | commit-ready |

All four stories:

- passed the deterministic word and repetition gates on the first whole draft;
- required zero length normalization;
- required zero semantic prose repair;
- had repeated 8-gram ratios at or near zero;
- passed every whole-story JEV threshold;
- produced schema-valid StoryOutcome proposals;
- did not write to the database.

### Dynamic scene-count evidence

The architect did not collapse onto a fixed six-scene pattern:

- 500 words -> 4 scenes;
- 1500 words -> 5 scenes;
- 2800 words -> 5 scenes;
- 4200 words -> 7 scenes.

This is positive evidence that scene count can be owned by the Narrative Architect while PAYOFF and RESOLUTION remain role-based rather than position-based.

### Continuity trend

JEV remained above threshold in every case.

Notable values:

- causal chain: 0.95 in all four cases;
- goal continuity: 0.97–0.98;
- evidence progression: 0.95–0.96;
- no contradictions: 0.90 / 0.91 / 0.84 / 0.84 as stories became more complex;
- decomposition fitness: 0.91 / 0.89 / 0.88 / 0.87.

The decline in contradiction confidence and decomposition fitness at higher complexity is not a failure, but it is a useful signal for future qualification. Longer stories should not be declared equally easy merely because they pass.

### Cost and latency at the observed 2026-09-24 exchange rate

Reported per-run model costs including whole-story JEV:

- 500-word story: about 0.61 TL, 59.7 s;
- 1500-word story: about 0.91 TL, 83.9 s;
- 2800-word story: about 1.16 TL, 104.5 s;
- 4200-word story: about 1.53 TL, 134.7 s.

Reported total for the four-story sweep: about 4.21 TL.

Provider preflight usage before/after the sweep moved by less than the sum of per-call reported costs, likely because provider account usage reporting is not guaranteed to update synchronously. For experiment accounting, immutable per-call evidence remains primary.

### Judge saturation discovered

All four materially different stories received the exact same Haiku pattern:

- instruction following: 5;
- coherence: 5;
- character consistency: 5;
- age appropriateness: 5;
- creativity: 4;
- style quality: 5;
- continuity: 5;
- ending quality: 5;
- average: 4.875.

This is too uniform to treat Haiku's scalar score as a high-resolution quality metric.

Decision:

> Haiku may remain a candidate production acceptance gate, but its 1–5 score must not be treated as sufficient evidence for relative story quality or model ranking.

Model Lab comparisons should add a calibrated pairwise/relative judge path before using judge scores to choose one generator/architect over another.

### StoryOutcome over-extraction discovered

The untyped prototype extractor sometimes proposes transient facts as persistent state, for example:

- a child's current activity;
- a temporary emotional state;
- an item briefly picked up and then put back;
- generic adult-support relationship wording.

These are story-supported facts, but they are not automatically canonical database mutations.

Decision:

> Evidence support is necessary but not sufficient for persistence.

Production state extraction must be closed by application-provided authority:

- canonical entity IDs;
- current revisions/fingerprints;
- allowed mutation types;
- persistence class;
- legal fields;
- old/current value where relevant.

The model must emit only typed `StateMutationProposal` records inside that closed contract. Transient scene facts should remain story evidence or memory candidates unless the application schema explicitly allows persistence.

## Updated v5 assessment after the four-length sweep

The whole-draft candidate is now materially stronger than a one-story proof of concept.

Positive evidence:

- 4/4 first-draft deterministic PASS;
- 4/4 JEV PASS;
- 4/4 semantic gate PASS;
- 4/4 outcome-schema PASS;
- zero prose repairs;
- zero length normalization in the sweep;
- scene count adapted to story length/complexity;
- low cost and latency relative to the earlier scene-by-scene Sonnet sample.

Remaining blockers are now less about basic prose generation and more about governance:

1. typed state-mutation authority;
2. judge calibration / pairwise quality discrimination;
3. production-like Character + World + Opportunity + Canon + Saga context;
4. atomic/idempotent application commit;
5. larger reliability sample before any SaaS SLO claim.

The evidence does **not** justify 80-cell qualification yet, but it does justify treating v5 whole-draft as the leading production-candidate architecture.


## Typed state-mutation authority calibration — 36023172608

Evidence branch:

`evidence/story-v5-hardening-36023172608`

The previously discovered free-form StoryOutcome surface was replaced experimentally by a closed application-owned authority contract.

The authority provides:

- an authority revision;
- canonical entity references;
- a finite list of allowed mutation types;
- the exact field key for each mutation;
- persistence classification.

The model may emit only exact `(mutation_type, entity_ref, field_key)` tuples from that list.

### Result

The age-5 / 500-word story run passed:

- accepted: true;
- 457 / 500 words;
- 4 dynamic scenes;
- deterministic errors: none;
- JEV: all dimensions above threshold;
- Haiku: 4.875;
- StoryOutcome validation errors: none;
- `commit_ready=true`;
- database write: false.

The typed extractor emitted only five authorized mutations:

1. protagonist goal completion;
2. protagonist knowledge addition;
3. blue-tag world location update;
4. garden marker-status update;
5. missing-tag thread resolution.

The earlier over-persistence classes did **not** appear:

- no transient `emotional_state`;
- no `current_activity`;
- no temporary inventory add/remove;
- no generic supportive-relationship mutation;
- no model-invented field path.

Decision:

> Closed application authority materially improves state safety and becomes a required v5 production boundary.

The model still proposes values and evidence. The application remains authoritative for schema validation, revision/fingerprint checks, conflict resolution and database commit.

## Pairwise judge calibration — Sonnet 5

Haiku's scalar-score saturation motivated a separate relative-quality experiment.

Two already-accepted versions of the same 1,500-word `The Lantern Map` fixture were compared blindly:

- Candidate A: 1,410-word normalized v5 story from run `36017226649`;
- Candidate B: 1,783-word first-draft v5 story from sweep `36018357054`.

Generator identity was not shown to the judge.

### Initial pairwise transport failure

The first pairwise attempt inside run `36023172608` was not a quality result.

Sonnet 5 consumed 2,199 of a 2,200-token completion budget as hidden reasoning and returned no visible JSON:

`finish_reason=length`

Decision:

- classify this as request-policy failure, not judge/model-quality failure;
- pairwise profile changed from high reasoning / 2,200 max tokens to medium reasoning / 5,000 max tokens so visible structured output has sufficient budget.

### Successful order-swapped retry — 36023582660

Evidence branch:

`evidence/story-v5-pairwise-36023582660`

Protocol:

`story-pairwise-judge.v1`

Judge:

`anthropic/claude-sonnet-5`

The exact same pair was judged twice:

1. A vs B;
2. B vs A.

The second result was normalized back to the original candidate labels.

Forward judgment:

- overall: B;
- preference strength: SMALL.

Reverse-order judgment after normalization:

- overall: TIE;
- preference strength: SMALL.

Only 3 of 7 criterion preferences remained identical after the order swap.

Calibration result:

- `status=POSITION_SENSITIVE`;
- `calibrated_winner=INCONCLUSIVE`;
- overall consistency: false.

Pairwise calibration cost:

- forward: USD 0.029858;
- reverse: USD 0.026448;
- total: USD 0.056306.

### Pairwise judge decision

This result does **not** mean Sonnet is a poor evaluator. It means one comparative LLM judgment is not a sufficiently stable authority for close story-quality decisions.

Canonical rules:

1. never choose a model from one A/B judgment;
2. every counted pairwise observation must be blind to generator identity;
3. every counted pair must be evaluated in both presentation orders;
4. an order-sensitive pair is `INCONCLUSIVE`, never a forced winner;
5. model-level comparison requires multiple stable pairs across distinct fixtures/ages/families/lengths;
6. Haiku scalar scores and Sonnet pairwise preferences are evidence signals, not independent promotion authority;
7. application/model-routing decisions must use an evidence aggregate rather than a single judge verdict.

This is a deliberate guard against position bias and judge overconfidence.

## Updated governance status after hardening calibration

The two governance issues discovered by the four-length sweep now have concrete experimental answers:

### State persistence

Status: **promisingly closed at the prototype boundary**.

Typed mutation authority successfully prevented the transient/free-form state classes observed in the untyped extractor.

Still required before LUMI integration:

- real canonical entity IDs;
- real Character/World/Saga/Opportunity mutation schemas;
- revision/fingerprint preconditions;
- deterministic old-value/current-value conflict checks;
- atomic and idempotent application commit.

### Relative quality judgment

Status: **not closed by one stronger judge**.

Sonnet's order-swapped result was position-sensitive on a close pair. Therefore relative model quality must be inferred from a multi-fixture calibrated comparison set rather than a single story duel.

### Production-candidate direction

The leading generation architecture remains v5 whole-draft.

The next highest-value evidence should come from production-like LUMI context:

`Character + World + Opportunity + Canon + Saga + relevant memories`

rather than immediately expanding to an 80-cell synthetic qualification campaign.


## Deterministic contract regression — 36024587848

The typed-state and pairwise calibration invariants were locked with unit tests.

Result:

**11 / 11 PASS**

Covered fail-closed cases include:

- model-invented mutation field;
- transient emotional-state persistence without authority;
- stale authority revision;
- stale entity base revision;
- wrong entity fingerprint;
- invalid evidence scene;
- duplicate mutation;
- valid authorized mutation;
- A/B label reversal normalization;
- presentation-order disagreement -> `INCONCLUSIVE`.

An earlier test run failed because the positive fixture omitted entity version metadata while the validator already required it. The validator was not weakened. The test fixture was repaired to include the required revision/fingerprint preconditions, and the fresh run passed all contracts.


## Typed state authority hardening — 36023901260

Evidence:

`evidence/story-v5-typed-state-36023901260`

The state extractor was converted from free-form StoryOutcome fields to a closed application-owned mutation authority.

Each allowed mutation now binds to:

- mutation type;
- canonical entity reference;
- allowed field key;
- entity base revision;
- entity base fingerprint;
- story evidence scenes.

The validation run passed:

- story accepted;
- 4 scenes / 412 words for the 500-word fixture;
- no repair;
- no length normalization;
- StoryOutcome validation errors: none;
- `commit_ready=true`;
- DB write: false.

The generated mutations copied the application-provided base revisions and fingerprints exactly.

Transient proposals previously observed, such as current activity, temporary emotion, and brief inventory handling, disappeared because those fields were not authorized.

Deterministic contract tests now explicitly fail closed on:

- model-invented fields;
- unauthorized transient-state mutation types;
- stale authority revision;
- stale entity base revision;
- stale entity fingerprint;
- invalid evidence scene;
- duplicate mutation.

Decision:

> Evidence support alone never creates persistence authority. The application owns the closed mutation catalog and optimistic-concurrency identity.

## Pairwise judge calibration — 36023582660

Evidence:

`evidence/story-v5-pairwise-36023582660`

Two already-accepted versions of the same 1,500-word Lantern Map fixture were judged blindly by Claude Sonnet 5.

Protocol:

1. candidate A vs B;
2. candidate order reversed;
3. second result normalized back to the original candidate identities;
4. a winner is accepted only when the overall result remains stable after the swap.

Initial pairwise attempt exposed a runtime-policy defect: a 2,200-token completion budget was consumed almost entirely by reasoning, leaving no visible JSON. This was a transport/budget failure, not a quality verdict.

The corrected run used medium reasoning and a 5,000-token completion budget.

Results:

- forward order: candidate B, SMALL preference;
- reversed order normalized to original identities: TIE, SMALL preference;
- overall consistency: false;
- stable criteria: 3 / 7;
- calibration status: `POSITION_SENSITIVE`;
- calibrated winner: `INCONCLUSIVE`.

Total Sonnet cost for the two comparison calls: USD 0.056306.

Decision:

> A strong pairwise judge is not automatically a stable ranking authority for close stories. Model Lab pairwise comparisons must be blind and order-swapped. Order disagreement produces INCONCLUSIVE, never a forced winner.

Consequences:

- Haiku remains useful as a production acceptance gate;
- Sonnet pairwise is a Model Lab diagnostic / relative-quality tool, not a per-story production dependency;
- scalar judge scores are not sufficient for generator ranking;
- pairwise winners must pass position-bias calibration.

## First production-like LUMI context run — 36024405327

Evidence:

`evidence/story-v5-production-like-36024405327`

The v5 pipeline was extended beyond a flat StorySpec with an application-compiled context pack containing:

- Character state and knowledge boundary;
- World state and Local Area statuses;
- current Opportunity;
- Canon revision/fingerprint and hard rules;
- eligible Saga context and forbidden reveal;
- relevant memory;
- canonical entity revisions and fingerprints.

Fixture:

- character: Deniz, age 10;
- target: 1,500 words;
- unknown boundary: `OLD_PUMP_PATH` remains RUMORED;
- explicit hidden-fact exclusions;
- opportunity requires investigation from known public ground only.

Result:

- accepted: true;
- 5 dynamically selected scenes;
- 1,672 words;
- repetition ratio: 0.0;
- no length normalization;
- no semantic repair;
- elapsed: 90.368 seconds;
- JEV context-authority probability: 0.96;
- all JEV dimensions above threshold;
- Haiku acceptance: 4.875 average;
- StoryOutcome validation errors: none;
- `commit_ready=true`;
- DB write: false.

Human inspection confirmed:

- `OLD_PUMP_PATH` was never entered;
- its RUMORED status was preserved;
- no hidden pump-house facts were revealed;
- no adult solved the central investigation;
- the character explicitly preserved an unseen contact-point uncertainty;
- the story did not manufacture danger.

This is the first v5 evidence that the whole-draft architecture can preserve application-provided G2/Living-Universe knowledge boundaries rather than only solve standalone benchmark briefs.

### Epistemic-state issue discovered

The accepted story correctly concluded that a repaired sign/bracket was the **best-supported explanation** for the sound while preserving uncertainty about the exact contact point.

The first state authority represented this as `WORLD_FACT_SET`.

That is too strong.

A supported hypothesis is not equivalent to a canonical fact merely because the story and judges accept it.

Decision:

> Story-state persistence must preserve epistemic class.

The experimental authority is therefore being hardened to distinguish facts from best-supported hypotheses. A hypothesis/uncertainty must never be silently upgraded to FACT during outcome extraction or commit.

Required state proposal properties now include:

- mutation type;
- field key;
- epistemic class where applicable;
- base revision;
- base fingerprint;
- proposed value;
- evidence scenes.

## Updated judge interpretation

The production-like Haiku result again emitted the familiar 4.875 score pattern. Its textual summary also contained minor internal inconsistencies (for example, referring to six constraints while enumerating seven, and describing creativity as a 5 while the structured score remained 4).

This does not invalidate the acceptance result, but reinforces the existing rule:

> Structured acceptance fields are authoritative; free-form judge prose is explanatory evidence only. Haiku scores are not a high-resolution ranking instrument.



## Epistemic-state hardening validation — 36024864692

Evidence:

`evidence/story-v5-production-like-36024864692`

The production-like context case was rerun after adding explicit epistemic mutation classes.

The authority no longer permits the bounded sound explanation to be stored as `WORLD_FACT_SET`.

It permits:

- mutation type: `WORLD_HYPOTHESIS_SET`;
- field: `commons.sound_hypotheses`;
- epistemic class: `BEST_SUPPORTED_HYPOTHESIS`.

Result:

- accepted: true;
- 5 dynamic scenes;
- 1,468 / 1,500 words;
- repetition ratio: 0.0;
- no length normalization;
- no semantic repair;
- JEV context authority: 0.97;
- all JEV dimensions above threshold;
- Haiku accepted;
- outcome validation errors: none;
- `commit_ready=true`;
- elapsed: 82.466 seconds.

The accepted mutation set preserved four distinct authority classes:

- `CHARACTER_KNOWLEDGE`;
- `BEST_SUPPORTED_HYPOTHESIS`;
- `THREAD_STATE`;
- `WORKFLOW_STATE`.

The world mutation was:

`WORLD_HYPOTHESIS_SET / commons.sound_hypotheses / BEST_SUPPORTED_HYPOTHESIS`

and explicitly retained the statement that the explanation may not account for every occurrence.

All proposals copied their application-owned base revisions and fingerprints exactly.

The deterministic contract suite also passed after adding a fail-closed test proving that a proposal cannot replace an authorized `BEST_SUPPORTED_HYPOTHESIS` epistemic class with `FACT`.

Decision:

> Epistemic status is part of state authority and optimistic-concurrency identity. Story acceptance does not authorize uncertainty collapse.

## v5 status after state + context hardening

The leading candidate now has evidence for:

- dynamic model-owned scene count;
- whole-draft generation;
- deterministic length/repetition gates;
- whole-story JEV;
- final semantic acceptance;
- application-compiled Character + World + Opportunity + Canon + Saga + memory context;
- knowledge-boundary preservation;
- typed mutation authority;
- base revision/fingerprint binding;
- epistemic-class preservation;
- fail-closed deterministic contract tests.

Still not proven:

1. atomic application commit;
2. idempotent replay;
3. conflict behavior when a base revision/fingerprint changes after story generation;
4. durable async recovery across provider/process failure;
5. larger production-like reliability sample.

Next engineering target:

`Validated StateMutationProposal[] -> Atomic/Idempotent Commit Simulator -> conflict/no-partial-write tests`

No real LUMI database write is authorized by this experiment.


## Atomic/idempotent state commit simulation — 36025700209

Evidence:

`evidence/story-v5-state-commit-36025700209`

Protocol:

`state-commit-simulator.v1`

The accepted production-like typed outcome from the epistemic-state run was applied to a deterministic state-store simulator.

### First commit

Status:

`COMMITTED`

Mutated entities:

- `CHARACTER:PROTAGONIST`;
- `WORLD:CURRENT`;
- `SAGA:CURRENT`;
- `OPPORTUNITY:CURRENT`.

Each touched entity advanced exactly one revision:

- Character 21 -> 22;
- World 34 -> 35;
- Saga 9 -> 10;
- Opportunity 7 -> 8.

New deterministic fingerprints were generated after mutation.

Important invariant:

`OLD_PUMP_PATH` remained `RUMORED` in committed world state.

The opportunity moved from `AVAILABLE` to `CONSUMED`.

The bounded sound explanation persisted under `commons.sound_hypotheses`, not as a world fact.

### Identical replay

The same outcome with the same idempotency key was submitted again.

Status:

`IDEMPOTENT_REPLAY`

Results:

- no entity mutated;
- no revision incremented;
- no duplicate knowledge appended;
- state hash before replay == state hash after replay.

### Stale-state conflict

A controlled fixture advanced the World revision from 34 to 35 before attempting the original outcome whose base revision remained 34.

Status:

`CONFLICT`

Conflict evidence:

`mutation_1_stale_revision:35!=34`

Results:

- zero mutated entities;
- state hash before == state hash after;
- no Character mutation leaked through;
- no Opportunity consumption occurred;
- no partial write.

### Deterministic contract suite

The expanded v5 contract suite passed 18/18 tests, including:

- authorized mutation success;
- invented field rejection;
- transient emotion rejection;
- stale authority revision rejection;
- stale entity base revision rejection;
- stale entity fingerprint rejection;
- epistemic-class mismatch rejection;
- invalid evidence rejection;
- duplicate mutation rejection;
- blind pairwise order-swap policy;
- atomic successful commit;
- identical idempotent replay;
- stale revision atomic abort;
- stale fingerprint atomic abort;
- idempotency-key collision rejection;
- rollback after an apply-stage failure occurring after a prior working-copy mutation.

Decision:

> State commit is validate-all-first, apply-to-working-copy, then publish atomically. Any authority, concurrency, or apply failure produces zero authoritative partial writes.

## Updated v5 production-candidate boundary

The experimental pipeline has now demonstrated, in Model Lab:

`Compiled Context -> Dynamic Architect -> Whole Draft -> Deterministic Gates -> JEV Context Gate -> Haiku Acceptance -> Typed/Epistemic Mutation Proposal -> Atomic/Idempotent Commit Simulation`

The Model Lab simulator does not authorize direct production database writes.

Remaining proof obligations before LUMI integration:

1. map the simulator contract to LUMI's real G2 entity/revision transaction boundary;
2. durable story-job lifecycle and process/provider recovery;
3. production-like multi-context reliability sample;
4. real application transaction rollback/idempotency tests;
5. end-to-end user delivery semantics after commit.

