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


## Owner policy: zero manual story-generation gates (2026-10-16)

**Mandatory for SERA and any integrated LUMI story worker.** Never design normal
story generation to require a person to fix model JSON, curate per-story model
answers, approve scene events/entities, perform manual gold review, press retry
or resume, or trigger a rescue CLI. Historical reviewer forms and human-gold
research may remain as *optional laboratory evaluation*, not as a generation
dependency. Older docs that mention human review as a release blocker are
superseded for the **runtime workflow** by this section and by the v0.16
canonical architecture addendum.

Every error must flow through machine-operated detection, source-bound
deterministic repair, inexpensive targeted second-model repair, independent
revalidation and, if necessary, complete affected-stage re-extraction,
automatic replan/rewrite and checkpoint resume. Model confidence or agreement
alone never authorizes WorldState/EventGraph changes. If safe completion is
impossible after authorized attempts, finish with an explicit durable
`FAILED_SAFE_FINAL` outcome and **zero unsafe world writes**; never leave a
mandatory `WAITING_FOR_HUMAN` or endless HOLD loop.

A missing durable provider response may conceal an already-billed call.
Never blindly resend an unknown in-flight request. Implement request-ID
reconciliation/idempotent provider recovery before declaring crash/outage
autonomy qualified. Budgets may bound *provider requests and observed cost*;
they must not impose model output token-generation ceilings.

**Do not confuse test coverage with semantic success.** v0.17 identity
candidate coverage, v0.18 source-bound independent opinions and v0.19
event-candidate projections are experimental **noncanonical** components,
not proof of a complete autonomous production pipeline. Production rollout
requires durable writer/replanner integration, real independent source
qualification, transaction/rollback and machine-verifiable commit permission.
