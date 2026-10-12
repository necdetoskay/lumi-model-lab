# Q25 — Narrative Intent & Memory Bank V1

Status: EXPERIMENTAL DESIGN / NOT PRODUCTION AUTHORITY
Date: 2026-10-12
Owner: LUMI Model Lab, SpineForge
Reference: https://www.youtube.com/watch?v=Ps5M9Ab1rZI
Upstream idea: https://github.com/gratajik/book-memory-bank
Historical evidence: Q22 accepted with editorial findings; Q24 rejected, reviewer citation/overreach and state-expressiveness concerns. See PR #264.
Base: experiment/spineforge-v21-bounded-scene-quality
No automatic provider dispatch, merge or production promotion is authorized by this document.

## Decision and hypothesis
Test whether explicit narrative intent, durable-but-non-authoritative creative memory, and an editorial master outline improve human-perceived story quality and reduce mechanical prose compared with Q22/Q24 baselines. This is **not** a claim of proven improvement.

Do not copy book-memory-bank files as runtime architecture. Translate the useful concepts into versioned, typed, reproducible Model Lab contracts. No legacy/second production authority.

## Authority boundaries

1. Immutable G2 StoryContract / seed / canon / topology / knowledge permissions remain the hard source of truth.
2. NarrativeIntentV1 states dramatic question, desired reader experience, protagonist external goal/internal need, conflict, decision, consequence, stakes, emotional arc, payoff, unresolved/forbidden reveals, age/style parameters.
3. NarrativeMemoryV1 is a derived, versioned creative view: character voices, emotional context, relationship context, reader knowledge vs character knowledge, unresolved threads, motifs, repetitiveness avoidance, prior accepted narrative events. Every entry has source_ref, epistemic_type (fact/belief/rumor/editorial), scope, revision, confidence/provenance; hard facts are never invented.
4. MasterOutlineV1 contains semantic beats: dramatic purpose, desire, choice, obstacle, consequence, reader discovery, character discovery, emotional transition, setup/payoff and dependencies. It is not a MOVE/OBSERVE/CONTAINER transaction DSL.
5. All model suggestions are *candidates*; application assigns IDs/fingerprints and applies allowed transformations only.
6. Narrative Memory cannot mutate world/character state or silently upgrade beliefs/rumors to facts. Only separately accepted state extraction + typed authority can propose persistent changes.
7. For new actors/objects or unsupported containment, preserve literal prose/evidence and report STATE_MODEL_GAP; do not reject otherwise valid creative text merely because closed persistence vocabulary lacks an identifier. Actual hard canon violations still block.

## Prototype pipeline
```
frozen StoryContract + seed
  -> safe context compiler
  -> 3 distinct NarrativeIntent candidates (optional controlled variant)
  -> selected Intent (selection rationale and fingerprints)
  -> NarrativeMemory projection
  -> MasterOutline candidate + structural/authority gate
  -> one whole-story draft (writer sees narrative inputs, not mutation/reviewer schemas)
  -> deterministic hard constraints (canon, knowledge, ages, physical timeline, goal)
  -> read-only independent editorial review (not automatic reject authority)
  -> *post-story* typed state extraction + expressiveness report
  -> memory update proposal, accepted only from authorized source artifacts
  -> immutable evidence bundle
```
First Q25 test: NO AUTOMATIC REWRITE. Store original prose; do not repeat a failed call. Bounded repair is a separate later experiment. EN master / TR localization, if used, remain separately versioned.

## Review policy
Three disjoint classes:
- HARD_INVALID: evidence-grounded contradiction of frozen facts, prohibited knowledge, demonstrable temporal/spatial/causal failure, safety issue. Deterministic checks preferred.
- EDITORIAL_DEFECT: concrete reader-experience flaw with quotes, exact ranges and independent adjudication; not automatically blocking.
- EDITORIAL_PREFERENCE: subjective tone/style suggestion; never blocking.

Reviewer must cite existing exact contiguous source spans and immutable authority refs for factual allegations. Bad/nonexistent citations lead to INVALID_REVIEW, not story REJECT. A model's PASS cannot prove semantic completeness; a model's REJECT cannot alone prove poor prose. A human blinded assessment adjudicates ambiguous claims. No model self-grading used as golden truth.

## Frozen Q25 experiment protocol
- Preserve Q22/Q24 runs, outputs, rejected decisions, ledger and source archives unchanged.
- Reuse the same immutable mystery StoryContract/seed where lawful and the same age/length/locale targets.
- Baseline arm: existing Q24 whole-story concept, with its previously saved draft as historical reference; do not claim historical and new runs are statistically matched.
- Q25 arm: Intent + Memory + Outline + single whole-story draft. If a provider comparison is authorized later, hold writer model and decoding/word targets constant as much as possible.
- Record raw prompts, responses, selected synopses, memory snapshots, fingerprints, code SHA, provider/model versions, tokens, actual USD, latency, and any unknown charge.
- Compare: blinded human score for engagement, agency, dialogue, naturalness, plot satisfaction (anchored 1–5); hard-invalid rate; unsupported-review finding rate; extracted state coverage and state-model gaps; cost/latency.
- At least two independent blinded human readers or explicit adjudication for conflicting editorial verdicts. One story is diagnostic, not production qualification.
- Initial offline replay of Q22/Q24 and synthetic/fixture tests costs $0. No paid calls without new specific scoped authorization, call-count ceiling, between-call cost threshold and immutable preflight.
- First design objective: distinct writer/reviewer/state-extraction responsibility. Avoid solving narrative defects with mechanical state restrictions.

## Acceptance criteria for engineering lane
1. Frozen seed and StoryContract unchanged; no new world authority.
2. Deterministic schema tests for Intent, Memory and Outline; invalid provenance, knowledge leakage and revision mismatch fail closed.
3. Writer prompt contains creative brief/outline/authorized context only, excludes reviewer/state mutation schema.
4. Reviewer incorrect citations classified INVALID_REVIEW; editorial preference cannot trigger technical rejection.
5. Narrative memory update has no direct persistence side effects and is idempotently replayable.
6. State extraction explicitly separates missing authority-vocabulary (STATE_MODEL_GAP) from genuine contradictions.
7. Full offline comparison report includes human-rated evidence and source fingerprints. Synthetic tests cannot be reported as real generated-story success.
8. Production untouched; feature flag experimental only; PR remains draft pending comparative evidence and CI.

## Delivery phases
P0 freeze evidence + Q24 failure taxonomy and baseline.
P1 typed NarrativeIntentV1 + generation/selection.
P2 NarrativeMemoryV1 projection + provenance/knowledge controls.
P3 MasterOutlineV1 + plan gate and writer prompt separation.
P4 Q25 whole-draft orchestration + independent review policy + state gap reporting.
P5 offline/human benchmark, reproducible replay and proposal for explicitly authorized paid run.
P6 decision gate: RETAIN / ITERATE / REJECT; no automatic production promotion.

## Risks and falsifiers
- More structured memory may make prose even more mechanical: measure and reject if so.
- Compact memory may lose an authority fact: exact-ref invariants and adversarial fixtures.
- Selection introduces extra cost: account for all calls.
- Human scores might disagree: preserve dissent and use blinded presentation.
- State-model gaps are not excuses for real canon violations.
- Do not use the author's proprietary published book as a training corpus or copy living authors' identifiable wording.
