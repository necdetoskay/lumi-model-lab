# English-First Story Production Pipeline v1

Status: **HISTORICAL — superseded by ENGLISH_FIRST_STORY_PIPELINE_V3.md**
Date: 2026-09-23

## Goal

Build a reliable LUMI story-production line where narrative planning, scene generation, continuity evaluation, and quality judging operate on one canonical English master story. Turkish is a presentation translation produced only after the English master passes all production gates.

The design addresses unstable word count, weak scene-to-scene continuity, premature resolution, repeated events, and expensive whole-story regeneration after a local defect.

## Canonical language boundary

The internal narrative language for this pipeline is English.

Inputs that originate in Turkish are projected into an English StoryContextPack before planning. Canonical identifiers, enum values, revisions, numbers, chronology, item identities, character identities, and world-state facts remain language-neutral and must not be altered by projection.

The accepted English story is the master narrative artifact. Turkish is a downstream localized rendering and is never allowed to silently mutate canon.

## Authority split

Deterministic code owns hard invariants. JEV owns bounded semantic continuity questions only after deterministic preconditions pass. Haiku owns the final semantic/quality judgment and ambiguous escalation. No judge or decision engine may mutate canon, character state, world state, or the immutable StoryContract.

## Pipeline

1. Context projection: G2 Character, World, Opportunity, Canon, Saga, memories and age/style constraints are projected to English; IDs/revisions/fingerprints remain unchanged.
2. Immutable StoryContract: protagonist goal, central problem, solution principle, theme thread, required constraints, prohibited events, ending state, open-thread policy, target total length.
3. Six-scene SceneGraph: exactly six scene contracts; each declares entry state, purpose, beats, must-include facts, must-not-do guards, handoff, and open threads. Decisive solution is reserved for Scene 5; Scene 6 resolves consequences.
4. Deterministic plan gate: schema validity, indexes 1..6, required fields, no duplicate purposes/handoffs, all StoryContract constraints scheduled, explicit early-resolution guards.
5. JEV Plan Continuity Gate: English structured state only. Atomic checks cover causal continuity, stable protagonist goal, constraint coverage, information progression, unexplained entity/fact risk, premature resolution risk, ending-chain consistency, and next action CONTINUE/TARGETED_REPAIR/ESCALATE. If the plan is not accepted, the same plan may receive at most two targeted repair passes using deterministic errors plus JEV and Haiku feedback; each repaired plan is re-evaluated by all three gates before scene generation.
6. Sequential scene generation: each scene receives immutable StoryContract, complete SceneGraph, cumulative ContinuityLedger, previous scene prose, current SceneContract, next-scene guard summary, and target word budget.
7. Every scene returns a structured envelope: prose, state_delta, facts_established, clues_added, objects_changed, relationships_changed, threads_opened, threads_resolved, handoff_state.
8. Scene deterministic gate: word-count range, schema, forbidden structural mutations, valid thread references, and handoff presence.
9. JEV Scene Continuity Gate: checks prior-state continuation, current-scene purpose, unexplained facts/entities, contradictions, protagonist goal, later-scene leakage, premature resolution, and handoff validity. Failure triggers local scene repair.
10. ContinuityLedger commit: only after deterministic + JEV gates pass; append-only for the current draft attempt.
11. Assembly: accepted scene prose is joined into the English master story; no generative rewrite during assembly.
12. Whole-story deterministic gate: total length, repeated n-grams, scene count, unresolved required threads, required constraints, structural omissions.
13. JEV Whole-Story Continuity Gate: causal chain integrity, goal continuity, clue/solution progression, contradiction risk, repeated event risk, ending consistency.
14. Haiku Final Quality Judge: anthropic/claude-haiku-4.5, English input, exact verified runtime profile. Rubric includes instruction following, coherence, character consistency, age appropriateness, creativity, style quality, ending quality, continuity, and critical failures.
15. Final Haiku targeted repair: if the final Haiku judgment misses the quality gate without a critical failure, each repair target distinguishes the scene where the defect is observed from the single minimal repair scene whose prose should be edited. A passing final judgment is defined by average >= 4.0, minimum criterion >= 3, and no critical failure; optional polish on an otherwise passing story is non-blocking and must not force a repair cycle. The repair scene may be earlier when the defect is missing setup or foreshadowing. Repair at most three distinct repair scenes per cycle. For each target, allow at most two prose-only repair attempts; after each attempt JEV asks focused atomic questions about whether that exact Haiku issue is resolved and whether equivalent ambiguity remains. These repairs are prose-only: state_delta, handoff, facts, clues, objects, relationships and thread state must remain byte-equivalent JSON. JEV verification is advisory; unresolved target risk is carried forward rather than hard-rejecting. Reassemble, rerun whole-story JEV, and rerun Haiku within the bounded polish cycle. Whole-story regeneration remains last resort.
16. Turkish localization: runs only after the English master is accepted. Translation preserves identities, facts, chronology, clue structure, scene boundaries, age tone, thread state and canon-sensitive terms. English master remains the production evidence source.

