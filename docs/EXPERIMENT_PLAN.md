# Experiment Plan

## Goal

Use LUMI story generation as a practical lab for learning synthetic data generation, distillation-style teacher/student workflows, QLoRA, Unsloth, local inference, MoE runtime behavior, and evaluation.

Cost reduction is secondary. The primary outcome is a repeatable learning workflow with measurable experiments and clear promotion gates.

## Current decisions

- Teacher model: GPT Luna.
- Teacher selection is frozen unless later evidence justifies reopening it.
- Student training and local inference are separate tracks.
- Dense/small models are the primary fine-tuning candidates.
- Large MoE models are inference/benchmark candidates first; they are not assumed to be trainable on the current local GPU.
- Model quality for LUMI stories is more important than headline benchmark scores or raw parameter count.

## Hardware and budget

- Current local GPU: RTX 3050 Ti Laptop, 4 GB VRAM.
- Target local GPU for more practical QLoRA work: RTX 4060 Laptop, 8 GB VRAM.
- Primary fine-tuning method: 4-bit QLoRA.
- Training framework target: Unsloth.
- Local inference runtimes: llama.cpp-compatible endpoint for dense/GGUF baselines; FreeToken experimental track for supported large MoE models.
- System RAM becomes a first-class constraint for FreeToken/MoE experiments.
- Monthly experimental budget: approximately 2,000 TRY.
- API spend is acceptable when it creates useful training or evaluation data.

## Architecture of the roadmap

The lab now has three connected but separate tracks.

### Track A — Teacher and dataset

GPT Luna produces the high-quality reference data used to teach and evaluate student models.

Flow:

`story spec -> GPT Luna -> quality gate/judge -> curated examples -> frozen training dataset`

The teacher dataset must remain model-independent so the same examples can be reused across Ornith, Qwen, Gemma, or later student candidates.

### Track B — Dense student training

This track answers: can a smaller locally runnable model learn LUMI story behavior from Luna-generated examples?

Initial candidates include compact Qwen/Gemma-class models and Ornith 1.5 9B if its baseline story quality is strong enough.

Flow:

`base model -> frozen benchmark -> QLoRA -> same frozen benchmark -> base vs adapter comparison`

RTX 3050 Ti is used for feasibility and constrained experiments. RTX 4060 8 GB remains the preferred target for practical 9B-class QLoRA.

### Track C — Large MoE local inference

This track answers a different question: can much larger MoE models be evaluated locally despite limited VRAM by using system RAM and hardware-aware expert scheduling?

FreeToken is the first experimental runtime for this track.

Flow:

`LUMI benchmark -> OpenAI-compatible local endpoint -> FreeToken -> supported MoE model -> judge/metrics`

This track is for inference and benchmarking first, not local fine-tuning.

## Milestone 0 — Repository bootstrap

Status: complete enough for active experimentation.

- Reproducible config files
- Prompt versioning
- Raw / curated / processed data separation
- Baseline and fine-tuned evaluation paths
- Experiment outputs excluded from Git by default
- Local preflight and hardware diagnostics
- OpenAI-compatible local endpoint benchmark path

## Milestone 1 — Freeze the teacher/data contract

1. Record GPT Luna as the current teacher decision.
2. Freeze the benchmark story specifications.
3. Produce the first small set of high-quality Luna stories.
4. Judge and manually inspect the outputs.
5. Convert accepted stories into supervised examples.
6. Freeze dataset v1 before comparing student models.

Exit gate:

- teacher outputs pass the LUMI quality bar,
- dataset schema is stable,
- examples can be traced back to source story/spec,
- the same dataset can be consumed by multiple student candidates.

## Milestone 2 — Ornith 1.5 9B local baseline

Goal: determine whether Ornith is worth treating as a serious LUMI student candidate before spending time on training.

1. Run one-story smoke inference first.
2. Use Q4/GGUF with CPU/system RAM and optional partial GPU offload on the RTX 3050 Ti.
3. Record runtime, completion behavior, word count, repetition, and technical failures.
4. If stable, expand to the frozen five-story benchmark.
5. Run the same LUMI judge used for other candidates.
6. Compare against existing compact student/base baselines.

Promotion gate to training:

- stable local generation,
- no systematic truncation/repetition failure,
- story quality competitive enough to justify QLoRA,
- model/runtime behavior is reproducible.

If the gate fails, Ornith remains an inference reference rather than a training target.

## Milestone 3 — FreeToken feasibility experiment

