# LUMI Decision Engine Lab — Canonical Qualification Contract

Status: **PROPOSED / LAB-ONLY**  
Canonical owner: **LUMI Model Lab**  
Related research epic: **#27 — JEV Judge Lab — AEGIS Qualification & Judge Cascade Decision**  
Primary extension: **#38 — Execution Decision Routing qualification**  
Related extensions: **#39 StoryOpportunity ranking**, **#40 bounded NPC reaction selection**  
Risk class: **AEGIS L2 for Model Lab experiments**  
Future Project_LUMI integration: **fresh AEGIS L3 required**

## 1. Purpose

This document is the provider-agnostic canonical contract for evaluating fast bounded decision engines in LUMI Model Lab.

The lab no longer asks only:

> Can JEV perform a particular LUMI decision workload?

The broader canonical question is:

> Which bounded decision engine and cascade policy can safely remove routine work from expensive reasoning/judge models while preserving deterministic authority, zero critical false-PASS requirements, reproducibility, and end-to-end quality?

JEV remains an important proprietary/reference engine. It is not the architectural center of the decision plane.

Open/local engines may be tested under the same evidence contract. Candidate families can include, but are not limited to:

- JEV or a compatible hosted typed-decision service,
- Decider-style small typed decision models,
- SemIf/logit-readout approaches over an existing open model,
- multilingual encoder/classifier approaches such as Laya-style models,
- NanoJev-style compact decision models,
- OpenJev/NLI-style cross-encoder approaches,
- later LUMI-specialized fine-tuned decision models.

Model names are candidate identities, not architectural dependencies.

## 2. Architectural principle

The target pattern under test is:

```text
Incoming state / candidate artifact
             |
             v
+-------------------------------+
| Deterministic preconditions   |
| schema / auth / privacy /     |
| locality / exact rules        |
+---------------+---------------+
                |
                v
+-------------------------------+
| Bounded Decision Engine       |
| choice / score / probability  |
+---------------+---------------+
                |
         confidence + risk
                |
      +---------+----------+------------------+
      |                    |                  |
      v                    v                  v
clear bounded        repair/reroute      uncertain /
decision             bounded action      high-risk
      |                    |                  |
      +--------------------+------------------+
                           |
                           v
                  Stronger LLM / human /
                  deterministic authority
```

A decision engine is a **traffic-control / classification layer**, not an autonomous authority.

## 3. Authority boundary

Deterministic code owns all exact and enforceable invariants, including:

- authorization and ownership,
- provider/model allowlists,
- privacy/data-classification and provider-locality policy before any hosted call,
- deterministic context/token-length ceilings where they are known exactly,
- hard budget ceilings,
- schema validity,
- revision/CAS/idempotency rules,
- exact graph reachability when known,
- inventory/state membership,
- hard age/safety/policy constraints,
- allowed action sets,
- final Project_LUMI state mutation and commit authority.

A bounded decision engine may:

- classify,
- score,
- rank already eligible candidates,
- choose among an explicitly allowed finite action set,
- recommend retry/repair/escalation paths,
- provide probabilities/confidence used by routing policy.

A bounded decision engine may not:

- invent a new action outside the supplied set,
- bypass deterministic constraints,
- create authority from confidence,
- mutate production/canonical state during Model Lab qualification,
- replace deep reasoning merely because it is cheaper or faster.

## 4. Canonical decision semantics

Every workload profile must use a typed bounded output contract.

Supported semantic primitives:

### 4.1 Choice

Select or score among an explicit finite option set.

Example:

```text
ACCEPT
TARGETED_REPAIR
REGENERATE
ESCALATE
```

### 4.2 Score

Return a bounded scalar or ordinal score with documented meaning.

Examples:

- semantic relevance,
- urgency,
- consistency likelihood,
- repairability.

### 4.3 Binary / nullable decision

A yes/no decision is permitted only when lack of evidence is distinguishable from a negative answer.

Where evidence may be incomplete, the workload must expose an explicit uncertainty path.

## 5. Mandatory abstention / escalation rule

