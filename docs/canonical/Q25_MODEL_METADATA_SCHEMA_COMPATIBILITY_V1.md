# Q25 — Model Metadata / Strict JSON Schema Compatibility V1

**Status:** implemented, offline tested, **not a real-model success certificate**  
**Date:** 2026-10-12  
**PR:** #273 (Draft)  
**Scope:** experimental LUMI Model Lab one-shot Q25 extractor only; no production LUMI change.

## Design decision

Do **not** put unsupported JSON Schema validation constraints directly into the
structured-output request to a model when its metadata forbids them.

The known Claude/Anthropic issue is documented upstream:
[Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
Strict JSON Schema grammars do **not** accept `minLength`, `maxLength`, numeric
range constraints and several array/object constraints. They enforce other
shape requirements such as closed objects and the limits on optional/union
parameters. Basic regex patterns can work but provider regex subsets vary,
so this version deliberately keeps `pattern` as **application-validated**
instead of depending on grammar portability.

Provider support varies **per endpoint**, not just by named model. The
[OpenRouter structured-output guide](https://openrouter.ai/docs/guides/features/structured-outputs)
documents this distinction. A model profile does not replace live
`supported_parameters` checks, pricing checks or the explicit
`require_parameters=true`, `allow_fallbacks=false` routing policy.

## Metadata contract and access

Central registry: `src/q25_model_metadata.py`, with an explicit entry for
each allowlisted model. All runtime wire-compilation and pilot ledger code
reads the same registry. Unknown models have **no implicit default**.

| Metadata field | Sonnet | Gemini |
| --- | --- | --- |
| `schema_profile` | `ANTHROPIC_STRICT_V1` | `OPENROUTER_CONSERVATIVE_V1` |
| `capability_basis` | Published Anthropic limits | Conservative interoperable subset; **not** a claim Google forbids these keywords |
| `wire_constraints_enforced_locally` | minLength, maxLength, pattern, numeric and excess array/object bounds | Same conservative wire subset until model/endpoint-specific qualification |
| `allowed_min_items` | 0 or 1 | Conservatively 0 or 1 |
| `max_optional_parameters` | 24 | Conservatively 24 |
| `max_union_parameters` | 16 | Conservatively 16 |
| `raw_response_validation` | `FULL_ORIGINAL_PYDANTIC_SCHEMA` | Same |
| `provider_capabilities_must_be_checked_live` | true | true |

Google supports more JSON Schema features in many native Gemini contexts:
[Gemini structured output documentation](https://ai.google.dev/gemini-api/docs/structured-output).
The conservative Q25 profile is an **intentional engineering restriction**, not
a factual limitation asserted about Gemini.

The metadata is versioned in code; the selected `schema_profile` and
SHA-256 of its effective entry are added to the provider's price snapshot
and the attempt ledger. This permits exact audit if the profile changes.

## Two distinct schemas — no contract weakening

1. **Provider wire schema:** `provider_safe_json_schema(original, model=...)`
   copies the immutable Pydantic JSON schema, removes only keywords listed
   in the selected metadata profile, and adds explanatory hints in descriptions.
   Unsupported constructs are rejected, object closure/required fields remain,
   and complexity guards remain active.
2. **Application validator:** `RawExtractorOutput.model_validate(raw_json)`
   always applies the **original, unchanged** Pydantic contract to the returned
   response. This catches invalid quote length, disallowed object ID pattern,
   malformed hashes, missing properties, unsupported roles, etc. Then the
   exact-quote, seed lineage, semantic-candidate and reconciliation gates run.

If a profile is absent, locally unsafe, or schema compilation exceeds the
profile's conservative limits, the request must STOP before any paid POST.
Neither fallback to another model nor a weaker accepted StoryState is allowed.

## Incident linkage

The first KITE-01 run [#38280659568](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38280659568)
made one HTTP POST and received **HTTP 400**. Its unmodified historical
archive lacks the provider error body; therefore schema incompatibility is a
**plausible cause**, not independently confirmed. Real actual charged usage
was not returned, so do **not** equate a rejected response to verified $0 spend.

The original remediation compiled a safer provider schema but applied one
shared hard-coded set of constraints to every model. This stage moves that
decision into model-specific metadata and adds tests that preserve the strict
local contract.

**Current result:** model-metadata code/tests CI
[#38285326416](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38285326416)
**315/315 PASS**, paid job SKIPPED. No new paid call or response was produced.

## Next gate

A **new, separately authorized single-call** trial is required to prove the
actual OpenRouter endpoint accepts the metadata-adapted schema. The earlier
failed attempt may not be retried. If the provider returns another HTTP 400,
the safe categorized diagnostic records only a non-sensitive category and
the attempted/billing-unknown status; do not automatically relax additional
contract fields, repeat the POST, or promote an unverified terminal state.
