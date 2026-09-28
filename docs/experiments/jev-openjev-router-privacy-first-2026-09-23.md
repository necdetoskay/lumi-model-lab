# Jev/OpenJEV Router — Privacy-First Routing and Difficulty Calibration

Status: **RADAR EVIDENCE / LAB-ONLY**  
Date: **2026-09-23**  
Source video: https://www.youtube.com/watch?v=ZR7anrL50xs  
Primary canonical owner: `docs/canonical/DECISION_ENGINE_LAB.md`  
Primary experiment issue: **#38 — Execution Decision Routing qualification**  
Related epic: **#27 — JEV Judge Lab — AEGIS Qualification & Judge Cascade Decision**

## Decision

The video materially strengthens the existing Decision Engine Lab direction but does **not** justify direct Project_LUMI integration.

The useful architectural result is not "use JEV as the router." The useful result is:

> qualify a provider-agnostic bounded routing plane that can emit lane, difficulty, locality/privacy, web/tool need and context-sufficiency signals, then let deterministic policy select an allowed execution route.

JEV remains a reference hosted engine. Local/open decision engines remain first-class candidates.

## What the demonstration adds

The demonstrated router evaluates several bounded questions over one state:

- lane/category choice,
- task difficulty score,
- privacy/PII-like detection,
- whether web access is needed.

The routing policy then combines those semantic signals with deterministic facts such as prompt length and configured model tiers.

The strongest new evidence for LUMI is the separation between **semantic decision signals** and **deterministic routing authority**.

## Critical privacy finding

A cloud model cannot be the first privacy gate for raw sensitive input.

If raw text is sent to a hosted decision service so that it can answer "does this contain private data?", the data has already crossed the locality boundary. Therefore:

- exact secret/credential patterns should be handled deterministically/local-first;
- a learned privacy classifier used before cloud egress must run locally/private;
- uncertain cases must fail toward local/private execution or escalation;
- hosted JEV may be used only after the privacy/locality gate permits egress.

This is a required routing architecture property, not merely a benchmark metric.

## Difficulty score interpretation

The demo uses a bounded difficulty score to decide whether a task can stay on a small/local model or should escalate.

LUMI must not copy a fixed threshold such as "difficulty > N => strong model" from the demo.

The score becomes useful only after calibration against frozen LUMI evidence:

- downstream task success by model tier,
- cost and latency,
- false economical-route failures,
- unnecessary strong-model escalations,
- routing regret against a measured oracle/frontier.

A human "difficulty" label is secondary. The actual target is **which route succeeds at acceptable quality/cost/risk**.

## Qualification additions for #38

Add fixtures that separately exercise:

1. lane/category classification;
2. ordinal task difficulty;
3. web/tool-needed decision;
4. context-insufficient / request-more-context decision;
5. privacy-sensitive / local-only routing;
6. combined multi-question request behavior;
7. confidence-triggered abstention/escalation;
8. deterministic prompt-length / hard-policy overrides.

Required comparisons:

- JEV hosted reference;
- selected local/open decision engine;
- stronger LLM/router baseline;
- deterministic-only baselines where applicable.

## Red-team additions

- obvious API key / credential markers;
- names, phone/email, child-profile-like content and mixed sensitive/non-sensitive state;
- privacy signal hidden inside long irrelevant context;
- instruction-like text attempting to force cloud routing;
- high-confidence wrong privacy classification;
- task that looks simple linguistically but fails on the economical model;
- task that looks difficult linguistically but succeeds reliably on the economical model;
- prompt-length threshold boundary;
- web-needed false-positive and false-negative cases;
- identical state with candidate/action order permutation.

## Evidence policy

Public/demo results are context only. They do not qualify any engine for LUMI.

The video reports very low decision latency, a high local-deflection share in its own demo, and successful use of a local SemIf/OpenJEV-style engine. Those are hypotheses to reproduce under LUMI fixtures, not promotion evidence.

## Production boundary

No change to Project_LUMI production routing is authorized.

Any #38 GO verdict remains a Model Lab result and requires a fresh Project_LUMI AEGIS L3 handoff before runtime use.