A bounded decision workload must not force a model to fabricate certainty when the supplied state is insufficient.

Where materially applicable, the allowed decision set must include one or both of:

- `INSUFFICIENT_EVIDENCE`
- `ESCALATE`

Equivalent workload-specific names are allowed only when their semantics are explicit and versioned.

Rules:

1. missing required evidence must not be silently mapped to a normal business choice;
2. confidence below the calibrated safe region must route to abstention/escalation;
3. high-risk classes may require escalation even at high confidence;
4. deterministic policy may force escalation regardless of model preference;
5. escalation is a valid successful decision outcome, not a model failure.

## 6. Workload profiles

The reusable harness may serve multiple independent workload profiles.

Each profile must define at least:

- `profile_id` and version,
- input/state schema version,
- deterministic preconditions,
- allowed choices/actions,
- output semantics,
- risk class,
- ground-truth/reference policy,
- dataset fingerprint,
- calibration partition,
- protected final holdout,
- escalation policy,
- qualification verdict.

Qualification evidence does not transfer automatically between workload profiles.

### 6.1 Judge profile

Owned by `docs/canonical/JEV_JUDGE_LAB.md`.

Candidate semantic responsibilities may include:

- contract alignment,
- character consistency,
- opportunity relevance,
- repetition,
- agency,
- relationship plausibility,
- knowledge plausibility when not exact,
- selected narrative progression dimensions.

Deep literary and multi-hop judgment remains LLM-owned unless separately qualified.

### 6.2 Execution Decision Routing profile

#38 is expanded from model/agent selection into bounded **execution decision routing**.

Candidate action families include:

- `CONTINUE`,
- `RETRY`,
- `TARGETED_REPAIR`,
- `REPLAN`,
- `USE_ECONOMICAL_MODEL`,
- `USE_STRONGER_MODEL`,
- `USE_SPECIALIST`,
- `REQUEST_MORE_CONTEXT`,
- `INSUFFICIENT_EVIDENCE`,
- `ESCALATE`,
- `ABORT`.

The exact set is fixture-specific and versioned.

This profile does not authorize the decision engine to execute arbitrary tools or actions. Deterministic orchestration validates the selected action before execution.

#### 6.2.1 Router signal decomposition

Execution routing qualification must distinguish **semantic signals** from the final route/action.

Candidate semantic signals may include:

- task/lane classification,
- ordinal task difficulty,
- whether web/tool access is semantically required,
- whether the state appears privacy-sensitive,
- whether additional context is required,
- route confidence / probability distribution.

These signals are evidence for deterministic routing policy; none of them directly creates execution authority.

Difficulty is not a model-tier label by itself. A `difficulty` score is useful only after it is calibrated against measured downstream success/failure for the actual candidate model tiers on frozen LUMI workloads. The lab must therefore measure routing regret and task success, not merely agreement with a human difficulty label.

Where an engine can answer several typed questions over the same state in one request, the lab should test the combined request shape as well as independent requests. Parallel multi-question evaluation may reduce latency/cost, but shared-state convenience must not be treated as proof of question independence or correctness.

#### 6.2.2 Privacy/locality pre-gate

A hosted decision engine must not receive raw sensitive state merely to decide whether that state was safe to send to the hosted engine.

For any routing profile that contains personal, credential, confidential, financial, medical, child, or other restricted data:

1. deterministic/local classification and redaction rules run first where exact patterns are available;
2. any learned privacy/sensitivity classifier used before cloud egress must itself run locally or on an explicitly approved private runtime;
3. hosted JEV or any other cloud decision service may receive only the state allowed by that pre-gate;
4. uncertain privacy classification fails toward the safer locality/escalation path;
5. the experiment records whether a route was forced local because of privacy policy.

This requirement is independent of a provider's claimed retention policy. It is an architectural data-egress boundary.

### 6.3 StoryOpportunity ranking profile

Owned by #39.

Only deterministically eligible candidates may enter ranking.

The decision engine may score/rank relevance and priority but may not revive an ineligible opportunity.

### 6.4 Bounded NPC reaction profile

