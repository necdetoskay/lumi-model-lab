# JEV Judge Lab — Canonical AEGIS Qualification Contract

Status: **PROPOSED / LAB-ONLY**  
Canonical owner: **LUMI Model Lab**  
Epic: **#27 — JEV Judge Lab — AEGIS Qualification & Judge Cascade Decision**  
Risk class: **AEGIS L2 for this lab experiment**  
Future Project_LUMI integration: **AEGIS L3 required; not authorized by this document**

## 1. Purpose

This document is the single source of truth for evaluating JEV as a fast probabilistic judge for LUMI story-quality workflows.

The experiment exists to answer one question with reproducible evidence:

> Can JEV safely handle a large share of routine semantic judge decisions, while deterministic validation owns hard invariants and an LLM judge handles uncertain or deep-narrative cases, such that end-to-end quality is preserved and judge cost/latency materially improve?

This is a falsification exercise, not an integration project.

## 2. Current system baseline

The repository already contains:

- a common six-dimension LLM judge;
- the frozen story benchmark and story specifications;
- stored judge artifacts under `runs/judgments/`;
- a 30-case human calibration manifest at `data/specifications/judge_human_calibration_v1.json`;
- a blind-human-label rule;
- current acceptance logic based on average/minimum scores and critical failures;
- existing cost/usage metadata for model qualification.

The existing six dimensions are:

1. instruction following,
2. coherence,
3. character consistency,
4. age appropriateness,
5. creativity,
6. style quality.

JEV qualification extends this evidence model. It does not silently redefine historical judge results.

## 3. AEGIS scope and classification

### 3.1 L2 experiment boundary

The Model Lab experiment is L2 because it:

- adds an external probabilistic provider;
- changes evaluation-policy research;
- may influence future model-selection economics;
- does **not** mutate Project_LUMI production/canonical state;
- does **not** route live LUMI decisions.

### 3.2 L3 promotion boundary

Any future use in Project_LUMI runtime is a separate L3 change because a judge cascade can affect:

- story acceptance,
- repair routing,
- child-facing content,
- canonical-outcome eligibility,
- production AI cost policy.

A GO verdict in this repository authorizes only a design handoff for a new L3 AEGIS epic in Project_LUMI.

## 4. Non-goals

This epic does not:

- install JEV into Project_LUMI;
- replace the current LLM judge before qualification;
- create a permanent compatibility/dual-read architecture;
- allow JEV to mutate canon, world state, character state, inventory, relationships, or story records;
- treat provider confidence as truth;
- treat vendor benchmarks as qualification evidence;
- optimize cost at the expense of critical false-PASS safety.

## 5. Canonical responsibility split

| Decision class | Authority |
|---|---|
| Structural schema validity | deterministic code |
| Revision / idempotency / CAS / canonical invariants | deterministic code |
| Exact graph reachability when graph data is available | deterministic code |
| Exact inventory/state membership | deterministic code |
| Rule-based age or policy hard constraints | deterministic code |
| Semantic brief/contract alignment | JEV candidate |
| Character-behavior consistency | JEV candidate |
| Opportunity relevance | JEV candidate |
| Character agency | JEV candidate |
| Semantic repetition | JEV candidate |
| Relationship plausibility | JEV candidate |
| Knowledge plausibility | JEV candidate, only when not deterministically decidable |
| Narrative progression | JEV candidate / likely hybrid |
| Ending quality | JEV candidate / likely hybrid |
| Literary quality and deep multi-hop narrative judgment | LLM judge |
| Uncertain or high-risk semantic cases | LLM judge |
| Final production commit authority | Project_LUMI deterministic services, outside this epic |

No benchmark result may promote a structural invariant from deterministic code to JEV solely to improve measured coverage.

## 6. Target architecture under test

```text
Candidate Story / Story Package
            |
            v
+---------------------------+
| Deterministic Validators  |
| schema / exact invariants |
+------------+--------------+
             |
             v
+---------------------------+
| JEV Atomic Judge          |
| Score / Choice / yes-no   |
+------------+--------------+
             |
      confidence + risk
             |
      +------+------+----------------+
      |             |                |
      v             v                v
 clear PASS   repairable FAIL     uncertain/high-risk
      |             |                |
      |             v                v
      |       policy simulation    Current LLM Judge
      |                              |
      +---------------+--------------+
                      v
               Experiment verdict
```

