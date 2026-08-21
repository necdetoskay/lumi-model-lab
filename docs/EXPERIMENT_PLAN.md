# Experiment Plan

## Goal

Use LUMI story generation as a practical lab for learning synthetic data generation, distillation-style teacher/student workflows, QLoRA, Unsloth, and evaluation.

Cost reduction is secondary. The primary outcome is a repeatable learning workflow with measurable experiments.

## Hardware and budget

- Local GPU target: RTX 4060 Laptop, 8 GB VRAM
- Primary fine-tuning method: 4-bit QLoRA
- Training framework target: Unsloth
- Monthly experimental budget: approximately 2,000 TRY
- API spend is acceptable when it creates useful training or evaluation data

## Milestone 0 — Repository bootstrap

- Reproducible config files
- Prompt versioning
- Raw / curated / processed data separation
- Baseline and fine-tuned evaluation paths
- Experiment outputs excluded from Git by default

## Milestone 1 — Small end-to-end experiment

1. Define a compact story specification and benchmark before training.
2. Generate 5 high-quality teacher stories (~2,000 words each).
3. Convert those stories into roughly 50–60 supervised examples.
4. Manually inspect and curate the examples.
5. Run the base model against the frozen benchmark.
6. Fine-tune the same base model with 4-bit QLoRA.
7. Run the fine-tuned model against the identical benchmark.
8. Compare base vs adapter using deterministic checks plus an LLM judge.
9. Record cost, runtime, VRAM use, failures, and lessons learned.

## Initial hypothesis

A very small but carefully curated dataset should be sufficient to validate the complete engineering workflow, but it should not be expected to create a production-quality story model. The first experiment exists to learn the pipeline and expose bottlenecks.

## Gate to scale the dataset

Do not generate hundreds or thousands of examples until the first small experiment proves that:

- the dataset format is useful,
- the training run is stable on the available hardware,
- the benchmark can detect meaningful changes,
- teacher and judge costs are understood,
- failures can be traced back to data, training, or evaluation.

## Next experiment candidates

After Milestone 1, compare one variable at a time, for example:

- 50 vs 200 training examples
- raw teacher stories vs structured sub-example extraction
- different LoRA ranks
- different base model sizes
- teacher model quality vs dataset size
- direct fine-tuning vs explicit teacher rationale removal