Owned by #40.

The decision engine may score/select within a finite action enum. Deterministic validation rejects prohibited or impossible actions.

No UniverseRevision, WorldState, CharacterState, or StoryOutcome mutation is authorized by this lab profile.

## 7. Engine adapter contract

#30 provider/evidence plumbing must be implemented as a **decision-engine adapter**, not a JEV-only transport.

Each engine run must capture:

- engine family,
- provider/runtime,
- exact model identifier,
- model revision / commit / artifact hash when available,
- quantization,
- serving stack and version,
- prompt/question/choice-set version,
- multi-question request shape and question count,
- language/projection variant,
- input/corpus fingerprint,
- device/GPU,
- peak VRAM where measurable,
- cold-start latency,
- warm latency,
- p50/p95 latency,
- returned choice/score/probability distribution,
- normalized router signals (lane, difficulty, locality/privacy, web/tool need, context sufficiency) when applicable,
- selected provider locality (local/private/cloud) and the policy reason,
- malformed/partial-output status,
- retry count,
- usage/token accounting when applicable,
- provider cost or reproducible local cost estimate,
- experiment timestamp and harness version.

The adapter must normalize evidence while preserving engine-native raw output.

No silent provider fallback is allowed.

## 8. Local hardware lane

The primary local qualification target is an **RTX 4060 8 GB** class machine.

The first local/open lane should prioritize models that are realistically runnable on that hardware.

Initial candidate order:

1. Decider-class ~2B model,
2. Decider-class sub-1B model,
3. SemIf/logit-readout over an approximately 4B open model if memory path is viable,
4. multilingual compact encoder/classifier lane,
5. NanoJev-style sub-1B compact lane,
6. OpenJev/NLI-style model where runtime fits.

Larger models may be tested remotely, but they must not distort the local economics baseline.

A model that does not fit the local hardware path is recorded as a hardware/runtime result, not automatically as a quality rejection.

## 9. Benchmark protocol

Every engine compared for one workload must receive:

- the same frozen corpus,
- the same deterministic preconditions,
- the same semantic questions/choice sets,
- the same calibration/final-holdout split,
- equivalent context content,
- a frozen policy version,
- the same privacy/locality pre-gate and redaction policy for cloud-facing comparisons.

Required comparisons include, where relevant:

- human/reference truth,
- current LLM judge/reasoner baseline,
- JEV,
- selected open/local decision engines,
- later LUMI-specialized fine-tuned candidates.

Vendor or public leaderboard results are context only.

They are never promotion evidence for LUMI.

## 10. Reproducibility fingerprint

The experiment fingerprint must include at least:

- workload profile/version,
- corpus manifest/hash,
- calibration/holdout partition,
- deterministic-policy version,
- question/choice/action-set version,
- engine family,
- exact model/revision/artifact hash,
- quantization,
- serving stack,
- hardware/device class,
- language/projection variant,
- threshold/cascade-policy version,
- harness version.

A public model name alone is not a reproducible identity.

## 11. Language qualification

The lab must not assume one language strategy.

Relevant profiles should compare:

- native Turkish input + Turkish decision schema,
- English input/semantic representation + English schema,
- Turkish source + controlled English semantic projection + English schema,
- native multilingual compact engines where applicable.

Controlled projection must preserve:

- canonical IDs,
- enumerations,
- numbers,
- chronology,
- structured state,
- negation and uncertainty.

Projection cost, latency, semantic drift, and failure rate are part of system economics and safety.

## 12. Calibration and confidence

Confidence is routing evidence, not truth.

Required metrics where meaningful:

- confusion matrix,
- critical false-PASS,
- false-BLOCK,
- exact/adjacent agreement,
- weighted kappa,
- Brier score,
- log loss,
- ECE or documented equivalent,
- selective-risk / coverage curve,
- high-confidence error inventory,
- escalation precision/recall,
- coverage at zero critical false-PASS,
- repeat stability.

Thresholds are:

- profile-specific,
- risk-specific where needed,
- calibrated before final holdout,
- frozen before final evaluation.

