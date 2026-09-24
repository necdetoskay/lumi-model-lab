# Model Runtime Profile Registry v1

Status: **Canonical**

## Purpose

LUMI Model Lab must test models using the same provider/transport facts that production uses. Model-specific behavior must not be scattered through generators as `if model == ...` branches.

The canonical source is:

`configs/model_runtime_profiles.yaml`

The runtime resolver is:

`src/model_registry.py`

## Separation of concerns

A task configuration answers **what the experiment wants**:

- model
- temperature preference
- output budget preference
- structured vs plain output
- timeout/retry policy

A Model Runtime Profile answers **how that model can actually be called**:

- structured output transport
- reasoning behavior
- whether temperature is sent or omitted
- whether max_tokens is sent, omitted, capped, or overridden
- whether seed is sent
- provider routing constraints
- exact-model vs model-family matching

Task configuration must never override a model fact that the runtime profile marks as mandatory.

## Request classes

The v1 registry supports task-sensitive overrides. Current classes include:

- `default`
- `teacher_story`
- `structured_small`
- `structured_large`

This is required because the same model may safely accept a bounded budget for a small structured object but should use provider/model technical limits for a large structured generation.

## Production parity rules

The registry carries the current production transport contract for production-used models.

Notable examples:

### Aion 3.0

- exact OpenRouter id: `aion-labs/aion-3.0`
- qualification-ready verified runtime profile
- JSON structured output uses `json_object`, not JSON-schema enforcement
- reasoning remains enabled/provider-managed for LUMI scene production
- current endpoint does not advertise seed support, so seed is omitted
- `story_plan`, `scene_story`, and `scene_repair` omit client `max_tokens`
- scene length is governed by LUMI word targets, local repair, and final deterministic gates
- current verified limits: 131,072 context / 32,768 completion tokens

### Aion 3.0 Mini

- reasoning is mandatory/provider-managed
- callers must not send `reasoning: none`
- structured JSON uses `json_object`
- large structured calls omit `max_tokens`
- small structured calls may cap `max_tokens` at 1200

### GPT-5.6 Luna

- exact OpenRouter id: `openai/gpt-5.6-luna`
- qualification-ready verified runtime profile
- fixed model slug is required for reproducibility; the moving `gpt-luna-latest` alias is not qualification evidence
- current verified limits: 1,050,000 context / 128,000 completion tokens
- OpenRouter advertises `reasoning`, `seed`, `max_tokens`, `response_format`, `tools`, and `tool_choice`
- temperature is omitted because it is not an advertised parameter for the verified model endpoint
- GPT-5.6 defaults to medium reasoning; LUMI `story_plan`, `scene_story`, and `scene_repair` explicitly use low reasoning as the initial quality/latency baseline
- scene structured output uses `json_object` in the current LUMI transport boundary; although Luna supports JSON Schema, the generic scene caller does not yet provide a per-request schema
- `story_plan`, `scene_story`, and `scene_repair` omit client `max_tokens`
- seed is retained for reproducible qualification attempts
- OpenAI provider routing is pinned and fallback disabled so provider variance does not contaminate Qwen/Aion/Luna comparisons

### GLM 5.3 Flash

Model Lab retains its verified generation behavior:

- reasoning enabled
- low effort
- reasoning excluded from visible output
- 10k shared completion budget for teacher-story generation

## Evidence and reproducibility

A resolved runtime profile has a deterministic SHA-256 identity.

Qualification fingerprints include the model runtime profile identity. Saga Narrative Architect fingerprints also include both:

- the runtime profile identity
- the registry file hash

Therefore a capability/transport change creates a new experiment identity. Old evidence is not silently reused under new model transport semantics.

## Unknown models

Unknown/custom model ids use the explicit generic OpenRouter profile. Generic behavior is intentionally conservative:

- provider-default reasoning
- temperature/max_tokens/seed sent when requested
- no hidden model-specific assumptions

If a new model requires special input behavior, add an exact or family profile before treating benchmark results as production-representative.

## Governance

When a provider/model behavior is discovered in production or Model Lab:

1. update `configs/model_runtime_profiles.yaml`;
2. add or update a regression test in `tests/test_model_runtime_profiles.py`;
3. rerun affected Model Lab experiments because the fingerprint changes;
4. mirror the verified rule into Project LUMI production ModelRuntimeProfile when applicable;
5. do not add new model-id branching to generators/provider callers.

The registry is the authority for runtime model transport facts.
