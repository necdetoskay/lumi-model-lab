# P4.12 — real metadata preflight and durable offline accounting

Base: P4.11 `1da48c99d4696426cb701dcf03bf6c929ee34199`, Draft PR #275,
open quality issue #291. This is a bounded readiness improvement, not a paid
execution or independently accepted story. $0.25 is proposed, not authorized.

## Verified provider observation

On 2026-10-13 a credential-free HTTPS GET to
https://openrouter.ai/api/v1/models/anthropic/claude-sonnet-5.5/endpoints
returned the exact `anthropic` endpoint, provider Anthropic, status 0,
prompt $0.000002/token, completion $0.00001/token, 1,000,000 context capacity,
128,000 maximum completion tokens. These are time-specific catalog facts,
not a binding request quote, hard spend cap, or exact request token count.

The endpoint advertises `max_tokens`, `response_format`, `structured_outputs`
but **does not advertise `temperature`**. Existing P4.10/P4.11 bodies require
`temperature=0` with `require_parameters=true`; preflight therefore reports
`UNSUPPORTED_REQUEST_PARAMETERS:temperature`. This is a catalog compatibility
blocker, not evidence of an attempted/rejected paid request. No silent removal
of temperature, provider fallback, output-limit change, or model substitution.

References: [endpoint catalog API](https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints),
[provider selection](https://openrouter.ai/docs/guides/routing/provider-selection).

## Concrete command and trust boundaries

```sh
python -m src.story_harness_p412 --repo-root . --refresh-provider
```

Expected exit **2**, `status=BLOCKED`. The optional refresh performs one bounded
HTTPS GET with certificate verification, no redirects, credentials, model POST,
or retry. Without the flag the command is offline. The CLI cannot accept a grant
or enable paid execution. Its timestamp and catalog digest identify an observation;
replaying JSON does not authenticate a live provider or refresh its age.

The Python preflight API reuses the P4.11 Ed25519 verifier on the original
envelope and the current UTC clock. It rejects a forged verified-grant summary,
missing/wrong externally pinned key, tampering and expiration. Test signers are
ephemeral fixtures; no actual human key or grant was issued. A deployment must
bind its trust key to the human outside the untrusted grant and repository.
Preflight never consumes a grant and remains blocked even after valid test signing.

## Accounting repair in the existing P4.11 module

- No second ledger or runner. Existing exclusive run/stage claims persist before
  fake transport; reservations are not released or reused.
- Reservation and outcome SHA now cover the actual body including `max_price`.
- Immutable redacted outcome files contain reported usage/cost and cumulative cost.
  Prompt/output usage must fit stage ceilings, cost must fit its reservation and
  cumulative total must fit the signed amount. Decimal arithmetic is retained.
- Missing/invalid usage, malformed response, timeout, overexposure or failure to
  persist the outcome blocks all subsequent stages, not just retry of that stage.
  Unknown spend is never recorded as zero. Run ID reuse after restart fails.
- POSIX file and directory fsync preserve records/names. Windows ACL and storage
  durability still need deployment qualification. Caller-supplied grant summaries
  are accepted only by this explicitly simulated ledger; they are not live authority.
  A local writable filesystem is not a trusted tamper-proof accounting service.

## Remaining blockers — no paid dispatch

1. No actual externally authenticated one-use human spending grant or trusted key;
   proposed $0.25 cannot be used as permission.
2. Restricted repair S167–S203 (37 spans) is not human-reapproved. Full bridge
   S162–S206 is 45 spans, exceeding frozen max 40. Outside-scope blockers reject.
3. Resolve observed route parameter mismatch through separately reviewed adapter
   behavior; do not alter frozen v21.4.
4. Establish request-bound billed input-token exposure (including router/provider
   formatting and schema overhead) and any additional charges. Catalog capacity,
   historical counts, byte estimates and caller integers cannot certify that ceiling.
5. Provision externally controlled accounting/one-use authority and review real
   transport integration. `live_paid_dispatch()` still unconditionally stops.

P4.12 makes **zero paid model calls**. No independent quality ACCEPT, English Master,
Q25/state authority, production modification or main merge. PR remains Draft;
issue #291 remains open. CI demonstrates offline behavior only.

## Validation

Local P4.10/P4.11/P4.12: **42 executed, 42 passed** (13 new P4.12 tests).
The broader `p41*` pattern also discovers 13 older pinned-source tests, skipped
locally. Full Windows discovery: 236 discovered, 91 passed, 144 skipped for
missing pinned checkouts, one pre-existing P1 CLI path portability error
(`Path` converts the manifest to backslashes rejected by `secure_artifact`).
Do not describe that run as a full pass. Linux CI runs the existing pinned-source
qualification steps and the new P4.12 step; its result must be verified on the
published head. Frozen source files have no Git changes.