Goal: determine whether the current machine can use supported 30–35B-class MoE models as practical local inference/benchmark candidates.

1. Record exact system RAM, CPU, PCIe/GPU details.
2. Install FreeToken on a supported environment without replacing the existing llama.cpp path.
3. Start with a supported A3B-class MoE model rather than the largest available model.
4. Verify `/v1/models` and `/v1/chat/completions` compatibility.
5. Point the existing `local_endpoint_baseline` runner at FreeToken.
6. Run a one-story smoke benchmark.
7. Record:
   - model and quantization,
   - system RAM use,
   - VRAM use,
   - prompt/prefill behavior,
   - generation tokens/sec,
   - total runtime,
   - failures or stalls.
8. If stable, run the same five-story frozen LUMI benchmark.
9. Compare quality and throughput with the dense/local candidates.

Promotion gate:

- machine has sufficient system RAM,
- endpoint is stable for LUMI-length prompts,
- no unacceptable hangs or context failures,
- throughput is useful enough for repeated evaluation,
- story quality provides a meaningful advantage over smaller local models.

FreeToken does not replace llama.cpp by default. It is promoted only for workloads where its dynamic MoE expert scheduling gives a measurable benefit.

## Milestone 4 — First student QLoRA smoke test

Only start after a student candidate passes its baseline gate.

1. Use a tiny subset of the frozen Luna dataset.
2. Start with the smallest viable sequence length and batch size.
3. Run only a few training steps.
4. Record peak VRAM, loss, runtime, OOM behavior, and checkpoint integrity.
5. Confirm the adapter can be reloaded and used for inference.

For RTX 3050 Ti 4 GB, 9B-class QLoRA is experimental and may be rejected by the hardware gate. Do not treat failure here as a project failure.

## Milestone 5 — Small end-to-end student experiment

1. Run the chosen base model against the frozen benchmark.
2. Train on dataset v1 with 4-bit QLoRA.
3. Run the fine-tuned model against the identical held-out benchmark.
4. Compare base vs adapter using deterministic checks plus an LLM judge.
5. Record cost, runtime, VRAM use, failures, and lessons learned.
6. Check for memorization by keeping evaluation prompts outside the training set.

Success is improvement on held-out LUMI story quality, not merely lower training loss.

## Milestone 6 — Student/runtime comparison matrix

After the first end-to-end run, compare one variable at a time.

Candidate matrix may include:

- compact dense base model
- Ornith 1.5 9B base
- Ornith 1.5 9B + Luna QLoRA, if hardware allows
- supported 30–35B A3B-class MoE via FreeToken
- later Qwen/Gemma candidates

Every candidate receives the same frozen benchmark and judge rubric.

Record both quality and systems metrics:

- instruction following
- coherence
- character consistency
- age appropriateness
- creativity
- style quality
- repetition/truncation
- tokens/sec
- time-to-first-token when available
- peak VRAM
- system RAM
- total runtime
- operational stability

## Milestone 7 — Scale only after evidence

Do not generate hundreds or thousands of examples until the small experiment proves that:

- the dataset format is useful,
- training is stable on available hardware or a clearly chosen larger GPU,
- the benchmark detects meaningful changes,
- GPT Luna teacher and judge costs are understood,
- failures can be traced back to data, training, runtime, or evaluation,
- the selected student is worth scaling.

Then compare one variable at a time, for example:

- 10–12 vs 50 vs 200 supervised examples
- raw teacher stories vs structured sub-example extraction
- different LoRA ranks
- different base model sizes
- dense student vs large MoE inference reference
- teacher model quality vs dataset size
- direct fine-tuning vs explicit teacher rationale removal

## Immediate execution order

1. Merge/validate the Ornith local baseline experiment.
2. Run Ornith one-story baseline on the RTX 3050 Ti machine.
3. Expand to five stories only if the smoke run is stable.
4. Freeze the first GPT Luna supervised dataset v1.
5. In parallel after hardware inventory, run a FreeToken feasibility smoke test with one supported A3B-class MoE model.
6. Compare Ornith/dense baseline quality with the FreeToken MoE inference reference.
7. Choose the first model that deserves QLoRA.
8. Run the smallest possible QLoRA smoke test.
9. Only then scale data, context length, or model size.

## Decision rule

Do not choose a model because it is newer, larger, cheaper, or faster in generic benchmarks.

Choose it only if it improves the LUMI objective under our actual constraints: high-quality Turkish children's stories, stable local operation, measurable learning from GPT Luna data, and a workflow we can understand and reproduce.
