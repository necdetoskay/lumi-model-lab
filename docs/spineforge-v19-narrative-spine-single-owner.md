# SpineForge v19 — NarrativeSpineV1 single-owner baseline

Status: zero-cost implementation phase.

## Topology

`SpineContextPack.v1`
→ exact reader/story-family obligations
→ **Sonnet 5.5 single Narrative Spine Architect**
→ `NarrativeSpineV1`
→ deterministic authority / reveal / obligation validation
→ **GPT-5.6 Luna compact adversarial Product Gate**
→ human-readable preview
→ **STOP / human approval**

Writer is not callable in the v19 SpineForge runtime.

## Why v19 exists

v11 proved that one Sonnet owner can produce a nearly valid complete spine in one call. v12 proved that mechanically derivable route metadata should not be model-owned. v14-v17 showed that a large scoring/audit surface created repair and transport churn. v19 keeps the successful single-owner direction while replacing the legacy `EpisodeSpineV3` product contract with a smaller story-first contract.

## Product ownership

Sonnet owns story promise, story family execution, protagonist goal/pressure, central question, stakes, world-specific use, beats, decision when required, climax, payoff, unresolved hooks, reveal limits, outcome candidates, and writer rules.

The application owns ContextPack identity/fingerprint, exact age, session, word targets, authority revisions, eligible milestone ids, commit-only-if-earned, writer authorization, approval ids, and token/cost/latency lineage.

## Deterministic gate

Code may reject objective defects only: stale/mismatched authority, unknown or locked refs, hidden-Saga system markers, exact type/shape problems, duplicate beat keys, reader/story-family obligation mismatch, and missing required real choice.

Subjective story quality belongs to the Luna Product Gate and then the human review.

## Qualification

The fixed six-case matrix is versioned at:
`data/specifications/story_lab/spineforge_v19_qualification_cases_v1.json`.

At this source revision, the age-18 Leyra context fixture is frozen and five additional production-like ContextPacks remain intentionally pending. This means **paid six-case qualification is blocked** even if zero-cost tests pass.

Transport rule: every qualification stage uses a v19-specific one-shot HTTP transport. Transient provider/HTTP errors are recorded as failed evidence and are never retried automatically. The compact Luna gate uses provider-strict JSON Schema; the larger Sonnet architect remains JSON-object + local typed validation.\n\nNo paid trigger may be added before:
1. zero-cost CI is GREEN;
2. all six context fixtures are frozen;
3. runtime/prompt/schema hashes are frozen;
4. the user explicitly authorizes the first paid attempt.