## Word-budget policy

For a 2,000-word story, a default distribution is 260 / 310 / 340 / 340 / 410 / 340 words. Each scene has a target and bounded local-repair tolerance. After bounded repair attempts, a residual scene-only word-count miss becomes advisory evidence rather than a production failure, provided schema/state/continuity invariants remain valid. The assembled story total remains the hard length gate with ±25% tolerance: 1,500–2,500 words for a 2,000-word target.

## Fail-closed rules

- No paid generator qualification without an exact qualification-ready runtime profile.
- OpenRouter transport retries only bounded transient gateway/rate/timeout failures; permanent client errors fail immediately.
- Structured JSON generation responses that are malformed or incomplete receive at most one format-recovery retry at lower temperature; malformed payloads are never committed to plan, scene state, or ContinuityLedger.
- No Haiku judge call without an exact judge-ready runtime profile.
- JEV absence must be recorded explicitly; it must never silently become PASS.
- JEV low-confidence/high-risk scene results trigger bounded local repair when a concrete repair signal exists; residual or ambiguous risk escalates to Haiku rather than inventing certainty.
- Scene repair may not modify StoryContract.
- Final Haiku targeted repair is prose-only. Any model-proposed state_delta change is discarded and the canonical pre-repair state_delta is restored before validation, so final polish cannot mutate story state.
- A final repair target may route from an observed later scene to one earlier repair scene when the smallest valid fix is antecedent setup/foreshadowing; only that repair scene's prose may change.
- Scene-level word-count misses never override schema/state/continuity failures; only pure word-budget errors may degrade to advisory after bounded repair.
- Total assembled-story word budget remains a deterministic hard gate with ±25% tolerance around the configured target.
- Final Haiku targeted repair touches at most three judge-targeted scenes; each target allows at most two prose-only repair attempts with atomic JEV verification, followed by exactly one final whole-story Haiku rerun.
- Translation may not become the canonical story artifact.

## Model Lab rollout

Phase A: Qwen 3.8 Flash creates an English StoryContract + six-scene plan. Deterministic validation, OpenRouter JEV 1.13 continuity evidence, and Haiku plan review are followed by at most two targeted plan repairs if needed.
Phase B: generate one full English story with six sequential scenes, local repairs, JEV scene gates and Haiku final judge.
Phase C: repeated qualification across Qwen, MiMo, DeepSeek and other candidates using identical frozen pipeline/gates.
Phase D: translate only accepted English masters and qualify translation fidelity separately.

## OpenRouter JEV transport

The canonical JEV candidate for this pipeline is the exact versioned OpenRouter Decisions API model `typesafe/jev-1.13`, called through `POST https://openrouter.ai/api/alpha/decisions` using the existing `OPENROUTER_API_KEY`. The older Vercel AI Gateway sidecar remains historical Model Lab infrastructure and is not the transport for this pipeline.

JEV runs in advisory-repair mode until calibrated on a frozen LUMI continuity corpus. A scene-level metric below threshold or TARGETED_REPAIR decision may trigger at most two local repairs before ContinuityLedger commit. JEV never independently accepts or rejects the story; unresolved risk is passed explicitly to the final Haiku judge. ESCALATE without a concrete low metric is not blindly rewritten.