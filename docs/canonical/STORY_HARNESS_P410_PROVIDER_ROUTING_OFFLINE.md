# Story Harness P4.10 — Original v21 callback → offline OpenRouter request blueprint and single-use reservation simulation

**2026-10-13** · [Issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291) · [Draft PR #275](https://github.com/necdetoskay/lumi-model-lab/pull/275)

## What is now implemented

`src/story_harness_p410.py` is a **request-shaping and offline-only stage-reservation tool**, not a paid adapter. P4.8 previously executed the real frozen v21.4 engine against the new 2,491-word Writer story with fake model transport. P4.10 builds an exact, in-memory OpenRouter chat-completions JSON body **from the same genuine v21 adapter callback signature**: `api_key, model, system_prompt, user_prompt, temperature, max_tokens, seed, request_class, schema_name, schema`.

The new preview will reject any extra callback keyword, API key, model substitution, cost-cap inflation, missing/fake source SHA, wrong approved Spine, incorrect reader age, malformed JSON, large payload, changed initial-story segment, expanded repair range or full-story final audit. Every preview calls the P4.9 full Writer/artifact SHA integrity gate first.

An accepted **local preview** has:
- OpenRouter `POST https://openrouter.ai/api/v1/chat/completions`.
- Model `anthropic/claude-sonnet-5.5`, `temperature=0`, `stream=false`.
- **Pinned routing preview**: `provider.only=["Anthropic"]`, `allow_fallbacks=false`, `require_parameters=true`. This is an *intended policy*, not verification that a particular provider is available for this request. If no compatible endpoint exists, the eventual live adapter must STOP.
- Exact stages: `INITIAL_AUDIT` (3,000 output tokens), optional single `SCENE_REPAIR` (3,500), then `FINAL_AUDIT` (1,800, targeted only). No second repair, automatic retry, cross-model fallback or full-story reaudit.
- Original strict JSON-schema formatting, schema-name/stage binding, all 228 real Writer segments for initial audit and provisional 37-span S167–S203 repair constraints.
- Request prompts and manuscript stay **in memory only** for this tool; a separately calculated `request_receipt` contains only the SHA of the full request body, model/route flags and mathematical exposure.

Official OpenRouter provider routing describes `only`, `allow_fallbacks`, `require_parameters`: https://openrouter.ai/blog/insights/model-routing/
OpenRouter's Sonnet 5.5 provider list: https://openrouter.ai/anthropic/claude-sonnet-5.5/providers
Strict JSON-schema request shape: https://openrouter.ai/docs/guides/features/structured-outputs

## Spending simulation, not authentication

`OfflineReservationLedger` does filesystem **one-time** run claims and sequential, atomic `O_EXCL` stage receipts, with fsync. Duplicate run IDs, duplicate stage, missing previous stage, budget exhaustion, invalid/nonfinite spending, tampered source, unsafe route and old story SHA are rejected. A crash consumes the run/stage rather than automatically retrying.

Each stage records **maximum response tokens** plus a *caller-declared* input-token ceiling, valued at indicative public Sonnet 5.5 $2/M input and $10/M output. This is **illustrative arithmetic only**: the current live model's exact request input tokens, provider-quoted price (including caching/reasoning) and final charge are not authenticated. The `0.25` USD per attempt remains **proposed**, not user-approved; simulation claims are always `synthetic=true`, `authenticated_user_grant=false`, and `provider_dispatch_count=0`. No ledger entry can authorize real spending.

**Security boundary:** `block_live_dispatch()` ALWAYS raises `P410_OFFLINE_CONTRACT_ONLY_NO_USER_AUTHENTICATED_LIVE_DISPATCH`. The original frozen v21.4 transport has not been altered or selected for paid use. The demo reservation ledger is not a replacement for a trusted, authenticated, interprocess-durable paid authorization service; its receipts are not tamper-evident against a malicious filesystem writer. Provider-side spending caps are not guaranteed.

## Next non-negotiable requirements before a real model call

1. Review the provisional scene remap. Full bridge S162–S206 is 45 spans, exceeding the original max-40 single repair limit; restricted 37-span S167–S203 either must be explicitly acknowledged or modified under a separately versioned scope review without relaxing the original invariant.
2. Collect a **current authenticated routing/price and token exposure** for the *exact new in-memory requests*, including provider parameter support, thinking/cache behavior and a limited, no-fallback provider route.
3. Implement a separate, version-pinned **real paid** transport wired to the original v21 adapter with an authenticated human grant and atomic once-only spending reserve, exact stage limits, output/usage completeness, redacted failure evidence, and **no automatic retry**. Offline simulation cannot be promoted with a flag.
4. **Only after an explicit finite total USD ceiling is approved** permit one live attempt and independent semantics decision. Successful requests alone do not certify physical/canon/age/narrative quality. Never auto-seal English Master or start Q25.

## Verification

```sh
python -m unittest discover -s tests -p 'test_story_harness_p410.py' -v
python -m src.story_harness_p410 --repo-root .
```

The full Story Harness GitHub CI workflow includes those offline tests, validates a source-bound initial request, fake repair/final requests, 3-stage sequential cost reservation and negative cases. No new provider call or cost, no main/production or English Master/Q25/State changes.

**Honest P4.10 success criterion:** exact source-bound request preview and synthetic budget ordering verified; `stop_reason=P410_OFFLINE_ROUTING_AND_LEDGER_QUALIFIED_LIVE_DISABLED`. Paid dispatch remains blocked until the distinct authenticated live implementation and user permission are completed.
