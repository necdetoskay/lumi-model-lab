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

### 1.1 Controlled decision-model extensions

The primary #27 verdict remains **JEV-as-Judge**. The reusable lab harness may also be used by separately qualified decision workloads, but no Judge GO/HOLD/REJECT result transfers automatically to them.

Controlled extension tracks:
- **#38 X1 — model/agent routing qualification**
- **#39 X2 — StoryOpportunity relevance/ranking qualification**
- **#40 X3 — bounded NPC reaction selection qualification**

Each extension owns a separate dataset, policy, metrics, protected holdout and GO/HOLD/REJECT verdict. They do not block the core Judge Lab execution order and they do not authorize Project_LUMI runtime integration.

### 1.2 Provider-agnostic Decision Engine Lab relationship

Shared decision-engine architecture is now governed by `docs/canonical/DECISION_ENGINE_LAB.md`.

This Judge contract remains authoritative for the story-judge workload, corpus, false-PASS gates, human calibration and JEV-specific evidence. The shared contract adds provider/model-neutral rules for:

- comparing JEV against open/local bounded decision engines,
- normalizing engine/runtime evidence,
- explicit `INSUFFICIENT_EVIDENCE` / `ESCALATE` semantics,
- local RTX 4060 8 GB qualification lanes,
- cascade comparisons,
- reproducible engine identity,
- later LUMI-specialized contrastive/counterfactual training.

A result from another decision engine does not inherit JEV qualification, and JEV does not inherit another engine's qualification. Every workload/engine pair retains its own evidence and verdict.

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

### Variant C
Turkish source/candidate + **controlled English semantic projection** + English rubric/questions.

Variant C exists to test the hypothesis that JEV performs better on an English decision representation without forcing the whole LUMI generation pipeline to become English-first. The projection must preserve canonical IDs, enumerations, numbers, chronology and structured state exactly. Any translation/projection step is part of the measured system and must be fingerprinted.

The test must record:

- decision agreement,
- critical false-PASS,
- per-dimension agreement,
- confidence calibration,
- cost,
- latency,
- failure rate,
- projection/translation disagreement for Variant C,
- projection cost and latency for Variant C.

English-first or English-projected evaluation is promoted only if held-out evidence supports it and the projection layer does not introduce unacceptable semantic drift.

If later used by Project_LUMI, canonical structured state remains language-independent where possible. User-facing Turkish localization remains a separate surface-quality problem and is not declared safe merely because an English semantic judge passed.

## 10. Decision-engine / harness boundary

JEV is accessed only through a Model Lab experiment adapter.

The shared transport/evidence core is a **provider-agnostic decision-engine adapter** governed by `DECISION_ENGINE_LAB.md`. It must support JEV and separately qualified open/local bounded decision engines without hiding their native differences.

The transport/evidence core should be reusable across **typed workload profiles** rather than hard-coded to story judging. Reuse of the transport/harness does not imply reuse of qualification evidence or a shared production abstraction.

A workload profile must identify at least:
- task/profile identifier and version,
- input/state schema version,
- question/choice/action-set version,
- expected output shape,
- risk class and deterministic preconditions,
- dataset/partition fingerprint.

The adapter must capture at least:

- engine family,
- provider/runtime,
- exact model identifier,
- model revision / commit / artifact hash when exposed,
- quantization when applicable,
- serving stack/version,
- rubric/question/choice-set version,
- language/projection variant,
- input/corpus fingerprint,
- request/state size,
- returned levels/choices/probabilities/confidence,
- device/GPU for local runs,
- peak VRAM where measurable,
- cold/warm latency and p50/p95 aggregation,
- usage/token accounting when exposed,
- provider cost or reproducible local cost estimate,
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
- Brier score where a binary/probabilistic target exists
- log loss where probability vectors are comparable
- expected calibration error (ECE) or a documented equivalent
- threshold sweep
- confidence-vs-error relationship
- selective risk / coverage curve
- area under the risk-coverage curve when meaningful
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
- when the supplied evidence may be incomplete, the question/choice contract must expose an explicit `INSUFFICIENT_EVIDENCE`, `ESCALATE`, or equivalent abstention path rather than forcing a normal choice.
- deterministic policy may force escalation regardless of model confidence.

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
- single-fact counterfactual mutations expected to change exactly the relevant decision,
- semantically irrelevant distractor insertion/removal,
- entity renaming that preserves relationships/state,
- missing-evidence / intentionally ambiguous state,
- repeated identical requests.

Every finding records:

- severity,
- exact reproduction artifact,
- expected/reference result,
- observed result,
- confidence,
- repair,
- regression case.

## 15.1 Counterfactual and invariance contract

Accuracy alone is insufficient for a bounded decision model. The lab must explicitly test whether outputs move for the **right reasons**.

Required metamorphic/counterfactual checks include:
- equivalent field/context ordering should not materially change the decision;
- irrelevant context should not materially change the decision;
- changing one causally relevant fact should change only the dimensions/actions that depend on that fact;
- renaming entities while preserving graph/state relations should preserve the decision;
- removing required evidence should reduce confidence, abstain, or escalate rather than invent certainty;
- repeated identical requests must be measured for distribution/decision stability.

Failures are recorded separately from ordinary disagreement because they indicate brittle decision boundaries even when aggregate accuracy appears strong.

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

Controlled, non-blocking extensions:
- **#38 X1** — execution decision routing qualification (model/agent/repair/retry/escalation choices)
- **#39 X2** — StoryOpportunity relevance/ranking qualification
- **#40 X3** — bounded NPC reaction selection qualification

P8 is blocked until P7 records GO.

X1/X2/X3 may reuse #30 provider/evidence harness primitives, but each track must freeze its own fixtures, labels, policies, thresholds and final holdout. A core Judge Lab GO does not qualify an extension track, and an extension GO does not widen the Judge production handoff.

## 19. Change control

This document is canonical for the JEV Judge Lab epic.

Material changes to:

- risk class,
- hard gates,
- protected holdout rules,
- responsibility split,
- promotion targets,
- production-integration boundary,
- transfer of qualification evidence between workload types,
- extension-track authority boundaries

must be changed in this document and called out in the epic before relying on the new rule.

## 20. Current decision

**JEV is not integrated into LUMI runtime.**

The authorized work remains isolated Model Lab qualification under this AEGIS contract.

Core Judge qualification follows P1–P8. X1/X2/X3 are independent lab-only extension tracks and may not mutate Project_LUMI runtime/canonical state or inherit a GO verdict from #27.

JEV remains the proprietary/reference Judge candidate for this contract, but final architecture selection must compare it against qualified open/local decision engines under the shared `DECISION_ENGINE_LAB.md` evidence rules before any production-dependency recommendation is made.
