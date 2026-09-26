# LUMI Story Defect Detection & Bounded Repair v1

Status: **CANONICAL QUALIFICATION ARCHITECTURE — IMPLEMENTATION IN PROGRESS**  
Date: 2026-09-26  
Risk class: AEGIS L3  
Frozen generator baseline: `configs/story_planner_profiles/tr_age4_narrative_load.v1.json`

## 1. Decision

LUMI stops optimizing the current Story V5 generator for first-draft perfection while this program is active.

The promoted Narrative Load v1 architecture is the **Frozen Champion Generator** for the qualified exact-age-4 / READ_ALOUD / nominal-500-soft scope.

The new product objective is:

> detect serious defects before publication, repair the smallest valid region, then independently prove that the repair fixed the defect without creating a regression.

LLM variance is treated as an expected property of generation. Reliability is therefore enforced at the system boundary rather than assumed from one generation.

## 2. Priority

False negatives are more expensive than false positives for serious physics/logic defects.

A false positive may cause an extra verifier call. A false negative may publish an incoherent story.

Primary qualification metric:

`SERIOUS + CRITICAL DEFECT RECALL`

Secondary metrics include precision, family recall, span-location recall, repair success, harmful-repair rate, latency and cost per accepted story.

## 3. Defect taxonomy

The first qualification wave covers:

- `physical_feasibility` — impossible or unsupported physical action/affordance;
- `causal_logic` — effect does not follow from established causes/rules;
- `state_continuity` — object/action/state silently resets or contradicts committed state;
- `epistemic_order` — a character uses information not yet observed/learned;
- `spatial_consistency` — incompatible location/position state;
- `temporal_consistency` — impossible or contradictory order/duration;
- `response_causality` — response limitation is incorrectly converted into perception failure;
- `closure_integrity` — story reopens action/payoff after terminal closure;
- `canon_integrity` — repair or prose invents/contradicts durable canon.

Language polish, age fit and literary quality remain separate gates. They must not hide a serious physical/logical failure behind a high aggregate score.

## 4. Detection architecture

```text
Frozen Champion Generator
        |
        v
completed draft + immutable StoryContract/state
        |
        +--> deterministic invariants
        |
        +--> JEV semantic sentinel
        |      - atomic defect-family questions
        |      - advisory only
        |      - no clean-pass authority until calibrated
        |
        v
risk map
        |
        v
strong defect verifier / locator
        |
        v
typed DefectMap
        |
        +--> LOCAL_REPAIR
        +--> STRUCTURAL_REPAIR
        +--> REPLAN
        |
        v
minimal repair
        |
        +--> same-defect verification
        +--> collateral regression verification
        |
        v
publication gate
```

## 5. JEV role

Pinned candidate: `typesafe/jev-1.13`.

JEV is not the final judge and not the repair writer.

Its first role is a cheap, fast semantic sentinel that answers atomic questions such as whether the story contains a physical, causal, state, epistemic, spatial, temporal, response-causality or closure risk.

One broad question such as “is this story good?” is forbidden for this lane.

Until calibration is complete:

- JEV cannot independently mark a story clean;
- no existing continuity threshold is inherited automatically;
- confidence is not interpreted as calibrated probability of correctness;
- threshold selection must come from the frozen LUMI defect corpus;
- suspicious and ambiguous cases escalate to the strong verifier.

## 6. DefectMap contract

Every confirmed finding must contain:

- defect family;
- severity;
- exact sentence/span IDs;
- concise reason;
- evidence/dependency;
- repair scope: `NO_REPAIR | LOCAL_REPAIR | STRUCTURAL_REPAIR | REPLAN`.

The verifier finds and classifies. It does not rewrite.

## 7. Repair ownership

### LOCAL_REPAIR

Allowed when the defect can be corrected inside one bounded span and the story's upstream/downstream causal state remains unchanged.

### STRUCTURAL_REPAIR

Required when setup, evidence, knowledge, object state or multiple dependent spans must change together.

### REPLAN

Required when the main causal chain, solution principle, StoryContract or core spine is invalid. A prose patch must never hide a plan defect.

## 8. Bounded repair contract

A repair receives only the authoritative contract/state, the confirmed DefectMap finding and the smallest context needed to make the edit.

Rules:

- make the minimum necessary change;
- preserve unrelated accepted prose;
- create no new canon;
- do not move the solution merely to silence the verifier;
- preserve typed object/knowledge/location obligations;
- after repair, rerun the exact defect check;
- then run a collateral regression check;
- unresolved serious risk cannot publish.

## 9. D0 — Frozen Defect Corpus & Detector Benchmark

D0 creates a versioned, immutable corpus with both clean and intentionally corrupted examples.

Each corrupted example records:

- clean source;
- one controlled mutation where possible;
- exact defect family;
- severity;
- gold span;
- expected repair scope.

Initial seed fixtures are contract tests only. They are **not qualification evidence**.

Qualification corpus target: at least 200 cases, with adequate positive coverage for each priority family. Representative full stories from the Frozen Champion Generator must be included; micro-fixtures alone cannot qualify a production detector.

Candidate targets:

- critical recall: 100%;
- serious+critical recall: >=98%;
- physical + causal-logic recall: >=99%;
- harmful repair rate: <=1%.

These are candidate goals, not permission to tune against one fixture. Any threshold change requires frozen held-out evidence.

## 10. Radar patterns adopted

This architecture directly adopts the Radar repository's:

- **Calibrated Evaluator as Measurement Instrument** — judge identity/prompt/threshold/aggregation are versioned and calibrated against trusted labels;
- **Adversarial Evaluation Matrix** — defect family × mutation × story family × severity;
- **Evaluator-Gated Self-Improvement** — detector/repair changes must beat the frozen accepted baseline before promotion;
- **Action-Binding Constraint Preservation** — state/canon obligations remain typed across repair;
- **Causal Capability Contribution Ablation** — JEV, strong verifier and repair stages must prove incremental lift;
- **Verification Capacity as Throughput Constraint** — accepted verified stories, not raw generations, define throughput.

## 11. Planned phases

- **D0** — contracts, segmentation, corpus schema, scoring harness, seed fixtures.
- **D1** — build 200–500 frozen labeled cases, emphasizing physics/logic/state.
- **D2** — qualify JEV sentinel; measure recall, bias and threshold curves.
- **D3** — qualify strong defect verifier/locator and escalation policy.
- **D4** — implement LOCAL/STRUCTURAL/REPLAN router and minimal repair.
- **D5** — independent same-defect + collateral regression verification.
- **D6** — adversarial matrix, ablations, held-out regression and economics.
- **D7** — production integration, telemetry, rollback and versioned promotion.

## 12. Freeze rule

During D0–D6, do not mutate Narrative Load v1 or the Frozen Champion Generator merely to make detector benchmark cases easier.

If a genuine generator defect is discovered, record it. Repair/detection must first prove it can contain the defect. A later generator v2 may address systematic causes through a separate qualification track.

This separation prevents the benchmark target from moving while the verifier is being measured.
