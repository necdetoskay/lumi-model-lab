# Ornith 1.5 9B Student Baseline Experiment

## Goal

Evaluate `ornith-ai/Ornith-1.5-9B` as a local LUMI student-model candidate before spending time on fine-tuning.

Teacher selection is unchanged: GPT Luna remains the teacher. This experiment only evaluates Ornith as a possible student/local inference model.

## Why inference first

The available machine has an RTX 3050 Ti with 4 GB VRAM. Ornith 1.5 9B Q4_K_M is about 5.6 GB before KV-cache/runtime overhead, so a pure-GPU load is not the expected path. The first baseline therefore uses a GGUF runtime with CPU/RAM and optional partial GPU offload, exposed through an OpenAI-compatible local endpoint.

Do not begin Ornith 9B QLoRA on the 4 GB GPU until the baseline is promising and a dedicated training-memory smoke test has been designed. Current 8B/9B Unsloth guidance makes 8 GB-class VRAM the practical starting point for QLoRA-style training.

## Frozen benchmark

Reuse `configs/teacher_benchmark.yaml` so Ornith is evaluated on the same five story specifications already used by the lab:

1. exploration / mystery
2. friendship / social
3. puzzle / problem solving
4. fantasy / adventure
5. emotional / calm

The first run is intentionally only one story. Expand to all five only after the local runtime is stable.

## Runtime contract

The repository runner talks to an OpenAI-compatible endpoint:

- config: `configs/local_baseline_ornith15_9b.yaml`
- runner: `python -m src.local_endpoint_baseline`
- default endpoint: `http://127.0.0.1:8000/v1/chat/completions`

A llama.cpp server is the preferred first runtime because it can use GGUF and split work between RAM and GPU.

Example server shape:

```text
llama-server -hf hf.co/ornith-ai/Ornith-1.5-9B-GGUF --port 8000 -c 6144 -ngl 0
```

Start with `-ngl 0` to prove CPU/RAM inference. Then increase GPU layers conservatively (for example 5, 10, 15) while watching VRAM. Do not assume the largest layer count is best; the 4 GB GPU must retain enough headroom for runtime buffers and KV cache.

## First command

```text
python -m src.local_endpoint_baseline --config configs/local_baseline_ornith15_9b.yaml --limit 1
```

Expected outputs:

```text
runs/model_baseline/pre_finetune_ornith15_9b/story_01.json
runs/model_baseline/pre_finetune_ornith15_9b/summary.json
```

The run records word count, runtime, token usage when supplied by the endpoint, and the existing LUMI technical length gate.

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

If promoted, the next experiment is a separate ultra-small training-memory smoke test. It must start with 2-3 short examples, batch size 1, very short sequence length, low LoRA rank, gradient checkpointing, and explicit OOM/VRAM logging. Failure on 4 GB does not reject Ornith as a model; it only rejects the 3050 Ti as the training target. The same student can then be revisited on the RTX 4060 8 GB system.

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
