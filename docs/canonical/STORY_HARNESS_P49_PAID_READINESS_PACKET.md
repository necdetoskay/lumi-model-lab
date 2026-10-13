# Story Harness P4.9 — New-story live-attempt readiness packet (no provider calls)

**Date:** 2026-10-13 · **Issue:** [#291](https://github.com/necdetoskay/lumi-model-lab/issues/291) · **Draft PR:** [#275](https://github.com/necdetoskay/lumi-model-lab/pull/275).

**What this is:** A minimal, read-only source-bound pre-dispatch STOP packet, not another quality algorithm, a user authorization or a live adapter. P4.8's real frozen v21.4 quality callbacks have already been qualified in fake-transport mode. P4.9 must not replace that engine or invent an ACCEPT.

## Source identity and actual scene evidence

- New full English Writer *candidate*: **2,491 words**, exact text SHA `74529205bd799f46221f22a26aeff93c4ddfe8418cbca2523d43c94e63919e28`.
- Original human-approved Spine hash `f9c5bed93448d6c56787466ae583dfcee06d0f856641d9c3901136f142bffae6`; existing approval's historical existence does **not** authenticate new repair coordinates.
- Original v21.4 model runner's paid source is a **different** story. No old run receipt is transferable.
- New Writer artifact: `evidence/story_harness_p48/new-story-writer-candidate.json`. It is not model-generated and not semantically accepted; its 228 spans must reconstruct the same complete manuscript in order.
- Full return bridge runs S162–S206 (**45 spans**); this exceeds the max single repair scope (**40 spans**).
- Current candidate repair envelope S167–S203 (**37 spans**) covers the central mechanics, not the whole bridge. Coordinates are **provisional / not reapproved**. Serious outside-envelope finding → `REJECT_UNBOUNDED_REPAIR_SCOPE`, not an expanded or retried repair.
- Five still-open author-side review dimensions: bough load capacity, moving harness clip, landing tether equipment in Canon, return clock, and age-12 dialogue/agency. Static source checks cannot certify these.

## What is verified — and what still BLOCKS live dispatch

The new `src/story_harness_p49.py` checks the source profile's exact P4.8 SHA, Writer artifact digest and unique ID, story bytes, full 228-span coverage, fixed approved Spine hash, age/word count, exact scene boundaries, <=3 calls, <=1 repair, and every downstream denial flag. It emits a deterministic report with an explicit STOP and refuses invented grants, synthetic quality acceptance, broadened scope, changed sources or fake provider authority. `require_paid_dispatch()` **always stops** in P4.9.

The current blockers are:
1. The new coordinate remap requires **explicit human scope approval** or a clearly documented restricted-run decision. The full 45-span scene cannot be repaired under one existing 40-span envelope.
2. OpenRouter's public [Sonnet 5.5 listing](https://openrouter.ai/anthropic/claude-sonnet-5.5/providers) shows **$2 / million input tokens** and **$10 / million output tokens** as of 2026-10-13; this is **not** an authenticated request-time quote for a fixed provider/routing, cache policy, reasoning usage, retries, or fallback pricing.
3. Future **actual request** input-token exposure is not yet measured across the branching 1-or-3-stage execution. Historical initial/repair/final inputs were 9,949 / 5,034 / 5,106. Combining those historical input counts with the old output caps (3,000 / 3,500 / 1,800) and only public list prices yields **$0.123178 conditional arithmetic**, **not** a worst-case cost ceiling for the new story.
4. A separate **authenticated, finite, once-only user grant** and atomic per-stage spend reservation, durable usage ledger, and fail-closed incomplete-accounting handling are still needed. The **$0.25** amount remains a **proposal**, not approved spend. Provider-side hard caps are not guaranteed.
5. A distinct **versioned live** OpenRouter adapter with pinned story/Spine/run IDs, request-time price+token exposure, bounded max 3 calls, and redacted failure evidence sink is **not implemented** in this P4.9 packet.

Do not unlock real mode by changing P4.8's `real_provider_dispatch_allowed=false` or inserting fake `approved=true` JSON. The original v21.4 frozen paid runner is immutable.

## Run and acceptance

```sh
python -m unittest discover -s tests -p 'test_story_harness_p49.py' -v
python -m src.story_harness_p49 --repo-root .
```

CI also runs all prior offline P4.8 checks. A successful P4.9 test means **accurate blocked-readiness evidence**, not permission to spend or a story quality PASS.

**Next engineering slice within #291:** implement separately reviewed live request builder/routing verifier and a one-use, authenticated grant ledger **with simulated payment dispatch still disabled**; prove budget/provenance failure cases. Then obtain explicit user approval for one exact total USD ceiling, review the restricted scene scope, and execute at most one genuine bounded quality run. Genuine independently verified `ACCEPT` may make the exact SHA eligible for a separately validated English Master seal; Q25 and any production State write remain separate steps.

No merge, production change, new model call or new spend in P4.9.
