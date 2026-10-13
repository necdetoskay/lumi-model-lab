# P4.13 — Explicit Sonnet routing compatibility, NOT a paid request

**2026-10-13** · [Draft PR #275](https://github.com/necdetoskay/lumi-model-lab/pull/275) · [Quality issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291)

## Verified and fixed for offline qualification

The credential-free P4.12 endpoint observation for `anthropic/claude-sonnet-5.5` + exact Anthropic route reports `max_tokens`, `response_format`, and `structured_outputs` but **not `temperature`**. The original frozen v21.4 adapter passes `temperature=0`. With `require_parameters=true`, this prevents selecting that route. Default model/provider fallbacks are prohibited.

A newly versioned harness projection, `src/story_harness_p413.py:adapt_wire()`, makes exactly **one visible non-equivalent transformation** on a verified P4.10 callback preview: **omit** the unsupported `temperature=0` field from the actual OpenRouter JSON request body. It retains exact original prompts, Writer SHA, model, schema, output cap, Anthropic-only provider route, no fallback and `require_parameters=true`, adding the existing `max_price` only. No other parameters may be silently dropped or altered.

**Important:** omission is **NOT** equivalent to `temperature=0`; decoding/default sampling behavior and repeatability may change. The offline function requires an explicit boolean acknowledgment of this non-equivalence. That local boolean is not a user spending approval, not a signed route exception and **never** authorizes a live request. A future signed live authorization must disclose/approve this deviation and must reference a fresh endpoint observation. If the endpoint begins supporting temperature, the special omission route stops rather than continuing unnecessarily.

The P4.13 call path is integrated into the **existing P4.11 fake-transport adaptor and its P4.12 repaired accounting**, not a new runner or ledger. The reserved body SHA is the SHA of the **actual projected wire** (including provider `max_price` but excluding temperature), and the same SHA is recorded after fake POST. All original P4.11/P4.12 offline default tests retain their existing temperature=0 behavior; optional P4.13 mode is explicit.

Run `python -m unittest discover -s tests -p 'test_story_harness_p413.py' -v` and `python -m src.story_harness_p413`. Negative tests prove: no acknowledgment, different model/route, price increase, output-cap change, unsupported schema fields, unauthorized fallback, tampered Writer SHA, transport failure, duplicate attempt and the exact per-stage SHA link all STOP or remain offline-only. No paid provider POST or credentials used.

## What P4.13 does not solve

1. **No genuine quality result:** Writer is a 2,491-word editorial candidate, not independently model-audited. Neither English Master, Q25 nor State can be admitted.
2. **No accepted human route deviation:** the above omission needs separate approval for a future paid run; no impersonation of an operator grant.
3. **No signed finite budget or trusted issuer provisioned:** `$0.25` is still a proposal, not authorized spending.
4. **No verified request-time billed token exposure:** OpenRouter's endpoint catalog, its 1M context limit, historical input counts and any caller-supplied `declared_input_ceiling_tokens` are not binding bills. `provider.max_price` is a per-token price filter, not per-run budget.
5. **No trusted live transport or independent immutable accounting:** original `live_paid_dispatch()` still always raises. All simulated result receipts say they are synthetic and non-authoritative. No main merge, production, extra story write, provider calls or paid cost.

A future live path requires out-of-band operator-bound grant, provider-side **dedicated per-key spending limit** or equivalently enforced guardrail, verified current route/price, authoritative usage accounting, a separately reviewed once-only real transport and explicit upper spending consent. OpenRouter documents credit limits, per-key caps and in-flight accounting but those controls should be verified under the actual user credential rather than assumed. OpenRouter's **per-key limit** may provide a stronger externally enforced budget than our synthetic ledger, but it can have other usage and reset policy, so a dedicated key is important.

- [OpenRouter provider selection and require_parameters](https://openrouter.ai/docs/guides/routing/provider-selection)
- [OpenRouter credit limits, key limits and in-flight budgets](https://openrouter.ai/docs/api-reference/limits)
- [OpenRouter strict structured output](https://openrouter.ai/docs/guides/features/structured-outputs)

## Acceptance boundary

**P4.13 PASS only means** a wire-compatible, explicitly disclosed no-temperature JSON body and exact once-only **fake-provider** SHA/ledger contract. The original frozen model callbacks and source artifacts remain unchanged. `sampling_semantics_equivalent=false`; `live_dispatch_allowed=false`; `quality_accepted=false`; `new_model_calls=0`; `cost_usd=0`. No implication that Sonnet has judged the story.
