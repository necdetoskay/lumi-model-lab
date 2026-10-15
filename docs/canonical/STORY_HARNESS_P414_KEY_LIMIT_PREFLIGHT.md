# Story Harness P4.14 — Dedicated OpenRouter key spend-limit read-only preflight

**2026-10-13** · [Draft PR #275](https://github.com/necdetoskay/lumi-model-lab/pull/275) · [Quality issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291)

## Objective and boundary

Qualify the **actual key-limit introspection contract** ahead of any paid story audit, WITHOUT creating keys, changing account limits, deploying, model inference, or treating test signatures as human consent. Reuse the P4.11 external Ed25519 grant verifier and the P4.12/P4.13 fail-closed Story Harness; no new live model runner or ledger.

OpenRouter documents `GET https://openrouter.ai/api/v1/key` to read the **current bearer token's** key metadata, including `limit`, `limit_remaining`, `limit_reset`, `include_byok_in_limit`, `usage`, `byok_usage`, `is_management_key`, `is_provisioning_key`, `is_free_tier`, and `expires_at`. Management keys, separately, can POST/PATCH keys using `/api/v1/keys`. P4.14 intentionally implements **NONE** of those mutations.

Official references:
- https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key
- https://openrouter.ai/docs/api/api-reference/api-keys/create-keys
- https://openrouter.ai/docs/api/api-reference/api-keys/update-keys
- https://openrouter.ai/docs/guides/overview/auth/management-api-keys

## Implemented read-only verification

`src/story_harness_p414.py` exposes a credential-bound one-shot **HTTPS GET only**, with certificate verification, 12s timeout, no redirects, no retries, maximum 32 KiB reply and safe errors without exception traces, headers, bearer tokens, full raw JSON or identifying provider fields. The minimal redacted metadata report is never treated as a spending authorization. CLI without a key prints blocked static status and does not make any request.

`analyze_key_metadata()` requires the **separately provisioned dedicated inference key** to have all of the following:
- Non-management, non-provisioning, not free-tier, explicitly finite positive `limit`.
- **No automatic limit reset** (`limit_reset=null`), since replenishment during an authorized attempt would violate one-use spending intent.
- `limit <= independently signed grant USD amount`, and `limit_remaining == limit`; observed OpenRouter `usage == 0`, `byok_usage == 0`, to reject reused keys.
- `include_byok_in_limit=true`, ensuring BYOK usage does not circumvent the key limit; no negative, NaN, missing or bool cost fields.
- Expiry absent or more than twenty minutes away, with strict UTC time check.
- Caller cannot use metadata supplied in a stored file to claim HTTPS authentication. An arbitrary JSON object can pass the *structure* validator; that never authorizes dispatch.

`validate_signed_key_preflight()` **first verifies** the real original P4.11 signed grant against an external trusted key + source SHA + expiration; only then performs a key-bound read-only GET. Its output is redacted; `provider_dispatch_authorized=false` unconditionally. A mocked opener in CI is explicitly marked **non-authenticated**. The function cannot prove exclusive key use, zero concurrent/in-flight charges, or an exact account-level hard USD cap; the provider key limit is an external control that must be independently provisioned under the user's actual account, then re-read with that key.

**No secrets should ever be written to GitHub, CI workflow YAML, Issue #291, PR #275 or story evidence.** Separate operator-controlled secret storage is required. Never reuse the general LUMI/OpenRouter key for this limited test, because other runs could spend its budget.

## Operator actions for a future explicitly approved one-off trial

These are NOT yet performed:
1. Obtain an explicit user-approved total USD ceiling and human acceptance of S167–S203 restricted repair, including **non-equivalence** of omitting `temperature=0`; full bridge S162–S206 has 45 spans and cannot fit frozen max 40. Outside-scope serious findings must REJECT.
2. Provision and independently pin an Ed25519 human-approval key out of band. No test signing key or repo field may substitute for the operator's trusted public key.
3. Create **a new dedicated inference key** inside the owner's OpenRouter account with finite limit <= the signed budget, `limit_reset=null`, BYOK counted, zero prior usage; keep the bearer secret only in a secure external store. A management key may be used by the authorized owner to create keys; management keys cannot make inference requests.
4. Only through secure operator execution, read the key's actual `GET /api/v1/key` metadata; verify `limit_remaining`, reset policy, expiry and all fields. Check concurrent/in-flight consumption protection, actual current provider route and billed-token exposure; use a reviewed real transport linked to one trusted atomic spending ledger. **No model POST until ALL gates pass**, and the signed grant is consumed in one trustworthy once-only operation.
5. Do not overstate the protection: provider key limits may have in-flight overshoot or races, and provider metadata does not prove single-user exclusive possession or a guaranteed upper bill bound. Provider's published price and a `provider.max_price` route filter are *not* a per-attempt spend guarantee.

## Safety state and tests

```sh
python -m unittest discover -s tests -p 'test_story_harness_p414.py' -v
python -m src.story_harness_p414 --repo-root .
```

P4.14's fake-key tests check credential-bound **GET only**, no redirects, no mutation/POST, hostile HTTP errors, malformed metadata and values, old/resettable/unlimited keys, account-identifier redaction, missing or expired signed grants, signed budget and model/Story SHA linkage, missing trust anchor, BYOK exclusion, pre-used credits, and unconditional downstream STOP.

### No real authorization

**Provider key actually provisioned: NO. Key spending limit verified on user's account: NO. External human authorization grant: NO. Sampling change separately approved for live: NO. Verified billed input upper bound: NO. Dedicated trusted live spending lock: NO. Actual paid model calls/cost: 0 / $0.**

No independent quality ACCEPT, English Master seal, Q25, StoryState, main merge or production deploy. P4.14 acceptance means offline safety interface and instructions GREEN only; `live_paid_dispatch()` still always stops. Next productive action will need operator-owned **actual dedicated key** and **finite user authorization** before any live work.
