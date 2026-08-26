# Ornith 1.5 9B Student Baseline Experiment

## Goal

Evaluate `ornith-ai/Ornith-1.5-9B` as a local LUMI student-model candidate before spending time on fine-tuning.

Teacher selection is unchanged: GPT Luna remains the teacher. This experiment only evaluates Ornith as a possible student/local inference model.

## Current hardware

Active test machine:

- NVIDIA GeForce RTX 4060 Laptop GPU
- 8 GB VRAM
- Python 3.11
- PyTorch 2.10.0 + CUDA 12.6
- Unsloth 2026.8.21

The local training preflight reports `candidate_ready`.

## Frozen benchmark

Reuse `configs/teacher_benchmark.yaml` so Ornith is evaluated on the same five story specifications already used by the lab:

1. exploration / mystery
2. friendship / social
3. puzzle / problem solving
4. fantasy / adventure
5. emotional / calm

The first run is intentionally only one story. Expand to all five only after the local runtime is stable.

## Experiment A — native HF/Unsloth 4-bit load

A direct CUDA baseline was attempted with:

- runner: `src/local_baseline.py`
- config: `configs/local_baseline_ornith15_9b_unsloth.yaml`
- model: `ornith-ai/Ornith-1.5-9B`
- `load_in_4bit: true`
- RTX 4060 Laptop GPU, 8 GB VRAM

### Result: blocked by model-load VRAM gate

The optional fast linear-attention path was unavailable and fell back to the Torch implementation. That warning was not the failure.

The actual failure happened during `from_pretrained` before story generation. Transformers/bitsandbytes attempted to dispatch some modules to CPU/disk because the quantized HF model did not fit wholly in the available GPU memory, then rejected that device map for the current 4-bit load path.

Observed exception class/message:

```text
ValueError: Some modules are dispatched on the CPU or the disk. Make sure you have enough GPU RAM to fit the quantized model.
```

### Decision

Do not add ad-hoc fp32 CPU offload to the training-oriented Unsloth baseline merely to force this checkpoint to load. That would make the baseline materially different from the intended later QLoRA path and would hide the real 8 GB feasibility constraint.

Classify this result as:

```text
native HF/Unsloth 4-bit inference on RTX 4060 8 GB: NOT FEASIBLE with the current load path
```

This does **not** reject Ornith as a model and does **not** yet prove that all possible Ornith QLoRA strategies fail. A separate training-memory smoke test may still be designed after baseline quality is known.

## Experiment B — GGUF endpoint baseline (next)

The baseline now falls back to the original, runtime-neutral path:

- model format: official `ornith-ai/Ornith-1.5-9B-GGUF`
- starting quantization: `Q4_K_M` (~5.63 GB model file)
- runtime: llama.cpp
- API: OpenAI-compatible local endpoint
- config: `configs/local_baseline_ornith15_9b.yaml`
- runner: `python -m src.local_endpoint_baseline`
- default endpoint: `http://127.0.0.1:8000/v1/chat/completions`

On Windows, the official Ornith GGUF model card documents llama.cpp installation through WinGet and serving the Q4_K_M quantization.

Example runtime shape:

```text
winget install llama.cpp
llama serve -hf ornith-ai/Ornith-1.5-9B-GGUF:Q4_K_M --port 8000 -c 6144
```

Then run exactly one frozen LUMI story:

```text
python -m src.local_endpoint_baseline --config configs/local_baseline_ornith15_9b.yaml --limit 1
```

Expected outputs:

```text
runs/model_baseline/pre_finetune_ornith15_9b/story_01.json
runs/model_baseline/pre_finetune_ornith15_9b/summary.json
```

## Gate to expand from 1 to 5 stories

Proceed to all five benchmark stories only if:

- the endpoint is stable;
- the story finishes without transport/runtime failure;
- generation time is acceptable for experimentation;
- output is not obviously repetitive or corrupted;
- the technical length result is interpretable.

Then run the frozen five-story baseline and pass the results through the existing judge/evaluation workflow.

## Decision gate before training

Ornith becomes a training candidate only if its held baseline is competitive enough in LUMI-specific story quality to justify the hardware effort. Coding/reasoning benchmark strength alone is not a promotion criterion.

If promoted, the next experiment is a separate ultra-small QLoRA memory smoke test on the RTX 4060. It must start with a very small dataset, batch size 1, short sequence length, low LoRA rank, gradient checkpointing, and explicit OOM/VRAM logging.

The direct 4-bit inference load failure above must be treated as evidence that the 8 GB boundary is real; training feasibility must be measured rather than assumed.

## Success criteria

For the baseline phase:

- reproducible local launch;
- one-story smoke run succeeds;
- five-story benchmark can be generated without model/runtime corruption;
- results are judgeable using the existing rubric;
- baseline artifacts are preserved before any fine-tune.

For a later fine-tune phase, compare at minimum:

- Ornith base;
- Ornith + GPT Luna supervised QLoRA;
- GPT Luna teacher reference.

Evaluation must use held-out prompts that were not part of the supervised training set.
