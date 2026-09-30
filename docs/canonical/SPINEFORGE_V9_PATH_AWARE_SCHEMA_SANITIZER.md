# SpineForge v9 — Path-Aware Strict Schema Sanitizer

Status: ZERO-COST QUALIFICATION

## Why v9 exists

v8 paid Attempt 1 proved that partitioned provider-strict Sonnet transport reaches inference and that durable evidence survives GitHub artifact-quota failure. It also exposed a generic transport defect: the sanitizer recursively removed every mapping key named `title`, including the legitimate application field `properties.title`, while leaving `title` in the schema's `required` array.

That made the provider schema internally inconsistent. Sonnet therefore could not be required to emit the field that local Pydantic validation still required.

v9 does not change the Creative Blueprint, structural contracts, prompts, ContextPack, model selection, stage ownership, Luna gate, or human-review boundary.

## v9 change

Provider-schema sanitization becomes path-aware:

- JSON Schema annotations such as `title`, `description`, `default`, pattern/range/list constraints, enum/const can be removed where they are schema keywords.
- Keys inside schema name maps such as `properties`, `$defs`, `definitions`, `patternProperties`, and `dependentSchemas` are preserved as application/schema member names.
- Before any strict provider call, every object schema must satisfy `required ⊆ properties`; otherwise execution stops before inference.
- Sonnet schema-size budget remains enforced.
- No parse retry is introduced.
- Writer remains unreachable before explicit human approval.

## Qualification rule

No paid v9 call is allowed until:
1. v9 sanitizer tests are GREEN;
2. inherited v8 evidence behavior remains GREEN;
3. historical frozen regressions remain GREEN;
4. v9 runtime is SHA-256 frozen and freeze verification is GREEN.
