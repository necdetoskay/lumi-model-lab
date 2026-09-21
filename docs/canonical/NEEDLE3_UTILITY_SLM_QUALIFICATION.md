# Needle 3 Utility SLM Qualification — Canonical AEGIS Contract

Status: **PROPOSED / LAB-ONLY**  
Canonical owner: **LUMI Model Lab**  
Epic: **#77 — Needle 3 Utility SLM Qualification**  
Parent research track: **#10 — Utility SLM Track**  
Conditional routing extension: **#38 / #85**  
Risk class: **AEGIS L2 in Model Lab**  
Future Project_LUMI integration: **fresh AEGIS L3 required**

## 1. Purpose

This document is the single source of truth for qualifying Cactus Compute Needle 3 as a tiny local/open specialist for narrow LUMI utility work.

The first workload is **U1 — Story State Delta Extraction**.

Needle 3 is **not** being evaluated here as:
- a long-form story generator;
- a holistic literary judge;
- a general reasoning model;
- a source of canonical truth;
- an autonomous tool executor.

The experiment asks a narrower question:

> Can a tiny local specialist reliably extract evidence-bound candidate state changes from stories, and later, only if separately qualified, select bounded tools/actions with typed arguments, while deterministic code retains all authority?

## 2. Architectural position

Needle 3 occupies a different niche from the current decision-engine/JEV track.

```
Exact rules / authority
        |
        v
Deterministic code
        |
        +------------------------------+
        |                              |
        v                              v
Decision engine                  Needle-style utility SLM
semantic score/choice            extraction/tool/arguments
        |                              |
        +---------------+--------------+
                        |
                        v
              stronger model if needed
```

The two lanes may be compared on overlapping routing workloads, but qualification does not transfer between them.

## 3. Authority boundary

Needle output is always **candidate evidence**.

Deterministic code owns:
- authorization and ownership;
- allowed action/tool sets;
- schema acceptance;
- canonical identifier validity;
- exact inventory/state membership;
- exact graph/reachability rules;
- revision/CAS/idempotency;
- budget ceilings;
- hard safety policy;
- canonical mutation and commit authority.

Needle may:
- extract candidate deltas;
- classify a bounded candidate;
- select from an explicit finite tool/action set;
- fill typed arguments;
- provide confidence/evidence used by routing policy.

Needle may not:
- invent authority;
- commit Character/World/Saga state;
- fabricate canonical IDs;
- bypass deterministic rules;
- execute arbitrary tools;
- convert confidence into permission.

## 4. First workload: U1 Story State Delta Extraction

Input:
- finished story text;
- bounded pre-story canonical context;
- supplied canonical IDs and known aliases where relevant;
- workload/schema version.

Output:
- zero or more **candidate deltas**;
- evidence supporting each candidate;
- uncertainty / insufficient-evidence state;
- confidence when exposed by the runtime.

Examples of candidate delta families:
- item acquired/lost/changed;
- NPC introduced/referenced;
- relationship changed;
- location discovered;
- thread opened/closed/advanced;
- Saga/Origin breadcrumb candidate;
- other explicitly versioned U1 categories.

No output is directly committable.

The exact v1 task contract is defined in:
`docs/canonical/NEEDLE3_U1_EXTRACTION_CONTRACT_V1.md`.

## 5. Experiment matrix

Base qualification must precede fine-tuning.

Initial Needle variants:
- 20-layer candidate;
- 8-layer candidate;
- 4-layer candidate.

Reference baselines:
- deterministic implementation where feasible;
- strong API/reference model;
- existing Utility SLM baseline when available.

Language variants:
- A — Turkish native;
- B — English;
- C — Turkish source -> controlled English semantic projection -> Needle.

Every variant receives separate evidence.

## 6. Required lineage and fingerprint

Every run must record at least:
- workload/profile version;
- corpus manifest/hash;
- partition identity;
- model/artifact identity;
- model depth/export identity;
- runtime/package version;
- quantization/export identity if applicable;
- prompt/schema/tool-set version;
- language/projection variant;
- code commit;
- device/GPU/CPU class;
- RAM/VRAM where measurable;
- telemetry configuration;
- threshold/policy version;
- fine-tuned vs base identity;
- training dataset fingerprint for trained artifacts.

Base and fine-tuned evidence must never be silently mixed.

## 7. Core metrics

