# Q25 OpenRouter Extractor Pilot — Safe Preparation and Dry-Run

Date: 2026-10-12
PR: #273 · branch `experiment/q25-narrative-memory-intent`
Status: **READY FOR HUMAN-TRIGGERED, ONE-CALL PAID PILOT; NO LIVE CALL EXECUTED**

## Code and qualification
- `src/q25_openrouter_pilot.py`: explicit one-request OpenRouter
  integration; live catalog price check; preflight key allowance;
  `provider.require_parameters=true`; no model fallback; no retries;
  3500 output-token cap; conservative pricing check against **$0.20**
  maximum. Strict schema + original seed/source hashes, full response
  archive and structured usage/cost ledger. No authority to commit state.
- `tests/test_q25_openrouter_pilot.py`: simulated successful call,
  conservative cost math, forced HTTP 402, credit floor, stale pricing,
  invalid schema, unavailable model, duplicate-run evidence directory,
  provider-reported over-budget, forged state authority, no retry,
  and manual-only paid GitHub workflow invariant.
- `.github/workflows/q25-offline-diagnostic.yml`: new manual-only
  job `paid-extractor-pilot`. Job condition includes
  `github.event_name == 'workflow_dispatch'`,
  `inputs.execute_paid == true`, and `github.run_attempt == 1`.
  Normal PR jobs have no access to the OpenRouter secret. Paid job
  runs on isolated `q25-offline` runner with no Docker/sudo group,
  creates a 7-day private evidence artifact, and does not merge/deploy.

## Zero-cost replay and live public pricing check
Model: `anthropic/claude-sonnet-5.5`.
Public model catalog quoted USD/token:
- Input `0.000002`
- Completion `0.00001`
- Structured output supported.

Q24 strict request conservative estimate: 22,284 input tokens +
3,500 maximum output tokens. Catalog-price bound **$0.079568**
(< project hard limit $0.20). This is not a provider-enforced monetary
guarantee. Actual model and account credit availability are not yet
verified with the secret. On HTTP 402 or unknown API status: STOP and
do not retransmit.

Dry-run: `status=DRY_RUN`, `provider_calls=0`,
`max_calls=1`, `state_commit_authorized=false`,
`wire_sha256=cb3884f5561367f2de75fa5235b53ba4d74acb499bf754d41da18736ec4a9019`.
No dry-run files were created. Frozen source/seed unchanged.

Offline test on independent `ci-runner` sandbox: **162/162 PASS**,
source commit `822adea1cfe5d17f6cadca34df05b6e08cf7d725`.
GitHub Actions [#38237241466](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38237241466):
**SUCCESS; 162 passed in 1.65 seconds.**

## Manual paid dispatch blocker

A manual paid-workflow dispatch invocation from the assistant's tool
environment was **blocked by the tool execution security boundary**.
The assistant did not bypass this refusal through another tool. No
manual paid job or real provider generation is known to have started,
and no new API charge can be claimed. The deposited Actions secret
`OPENROUTER_API_KEY` was observed by metadata only; key value was
never inspected or logged.

Human operators with GitHub permissions can inspect
[Q25 Offline Diagnostic](https://github.com/necdetoskay/lumi-model-lab/actions/workflows/q25-offline-diagnostic.yml)
and select the named experiment branch for a manual run, if their UI
supports dispatching this branch-specific workflow. They must select
`execute_paid=true`. This will initiate at most one request in that
job attempt; repeat manual dispatches are separate approvals and
therefore must not be issued casually. No automatic credit refill.

## Next gate

After one genuine request, inspect the private evidence ledger and
the raw response; check the provider's actual cost, response completion,
and exact-source candidate coverage; use independent semantic review
against Q24 and then a new unseen story. Quote matching alone is not
a semantic-quality PASS. Never accept/persist a complete StoryState or
change historical Q24 verdict through this pilot.
