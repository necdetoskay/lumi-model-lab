# Repository Coding-Agent Instructions

Follow the existing EOS source-of-truth hierarchy (Constitution > Standards > Templates > Playbooks > Project Docs > Sprint Docs). This file provides a specific user-supplied execution constraint, not a replacement for that hierarchy.

## Explicit recurring user constraint: DO NOT impose model-output token caps

The user has explicitly and repeatedly prohibited adding application-specified model output token limits. Across **all new code, experiments, API calls, prompts and workflows** in this repository:

- Never configure `max_tokens`, `max_completion_tokens`, `max_output_tokens`, `max_generation_tokens`, `max_new_tokens`, `num_predict` or equivalent output ceilings, unless the user expressly changes this decision.
- Do not invent or silently restore an arbitrary output cap for cost, latency, retry or JSON-truncation handling.
- Treat existing historical configurations containing such limits as **old evidence**, not as templates or permission to repeat the behavior.
- Model/provider intrinsic limits are not removable by our code; diagnose them separately. If a response is incomplete, investigate schema compatibility, task decomposition and model capabilities instead of inserting a new cap.
- For SERA direct provider clients, use `experiments/sera/request_policy.py` and maintain the CI enforcement coverage and unit tests.
- Before making a paid provider request, verify the exact outbound payload. Do not turn a dry run into an unapproved paid run.

This rule exists to prevent repetition of a user-reported failure; do not ask the user to repeat it.
