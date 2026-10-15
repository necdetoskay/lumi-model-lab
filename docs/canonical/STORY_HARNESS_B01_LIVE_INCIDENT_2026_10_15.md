# B01 live incident — 2026-10-15 (read-only postmortem)

## Scope and immutable source

- Repo \`necdetoskay/lumi-model-lab\`, frozen V1 commit
  \`66aa9c1531d063f7b91fe89e6bcecff58add3eda\`.
- First actual B01 attempt:
  https://github.com/necdetoskay/lumi-model-lab/actions/runs/38677544426
- Full eight-file GitHub artifact #11947005149, SHA-256
  \`6fdd0fd99f43bb6d51b1db9db668a1ebdef96a4f5fa60905d692f7f9607d4a5a\`.
- Original V1 branch was not modified after the B01 attempted dispatch.
  This report and offline instrumentation live on a SEPARATE investigation
  / V1.1 branch. Neither is authorization to bill or retry.

## Observed, not inferred

1. Runner checkout succeeded, the existing inference key passed the
   pre-dispatch GET, and \`B01-00-attempt.json\` was written.
2. Exactly one model post was attempted: SPINEFORGE. Durable source-bound
   request intent hash was
   \`a016e17922ebf50c65417799e175544dfb2e9370d2c5f53a8653f546d36f0464\`.
3. Producer receipt is TRANSPORT / OTHER_CONTRACT_VALIDATION, with no
   provider envelope, no generation ID, no cost, no completed story.
   TrialLedger global cost uncertainty stopped the round. Zero settled
   receipts and zero retries; B02..B10 never started.
4. Root-cause **information loss is established in code**: TrialLedger
   catches *all* exceptions from the HTTPS transport and wraps them in
   ProviderCostUnknown. The pilot then flattens this into the generic
   OTHER_CONTRACT_VALIDATION. That report DOES NOT distinguish HTTP errors,
   network failures, missing usage, route mismatches or generation GET
   failures. We cannot assert the original provider failure category.

## Read-only provider finance observations

Separate investigation-branch manual diagnostic **GET only** jobs:
- https://github.com/necdetoskay/lumi-model-lab/actions/runs/38678161460
  at 03:48:26 UTC
- https://github.com/necdetoskay/lumi-model-lab/actions/runs/38678246825
  at 03:49:27 UTC

Both authenticated key snapshots are **identical**:

| OpenRouter shared-key field | USD |
| --- | ---: |
| Key configured limit | 40 |
| Remaining configured allowance | 26.8159069 |
| UTC-day key usage | 0.024528 |
| Weekly usage | 1.45977346 |
| Monthly usage | 13.1840931 |
| Lifetime usage | 46.283604502 |
| BYOK usage | 0 |

No model POST was sent by either diagnostic. $0.024528 is the entire
shared key's observed daily total, NOT authenticated attribution to B01.
It may include other consumers, and no exact baseline from immediately
before B01 was retained. B01 billed charge remains unknown.

OpenRouter GET /api/v1/generation requires a generation ID (not saved
by failed V1); GET /api/v1/activity requires a separate management key.
A normal inference key's daily total does not prove a single generation.

## Global STOP, conservative hold, and V1.1 change policy

V1 ended in a GLOBAL SAFETY STOP with a consumed B01 HTTP attempt.
Count **zero completed real stories**, but DO NOT claim zero provider
spend. For budget planning only, reserve the entire frozen SpineForge
stage allowance ($0.075) as an unresolved hold, not a settled charge.
Do not run B01 a second time under this V1 lock or bypass the unknown
charge. The agreed study cap is $20 total including LUMI prior exposure.

The V1.1 offline-only patch now preserves a sanitized original transport
status (HTTP category / no secret), and durably records a provider
generation ID and reported cost IF a response was received, BEFORE
cross-checking the separate generation GET. Failure continues to
STOP globally with zero retries. This is diagnostic hardening; it does
not cure the original provider error or retroactively settle B01.
No production/Main changes. Another paid baseline requires fresh,
separate version/freeze approval and real cost reconciliation.
