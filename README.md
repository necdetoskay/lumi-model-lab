# LUMI Model Lab

Hands-on experimentation repository for learning synthetic data generation, distillation, LoRA/QLoRA, Unsloth, evaluation, and small-model fine-tuning through the LUMI story-generation use case.

## Current milestone

Milestone 1 validates the full learning pipeline with a deliberately small dataset before scaling cost or training time:

1. generate teacher stories through OpenRouter
2. record reproducible prompts, metadata, token usage, and cost
3. judge and curate samples
4. compile supervised training examples
5. run a frozen base-model benchmark
6. train a small QLoRA adapter
7. compare base vs fine-tuned results on the same benchmark

The current phase is GPU-independent. Teacher generation and dataset preparation can be performed on any development machine. Local QLoRA compatibility will be tested separately before training.

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
```

Set at least:

```env
OPENROUTER_API_KEY=...
TEACHER_MODEL=...
```

`USD_TRY_RATE` is optional. If supplied, the exact rate used is stored beside the generated sample so historical TRY estimates remain reproducible.

## First dry run

This validates configuration, schema parsing, and the rendered story brief without spending API credit:

```bash
python -m src.generate --count 1 --dry-run
```

## Generate the first teacher story

```bash
python -m src.generate --count 1
```

The generated record is written to:

```text
data/raw/story_0001.json
```

Raw generated datasets are intentionally ignored by Git. Specifications, prompts, configs, and code remain versioned.

## Reproducible story brief

The first test brief lives at:

```text
data/specifications/example_story.yaml
```

Edit or add specification files instead of hard-coding experiment prompts in Python. This lets the same brief be tested against different teacher models and prompt versions.

> Status: teacher-generation pipeline implemented on the initial feature branch. Judge/curation is the next stage.
