# Shared paid authority and Q7E reconciliation

Two different executions used the same Q7E name and approval. The local process claimed a checkout-local file; CI claimed a GitHub file. These were not transport retries or bounded rewrites. Both had four successful provider calls, but their response IDs and prose differ.

| Execution | Calls | Recorded cost |
| --- | ---: | ---: |
| Q7D | 10 | $0.320349 |
| Q7E local | 4 | $0.156380 |
| Q7E CI | 4 | $0.157202 |
| Total | 18 | $0.633931 |

The approved combined $0.60 ceiling was exceeded by $0.033931. No refund or ledger adjustment is asserted. The existing authority is closed; no new inference was performed during this repair.

## Evidence preservation

The canonical `SFR-V1-Q7E-PLAN-COVERAGE-20261007/` retains the CI records unchanged. Local records live in `SFR-V1-Q7E-PLAN-COVERAGE-20261007-local/`, byte-for-byte, including their original authorization history and local claim. Both independently replay to revision 6. Their distinct reviews remain distinct: CI's assembled candidate was accepted with a repetition warning; the local candidate passed with repetition and handoff-distance warnings. Neither result is overwritten or relabelled.

`SFR-V1-Q7E-DUPLICATE-AUDIT-20261008/` records both costs, response identities, file hashes and replay results. Every changed path in the local source commit `9d0ed3c` is additionally captured as its exact Git blob, including the original documentation and tests. The CI tests remain active; the local recorded-evidence tests are retained under a separate filename. A local bundle also preserves the original commit. Reconciliation preserves both histories without a PR merge or force push.

## Common admission path

All supported new local/CI executions use `src.spineforge_relay_v1_paid_entry`. It verifies the workspace fixture and frozen outer preflight before consuming authority. `prepare_reserved_story()` binds the original story preflight and the shared gate, lease-context, transport and dependency sources. Relative fixture paths are identical across machines. No entry automatically creates a grant; unknown or stale approvals are denied.

The central authority is the same repository's data-only `sfr-paid-reservations` branch. Its `authorizations/` ledger is addressed by approved grant ID. Grants freeze approval-evidence hash, permitted scopes, exact preflight hashes, models, call limits and cost limits. A single ledger contains all scopes sharing a budget, preventing independently valid per-run caps from exceeding the combined cap.

Before inference, a client reads the ledger and conditionally updates it with the file's previous blob SHA. A competing update is denied; there is no retry or checkout-local fallback. GitHub's [Contents API](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents) requires the existing blob SHA for updates and reports conflicts. A live two-client race with the same initial SHA verified exactly one successful reservation.

The entire maximum scope cost and call allowance is held before dispatch. Complete observed usage settles actual spend; unused funds can support a different already-approved scope. The same scope remains permanently consumed even after settlement. Uncertain dispatch, missing usage or failed settlement holds the full reservation. There is no automatic lease expiry, reopening, rollback or retry.

Before every dispatch the client checks the shared lease and unchanged grant again. The transport wrapper enforces allowed model, call count, per-call cost (default $0.15) and aggregate conservative cost. The actual provider usage must be finite and valid. These are admission/stop limits, not a provider-enforced billing guarantee: an unexpected provider charge cannot be undone by this code.

The Relay request classes in `_request_once` additionally require an exact, single-use in-process capability issued by the reserved wrapper. Old direct runner invocations therefore stop before HTTP. A different prompt or second HTTP call cannot reuse that capability. Other SpineForge request classes are unaffected. This protects supported trusted entrypoints; Python code with arbitrary modification/import privileges or outdated external checkouts is not a security boundary. Every client must use the updated entry and registered authority; owner credentials and grant registration remain trusted administrative controls.

## Historical source versions

Historical contracts, requests, responses, usage, deltas and state remain immutable. The original transport bytes are stored by SHA under `frozen-sources/`. Historical replay verifies the source version named in the old preflight against an explicitly registered, hash-checked snapshot when active code has changed. Unknown paths/hashes and corrupted snapshots fail. This does not assert that today's transport matches an old preflight; new paid preflights freeze today's gate sources instead.

## Execution controls and validation

Historical direct paid workflow jobs are retired. The only new paid workflow is manual and invokes the common entry; it still requires a separately registered explicit grant and fresh preflight. No new paid grant or paid workflow was launched for this repair. The old Q7D/Q7E account is registered CLOSED, including its observed overrun. A synthetic no-provider account was used solely for GitHub CAS proof and then closed. The registry tip contains only authorization records and README, so it has no executable workflows.

Tests cover local/CI races, concurrent scopes under one budget, consumed scopes, unavailable authority, lost settlement, unknown usage, revocation, model/call/cost limits, direct legacy transport, exact single-use dispatch, workspace path restrictions, source snapshot corruption and both recorded Q7E variants. GitHub control-plane proof had zero provider calls and did not load an OpenRouter key. The zero-cost CI uses the available self-hosted `local-runner-pool`; no pool capacity or production service was changed.

PR #264 remains draft. Production LUMI is untouched. This repair qualifies reservation and evidence consistency; it does not re-run the story or prove general story quality.

Final local validation: **305 Relay tests PASS**. Both local and CI Q7E evidence sets replay after the transport gate change, and the archived source blobs pass exact hash checks. No new provider calls or provider spend occurred.
