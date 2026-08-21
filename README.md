# LUMI Model Lab

Hands-on experimentation repository for learning synthetic data generation, teacher-model qualification, distillation-style dataset construction, LoRA/QLoRA, Unsloth, evaluation, and small-model fine-tuning through the LUMI story-generation use case.

## Project rule: README stays current

This README is the human entry point and current-state document for the repository. Any PR that materially changes the experiment pipeline, primary commands, dataset policy, model-selection protocol, or current milestone must update this README in the same PR.

## Current milestone

Milestone 1 validates the complete learning loop with a deliberately small but reproducible dataset before scaling data volume or training cost.

Completed foundations:

- OpenRouter teacher-story generation with prompt/model metadata, token usage, provider metadata, and cost
- frozen five-story teacher benchmark
- LLM judge with six scored criteria and acceptance gates
- independent five-story source dataset for training-data creation
- supervised extraction into 11 examples per accepted source story (55 examples for five stories)
- deterministic curation and manual-review gate
- frozen UTF-8 JSONL training dataset with SHA256 manifest
- local CUDA / Unsloth preflight tooling
- Qwen3.5-0.8B 4-bit model-load probe on a 4 GB RTX 3050 Ti Laptop GPU
- successful QLoRA smoke training
- frozen five-story pre-finetune local baseline
- one-command teacher-model qualification pipeline and model leaderboard
- external/manual source-story ingest path with independent judge and training-example extraction
- raw, curated, processed dataset artifacts and compact experiment records tracked in Git for cross-machine reproducibility

Next major experiment: full 55-example QLoRA training, post-finetune frozen benchmark, and before/after comparison.

The original 4B target remains `Qwen/Qwen3.5-4B` as the starting checkpoint for the stronger-GPU experiment. The 0.8B checkpoint is used locally to learn and validate the complete training mechanics on constrained hardware.

## Repository data policy

Small textual data and reproducibility artifacts are versioned so the same experiment can be continued on another machine.

Tracked:

```text
data/raw/
data/curated/
data/processed/
data/specifications/
runs/                 # manifests, reports, qualification outputs, benchmark text/JSON
```

Not tracked:

```text
.env
.venv/
.venv-train/
models/
adapters/
.cache/
**/checkpoint-*/
```

Large model weights, virtual environments, Hugging Face caches, LoRA adapters, and trainer checkpoints remain local.

## API / data-generation setup

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
JUDGE_MODEL=...
```

`USD_TRY_RATE` is optional. When supplied, qualification summaries also show the USD total converted to TRY using that explicit rate.

### Training environment note

The separate `.venv-train` environment is used for the CUDA / Unsloth stack, but it still needs the repository's lightweight application dependencies (`python-dotenv`, `pyyaml`, `requests`, `rich`, `pydantic`). After creating or activating `.venv-train`, also run:

```bash
python -m pip install -r requirements.txt
```

This does not install or replace the CUDA / Unsloth training stack because those packages are intentionally not pinned in `requirements.txt`.

## One-command model qualification

The preferred way to test a newly discovered OpenRouter model is:

```bash
python -m src.model_qualify --model "provider/model-name"
```

Default behavior is quality-gated and sequential:

```text
1. duplicate/fingerprint registry check
2. frozen 5-story technical benchmark
   └─ fail -> stop before judge cost
3. judge benchmark
   └─ fail -> stop before dataset-generation cost
4. independent 5-story training-source generation + judge
   └─ fail -> stop
5. supervised extraction (target: 55 examples)
6. deterministic curation
   └─ review/reject -> stop as NEEDS_MANUAL_REVIEW
