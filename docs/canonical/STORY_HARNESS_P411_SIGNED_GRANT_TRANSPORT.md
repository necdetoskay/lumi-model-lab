# Story Harness P4.11 — Signed one-shot authorization contract and guarded OpenRouter adapter seam

**2026-10-13** · [Epic #276](https://github.com/necdetoskay/lumi-model-lab/issues/276) · [Quality issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291) · [Draft PR #275](https://github.com/necdetoskay/lumi-model-lab/pull/275)

## Intent

Stop designing new story generation paths; qualify the minimum controlled real-transport seam for the existing **2,491-word English Writer candidate**. The original v21.4 bounded quality engine, immutable story SHA, approved Spine and P4.8 offline adapter are not modified or replaced. P4.11 is **not** a paid E2E success, not English Master and not production admission.

## Implemented

1. `src/story_harness_p411.py:verify_one_time_grant()` verifies an **Ed25519 detached signature** over a deterministic JSON authorization payload. A trusted 32-byte Ed25519 public key must be provisioned **independently by the user's authorized operator**, never accepted from the grant itself or from the repository. The key is **not provisioned here**, and this tool does **not claim that signature by itself proves the signer's real-world identity**. The issued/expiry window is UTC-only and at most 20 minutes. Grant is bound to:
   - exact story SHA `74529205bd799f46221f22a26aeff93c4ddfe8418cbca2523d43c94e63919e28`, immutable Writer artifact and approved Spine;
   - Sonnet 5.5 model, Anthropic provider, explicitly acknowledged restricted S167–S203 repair scope;
   - 1 run, at most 3 calls, at most 1 scene repair and exact finite total user-selected dollar ceiling (e.g. the **proposed**, not authorized, $0.25);
   - issuance/expiry, approved intent and unique run identifier.
2. `OneAttemptLedger` consumes the **offline verified** test grant in a secure temporary directory via atomic exclusive creation, then writes each source-bound, one-time stage reservation and cumulative conditional dollar exposure **before** fake POST. It rejects stage duplication, out-of-order sequences, missing earlier calls or cumulative ceiling overruns. Crash/transport ambiguity consumes the attempted stage: **no retry**.
3. `validate_callback()` accepts the **original pinned v21 model-adapter callback shape**, never persists API key, reconstructs the P4.10 immutable request preview and verifies Writer/Spine/source/scope/model/cap/schema. `guarded_adapter_once()` then adds OpenRouter `provider.max_price={prompt:2,completion:10}`, retains `provider.only=["Anthropic"]`, `allow_fallbacks=false`, `require_parameters=true`, and **calls an injected fake POST only**. It passes a structured response back in the original adapter's `(raw, body, request, failures)` shape; missing cost, invalid usage or malformed JSON cause STOP without replay.
4. Every P4.11 positive test uses an **ephemeral offline signing key** and fake model transport. A simulated cryptographically correct grant is never treated as user-approved real spending. No private signing key, provider credential, prompt, manuscript, transport response body or simulated acceptance is committed to the project.
5. `live_paid_dispatch()` **always throws**. No real OpenRouter POST method is wired into the current workflow; no environment flip can turn a fake-transport test into a paid run. P4.11 adds neither English Master seal nor Q25 nor Canon writes.

## Why live sending is still blocked

A signed grant is necessary but insufficient. There is **no actually registered user-controlled trust anchor, no user-approved finite grant**, and **no authenticated request-time endpoint pricing/parameters or model-specific input-token upper bound** for all branches of the quality runtime. A quoted price or a max-output token limit does not by itself guarantee the total charged dollars, especially for cache, reasoning, request failure with incomplete usage, and uncertain provider tokenization.

OpenRouter documentation confirms provider `only`, `allow_fallbacks`, `require_parameters` and `max_price`. Those are per-token/provider routing controls, **not guaranteed per-attempt spending caps**:
- https://openrouter.ai/blog/insights/model-routing/
- https://openrouter.ai/blog/tutorials/how-to-get-the-lowest-cost-llm-inference-on-openrouter/
- https://openrouter.ai/docs/guides/features/structured-outputs

**Remaining engineering:** trusted signature-issuer provisioning; authenticated live provider/parameter/rate probe with no fallback; verified input-token ceiling/overage policy; durable accounting despite unknown usage; a separately reviewed true network transport with bounded API keys and an actual one-use operator grant; explicit human acknowledgment of the provisional 37-span repair scope. No auto-merge, production, paid API or success assertions.

## Reproduce without paid calls

```sh
python -m unittest discover -s tests -p 'test_story_harness_p411.py' -v
python -m src.story_harness_p411 --repo-root .
```

New negative tests cover forged approval, signatures from the wrong key, edited signed budget/story/Spine/model/scene bounds, missing trust anchor, expired grants, run ID reuse, stage duplication/out-of-order/over-budget, transport exception and missing usage, correct Writer request with fake adapter response, fake key leakage and unconditional live kill switch.

**Acceptance of P4.11 is only an authenticated-authorization *mechanism* and offline request/ledger interface.** It is not an authorization event or real provider model verdict. Current outcome should remain `P411_SIGNED_GRANT_OFFLINE_TRANSPORT_ONLY_LIVE_STOP`, 0 new provider calls, $0 cost, no quality ACCEPT.
