# FreeToken MoE Feasibility Experiment

## Purpose

Evaluate whether FreeToken can make supported 30–35B-class Mixture-of-Experts models practical as local LUMI inference and benchmark references on a low-VRAM laptop by combining GPU VRAM, system RAM, CPU execution, and dynamic expert scheduling.

This experiment is inference-only. It does not change the student fine-tuning plan and does not imply that large MoE models can be QLoRA-trained on the RTX 3050 Ti.

## Relationship to the LUMI roadmap

- Teacher: GPT Luna.
- Dense student training: compact models first; Ornith 1.5 9B remains a candidate if its story baseline is strong enough.
- Large MoE inference: FreeToken experimental track.
- Existing llama.cpp-compatible path remains the default mature local inference path unless FreeToken shows a measurable benefit.

## Hypothesis

For supported MoE models that exceed local VRAM, FreeToken may outperform a static CPU/GPU split by caching frequently used experts, overlapping PCIe transfers, and scheduling CPU/GPU work according to hardware behavior.

The experiment succeeds only if this advantage is useful for actual LUMI story prompts, not merely short synthetic benchmarks.

## Required hardware inventory

Record before the first run:

- GPU model and VRAM
- CPU model
- system RAM capacity
- operating system / Linux environment
- CUDA and driver versions
- storage type and free space
- PCIe link information when available

System RAM is a hard feasibility constraint because model weights that do not fit in VRAM must live elsewhere.

## Candidate selection

Start with one FreeToken-supported A3B-class MoE model in the 30–35B total-parameter range rather than the largest supported model.

Selection criteria:

- officially supported by the installed FreeToken revision
- quantization available and documented
- total host RAM requirement fits the machine with safety margin
- useful instruction/chat behavior
- Turkish output capability adequate for a LUMI benchmark

Do not hard-code a model name in the roadmap until the installed FreeToken version and current supported-model list are checked.

## Stage 0 — Installation and API smoke

1. Install FreeToken in a separate environment.
2. Do not remove or modify the working llama.cpp path.
3. Start the FreeToken API server.
4. Verify `/v1/models`.
5. Send a trivial `/v1/chat/completions` request.
6. Confirm the API is compatible with `src.local_endpoint_baseline` or document the smallest adapter required.

Exit gate: endpoint returns stable, valid responses without hanging.

## Stage 1 — One LUMI story

Run exactly one frozen benchmark spec first.

Record:

- selected model
- quantization
- prompt tokens
- output tokens
- target words / produced words
- time to first token if exposed
- tokens/sec
- total runtime
- peak VRAM
- peak system RAM
- CPU utilization observations
- context/prefill behavior
- completion/EOS behavior
- any stall, OOM, queue, or timeout

Do not judge throughput alone. Preserve the story for the same LUMI quality evaluation used for other local candidates.

## Stage 2 — Frozen five-story benchmark

Proceed only if Stage 1 is stable.

Use the same five story specifications, prompt contract, technical gates, and judge rubric as the dense-model baseline.

Compare against:

- compact dense baseline
- Ornith 1.5 9B baseline
- later fine-tuned student when available

## Success criteria

FreeToken earns a place in the regular model-lab toolchain if:

- the machine has sufficient RAM with safe headroom,
- LUMI-length prompts complete reliably,
- no systematic hangs/context failures occur,
- local throughput is useful for repeated benchmarking,
- story quality is meaningfully competitive or better than smaller alternatives,
- the result is reproducible across repeated runs.

## Failure interpretation

Failure does not invalidate FreeToken generally. Classify failure as one of:

- insufficient system RAM
- insufficient/unsupported GPU
- unsupported model/quantization
- context/prefill limitation
- runtime instability
- API integration issue
- throughput too low for practical use
- story quality not worth the systems complexity

## Decision after the experiment

Possible outcomes:

1. **Adopt for MoE benchmark reference** — FreeToken remains alongside llama.cpp.
2. **Watch only** — promising but too immature or unstable on current hardware.
3. **Reject for current machine** — hardware/RAM limits make it impractical; revisit with RTX 4060 or more system RAM.

No outcome changes the GPT Luna teacher decision.
