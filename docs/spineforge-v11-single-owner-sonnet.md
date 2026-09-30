# SpineForge v11 — Single-Owner Sonnet

## Goal

Test whether one strong story-architecture model can own the complete Episode Spine and remove the failure surface created by Creative Blueprint -> Frame -> Beats -> Resolution -> Assembly partitioning.

## Frozen topology candidate

SpineContextPack.v1
-> Sonnet 5.5 Story Spine Architect
-> EpisodeSpineV3 local validation
-> deterministic ContextPack authority validation
-> Sonnet 5.5 Aggressive Red-Team Audit
-> ACCEPT: STOP / human review
-> REPAIR: STOP / explicit future repair revision

The writer never runs inside SpineForge.

## Story quality thesis

The Architect is roleplay-first rather than schema-first. It must design an experience with active protagonist agency, sceneable beats, world-specific mechanics, escalating pressure, evidence-grounded reversal, consequential choice, earned climax, local payoff, and age-appropriate maturity.

The Auditor is intentionally adversarial. Contract validity alone is insufficient. It tests story desire, roleplay potential, scene potential, character-drivenness, world specificity, intrigue, maturity, causality, escalation, reversal, agency, branch executability, climax/payoff, local satisfaction, saga alignment, authority safety, writer executability, and freshness.

## Transport decision

v11 does not send the full EpisodeSpine as a large provider strict JSON grammar. Sonnet uses JSON-object transport and the application validates EpisodeSpineV3 locally. This deliberately removes the provider grammar-size failure mode seen in earlier SpineForge revisions while preserving exact application contracts.

## Qualification policy

- ContextPack source and fingerprint are fixed.
- Runtime and both prompts are frozen before paid inference.
- Attempt 1 can use at most two paid model calls: Architect, then Auditor only if deterministic validation succeeds.
- No automatic parse/model retry.
- No automatic repair.
- No writer.
- Every paid attempt requires explicit authorization.
- Exact tokens, cost, latency, raw product, audit, and failure evidence are persisted to the repository before best-effort artifact upload.

## Repair policy

v11 qualification intentionally stops on REPAIR. The first real product should reveal which repair classes actually occur. A repair stage will only be frozen after that evidence exists; mechanical repair may use a cheaper model or deterministic code, while semantic story-architecture repair should remain with a model strong enough to preserve causality and dramatic quality.
