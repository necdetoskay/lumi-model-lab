# SERA Agent Guardrails — Non-negotiable User Requirements

## Output token ceilings (user-prohibited)

**DO NOT** add a configured LLM output token ceiling in SERA experiments, provider adapters, test runners, launch definitions or examples. In particular, never add `max_tokens`, `max_completion_tokens`, `max_output_tokens`, `max_generation_tokens`, `max_new_tokens`, `num_predict` or `n_predict`.

This is an explicit repeated user instruction. Do **not** silently reintroduce caps in an attempt to save cost, avoid JSON truncation, reduce latency, or retry an experiment. Only revisit if the user explicitly reverses this rule.

- Provider/model-side hard limits still exist and cannot be removed by our request.
- Resolve truncated responses through appropriate response schema, context size, task decomposition or compatible provider/model capabilities—not by imposing arbitrary output limits.
- At every SERA direct provider request boundary, call `enforce_no_output_token_limit(payload)` from `request_policy.py`.
- Update `request_policy.CLIENTS` whenever adding a new direct model HTTP client, so the static guard can inspect it.
- The `sera-state-engine-tests.yml` GitHub Actions workflow must run the guard and unit tests on SERA branch changes.
- Historical paid-run configurations and evidence must remain auditably intact; they are records of prior mistakes, **not templates to copy**.
- Do not treat an offline test PASS as proof of model extraction completeness; no unvalidated canonical state commit.

## Preflight before every billable attempt

1. Confirm exact frozen input and whether paid execution is authorized.
2. Check the outgoing payload has **no application output token limit**; provider hard limits are not application-defined.
3. Check source hash, cost reporting, state write locks and independent semantic validation.
4. One complete evidence record per attempt; if a provider fails, inspect that failure before proposing another billable attempt.

Violating this requirement is a test failure, not an ordinary design preference.
