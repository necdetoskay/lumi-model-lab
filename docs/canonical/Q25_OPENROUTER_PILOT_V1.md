# Q25 — OpenRouter Extractor Pilot V1: one-call budget gate

Status: **DRY-RUN GREEN; LIVE PAID DISPATCH NOT COMPLETED**
Date: 2026-10-12
PR: #273 (DRAFT, not merged)

## Contract

The experimental `src/q25_openrouter_pilot.py` implements an explicit,
single-request OpenRouter Chat Completions transport for Q25.
There is no import/use of the legacy retry helper. The pilot is opt-in
and only takes an `OPENROUTER_API_KEY` provided by the GitHub Actions
secret store in a manually triggered job.

Eligible models are pinned to an exact allowlist:
`anthropic/claude-sonnet-5.5` and `google/gemini-2.5-flash`.
There is no automatic fallback to another model or request retransmission.
`q25.offline-extractor-replay.v1` still has no semantic approval or
canonical write authority.

The script compiles a Pydantic `response_format: json_schema` request,
requires `provider.require_parameters=true` and
`provider.allow_fallbacks=false`, and rejects any unexpected response
format, failed finish reason, or invalid raw output.

## Budget safety — defense in depth

- Manual GitHub Actions `workflow_dispatch` with explicit
  `execute_paid=true` and run attempt exactly **1**; PR pushes and
  ordinary test runs cannot use the paid job.
- The job has `contents: read` and runs on the isolated
  `q25-offline` runner, not production or IT-Manager runners.
- The key is held only in the Actions secret and in the process
  environment, never committed, logged or included in the evidence archive.
- Pull **live model pricing** from the public `/api/v1/models` endpoint,
  verify structured output support and compute a conservative upper bound
  on input tokens from UTF-8 bytes + 4096 overhead and output tokens capped
  at 3500. Neither the model nor context length may be changed implicitly.
- `/api/v1/key` preflight checks key spending-limit availability when
  `limit_remaining` is reported. A null key limit is **not** proof of
  sufficient account-level credit. Low credit can still return HTTP 402.
- The scripted cap is **$0.20 for one request**; any preflight worst-case
  estimation above the cap stops before the request. Pricing can change
  during a request, so this check is a bound using the quoted pricing,
  **not a guaranteed provider-enforced monetary cap**.
- Any HTTP 402, 429, timeout, JSON parse error, bad contract or unexpected
  exit stops; no retries, fallback, or loops. Non-200 error responses are
  not printed, protecting provider-specific tokens and user data.
- Existing model-credit problems should produce a clear STOP; the
  workflow never adds credits, changes account limits, or upgrades models.
- The one-call ledger stores model ID, SHA hashes, upper estimate, number
  of attempted calls, provider response hash, usage/cost if received,
  latency, and deterministic downstream status.
- Experimental output artifacts are kept in a private GitHub Actions
  artifact with 7-day retention, not committed to production data.

## Checked before paid dispatch

At the inspected catalog (2026-10-12) Sonnet 5.5 showed
input price `0.000002` and output price `0.00001` USD/token,
and supported structured outputs. The Q24 payload preview:
22,284 conservative input-token bound + 3,500 max output tokens,
for **$0.079568 worst-case estimate at those published token prices**.
The allowed charge ceiling remains **$0.20**; actual credit
availability has not been queried with the protected secret.

Offline CLI test (no key needed, no HTTP, no file changes):

```sh
python -m src.q25_openrouter_pilot \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json \
  --model anthropic/claude-sonnet-5.5 \
  --max-cost-usd 0.20 \
  --archive-dir /tmp/q25-pilot-dryrun
```

Result: `status=DRY_RUN`, `max_calls=1`, `provider_calls=0`,
`state_commit_authorized=false`. No archive directory created.

Raw request SHA from dry-run: `cb3884f5561367f2de75fa5235b53ba4d74acb499bf754d41da18736ec4a9019`.
Q24 seed SHA: `777b2d432ad292a91d9390725d4fe03c2ad91e4d358c9e3dcc785ee0b1daeb88`.

**A live manual GitHub Actions dispatch was attempted from this chat,
but the invocation was blocked by the execution environment's safety
controls. Do NOT record a paid call or claim paid qualification success.
No paid call is known to have been sent in this phase.**

A future *human-initiated* GitHub Actions manual dispatch, if permitted
by the repository/workflow settings, uses `Q25 Offline Diagnostic` on
branch `experiment/q25-narrative-memory-intent`, selects a pinned
model, and sets `execute_paid=true`. The state check remains
`SOURCE_BOUND_CANDIDATES_ONLY`, not `ACCEPTED`.

## Formal acceptance gates still missing

- Actual live OpenRouter extraction result from unseen story
- Semantic citation relevance, epistemic disambiguation and hallucination audit
- Character knowledge/goal/relationship and world-time completeness
- Stable multi-story pilot with frozen prompts, token/cost ledger
- Canonical StoryState adapter, write authority and production qualification

Nothing in Q25 authorizes production deployment, canonical state
commit, acceptance of the old rejected Q24 run, or automatic retry.
