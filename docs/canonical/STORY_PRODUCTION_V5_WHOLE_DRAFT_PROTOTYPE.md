# LUMI Story Production v5 — Whole-Draft Prototype

Date: 2026-09-24  
Status: EXPERIMENTAL / NOT PROMOTED  
Risk class: AEGIS L3

## Motivation

The v3/v4 story pipeline generated prose scene by scene. That architecture improved local control but also increased:

- model-call count;
- latency;
- repeated context transfer;
- evaluator disagreement surface;
- repair-loop complexity;
- chances of state drift between calls.

The v5 prototype tests a simpler production hypothesis:

> Plan once, write the complete story once, validate the complete story, repair only when a proven defect exists, then extract canonical state.

## Prototype flow

`StorySpec -> Dynamic Narrative Architect -> StoryContract + SceneGraph -> Whole Story Writer -> Deterministic Gates -> Whole-Story JEV -> Haiku Final Gate -> StoryOutcome Extractor -> Application-Owned DB Commit`

The database commit is intentionally not implemented in the prototype. The prototype emits a validated state proposal only.

## Authority boundaries

- Narrative Architect owns the proposed story decomposition and scene count.
- Application validation owns structural validity.
- Whole Story Writer owns prose only.
- JEV evaluates causal/continuity properties.
- Haiku acts as final production quality gate.
- StoryOutcome Extractor proposes state changes only after final story acceptance.
- The LUMI application, not an LLM, will own atomic/idempotent database commit.

## First mechanics proof

Models:

- architect: `openai/gpt-5.6-luna`
- whole-draft writer: `openai/gpt-5.6-luna`
- continuity evaluator: `typesafe/jev-1.13`
- semantic judge: `anthropic/claude-haiku-4.5`
- outcome extractor: `openai/gpt-5.6-luna`

The first valid generation run exposed one clear defect:

### Run 36016223639 — semantic success, deterministic word-budget failure

- target: 1,500 words
- actual: 2,119 words
- dynamic scenes: 5
- repeated 8-gram ratio: 0
- whole-story JEV: clean
- Haiku: 4.875 / 5
- repair targets: none
- terminal acceptance: false

The only blocking failure was:

`above_total_word_budget:2119>1875`

Canonical lesson:

> Whole-draft generation still requires application-owned scene-budget guidance. A single generation call does not mean an ungoverned length target.

## Governed word-budget proof

The prototype then normalized the total target across planner-provided scene weights and supplied both:

- per-scene word targets;
- hard total accepted range.

### Run 36016585318 — first accepted v5 whole-draft story

- target: 1,500 words
- actual: 1,567 words
- dynamic scenes: 6
- roles:
  - SETUP
  - INCITING_INCIDENT
  - INVESTIGATION
  - COMPLICATION
  - PAYOFF
  - RESOLUTION
- repeated 8-gram ratio: 0
- deterministic errors: none
- prose repair cycles: 0
- whole-story JEV: all dimensions >= 0.80
- Haiku average: 4.875
- Haiku minimum criterion: 4
- critical failures: none
- repair targets: none
- StoryOutcome validation: PASS
- StoryOutcome commit_ready: true
- database_written: false
- elapsed: 82.77 seconds

Observed costs:

- plan: USD 0.0046136
- whole draft: USD 0.00356635
- JEV: USD 0.000241374
- final Haiku: USD 0.008301
- StoryOutcome extraction: USD 0.0029447
- total observed: approximately USD 0.019667

At the observed 2026-09-24 USD/TRY rate near 48.85, the run was approximately 0.96 TL.

## State extraction proof

The accepted story produced a structured state proposal containing:

- character changes;
- world changes;
- relationship changes;
- inventory changes;
- knowledge changes;
- resolved threads;
- opened threads;
- memory candidates;
- opportunity effects.

Every evidence-bearing change cited supporting scene indexes.

This is not yet sufficient for production DB commit. Production still requires:

- canonical LUMI StoryOutcome schema;
- current-state revision/fingerprint;
- evidence-backed mutation rules;
- authority validation;
- conflict detection;
- idempotency key;
- transaction/outbox boundary;
- atomic Story + Character + World commit;
- post-commit revision/event creation.

## Interpretation

This single accepted story does not prove v5 superiority or production readiness.

It does provide a meaningful architectural signal:

- one planning call;
- one whole-draft call;
- one whole-story continuity pass;
- one final judge;
- zero repair;
- accepted story;
- validated state proposal;
- materially lower latency and cost than the recent sequential-scene Sonnet experiment.

The evidence justifies further controlled validation of the simpler whole-draft direction before returning to large Capability Cube campaigns.

## Next controlled validation

Do not run 80 cells yet.

Next evidence should answer:

1. Does whole-draft remain reliable across materially different story lengths?
2. Does it remain coherent in mystery, emotional, exploration and lore-heavy families?
3. At what length/complexity does whole-draft begin to fail compared with sequential scene generation?
4. Is Luna sufficient as Narrative Architect, or does Haiku/Sonnet materially improve the plan?
5. Can StoryOutcome extraction remain evidence-grounded under real LUMI Character + World + Opportunity + Canon context?
6. Can accepted stories reach the eventual production delivery SLO after durable job and atomic commit are included?

## Promotion rule

v5 remains experimental until a small diverse cohort demonstrates:

- no structural dependence on a fixed scene count;
- high first-draft acceptance;
- bounded repair burden;
- stable word-budget behavior;
- acceptable latency/cost;
- evidence-grounded StoryOutcome extraction;
- clear authority and commit semantics.

Existing v3/v4 evidence remains historical evidence under its original protocol identity and must not be mixed with v5 qualification evidence.
