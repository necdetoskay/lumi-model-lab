# Evaluation Strategy

## Core rule

Freeze a small benchmark before fine-tuning and run both the untouched base model and every trained adapter against exactly the same prompts.

For teacher-model selection, optimize for output quality first. Cost is a secondary tie-breaker only when two candidates achieve comparable quality and reliability. Do not choose a cheaper teacher if it produces measurably worse training data.

For production-role qualification, nominal token price is never sufficient by itself. Compare total lifecycle economics per successfully qualified task, including reasoning, retries, validation, repair and escalation where applicable.

Materially compressed, quantized, pruned, distilled or otherwise capability-changing deployment variants must be evaluated as distinct candidates even when they share the same base-model lineage.

## Evaluation layers

### 1. Deterministic checks

- output exists
- language is correct
- approximate length is within target range
- required characters/entities appear
- forbidden formatting or metadata is absent
- declared structured output validates against the expected schema
- canonical/state invariants pass where the role has exact constraints

### 2. Rubric-based LLM judge

Score each output on a fixed scale for:

- instruction following
- coherence
- character consistency
- age appropriateness
- creativity
- style quality

Role-specific tracks may add grounding, contradiction detection, continuity, abstention and evidence-use metrics.

The judge prompt and model must be versioned so experiment scores remain comparable.

For teacher-model comparisons, a model must first pass deterministic checks. Among technically valid candidates, compare rubric scores and human review before considering cost. Cost should decide only between candidates whose quality is effectively comparable.

### 3. Human review

For Milestone 1, manually compare a small blind sample of base vs QLoRA outputs. Human review is the tie-breaker when automated scoring disagrees with obvious story quality.

The same principle applies to teacher selection: if two models receive similar judge scores, inspect a small blind sample before selecting the cheaper option.

### 4. Task-level economics

For production-role experiments, record the full governed call chain rather than only the primary generation call.

Measure **Cost Per Successful Task (CPST)** when a task has a qualification outcome:

`CPST = total governed lifecycle inference cost / successfully qualified tasks`

For end-to-end story experiments, measure **Cost Per Qualified Story (CPQS)** including architect, scene generation, continuity review, validators/judges, repairs, retries and escalations.

Nominal input/output token rates remain useful metadata but are not the final routing metric.

### 5. Long-context and reasoning-budget evaluation

Advertised context size is not treated as proof of usable context. Long-context candidates should be tested at explicit context bands and evaluated for quality degradation, time-to-first-token, total latency, token usage and cost.

Reasoning-capable candidates should be tested under bounded reasoning profiles where supported. Record whether easy tasks remain economical, hard tasks escalate correctly, budget exhaustion is controlled and validators trigger escalation only when needed.

The detailed protocol is defined in `experiments/COMPRESSION_REASONING_ECONOMICS_QUALIFICATION.md`.

## Experiment record

Each run should eventually record:

- candidate deployment/artifact id
- base model/lineage when known
- adapter/config version
- compression/quantization/distillation method when applicable
- dataset version
- prompt version
- benchmark version
- role under test
- context-band id where applicable
- reasoning-budget profile id where applicable
- seed
- runtime/hardware
- peak VRAM/RAM
- p50/p95 latency for production-role tests
- API input/output/reasoning token usage when available
- estimated/actual cost breakdown
- retry/repair/escalation count
- per-metric scores
- deterministic qualification outcome
- judge/human-review outcome
- CPST/CPQS contribution where applicable
- notable failures

## Success criterion for Milestone 1

Success does not mean the QLoRA model must beat the base model dramatically. The milestone succeeds when the same experiment can be reproduced and we can explain whether the adapter improved, degraded, or left behavior unchanged.

## Success criterion for production-role qualification

A candidate wins only when it satisfies the role's quality and safety/grounding gates and then improves one or more deployment objectives such as CPST/CPQS, latency, VRAM or availability without causing an unacceptable capability regression.
