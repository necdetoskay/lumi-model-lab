# Production Story Generator Baseline

Status: **FROZEN**
Date: 2026-08-31
Scope: LUMI Model Lab story-generation experiments

## Canonical production generator

- Model: `z-ai/glm-5.3-flash`
- Generation architecture: `story_scene_first_v0.3`
- Provider path: OpenRouter
- Selection priority: quality first, reliability second, cost as a tie-breaker

## Decision

`z-ai/glm-5.3-flash` is the canonical production-generator candidate for the current LUMI Model Lab qualification cycle.

The model-selection search is closed for this cycle. Other tested models remain preserved as benchmark evidence and must not silently replace GLM in the production path.

## Evidence summary

Scene-first calibration/resilience evidence covered 500, 700, and 1000 target-word stories across age/constraint profiles.

GLM-5.3 Flash results:

| Target | Actual | Technical pass | Scene pass | Generation cost (TRY) | Sonnet 5 judge |
|---:|---:|:---:|:---:|---:|---:|
| 500 | 503 | yes | 6/6 | ~0.13 | 4.00 |
| 700 | 684 | yes | 6/6 | ~0.12 | 4.167 |
| 1000 | 955 | yes | 6/6 | ~0.18 | 4.333 |

Across these three qualification probes GLM produced 3/3 technical passes and 18/18 scene passes, with no provider retry requirement and zero measured 8-gram repetition.

## Alternatives retained as evidence

- `openai/gpt-5.6-luna`: faster, but weaker length/scene-contract reliability in the same scene-first protocol.
- `deepseek/deepseek-v4-pro-0813`: strong semantic-quality signal in the 500-word probe, but insufficient length/reliability at 700/1000 and unstable provider routing.
- `deepseek/deepseek-v4-flash-0731`: low cost but failed technical qualification at 500/700/1000 under scene-first v0.3.
- `anthropic/claude-haiku-4.5`: insufficient quality/reliability for generator fallback in this cycle.
- `anthropic/claude-sonnet-5`: premium-quality candidate, but failed 500/700 total-length qualification and missed multiple scene budgets; cost was orders of magnitude above GLM in the multi-call scene-first path.

These alternatives are research/emergency evidence only. They are not production drop-in fallbacks.

## Judge baseline

Primary semantic judge remains:

- `anthropic/claude-sonnet-5`
- rubric/prompt: `story_judge_v0.2`

Technical gates remain separate from semantic scoring. A semantically strong story does not become promotion-eligible when required technical gates fail.

## Remaining qualification work

Model selection is complete. The remaining generator benchmark should therefore be reduced from the obsolete 3-model / 36-attempt search matrix to a **GLM-only final qualification matrix**:

1. Run all 6 canonical generator-v2 scenarios with GLM-5.3 Flash.
2. Run 2 independent repeats per scenario (12 total final GLM generations).
3. Preserve all failures; do not silently regenerate/replace failed evidence.
4. Record technical validity, word adherence, all-scene pass, repetition, latency, provider/retry evidence, token usage, USD/TRY generation cost.
5. Run Sonnet 5 / `story_judge_v0.2` only on technically eligible outputs.
6. Produce final per-scenario and aggregate reliability/quality/cost report.
7. Use a small adversarial secondary-judge/human subset only after the canonical GLM matrix is complete; do not rerun already-established model-selection experiments.

## Change control

Changing the canonical production generator after this freeze requires new comparative evidence showing a material improvement in quality or reliability, not merely a lower price or isolated high-scoring story.
