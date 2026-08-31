# LUMI Training Candidate Archive

This directory preserves generated story artifacts that may later be useful for supervised fine-tuning, QLoRA/LoRA, distillation, evaluation-set construction, or prompt research.

## Important rule

An artifact being present here means **candidate evidence only**. It does not mean the story is approved for training.

Promotion into a future training dataset must remain a separate reviewed step.

## What to preserve for each generated candidate

Each candidate record should retain enough provenance to reproduce and audit the sample:

- story text
- generator model and exact model slug
- generation architecture / prompt version
- source StorySpec path
- target word count and actual word count
- scene budgets and scene-level pass/failure
- technical pass/failure and reasons
- repetition metrics
- provider/retry evidence when available
- generation latency
- token/cost evidence when available
- semantic judge model / rubric / scores when later evaluated
- human-review status when later evaluated
- source benchmark/run identifier

## Suggested lifecycle

1. `candidate` — generated and preserved, no training approval implied.
2. `technically_eligible` — deterministic gates passed.
3. `semantically_accepted` — canonical judge passed.
4. `human_approved` — optional human review passed.
5. `training_selected` — explicitly selected for a versioned training dataset.

Technical failures should normally still be preserved as negative/diagnostic evidence. They must not be silently deleted or rewritten.

## Current canonical generator baseline

For the current qualification cycle the frozen canonical generator is:

- model: `z-ai/glm-5.3-flash`
- generation architecture: `story_scene_first_v0.3`

The final qualification matrix is expected to archive all 12 GLM outputs (6 StorySpecs × 2 independent repeats), including failures, together with their provenance.
