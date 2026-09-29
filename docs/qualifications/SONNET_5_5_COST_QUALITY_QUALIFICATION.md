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
