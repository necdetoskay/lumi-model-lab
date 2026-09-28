# Step 5 Preview — LUMI Qualification Intake

Status: **RESEARCH CANDIDATE / LAB-ONLY**  
Date: **2026-09-23**  
Linked issue: **#94**  
Source video: https://www.youtube.com/watch?v=kvM-5p78XIE  
Official model page: https://www.stepfun.com/step-5-preview  
Official model docs: https://platform.stepfun.ai/docs/en/guides/models/step-5-preview  
Independent reference: https://artificialanalysis.ai/models/step-5

## 1. Decision

`step-5-preview` is admitted as a **Model Lab research candidate**, not a production model.

It should be evaluated for two independent roles:

1. **Story Generator** — against the frozen GLM scene-first baseline.
2. **Premium Narrative Architect** — inside the Long-Horizon Saga Lab.

It is not currently admitted as a Judge/Decision Engine candidate. Those workloads already have purpose-built JEV/local decision-engine qualification tracks and should not spend premium-model budget without a separate reason.

## 2. Verified provider facts

As of 2026-09-23, StepFun documents:

- model id: `step-5-preview`;
- sparse MoE: 600B total parameters, 27B active per token;
- 1M-token maximum input/context;
- 64K maximum output;
- text, image and video input; text output;
- streaming;
- tool calling;
- JSON Mode and JSON Schema structured output;
- reasoning effort: `low`, `medium`, `high`;
- prompt caching;
- direct StepFun API availability.

Current direct API pricing:

- cache-miss input: **$1.00 / 1M tokens**;
- cache-hit input: **$0.05 / 1M tokens**;
- output: **$2.70 / 1M tokens**.

Provider documentation states that output billing includes reasoning tokens.

StepFun says open weights are planned for **2026-10-15**. Until actual weights, license, model card/config and runtime evidence are available, this is only a future provider claim and creates no local/self-host qualification status.

## 3. Independent evidence

Artificial Analysis currently reports:

- Intelligence Index: **44**;
- cost per Intelligence Index task: about **$0.72**;
- strong long-context performance;
- substantially higher-than-median output-token usage / verbosity.

These numbers justify testing but are not LUMI promotion evidence.

Of particular concern, a low per-token price can be offset by verbose reasoning/output. LUMI economics therefore must use **cost per accepted artifact**, not headline token pricing.

## 4. LUMI opportunity

### 4.1 Story Generator

Step 5 may be useful if its long-form behavior avoids the under-length, truncation and scene-budget failures seen in some previous candidates.

However, the opposite failure mode is equally plausible: over-generation, verbose reasoning, redundant prose and expensive output.

The key question is not whether Step 5 writes impressive prose. It is:

> Does Step 5 reliably produce a technically valid, coherent, age-appropriate story at the requested length and scene structure with acceptable cost and latency?

### 4.2 Premium Narrative Architect

The stronger fit is potentially the Long-Horizon Saga Lab because Step 5 combines:

- large context;
- structured output;
- long-horizon / agentic training emphasis;
- high output ceiling;
- aggressive cache pricing.

This may help when producing a durable Origin + Narrative Blueprint from Character + World context.

But creation-time quality is not sufficient. The blueprint must produce measurable downstream narrative lift over repeated stories under the existing Saga evaluation protocol.

## 5. Runtime-profile requirement

Do not run paid qualification under a generic model profile.

Before testing, record an explicit runtime profile covering:

- provider runtime: `stepfun-direct` unless another route is intentionally qualified;
- model id: `step-5-preview`;
- API endpoint/transport;
- structured-output mode;
- reasoning-effort parameter mapping;
- explicit max-output policy;
- timeout/retry behavior;
- usage and reasoning-token accounting;
- cache hit/miss metadata;
- provider request id / trace identity;
- no silent provider fallback.

If the model later appears through OpenRouter, direct StepFun and OpenRouter runs are separate runtime identities and may not share evidence fingerprints.

## 6. Output-budget rule

StepFun documents that `max_tokens` can default to effectively unbounded/model-decided behavior.

LUMI qualification must **never** rely on that default.

Every paid test must use an explicit output budget appropriate to the workload.

Reason:

- independent evidence already suggests high verbosity;
- output and reasoning tokens are both billable;
- unbounded output makes cost comparisons misleading;
- Story Generator has explicit length/scene targets;
- Narrative Blueprint has a finite schema and does not benefit from arbitrary expansion.

## 7. Qualification ladder

### P0 — provider/runtime intake

Freeze exact provider/model/profile identity and verify structured output, reasoning and usage telemetry.

### P1 — cheap screen

Run only:

- one 500-word story fixture;
- one 1000-word story fixture;
- one structured Saga Narrative Blueprint fixture;
- reasoning `low` and `high` initially.

Do not pay for a full matrix if these fail.

### P2 — Story Generator qualification

If P1 survives, compare against the current frozen GLM baseline using the canonical generator fixtures and judge contract.

Required primary economics:

- cost per technically valid story;
- cost per semantically accepted story;
- retry-adjusted latency;
- output-token efficiency.

### P3 — Narrative Architect qualification

If the structured P1 artifact survives deterministic Blueprint validation, add Step 5 as a premium candidate under #55/#60.

Use the same Character + World fixtures and downstream evaluation arms.

### P4 — context falsification

Do not benchmark the 1M context number for spectacle.

Use controlled tiers:

1. minimal required context;
2. normal LUMI context;
3. expanded distractor-heavy context.

Measure:

- contradiction rate;
- context dilution;
- missed important facts;
- latency;
- total tokens and cache economics;
- output quality.

Extreme context should be tested only if a real LUMI workflow needs it.

### P5 — verbosity/economics falsification

Explicitly measure:

- requested-vs-actual word count;
- scene-budget overshoot;
- reasoning-token share;
- redundant prose;
- repeated concepts/ngrams;
- output tokens per accepted artifact;
- cost per accepted story/blueprint.

### P6 — separate verdicts

Produce two independent results:

- `STORY_GENERATOR_GO | HOLD | REJECT`;
- `NARRATIVE_ARCHITECT_GO | HOLD | REJECT`.

A result in one role does not transfer to the other.

## 8. What not to infer

Do not infer any of the following from public claims:

- 600B total parameters means better LUMI narrative quality;
- 1M context should be filled;
- low token price means low story cost;
- strong finance results imply strong children's-story writing;
- strong coding/agentic benchmarks imply strong Saga planning;
- announced open weights imply RTX 4060 feasibility;
- provider benchmarks authorize production.

## 9. Hardware/local boundary

Step 5 Preview is not a realistic RTX 4060 8 GB local target.

Even after open weights arrive, any self-host investigation would be a separate server-class/offload/distributed feasibility track. It must not displace the current local compact-model lane.

## 10. Production boundary

No Project_LUMI runtime integration is authorized by this intake.

A positive Model Lab verdict may only produce a separate AEGIS L3 production handoff.