No global confidence threshold is assumed to work for every workload or engine.

## 13. Counterfactual and invariance qualification

Every serious decision candidate must be tested for whether it changes decisions for the **right reason**.

Required families include:

- single causally relevant fact mutation,
- irrelevant-context insertion/removal,
- entity renaming while preserving relations,
- equivalent context reordering,
- candidate/action ordering changes,
- missing required evidence,
- repeated identical requests,
- adversarial instruction-like content inside state.

The expected property is not merely aggregate accuracy.

The model should:

- change dependent decisions when the relevant fact changes,
- preserve unrelated decisions when irrelevant facts change,
- abstain/escalate when evidence is insufficient.

## 14. LUMI-specialized training lane

Open/local qualification begins zero-shot or with the engine's published weights.

Fine-tuning is a later lane, not the baseline.

The lab may reuse **contrastive/counterfactual fixture construction** to build training data:

```text
case A: all state equal + critical fact X -> decision A
case B: all state equal + critical fact Y -> decision B
```

Training data and evaluation data must remain isolated.

A specialized model is promoted only if it beats the frozen generic baseline on held-out LUMI evidence without worsening critical safety, calibration, robustness, or economics.

## 15. Cascade policies to compare

At minimum, the lab should compare:

### Policy A

```text
Deterministic -> JEV -> Strong LLM
```

### Policy B

```text
Deterministic -> Local/Open Decision Engine -> Strong LLM
```

### Policy C — optional

```text
Deterministic -> Local/Open Engine -> JEV -> Strong LLM
```

### Policy D — privacy-first routing

```text
Deterministic exact guards
  -> Local privacy/locality gate
  -> Local/Open Decision Engine
  -> qualified cloud model only when policy permits
```

Policy D is mandatory to evaluate for workloads that can contain sensitive state. A cloud decision model is never the first privacy detector for raw restricted input.

Policy C must not be preferred merely because it contains more stages.

It is admitted only when evidence shows material additional value after accounting for complexity, latency, failure modes, and maintenance cost.

## 16. Economics

Measure full decision economics, not isolated inference price.

Include:

- engine inference cost,
- translation/projection cost,
- local compute/runtime cost estimate,
- warmup/compile overhead where relevant,
- retries,
- escalation rate,
- downstream strong-model cost,
- latency p50/p95,
- operational complexity,
- local-deflection rate by workload class,
- routing regret from selecting a weaker/stronger tier than downstream evidence supports.

A very cheap first-stage engine is not useful if it causes expensive incorrect routing or excessive escalation.

## 17. Production boundary

This canonical contract authorizes **Model Lab qualification only**.

No result here may directly:

- change Project_LUMI production routing,
- replace a production judge,
- change canonical mutation authority,
- enable autonomous browser/tool execution,
- weaken deterministic guards.

A GO verdict for a profile produces a separate Project_LUMI AEGIS L3 handoff.

Each profile requires its own production admission.

## 18. Relationship to JEV Judge Lab

`JEV_JUDGE_LAB.md` remains the authoritative workload contract for the core story-judge experiment.

This document is authoritative for shared decision-engine architecture:

- provider/model neutrality,
- adapter evidence requirements,
- explicit abstention/escalation semantics,
- local/open comparison lanes,
- reproducible engine identity,
- cascade comparison,
- specialized-training boundaries.

Where the two documents overlap:

- Judge-specific safety targets and corpus rules come from `JEV_JUDGE_LAB.md`;
- shared engine/runtime/evidence rules come from this document;
- the stricter rule wins until explicitly amended.

## 19. Current decision

The lab will not optimize around JEV as a permanent dependency.

The current authorized direction is:

> Build a provider-agnostic LUMI Decision Engine qualification plane in Model Lab, retain JEV as a reference candidate, qualify realistic local/open alternatives on the same frozen evidence, enforce a local/privacy pre-gate before hosted routing decisions, calibrate difficulty against real downstream model success, and escalate uncertain/high-risk/deep-reasoning cases to stronger models.

No production integration is authorized by this decision.
