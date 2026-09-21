# LUMI Model Lab

Hands-on experimentation repository for learning synthetic data generation, teacher-model qualification, distillation-style dataset construction, LoRA/QLoRA, Unsloth, evaluation, and small-model fine-tuning through the LUMI story-generation use case.

## Project rule: README stays current

This README is the human entry point and current-state document for the repository. Any PR that materially changes the experiment pipeline, primary commands, dataset policy, model-selection protocol, or current milestone must update this README in the same PR.

## Current milestone

Milestone 1 validates the complete learning loop with a deliberately small but reproducible dataset before scaling data volume or training cost.

The current roadmap now separates three model-lab tracks:

1. **Teacher/data track** — GPT Luna remains the selected teacher for high-quality supervised story generation.
2. **Dense/local student track** — compact/dense candidates are baseline-tested first, then promoted to QLoRA only if both story quality and hardware feasibility justify training.
3. **Large-MoE inference track** — FreeToken is evaluated separately as an inference/benchmark runtime for supported large MoE models; it is not treated as a low-VRAM training solution.

## Experimental decision-engine track

The lab is evaluating **bounded decision engines** as a fast classification/routing layer in front of expensive reasoning models. JEV remains a reference/proprietary candidate, but the architecture is provider-agnostic and must compare realistic open/local alternatives on the same frozen LUMI evidence before any production dependency is proposed.

Shared rules include deterministic authority for hard invariants, explicit `INSUFFICIENT_EVIDENCE` / `ESCALATE` paths, per-risk confidence calibration, reproducible engine/runtime fingerprints, counterfactual/invariance tests, and full cascade economics.

- Shared canonical contract: `docs/canonical/DECISION_ENGINE_LAB.md`
- Judge-specific canonical contract: `docs/canonical/JEV_JUDGE_LAB.md`
- Core research epic: #27 — JEV Judge Lab — AEGIS Qualification & Judge Cascade Decision
- Shared harness: #30 — provider-agnostic decision-engine adapter + evidence ledger
- Execution routing: #38 — bounded model/agent/repair/retry/escalation routing
- StoryOpportunity ranking: #39
- Bounded NPC reaction selection: #40
- Local target: RTX 4060 8 GB class hardware for the first open/local lane
- Production boundary: any Project_LUMI integration requires a separate L3 AEGIS review and is **not** authorized by this repository.

### Decision-engine harness

The provider-agnostic evidence harness now has a first executable baseline:

```bash
python -m src.decision_engine_runner --config configs/decision_engine_fixture_smoke.yaml
```

The initial adapter types are:

- `fixture` — deterministic dry-run/test evidence;
- `command` — JSON-over-stdin/stdout sidecar boundary for local/open or hosted engine adapters.

The command adapter never uses `shell=True`. It receives a versioned workload/case envelope and must return the normalized `DecisionEngineOutput` JSON contract.

Evidence is stored under a SHA256 experiment fingerprint and includes request fingerprints, state size, question count, exact engine identity, per-case raw output, runtime/provider metadata, usage/cost fields, cold/warm latency, malformed-output classification and runtime-error classification. Re-running the same experiment refuses silent overwrite unless `--rerun` is explicit.

### Judge gold/reference corpus

The Judge track now has a frozen v2 case plan and blind-human protocol:

- protocol: `docs/canonical/JUDGE_GOLD_CORPUS_PROTOCOL.md`
- manifest: `data/specifications/judge_gold_corpus_v2.json`
- 100 case descriptors with source-family partition isolation
- 46 calibration / 27 development holdout / 27 final holdout
- explicit critical-protected and Turkish ↔ controlled-English comparison subsets
- validator: `python -m src.judge_gold_corpus`

Current status is intentionally **NOT_PROMOTABLE**: synthetic mutation artifacts still require materialization and the corpus still requires complete blind human labels. Automation must not invent human labels.

Current local student experiment:

- candidate: `ornith-ai/Ornith-1.5-9B`
- hardware: RTX 4060 Laptop GPU, 8 GB VRAM
- native HF/Unsloth 4-bit load: does not fit with the current pure-GPU load path; this is recorded as a hardware/load-path result, not a model rejection
- working baseline runtime: llama.cpp GGUF through an OpenAI-compatible local endpoint
- one-story smoke: PASS, 1,924 words, 101.7 s
- frozen five-story baseline: 5/5 runtime completions, 4/5 technical length passes, 1,611.8 average words, 467.2 s total runtime
- current failing case: `05_emotional_calm` produced 915 words and failed the target-length gate
- next gate: common LUMI judge rubric and failure/repetition inspection before deciding whether Ornith is a training candidate

Epic #12 (`Local Student Training & Large-MoE Inference Roadmap`) is the SSOT for this sequence. PR #11 contains the current Ornith local-baseline work.

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
.venv-ornith/
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

A separate training environment is used for the CUDA / Unsloth stack, but it still needs the repository's lightweight application dependencies (`python-dotenv`, `pyyaml`, `requests`, `rich`, `pydantic`). After creating or activating the environment, also run:

```bash
python -m pip install -r requirements.txt
```

This does not install or replace the CUDA / Unsloth training stack because those packages are intentionally not pinned in `requirements.txt`.

## Ornith local endpoint baseline

The preferred baseline path for Ornith on the RTX 4060 8 GB machine is GGUF + llama.cpp rather than the current native HF/Unsloth pure-GPU load path.

Start a local OpenAI-compatible llama.cpp server with the Ornith Q4_K_M GGUF, then run:

```bash
python -m src.local_endpoint_baseline --config configs/local_baseline_ornith15_9b.yaml --limit 1
```

After a stable one-story smoke, expand to the frozen five-story benchmark:

```bash
python -m src.local_endpoint_baseline --config configs/local_baseline_ornith15_9b.yaml --limit 5
```

Local endpoint artifacts are written under:

```text
runs/model_baseline/pre_finetune_ornith15_9b/
```

They can be judged with the same six-criterion LUMI rubric through:

```bash
python -m src.judge_local_endpoint --input runs/model_baseline/pre_finetune_ornith15_9b/story_01.json
```

This judge adapter uses the configured `JUDGE_MODEL` and `OPENROUTER_API_KEY`, so it may incur provider cost.

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

Provider/request failures are not model-quality failures. If benchmark generation cannot complete because the provider rejects request parameters, the run is recorded as `generation_error` instead of `rejected_technical`. Model-specific OpenRouter compatibility options belong in `src.generate.build_model_options`; for example, `google/gemini-3.7-flash` keeps mandatory reasoning enabled at low effort while excluding reasoning text from the visible story response.

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
  judgment/
  extraction/
  curated/
  dataset/
  manifest.json
```
