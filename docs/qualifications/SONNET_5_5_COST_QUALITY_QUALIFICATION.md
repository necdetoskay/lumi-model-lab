# Sonnet 5.5 Cost–Quality Qualification

Status: ACTIVE — isolated Model Lab experiment.

## Non-negotiable baseline freeze

AGE12-R05-PUBLICATION-READY-20260929 is the known-good reference. This experiment must not replace or mutate its prompts, artifacts, model assignments, or evidence. Sonnet 5.5 promotion is allowed only after measured qualification.

## Objective

Evaluate anthropic/claude-sonnet-5.5 as a drop-in or topology-changing successor to Sonnet 5 while preserving serious/critical defect recall and lowering canonical cost/latency.

## P0 — Runtime qualification

Verify exact OpenRouter model identity, pricing, context/output limits, structured output, reasoning/effort contract, request normalization, and canonical usage/cost capture.

PASS requires deterministic tests before any paid call.

## P1 — Audit A/B

Use the exact frozen raw Aion story from writer run 36526379349, the exact approved Revision-05 spine/context, and the same StoryForge AUDIT_SYSTEM.

Baseline A is already paid and frozen:
- Model: Sonnet 5
- Stage: initial primary audit from postprocess run 36528435261
- Cost: $0.065728
- Latency: 8.855 s
- Root-defect recall on frozen six-root corpus: measured from archived evidence.

Candidate B:
- Model: Sonnet 5.5
- One paid editorial_audit call.
- low effort, reasoning excluded, JSON object, max output 2800.

No Sonnet 5 re-call is needed.

### Frozen six-root defect corpus

1. Unauthorized durable history/canon.
2. Measurement-series causal inconsistency.
3. Four-vs-five reading state inconsistency.
4. Future protocol/outcome overcommit.
5. Flooding-ridge spatial/physical escape inconsistency.
6. Control-check certainty/response-causality weakness.

Scoring is based on overlap with gold source anchors/segments, not wording identity.

## P2 — Spine A/B

Only after P1. Same character/world/premise input and same Luna gate. Compare contract pass, Luna decision, tokens, cost, latency, and human premise quality.

## P3 — Adaptive QA proof

Target topology:

Sonnet 5.5 primary audit -> conditional Sol confirmation/repair -> Luna targeted recheck -> Gemini translation -> Luna fidelity.

The frozen baseline remains unchanged.

## Promotion gates

- No regression in serious/critical root-defect recall.
- No unacceptable new false positives/unmapped blockers.
- Canonical story cost <= 15 TRY average; target <= 10 TRY.
- Lower latency than baseline.
- All model calls captured in canonical usage/cost lineage.

## Current qualification status — 2026-09-29

### P0 — PASS
- Exact Sonnet 5.5 runtime profile verified.
- Deterministic qualification suite: 46/46 PASS before paid P1.
- Frozen baseline remains unchanged.

### P1 — COMPLETE
Run: 36534387514.

Human-adjudicated six-root result:
- Sonnet 5 baseline initial primary audit: 1/6 roots.
- Sonnet 5.5 candidate initial primary audit: 4/6 roots.
- Candidate misses: unauthorized durable history; control-check certainty weakness.
- Candidate false positive: temporal consistency around remaining light vs site-security window.
- Cost: $0.068302 vs $0.065728 (+3.9%).
- Latency: 9.2 s vs 8.855 s (+3.9%).
- Candidate output throughput: ~26.5% higher.

Decision: advance to P2. Do not promote and do not remove secondary QA based on P1.

### P2 — PREPARED, NOT RUN
Workflow is isolated at .github/workflows/sonnet55-spine-ab.yml.
It uses Sonnet 5.5 Architect + unchanged GPT-5.6 Luna gate against Revision-05 feedback.
No P2 paid call has been authorized or triggered yet.


### P2 — COMPLETE, HUMAN REVISE
Run: 36535132929.

Measured candidate vs frozen baseline:
- Luna gate: ACCEPT vs ACCEPT.
- Architect output tokens: 8,986 -> 6,133 (-31.8%).
- Architect cost: $0.115908 -> $0.087382 (-24.6%).
- Architect latency: 93.684 s -> 42.639 s (-54.5%).
- Full spine+gate cost: $0.11957935 -> $0.09093235 (-24.0%).
- Full spine+gate latency: 106.902 s -> 56.403 s (-47.2%).

Human adjudication found a contract-blocking self-contradiction:
- logistics_plan introduces Meridian Harbor before/after Beacon Ridge;
- b10_payoff is located at Meridian Harbor;
- writer_rules simultaneously says the episode stays at Beacon Ridge throughout and forbids sequential Harbor/Ridge travel.

Luna ACCEPT missed this contradiction.

Decision:
- Do not promote Sonnet 5.5 Architect yet.
- Do not advance to P3 yet.
- Next phase is P2.1: fix/validate location-contract consistency while retaining the measured cost/latency gain.


### P2.1 — LOCATION CONTRACT PASS, PAYOFF HUMAN REVISE
Run: 36536725908.

Measured:
- Deterministic location-contract validator: PASS.
- Luna gate: ACCEPT.
- All beats/logistics/writer rules are now single-site Beacon Ridge.
- Architect cost: $0.081272.
- Full spine+gate cost: $0.08559685 (~28.4% below frozen Sonnet 5 baseline).
- Full spine+gate latency: 57.045 s (~46.6% below frozen baseline).

Human adjudication found the previous branch/payoff defect reintroduced:
- b9 state change guarantees a dated entry exists;
- global local payoff guarantees a dated entry and mentor-relationship shift;
- fresh-setup branch mechanics can still consume reporting time and leave no completed reviewed log.

Decision: HUMAN REVISE. Do not promote. P2.2 should change only payoff conditionality and preserve the clean location contract.


### P2.2 — PAYOFF PASS, CONTRACT REJECT BEFORE GATE
Run: 36537449744.

- Sonnet 5.5 Architect ran once.
- Cost: $0.080368.
- Latency: 38.178 s.
- Luna was NOT called; deterministic validation stopped the run.
- Location contract: PASS.
- Payoff conditionality: PASS. The prior guaranteed-log defect is fixed.
- Branch failure/unlogged-result states are preserved.
- New blocker: episode_role=world_exploration while targeting first_discrepancy_logged.

This is exactly the intended value of deterministic contract validation: the classification regression was stopped before gate/downstream cost.

Decision: P2.3 should change only episode-role authority while preserving the now-clean location/payoff logic.
