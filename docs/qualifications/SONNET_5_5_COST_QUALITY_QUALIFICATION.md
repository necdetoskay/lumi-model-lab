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


### P2.3 — CONTRACT PASS, LUNA REPLAN
Run: 36540005836.

- Main Saga role authority: PASS.
- Single-site Beacon Ridge contract: PASS.
- Payoff conditionality: PASS.
- Full spine+gate cost: $0.08590645.
- Full spine+gate latency: 60.787 s.
- Luna decision: REPLAN.

Luna correctly identified the next structural gap:
1. Tide-correlation evidence was not operationally specific enough to audit against setup movement.
2. Branch choice was open as intended, but branch RESULT was also open. The writer still had to invent the decisive evidence result and mentor response.
3. Because branch core results were open, the local payoff was not outcome-complete.

P2.4 rule:
- branch choice remains uncommitted;
- each branch receives one predefined core evidence result and mentor/local outcome;
- durable commit remains commit-only-if-earned.


### P2.4 — CONTRACT PASS, LUNA REPLAN
Run: 36541205326.

- Main Saga role: PASS.
- Single-site Beacon Ridge: PASS.
- Payoff conditionality: PASS.
- Branch core results fixed: PASS.
- Reversal observational structure: PASS.
- Full spine+gate cost: $0.08596945.
- Full spine+gate latency: 53.44 s.
- Luna decision: REPLAN.

Single remaining blocker:
- The fresh-setup branch used one similar fresh reading to claim setup-dependence was resolved in favor of a real offset.
- One fresh-setup repeat can weaken the original-setup-only explanation, but cannot prove setup-independence, eliminate all setup/instrument error, establish beacon causation, or establish recurrence.

P2.5 rule:
- keep the fixed fresh-setup result;
- weaken only its evidentiary interpretation;
- report_now remains the only branch that can earn the provisional reviewed Main Saga discrepancy entry in this proof.


### P2.5 — SEMANTICALLY CLEAN, CONTRACT SELF-REF REJECT
Run: 36541988910.

- Sonnet 5.5 Architect cost: $0.088474.
- Luna was not called.
- Role/location/payoff/branch-result/evidence-ceiling mechanics were human-adjudicated clean.
- Contract rejection was limited to one reversal evidence item citing its own reversal beat in addition to a valid pre-reversal source.
- Qualification-only safe normalization removes only that invalid self/future ref when a valid pre-reversal source remains.
- Safe normalizer regression passed and does not edit claims, certainty, beats, or outcomes.

### P2.6 — LUNA-ONLY RECOVERY REPLAN / AUTHORITY GAP
Run: 36545732284.

- No new Sonnet call.
- Safe normalization applied exactly once; semantic fields unchanged.
- Incremental Luna cost: $0.00397345.
- Candidate inherited Architect + Luna cost: $0.09244745.
- Luna decision: REPLAN.

The REPLAN exposed an authority-order bug in the qualification gate:
- the original approved premise says Deniz secures at least a provisional logged acknowledgment;
- the later HUMAN-APPROVED Revision-05 explicitly refined this mechanic so the fresh-setup branch may legitimately end with stronger evidence but no completed reviewed log;
- frozen Revision-05 was ACCEPTed with commit_only_if_earned=true and a writer rule forbidding either branch from guaranteeing a log;
- P2.6 gate input did not include the later human-approved authority, so Luna reasserted the older premise payoff.

Decision:
- do not change the P2.5 candidate on this basis;
- do not mutate the production/frozen generic gate;
- P2.7 uses a qualification-only authority-aware Luna gate where explicit Revision-05 mechanics outrank conflicting older premise mechanics.

### P2.7 — PREPARED, NOT RUN

Free preparation complete:
- frozen Revision-05 qualification authority pinned;
- separate authority-aware gate prompt created;
- same P2.5 normalized candidate reused; no Sonnet call;
- production gate prompt remains untouched;
- regression: 47/47 PASS.

Paid scope, if authorized: GPT-5.6 Luna gate only.


### P2.7 — AUTHORITY-AWARE LUNA GATE ACCEPT
Run: 36551283455.

- Same P2.5 Sonnet 5.5 spine reused.
- Qualification-only safe normalization applied once; semantic fields unchanged.
- Frozen human-approved Revision-05 mechanics supplied as top authority where they explicitly refine the older premise.
- No new Sonnet call.
- GPT-5.6 Luna gate decision: ACCEPT.
- Blocking reasons: none.
- All 11 gate dimensions scored 5/5.
- Incremental Luna cost: $0.00352105.
- Incremental Luna latency: 8.153s.
- Candidate Architect + authority-aware Luna cost: $0.09199505.
- Candidate Architect + gate latency: 49.877s.
- Candidate Architect + gate total tokens: 29,807.
- Writer remains unauthorized pending human spine review.

Interpretation:
- P2.6 REPLAN was confirmed as an authority-input defect, not a candidate-spine defect.
- The fresh_setup_retest branch may legitimately end with stronger evidence and no completed reviewed log, exactly as frozen Revision-05 allows.
- first_discrepancy_logged remains commit-only-if-earned.
- Sonnet 5.5 candidate is now mechanically qualified for human review; no writer inference is authorized by this result.


### Writer qualification — Aion 3.5 Mini on P2.7 approved spine
Run: 36552606045.

- Deterministic status: PASS.
- English words: 1,988 (target 1,600-2,500).
- Chosen branch: report_now.
- Writer cost: $0.0140658.
- Writer latency: 105.118 s.
- Writer tokens: 13,909 total; 3,926 reasoning.
- Source spine+gate+writer pipeline cost: $0.10606085.
- Source pipeline tokens: 43,716.
- No audit/repair/translation call was made.

Compared with frozen baseline Writer run 36526379349:
- Writer cost: $0.02961708 -> $0.0140658 (-52.5%).
- Writer latency: 342.112s -> 105.118s (-69.3%).
- Reasoning tokens: 19,638 -> 3,926 (-80.0%).
- Frozen baseline spine+writer: $0.14919643.
- Sonnet 5.5 spine+writer: $0.10606085 (-28.9%).

Human pre-audit found likely quality targets before any paid judge:
- unauthorized beacon age/origin history;
- unauthorized old-builder tide knowledge;
- field-notes vs formal-log ambiguity;
- future pilot-spread overcommit;
- mentor identity authority check;
- new mentor backstory.

### P3-A — PREPARED, NOT RUN

Blind Sonnet 5.5 primary-audit qualification is ready:
- Human pre-audit findings are NOT supplied to the model.
- They are used only after inference to score recall.
- One Sonnet 5.5 editorial-audit call only.
- No Sol, repair, re-audit, translation, or fidelity call.
- Regression: 52/52 PASS before paid P3-A.
