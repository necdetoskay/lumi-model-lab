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

## Zero-cost qualification result

v11 is frozen and ready for the first explicitly authorized paid qualification attempt.

- Freeze run: `36745836787` — SUCCESS
- Runtime revision: `SPINEFORGE-SINGLE-OWNER-FROZEN-v11`
- Runtime source commit: `88ed91d6ed301958280106c441f497157244a295`
- Frozen runtime files: 22
- Final zero-cost run: `36746068515` — SUCCESS
- v11 architecture/contract/runtime/freeze tests: 12 PASS
- Episode Spine regression tests: 15 PASS
- Paid model calls during qualification: 0
- v11 spend before paid boundary: $0
- Paid trigger `experiments/triggers/spineforge-v11.json` must remain absent until explicit authorization.

The first paid attempt is intentionally capped at two model calls: Sonnet Story Spine Architect, then Sonnet Aggressive Red-Team Auditor only if local contract and authority validation succeeds.
