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

- Current active local GPU: RTX 4060 Laptop, 8 GB VRAM.
- Secondary constrained GPU reference: RTX 3050 Ti Laptop, 4 GB VRAM.
- Primary fine-tuning method: 4-bit QLoRA.
- Training framework target: Unsloth.
- Local inference runtimes: llama.cpp-compatible endpoint for dense/GGUF baselines; FreeToken experimental track for supported large MoE models.
- System RAM becomes a first-class constraint for FreeToken/MoE experiments.
- Monthly experimental budget: approximately 2,000 TRY.
- API spend is acceptable when it creates useful training or evaluation data.

## Architecture of the roadmap

The lab has three connected but separate tracks.

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

RTX 4060 8 GB is the current active target for practical QLoRA experiments. The RTX 3050 Ti remains useful only for constrained feasibility references.

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

Status: runtime and technical benchmark complete; quality gate in progress.

Observed on RTX 4060 Laptop 8 GB:

- native HF/Unsloth 4-bit pure-GPU load did not fit with the current load path;
- llama.cpp + `Ornith-1.5-9B-GGUF` Q4_K_M through an OpenAI-compatible endpoint is stable;
- 1-story smoke: 1/1 technical PASS, 1,924 words, 101.7 s;
- frozen 5-story run: 5/5 runtime completions, 4/5 technical length PASS;
- average words: 1,611.8;
- total runtime: 467.2 s;
- failing technical case: `05_emotional_calm`, 915 words.

Current interpretation:

- model/runtime stability is sufficient to proceed;
- the technical failure is a length/termination behavior issue, not a runtime crash;
- Ornith is not promoted to training until the common LUMI judge rubric and repetition/failure inspection are complete.

Next gate:

1. Judge all five frozen stories with the same six LUMI quality dimensions.
2. Preserve the 05 emotional/calm length failure in the final promotion decision even if its prose quality is acceptable.
3. Inspect repetition, truncation/early-stop behavior, and critical failures.
4. Decide Ornith status: train candidate / inference-only candidate / reject.

## Milestone 3 — FreeToken feasibility experiment

Goal: determine whether the current machine can use supported 30–35B-class MoE models as practical local inference/benchmark candidates.

1. Record exact system RAM, CPU, PCIe/GPU details.
2. Install FreeToken on a supported environment without replacing the existing llama.cpp path.
3. Start with a supported A3B-class MoE model rather than the largest available model.
4. Verify `/v1/models` and `/v1/chat/completions` compatibility.
5. Point the existing `local_endpoint_baseline` runner at FreeToken.
6. Run a one-story smoke benchmark.
7. Record model/quantization, system RAM use, VRAM use, prompt/prefill behavior, generation tokens/sec, total runtime, and failures/stalls.
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

For Ornith 9B on RTX 4060 8 GB, QLoRA remains a separate memory-feasibility smoke test. The failed native pure-GPU inference load must not be interpreted as proof that QLoRA is impossible, but it is a warning that memory margins are tight and must be measured explicitly.

## Milestone 5 — Small end-to-end student experiment

1. Run the chosen base model against the frozen benchmark.
2. Train on dataset v1 with 4-bit QLoRA.
3. Run the fine-tuned model against the identical held-out benchmark.
4. Compare base vs adapter using deterministic checks plus an LLM judge.
5. Record cost, runtime, VRAM use, failures, and lessons learned.
6. Check for memorization by keeping evaluation prompts outside the training set.

Success is improvement on held-out LUMI story quality, not merely lower training loss.

## Milestone 6 — Student/runtime comparison matrix

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

1. Ornith 1-story smoke. ✅
2. Ornith frozen 5-story runtime/technical benchmark. ✅ (4/5 technical PASS, 5/5 completion)
3. Ornith common judge + repetition/failure inspection. ← current
4. Decide whether Ornith deserves a QLoRA smoke test.
5. Freeze/confirm the first GPT Luna supervised dataset v1 used for the selected student experiment.
6. Run the smallest QLoRA memory/training smoke on the selected student.
7. In parallel after hardware inventory, run a FreeToken feasibility smoke test with one supported A3B-class MoE model.
8. Compare dense student and MoE reference under the same LUMI benchmark.
9. Scale data, context length, or model size only after evidence supports it.

## Decision rule

Do not choose a model because it is newer, larger, cheaper, or faster in generic benchmarks.

Choose it only if it improves the LUMI objective under our actual constraints: high-quality Turkish children's stories, stable local operation, measurable learning from GPT Luna data, and a workflow we can understand and reproduce.