For U1:
- schema-valid rate;
- field-level precision/recall/F1;
- unsupported/hallucinated candidate rate;
- omission rate;
- no-change accuracy;
- negation accuracy;
- hypothetical/conditional accuracy;
- quoted-claim handling;
- ambiguity handling;
- multi-delta accuracy;
- evidence/span correctness where supported;
- confidence calibration;
- p50/p95 latency;
- cold/warm latency;
- RAM/VRAM;
- artifact size.

The most important safety-oriented errors are:
1. unsupported state delta;
2. critical omission;
3. high-confidence wrong extraction.

## 8. Confidence and abstention

Confidence is routing evidence, not truth.

The lab must not adopt vendor example thresholds as promotion policy.

Where confidence is available, measure:
- Brier score and/or log loss where meaningful;
- ECE or documented equivalent;
- selective-risk / coverage;
- high-confidence error inventory;
- error rate above candidate thresholds.

The runtime/policy must support:
- normal candidate;
- insufficient evidence / abstain;
- deterministic rejection;
- escalation to stronger evaluation.

## 9. Language qualification

Turkish support is empirical.

Controlled English projection must preserve:
- canonical IDs;
- enumerations;
- numbers;
- chronology;
- negation;
- uncertainty;
- entity relations;
- state membership.

Projection latency, drift, omission and unsupported-delta changes are part of the result.

## 10. Red-team requirements

At minimum test:
- prompt/instruction-like story text;
- quoted false facts;
- hypothetical actions;
- negation and double negation;
- aliases and near-duplicate names;
- unsupported ID bait;
- irrelevant-context flooding;
- field/context reorderings;
- long-context dilution;
- missing evidence;
- ambiguous evidence;
- repeated identical input;
- schema-pressure/malformed cases;
- high-confidence wrong outputs.

Any critical failure must remain visible in the final verdict.

## 11. Privacy / telemetry

Qualification runs must default to telemetry-off configuration where the runtime permits it.

Secrets, prompts, outputs and dataset artifacts must not be sent to unapproved services by default.

Any telemetry exception requires:
- explicit experiment purpose;
- separate run identity;
- documented data surface;
- no protected holdout leakage.

## 12. Fine-tuning gate

Fine-tuning is **conditional**, not the starting point.

P6 may proceed only if P3–P5 show:
- the base model is technically viable;
- the task fit is promising;
- the remaining error profile appears learnable;
- the expected benefit justifies added maintenance complexity.

Training may teach:
- extraction semantics;
- schema behavior;
- uncertainty/no-change behavior;
- evidence binding;
- stable task policy.

Training must not encode mutable LUMI user/world facts as knowledge.

All fine-tuned artifacts must be requalified on an untouched protected holdout.

## 13. Conditional bounded tool-routing lane

#85 may proceed only after earlier evidence justifies it.

Possible bounded actions may include:
- CONTINUE;
- RETRY;
- TARGETED_REPAIR;
- REPLAN;
- REQUEST_MORE_CONTEXT;
- USE_ECONOMICAL_MODEL;
- USE_STRONGER_MODEL;
- ESCALATE;
- ABORT.

Needle may return only a candidate action/tool plus typed arguments.

Deterministic orchestration still validates:
- allowlist membership;
- authorization;
- budgets;
- safety;
- schema;
- execution preconditions.

U1 success does not qualify routing automatically.

## 14. Execution order

- #78 P0 — freeze this contract, risk map and fingerprint
- #79 P1 — local runtime adapter + telemetry-off smoke
- #80 P2 — frozen U1 corpus + protected holdout
- #81 P3 — base 20L/8L/4L benchmark
- #82 P4 — Turkish/English/controlled-English comparison
- #83 P5 — confidence calibration + red-team
- #84 P6 — conditional LoRA fine-tune + artifact requalification
- #85 P7 — conditional #38 bounded tool/execution routing
- #86 P8 — independent AEGIS re-review + final verdict

## 15. Final U1 verdict

Exactly one:
- `PROMISING_LOCAL_UTILITY`
- `CLOUD_SMALL_MODEL_ONLY`
- `RESEARCH_ONLY`
- `REJECT_FOR_TASK`

A positive verdict does not authorize Project_LUMI production deployment.

## 16. Production boundary

This document authorizes **Model Lab qualification only**.

Any Project_LUMI adoption requires:
- fresh AEGIS L3 architecture/security review;
- production-specific shadow evidence;
- deterministic authority preservation;
- explicit admission for the exact workload.

No legacy/fallback production path is created by this experiment.

## 17. Current decision

Proceed with Needle 3 as a **narrow Utility SLM candidate**, beginning with U1 Story State Delta Extraction. Measure the base model first. Fine-tune only after evidence. Treat bounded tool routing as a later, separately qualified extension.
