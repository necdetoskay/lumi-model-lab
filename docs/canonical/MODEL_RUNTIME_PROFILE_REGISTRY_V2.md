# Model Runtime Profile Registry v2

Status: **Canonical**

## Purpose

LUMI Model Lab must keep the shared story pipeline model-agnostic while still allowing each model to use the transport and generation settings that make it reliable in production.

The canonical source is:

`configs/model_runtime_profiles.yaml`

The resolver is:

`src/model_registry.py`

The governing rule is:

> If behavior must change when the model changes, it belongs in the model profile. If every model needs the rule for the story system to remain correct, it belongs in the shared pipeline.

## v2 authority boundary

A model profile has two different kinds of authority.

### 1. Runtime contract

The top-level `transport` and verified `metadata` describe provider/model facts and request capabilities.

Examples:

- structured-output transport
- reasoning support
- temperature support or omission
- max-token support
- seed support
- streaming behavior
- provider routing constraints
- context/output limits
- provider model slug
- native provider pricing metadata

Runtime facts must be supported by provider/upstream documentation or live runtime evidence.

### 2. LUMI production policy

`production_policy.request_classes` describes how LUMI chooses to use that verified runtime for a specific workload.

Examples:

- `teacher_story`
- `story_plan`
- `scene_story`
- `scene_repair`
- `judge`
- `scene_plan_judge`
- bounded structured helper calls

A production-policy entry may choose:

- reasoning effort
- reasoning visibility
- whether max_tokens is sent/omitted/capped
- whether temperature is sent/omitted
- whether seed is sent/omitted
- whether streaming is used
- which structured-output mode is used when multiple supported modes exist

The shared generator resolves:

`model + request_class -> runtime contract + production policy -> normalized provider request`

No generator or pipeline stage should add model-id branches for these behaviors.

## What production policy may NOT change

Model-specific production policy cannot weaken or redefine the common qualification test.

The following remain shared pipeline authority:

- StoryContract and SceneGraph semantics
- required story constraints
- deterministic state/canon validation
- JEV questions and thresholds
- Haiku rubric and acceptance gate
- safety requirements
- shared total-story length tolerance
- contradiction/continuity rules
- critical-failure definitions

A model profile controls how a model takes the test. It does not control the passing score.

## Clean-cutover rule

Schema v2 does not accept the old `request_overrides` key.

All task-sensitive model behavior must live under:

`production_policy.request_classes`

The registry loader fails closed if a v2 profile still contains `request_overrides`.

## Evidence identities

A resolved profile now has three SHA-256 identities:

- `profile_sha256` — complete resolved profile
- `runtime_contract_sha256` — verified transport + metadata identity
- `production_policy_sha256` — LUMI model-usage policy identity

Qualification fingerprints include the resolved model profile identity. Therefore either a runtime-fact change or a production-policy change creates new qualification evidence instead of silently reusing old results.

This lets us distinguish:

- “the provider/model changed”
- “LUMI changed how it uses the same model”

## GPT-5.6 Luna baseline

Exact OpenRouter id:

`openai/gpt-5.6-luna`

Canonical provider model:

`openai/gpt-5.6-luna-20260709`

Verified baseline:

- OpenAI provider pinned
- provider fallback disabled
- default/standard service tier baseline
- 1,050,000-token context
- 922,000-token prompt limit on the standard OpenAI endpoint
- 128,000-token completion limit
- reasoning supported; provider default is medium
- seed supported
- temperature is not advertised by the selected endpoint and is omitted
- strict structured output is supported
- current English story pipeline uses `json_object` because application schemas are validated locally

Initial LUMI production policy:

- `teacher_story`: medium reasoning, no client max_tokens
- `story_plan`: medium reasoning, JSON object, no client max_tokens
- `scene_story`: medium reasoning, JSON object, no client max_tokens
- `scene_repair`: medium reasoning, JSON object, no client max_tokens
- reasoning text excluded from visible output
- seed retained
- temperature omitted

Flex and priority/fast tiers are separate future experiments and must not be mixed into baseline qualification evidence.

## Other model examples

### Qwen 3.8 Flash

Qwen-specific reasoning, streaming, token-budget and structured-output behavior remains in the Qwen profile. Qwen tuning must not add Qwen branches to the shared story pipeline.

### Aion

Aion-specific provider-managed reasoning, seed omission and unbounded scene-generation behavior remains in the Aion profile. Aion may be frozen from active use without deleting its historical verified profile/evidence.

### Haiku judge

Judge-specific non-reasoning and bounded structured-output settings remain under the Haiku profile's production policy. The judge rubric itself remains shared pipeline authority.

## Qualification output

A model qualification should produce more than a score. The evidence package should identify:

- exact model id
- resolved runtime identity
- production-policy identity
- benchmark/judge evidence
- latency evidence when available
- usage/cost evidence
- accepted/rejected status
- reasons and repair evidence

Provider-native pricing may remain stored in USD because that is the upstream source format. User-facing cost reports are converted to TRY using the report-time USD/TRY rate and should state the rate used.

## Governance

When Model Lab discovers a model-specific requirement:

1. determine whether it is a model/provider fact or a shared-pipeline correctness rule;
2. model/provider fact -> update runtime metadata/transport;
3. LUMI-specific tuning -> update `production_policy.request_classes`;
4. shared correctness bug -> repair the shared pipeline;
5. add regression tests;
6. rerun qualification because profile identity changes;
7. never lower qualification gates only for one model;
8. never add model-id conditionals to the generator when the behavior can be expressed by the profile.

This registry is the authority for model-specific runtime and production-use behavior. The story pipeline remains the authority for story correctness.