During this epic, the diagram is **simulation/evaluation only**. No live production verdict is affected.

## 7. Gold/reference evidence contract

### 7.1 Starting corpus

The existing 30-case manifest is preserved and extended; it is not replaced.

Current source:

`data/specifications/judge_human_calibration_v1.json`

Only a subset is currently human-labeled. Completing and expanding this reference set is mandatory before final promotion.

### 7.2 Final corpus minimum

Before GO/HOLD/REJECT:

- >=100 labeled/validated cases;
- PASS, BLOCK, borderline, and adversarial coverage;
- explicit critical-protected partition;
- calibration and final holdout partitions;
- immutable final holdout after freeze;
- provenance and hashes for every case.

### 7.3 Blind labeling

Human/reference labeling must remain blind to:

- JEV outputs,
- JEV confidence,
- LLM judge outputs,
- model/provider identity when practical.

Machine output is evidence to compare against human/reference truth; it is never the source of truth.

### 7.4 Critical-protected cases

At minimum include:

- hidden contract violation,
- character knowledge leak,
- relationship contradiction,
- location/state contradiction,
- lost/nonexistent item use,
- unsafe or age-inappropriate content,
- severe text corruption,
- fluent prose with one critical semantic defect,
- prompt injection inside candidate content.

## 8. Atomic rubric contract

JEV must not be qualified using only a single question such as “Is this a good story?”

The JEV rubric is decomposed into atomic dimensions/questions.

Candidate dimensions:

- contract alignment,
- character consistency,
- world/state consistency,
- opportunity relevance,
- character agency,
- repetition,
- age fit,
- relationship consistency,
- knowledge consistency,
- narrative progression,
- ending quality.

Each dimension must define:

- semantic purpose,
- ordinal levels or binary outcome,
- concise level definitions,
- a small set of representative calibration anchors,
- critical/non-critical classification,
- escalation policy,
- version identifier.

Anchor examples come only from calibration data or dedicated synthetic examples, never from the final holdout.

## 9. Language experiment

JEV language behavior is measured rather than assumed.

Required comparison:

### Variant A
Turkish candidate/story representation + Turkish rubric/questions.

### Variant B
English semantic/candidate representation + English rubric/questions.

The test must record:

- decision agreement,
- critical false-PASS,
- per-dimension agreement,
- confidence calibration,
- cost,
- latency,
- failure rate.

English-first is promoted only if held-out evidence supports it.

If later used by Project_LUMI, canonical structured state remains language-independent where possible. User-facing Turkish localization remains a separate surface-quality problem and is not declared safe merely because an English semantic judge passed.

## 10. Provider/harness boundary

JEV is accessed only through a Model Lab experiment adapter.

The adapter must capture:

- provider/model identifier,
- provider model/version metadata when exposed,
- rubric/question-set version,
- input/corpus fingerprint,
- request/state size,
- returned levels/choices/probabilities/confidence,
- latency,
- usage/token accounting when exposed,
- provider cost or reproducible cost estimate,
- retry/error metadata.

The adapter must:

- load secrets only from environment variables;
- never write API keys into logs/artifacts;
- fail closed on malformed/partial outputs;
- classify provider/runtime failure separately from model-quality failure;
- never silently switch providers;
- preserve immutable experiment evidence by fingerprint.

## 11. Reproducibility and experiment fingerprint

A JEV experiment fingerprint must cover at least:

- corpus manifest/hash,
- calibration-vs-holdout partition version,
- rubric version,
- anchor version,
- JEV model/provider version when known,
- language variant,
- threshold/policy version,
- harness version.

Intentional reruns are allowed but must create distinct evidence rather than overwrite prior results.

## 12. Evaluation metrics

### 12.1 Decision safety
- PASS/BLOCK confusion matrix
- critical false-PASS
- non-critical false-PASS
- false-BLOCK
- protected holdout results

### 12.2 Dimension quality
- exact agreement
- adjacent agreement for ordinal scores
- weighted kappa where meaningful
- per-dimension confusion/error analysis