7. frozen training JSONL + SHA256 manifest
8. registry + token/cost ledger + final report
```

Benchmark stories are never used as training examples. Training source stories come from a separate frozen specification set.

### Fast screening only

```bash
python -m src.model_qualify --model "provider/model-name" --screen
```

This stops after benchmark + judge and avoids source-story/extraction cost.

### Duplicate protection

A qualification fingerprint includes the model id, current judge model id, prompts, protocol configs, frozen benchmark specifications, and frozen training-source specifications. The same model under the same experiment fingerprint is not run again accidentally.

```bash
python -m src.model_qualify --model "provider/model-name"
# -> ALREADY TESTED when the exact experiment already exists
```

Intentional repeat:

```bash
python -m src.model_qualify --model "provider/model-name" --rerun
```

A prompt, judge, gate, or frozen-spec change produces a different fingerprint and is treated as a new experiment.

### Import pre-registry benchmark history

```bash
python -m src.import_legacy_benchmark
```

Legacy records are marked `legacy_screened`. Historical generation manifests did not store teacher input-token counts, so their total-token value is explicitly marked as a lower bound; stored USD costs and available judge usage are preserved.

### Registry and status

```bash
python -m src.model_qualify --list
python -m src.model_qualify --model "provider/model-name" --status
```

Registry: `runs/model_registry/registry.json`.

## External/manual source story ingest

A story generated outside the normal OpenRouter teacher pipeline can be admitted as a training source only through the same independent quality controls. The canonical generation prompt is versioned at:

```text
prompts/generated_story_source.md
```

Give that prompt to any LLM, save its YAML output, and run:

```bash
python -m src.ingest_story --input path/to/story.yaml
```

The ingest pipeline is intentionally gated:

```text
external YAML story
    ↓
1. schema + technical validation
    └─ fail -> REJECTED_TECHNICAL; no judge/extraction spend
    ↓
2. independent JUDGE_MODEL evaluation
    └─ fail -> REJECTED_JUDGE; no extraction spend
    ↓
3. fixed extractor protocol
    └─ 11 supervised examples expected
    ↓
4. deterministic curation
    └─ review/reject -> NEEDS_MANUAL_REVIEW
    ↓
5. isolated training-ready JSONL + SHA256 manifest
```

The external model's own `training_eligible` or `suitability` values are stored as provenance only. They never override the local technical gate or independent judge decision.

Each successful story produces the same 11-example shape:

```text
1  full_story_from_brief
2  continuation
2  character_dialogue
2  scene_expansion
1  conflict_resolution
1  ending_generation
2  plan_to_prose
-----------------------
11 examples/story
```

The output is isolated from the frozen Milestone-1 55-example dataset:

```text
runs/manual_ingest/<story-id>__<input-sha>/
  input_snapshot.yaml
  source/
  judge/
  extraction/
  extracted/
  curated/
  curation/
  dataset/
    train.jsonl
    manifest.json
  final_report.json
```

Re-running the exact same YAML is blocked by default. Use `--force` only for an intentional repeat.

## Model leaderboard

```bash
python -m src.leaderboard
```

Ranking is quality-first: judge score first, technical reliability second, and API cost only as a tie-breaker when quality is comparable. Stored output: `runs/model_registry/leaderboard.json`.

Each new qualification record keeps, where returned by the provider, prompt/input tokens, completion/output tokens, total tokens, generation/judge/extraction cost, total USD cost, optional TRY conversion, and stage-by-stage cost breakdown.

## Qualification gates

The protocol is versioned in `configs/qualification.yaml`.

Current screening defaults:

```yaml
min_technical_pass_rate: 0.80
min_judge_accept_rate: 0.80
min_average_judge_score: 4.00
max_critical_failures: 0
```

Full dataset gate:

```yaml
required_accepted_source_stories: 5
required_ready_examples: 55
require_zero_review: true
require_zero_reject: true
```

Do not loosen gates merely to make a model pass. A changed gate is a changed protocol and therefore a different fingerprint.

## Existing lower-level commands

Individual stages remain available for debugging and focused experiments.

```bash
python -m src.generate --count 1 --dry-run
python -m src.teacher_benchmark all
python -m src.source_dataset all
python -m src.extract_examples
python -m src.curate_examples
python -m src.prepare_training
python -m src.local_preflight
python -m src.model_probe
python -m src.smoke_train
python -m src.local_baseline
```

## Milestone-1 dataset design

The frozen small dataset contains 5 approved source stories × 11 examples = 55 supervised examples. It validates workflow and learning behavior; it is not treated as sufficient evidence of production-quality fine-tuning.

## Evaluation principle

Before and after fine-tuning, the same frozen benchmark, inference prompt, judge protocol, and technical gates must be used. Benchmark-derived outputs must never enter the training dataset.

Record at minimum technical pass rate, completion/EOS behavior, word-count compliance, judge average and criterion scores, runtime, peak VRAM, dataset SHA256, and model/adapter identity.

## Tests

```bash
python -m unittest discover -s tests -v
```

Run tests before merging pipeline changes.
