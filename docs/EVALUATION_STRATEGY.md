# Evaluation Strategy

## Core rule

Freeze a small benchmark before fine-tuning and run both the untouched base model and every trained adapter against exactly the same prompts.

## Evaluation layers

### 1. Deterministic checks

- output exists
- language is correct
- approximate length is within target range
- required characters/entities appear
- forbidden formatting or metadata is absent

### 2. Rubric-based LLM judge

Score each output on a fixed scale for:

- instruction following
- coherence
- character consistency
- age appropriateness
- creativity
- style quality

The judge prompt and model must be versioned so experiment scores remain comparable.

### 3. Human review

For Milestone 1, manually compare a small blind sample of base vs QLoRA outputs. Human review is the tie-breaker when automated scoring disagrees with obvious story quality.

## Experiment record

Each run should eventually record:

- base model
- adapter/config version
- dataset version
- prompt version
- benchmark version
- seed
- runtime
- peak VRAM
- API token usage and estimated cost
- per-metric scores
- notable failures

## Success criterion for Milestone 1

Success does not mean the QLoRA model must beat the base model dramatically. The milestone succeeds when the same experiment can be reproduced and we can explain whether the adapter improved, degraded, or left behavior unchanged.
