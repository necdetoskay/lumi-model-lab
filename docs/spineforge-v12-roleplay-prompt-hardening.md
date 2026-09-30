# SpineForge v12 — Roleplay Prompt Hardening

## Purpose

v12 preserves the v11 single-owner architecture and changes the experimental variable that matters most before paid qualification: prompt quality.

Pipeline:

SpineContextPack.v1
-> Sonnet 5.5 Roleplay Story Spine Architect
-> deterministic EpisodeSpineV3 + authority validation
-> Sonnet 5.5 aggressive red-team audit
-> STOP for human review or explicit future repair.

No Aion blueprint, no Frame/Beats/Resolution partitioning, no Luna gate, no writer, and no automatic repair.

## Architect prompt contract

The architect prompt is production-oriented rather than a short instruction. It explicitly defines:
- role and mission;
- authority precedence;
- instruction/data boundary;
- story-first dramatic engine;
- active protagonist and roleplay density;
- sceneability;
- character/world specificity;
- creative ambition inside canon;
- exact-age maturity;
- beat causality and escalation;
- observed/inferred/hypothesis discipline;
- earned reversal;
- credible decision branches;
- causally earned climax;
- local payoff;
- Saga/reveal safety;
- exact field-by-field EpisodeSpine guidance;
- bad examples, corrections, and anti-patterns;
- a silent self-red-team pass before JSON emission.

Qualification-case-specific entities are explicitly absent from prompt examples so the test does not teach Sonnet the answer.

## Auditor prompt contract

The second Sonnet call has a separate adversarial role. It does not rewrite. ACCEPT carries a burden of proof and must be supported by concrete spine evidence across story desire, roleplay, sceneability, character/world specificity, maturity, causality, escalation, reversal, agency, branches, climax/payoff, local satisfaction, Saga alignment, authority safety, executability, and freshness.

## Qualification evidence

Final zero-cost qualification before freeze:
- GitHub Actions run 36747268238
- v12 prompt/runtime suite: 9 PASS
- Episode Spine regression: 15 PASS
- paid calls: 0
- actual spend: $0

The earlier red runs during prompt hardening were test-harness/assertion defects, not paid inference attempts.

## Paid boundary

v12 must be frozen before Attempt 1.
Every paid attempt requires explicit user authorization.
Attempt 1 is capped at two model calls: Architect, then Auditor only if local validation succeeds.
Repair remains disabled for the first real product so failure evidence is observable rather than hidden by automatic retries.
