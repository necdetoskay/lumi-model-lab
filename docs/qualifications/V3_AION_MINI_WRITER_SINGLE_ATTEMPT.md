# Aion 3.5 Mini — Single-attempt Writer guard

Scope: already-human-approved age-18 Beacon Ridge control, not the new
Forbidden Cartographer fantasy case. Aion Mini writes; Sonnet plans.
No paid Writer grant exists and the earlier $0.50 SPINE grant is not reusable.

The guard uses one billable Writer POST and fails closed on transport timeout,
HTTP 429/5xx, missing provider generation ID/cost, second call, over-cost or
unsuccessful deterministic Writer output. Every attempted POST has immutable
evidence. A provider spend cap assessed after response is NOT a hard external
billing cap.

The runner requires a separate Writer-specific grant, exact guard commit,
43 frozen V3 source checks, fixed SHA of the prior approved Spine and a
persistent one-use grant claim. Cross-runner live dispatch will additionally
require a GitHub-global claim ref before any provider POST.

Historical Writer: successful run 36612862926, 2,172 EN words, $0.0316043.
That run used the v2 Writer prompt; this guarded run uses the v3 generic prompt.

No user-approved new Writer POST has been sent, and no existing
production / main / frozen V3 source is changed.

## Actual Aion story audit (existing paid artifacts; no new provider calls)

The original historical C2 Aion 3.5 Mini output was 2,172 English
words, $0.0316043 for its Writer call. Applying the frozen V3
deterministic authority rules to this **real stored** output with
authority packet v2 produces **five findings**: premature formal record,
two raw-observation erasures, and two setup-overclaim statements.
The repaired/accepted English master is 2,176 words with **zero**
such deterministic findings. The accepted Turkish delivery is 1,817
words and triggers **zero** deterministic translation semantic findings.
Historical final path: 6 total paid calls, $0.17766185, 426.802 seconds,
with reconciled call-summed token and cost evidence.

These are deterministic replay results on stored artifacts, not a new
provider run, semantic judge verdict, or a claim of perfect literary quality.

An earlier Forbidden Cartographer F1 Gate returned **REPLAN** with six
blocking dimensions and no human Writer authorization. The frozen new
fantasy case remains **READY_FOR_FROZEN_SPINE_F1**; never repurpose the
older unapproved F1 as an approved input to Aion Mini.

Result: Writer-only mock PASS is necessary but insufficient. Actual product
qualification requires controlled Spine -> explicit approval -> Aion Writer
-> authority -> bounded repair if needed -> translation -> fidelity.

## Existing OpenRouter secret verified through real GitHub Actions (no paid POST)

On 2026-10-15 an already-installed diagnostic workflow was dispatched,
run ID 38694937823, branch experiment/story-v5-whole-draft-prototype-20260924.
GitHub Actions job completed SUCCESS, and authenticated OpenRouter
GET /api/v1/key returned HTTP 200 with the existing repository secret.
No Chat Completions POST or charge was made by this diagnostic.

The auxiliary GET /api/v1/activity?date=2026-09-29 returned HTTP 403
with error 'Only management keys can fetch activity for an account'.
That is an endpoint authorization distinction, NOT absence or
invalidity of OPENROUTER_API_KEY. No management key is requested,
replaced, or copied into an independent shell process.

This confirms the usable provider credential is available within the
existing GitHub Actions execution boundary. It does NOT itself enable
safe paid dispatch of the new single-attempt Writer/Spine guard:
a suitably authorized guarded workflow remains required. Never run
the older auto-retrying Story stage in its place.
