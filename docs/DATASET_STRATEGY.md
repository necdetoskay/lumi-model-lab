# Dataset Strategy

## Principles

1. Start small and inspect everything.
2. Keep raw teacher output immutable.
3. Curate before training.
4. Version prompts and configs with the dataset.
5. Separate benchmark data from training data.
6. Never evaluate on examples derived from the same source story used for training.

## Initial dataset flow

`specification -> teacher generation -> raw stories -> extraction -> curated examples -> processed training JSONL`

### Raw

Teacher output exactly as returned by the API plus metadata such as model, prompt version, temperature, token usage, and estimated cost.

### Curated

Human-reviewed stories/examples. Rejected or repaired items should keep an audit reason rather than silently disappearing.

### Processed

Training-ready JSONL generated deterministically from curated inputs.

## Initial supervised example types

A single teacher story can yield multiple useful examples, including:

- story generation from a structured brief
- next-scene continuation
- character-consistent dialogue
- scene expansion
- age-appropriate rewriting
- conflict resolution
- ending generation
- structured story-plan to prose

For Milestone 1, keep the taxonomy intentionally small and target about 50–60 total examples from five strong stories.

## Leakage rule

Benchmark prompts and reference outputs live under `data/benchmark/` and must never be transformed into training examples.
