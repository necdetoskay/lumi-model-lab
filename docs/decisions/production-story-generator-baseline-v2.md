# Production Story Generator Baseline v2

Status: **ACTIVE MODEL-LAB BASELINE / QUALIFIED INTEGRATION CANDIDATE**
Date: 2026-09-24
Scope: Current LUMI English-first scene-by-scene story production pipeline

## Decision

The active generator baseline for the current English-first LUMI Model Lab story pipeline is:

- generator: `openai/gpt-5.6-luna`
- provider path: OpenRouter with the upstream OpenAI provider pinned
- continuity evaluator implementation at promotion: `typesafe/jev-1.13`
- semantic judge implementation at promotion: `anthropic/claude-haiku-4.5`
- story production protocol: current `english_story_pipeline_v1`
- runtime registry: `model-runtime-profile.v2`

This is a Model Lab promotion decision. It qualifies Luna as the generator to carry forward into LUMI integration work; it does **not** claim that the LUMI application has already deployed Luna in production.

## Why the baseline changed

The prior 2026-08-31 GLM decision was produced under `story_scene_first_v0.3`. The current production architecture is materially different: it uses an English-first six-scene contract, a continuity-evaluator role, deterministic story/state gates, a semantic-judge role, and model-specific production policies resolved through Model Runtime Profile v2.

Because the protocols differ, old GLM scores and current Luna scores are retained as separate historical evidence. They are not treated as an apples-to-apples benchmark.

The active pipeline needed a fresh generator qualification under the current production contract. Luna satisfied that contract with repeated successful full-pipeline runs without requiring model-specific weakening of common gates.

## Frozen Luna runtime identity

Model id:

`openai/gpt-5.6-luna`

Resolved identities at promotion:

- profile SHA-256: `a938538d68df16de6bf5c0a2e9302f07e86595d5e807b94a248a269108d1027b`
- runtime-contract SHA-256: `ef8ad486f139c2885915203135c81e8eab3ed449ad507e20a133018461e1df0b`
- production-policy SHA-256: `d2cb13b2b9c09749cf7c47f76efe941fd7b41504882c705464c0b1036826e9d7`

Any change to these identities requires new qualification evidence.

## Production policy at promotion

For story planning, scene generation, scene repair, and teacher-story generation:

- reasoning effort: medium
- reasoning text: excluded
- temperature: omitted
- client max-token cap: omitted for story-generation request classes
- seed: retained
- structured story requests: JSON object transport with local schema validation
- provider: OpenAI pinned
- provider fallback: disabled
- baseline service tier: standard/default

Flex and priority/fast service tiers are separate experiments. They must not silently replace the baseline endpoint in qualification evidence.

## Common gates remain model-independent

The Luna profile controls how Luna is called. It does not control what counts as a passing story.

The following remain shared pipeline authority:

- StoryContract and SceneGraph requirements
- deterministic validation
- scene continuity rules
- continuity-evaluation questions and thresholds
- semantic-judge rubric and acceptance thresholds
- total-story word tolerance
- critical-failure definitions
- safety constraints
- canon/state integrity

No Luna-specific relaxation of these gates was introduced for promotion.

## Qualification evidence

The promotion evidence uses the frozen five-case English benchmark set:

1. Exploration / Mystery
2. Friendship / Social
3. Puzzle / Problem Solving
4. Fantasy Adventure
5. Emotional Calm

The canonical stability matrix is recorded in:

`docs/experiments/gpt56-luna-production-qualification-20260924.md`

The migrated immutable run evidence and derived multidimensional capability
view are governed by:

`docs/canonical/MODEL_CAPABILITY_CUBE_V1.md`

The initial cube deliberately marks these five CHILD × STANDARD cells as
PROVISIONAL because each currently has only two retained runs. Promotion as a
Model Lab integration candidate and evidence-density status are separate
concepts.

Promotion requirements:

- all five frozen cases must pass on canonical `main`
- repeated runs must not reveal a persistent model-specific failure pattern
- final semantic-judge minimum must remain at or above the global acceptance floor
- no model-specific judge/rubric threshold modification is allowed
- failures must be preserved rather than silently replaced
- cost reporting must include plan, scene generation, continuity evaluation, and semantic-judge stages

## Observed reliability signal

At the time of this decision, the canonical-main matrix showed:

- **10/10** full-pipeline qualification runs accepted across five frozen cases with two repeats each
- **60/60** final scenes accepted
- **65** total scene-generation attempts
- **2** semantic scene repairs, both in Scene 5 of one Case 01 repeat
- one Case 03 first repeat required four Scene 2 generation attempts but no semantic repair; its second repeat accepted all six scenes first-attempt
- final semantic-judge average across the matrix: **4.0875/5**
- lowest observed final criterion score: **3**, with no critical failure
- no persistent failure signature requiring Luna-specific prompt, weaker judge thresholds, or pipeline branching

One accepted Case 01 repeat retained a final prose-level continuity repair target. That evidence is preserved rather than hidden: Luna is qualified as a production candidate **with the shared repair architecture active**, not as a model that never needs repair.

This is materially different from a situation where repeated failures force the shared pipeline to accrete model-specific exception logic.

## Cost interpretation

Provider-native raw evidence remains stored in USD for reproducibility. User-facing reporting is in TRY.

The qualification report uses the report-time FX rate documented in the evidence file. Cost is a secondary selection criterion; story quality and production reliability remain primary.

## Change control

Luna remains the active Model Lab generator baseline until one of the following happens:

1. repeated production-like qualification reveals a persistent reliability defect;
2. the Luna runtime or production-policy identity changes;
3. a competing generator is evaluated under the **same current protocol** and demonstrates a material quality/reliability advantage;
4. the story production architecture changes enough to invalidate this qualification protocol.

A lower price alone is not sufficient to replace the baseline.

## Integration boundary

The next step after this Model Lab promotion is controlled LUMI integration:

- mirror the exact Luna production policy into the application runtime profile;
- keep continuity-evaluator and semantic-judge gates unchanged;
- run application-level StoryContext/StoryContract integration qualification;
- verify end-to-end durable story lifecycle and accepted-story persistence;
- only then promote the application route.

Model Lab qualification is necessary evidence for integration, not a substitute for application-level verification.