### 12.3 Confidence
- reliability/calibration curves
- threshold sweep
- confidence-vs-error relationship
- escalation coverage
- high-confidence error inventory

### 12.4 Economics
- cost/case
- cost per accepted/blocked case
- total benchmark cost
- full cascade cost including LLM escalations
- savings versus current LLM-judge baseline

### 12.5 Performance
- latency p50/p95
- provider/runtime error rate
- repeat stability

## 13. Promotion targets

These are target gates established **before** final JEV results are observed.

- Critical protected holdout: **0 critical false-PASS**.
- Non-critical held-out PASS/BLOCK agreement target: **>=95%**.
- JEV-owned ordinal dimensions: weighted kappa target **>=0.70**.
- Safe selected cascade policy: LLM-judge escalation target **<=30%**.
- End-to-end judge cost reduction target, including escalation: **>=70%**.
- P95 judge latency improvement target: **>=50%**.

A target may be tightened after baseline measurement. Weakening a target after seeing JEV results requires an explicit AEGIS change record and cannot be hidden in implementation code.

Failure to meet a target does not automatically mean total REJECT; it can result in HOLD/restricted-scope ownership. Critical false-PASS remains a hard blocker.

## 14. Confidence policy rules

Confidence is routing evidence, not correctness.

Rules:

- no single global confidence threshold for every risk class;
- critical/high-risk semantic checks receive stricter gates;
- thresholds are calibrated on calibration data;
- thresholds are frozen before final holdout;
- low-confidence and ambiguous cases escalate;
- high-confidence errors are separately analyzed because they are more dangerous than ordinary errors.

## 15. Red-team plan

The red-team suite must attempt to break the judge with:

- candidate-text prompt injection,
- irrelevant-context flooding,
- long context,
- fluent near-miss defects,
- anchor/rubric mimicry,
- multilingual corruption,
- swapped entities/items/relationships/locations,
- age/safety boundary cases,
- good prose + wrong contract,
- bad prose + correct contract,
- equivalent context reorderings,
- repeated identical requests.

Every finding records:

- severity,
- exact reproduction artifact,
- expected/reference result,
- observed result,
- confidence,
- repair,
- regression case.

## 16. Repair loop

AEGIS repair follows:

```text
finding
  -> reproduce
  -> classify root cause
  -> change one variable
  -> rerun affected calibration cases
  -> run regression set
  -> independent re-review
```

Possible repair surfaces:

- question decomposition,
- rubric wording,
- calibration anchors,
- context minimization,
- language representation,
- confidence policy,
- deterministic/JEV/LLM responsibility split.

Do not “repair” by leaking final holdout examples into anchors.

## 17. GO / HOLD / REJECT

### GO
Evidence supports a safe/economic JEV cascade candidate. Outcome: create only the Project_LUMI L3 design handoff in #36.

### HOLD
JEV is useful only for restricted dimensions or evidence is insufficient. Keep it in Model Lab; no LUMI runtime handoff.

### REJECT
JEV does not provide enough safety, quality, stability, or economics. Preserve evidence and stop integration work.

## 18. Issue map / execution order

- **#27** — Epic / SSOT execution tracker
- **#28 P0** — Canonical contract & AEGIS risk map
- **#29 P1** — Gold dataset & blind human labels
- **#30 P2** — Isolated JEV harness & evidence ledger
- **#31 P3** — Atomic rubric, anchors, English-first variants
- **#32 P4** — JEV vs LLM judge vs human benchmark
- **#33 P5** — Red-team/falsification
- **#34 P6** — Confidence calibration & cascade simulation
- **#35 P7** — Independent AEGIS re-review and GO/HOLD/REJECT
- **#36 P8** — Conditional Project_LUMI L3 handoff after GO only

P8 is blocked until P7 records GO.

## 19. Change control

This document is canonical for the JEV Judge Lab epic.

Material changes to:

- risk class,
- hard gates,
- protected holdout rules,
- responsibility split,
- promotion targets,
- production-integration boundary

must be changed in this document and called out in the epic before relying on the new rule.

## 20. Current decision

**JEV is not integrated into LUMI runtime.**

The only authorized next step is isolated Model Lab qualification under this AEGIS contract.
