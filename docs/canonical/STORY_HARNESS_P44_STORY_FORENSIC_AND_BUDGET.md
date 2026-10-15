# Story Harness P4.4 — Real island story forensic and cost-overrun preflight

**Date:** 2026-10-13. **Issue:** #288 (real paid attempt still open). **PR:** #275 Draft.
**New API cost:** $0, **new model calls:** 0. **Paid dispatch:** OFF.

## Purpose: fix a story, not merely pass a harness

The pinned age-12 story is **The Island That Wasn't on Any Map**, 2,407
English whitespace-delimited words, story SHA pinned in
`configs/story_harness_p44_story_quality_preflight.json`, original v20
cycle-10 source, same island approved Spine and ContextPack. It is
**not** an accepted English Master.

The original real v21 paid quality run `37230896244` had:

| Stage | Token input/output | Actual historical cost | Status |
| --- | ---: | ---: | --- |
| Initial blocking audit | 9,949 / 298 | $0.022878 | Completed, one serious physics finding |
| Targeted scene repair | 5,034 / 955 | $0.019618 | Completed, old candidate only |
| Targeted final audit | 5,106 / 528 | $0.015492 | `AdapterResponseError` |
| **Total** | **20,089 / 1,781** | **$0.057988** | **`REJECT_PROVIDER_FAILURE`** |

The failed final audit produced **no trustworthy ACCEPT**.
No repair may be registered as accepted merely because it is present
in immutable evidence.

## Concrete source-anchored problems

All seven editorial observations have an exact quote, character offsets,
the SHA-256 of the pinned source containing that quote, severity and a
bounded acceptance obligation. They are **preliminary human-readable
editorial criteria**, not a signed independent human reviewer verdict.

| ID | Level | Defect / required correction |
| --- | --- | --- |
| MECH-001 | Blocking | One end tied to a trunk, other end clipped to Arda; the narrative simultaneously throws a nonexistent free end. Define the load-bearing route |
| MECH-002 | Blocking | Nisa is returning from the camp with Arda, yet suddenly catches a line from the opposite bank. Fix the characters' locations before the crossing |
| MECH-003 | Blocking | Falling root span allegedly drags Arda by a line with unclear snag point and force direction. Make cutting it physically causal |
| MECH-004 | Blocking | Real paid v21 scene repair also throws a coil to Nisa without establishing where she stands. Repair output is not automatically an improvement |
| MECH-005 | Blocking | Nisa hauling herself hand-over-hand across an insufficiently supported rope lacks an explained anchor/crossing method |
| ART-001 | Advisory | The line is detached from the glider used at the shore, with no subsequent securing of the gliders during strong winds |
| NARR-001 | Advisory | The agreed turnaround signal is triggered, yet the journal/camp investigation and escape must preserve a credible remaining time window |

**Quality obligations for a future one-shot real attempt:**
show whose side Nisa and Arda occupy before each throw, keep
trunk/harness/bridge anchors separate, define load path and why one cut
frees him, retain a believable storm and departure clock. Preserve the
journal, old knots, mysterious gate, friends' conflict/resolution and
real age-12 dialogue and agency; do not flatten the story into engineering
instructions. Strict repair envelope: `S159–S177` only, entry `S158`,
exit `S178`; one repair maximum, targeted final audit only, no repeated
full-story audit and no loop.

## Cost check and user's cost-overrun permission

OpenRouter publicly listed `anthropic/claude-sonnet-5.5` at
**$2 per 1M input tokens** and **$10 per 1M output tokens** on
2026-10-13. Source: https://openrouter.ai/anthropic/claude-sonnet-5.5/providers.
The current public listing is useful for indicative planning but not an
authenticated request-time routing/provider quote, no provider spending
cap or cached/reasoning/fallback charge guarantee.

The original frozen runtime `max_tokens` per stage is 3,000 / 3,500 /
1,800. Using only **historical actual input token totals** and these
maximum output limits yields the **conditional exposure $0.123178**,
greater than the former **$0.10 target**, even though the earlier actual
run cost $0.057988. Input/context and output counts can differ in future
attempts, so this is **not a worst-case provider hard limit**.
All three per-stage exposures individually exceed original target caps
at that same hypothetical maximum.

The user explicitly allowed a **cost overrun of the $0.10 target** during
P4.4. This permission is preserved in the immutable source preflight:
`quality_target_overrun_user_permitted=true`. It is *not* construed as
unlimited spending, an exact user-approved USD ceiling, or permission
for any number of paid calls. Source contract explicitly records:
`authorized_paid_spend_ceiling_usd=null`,
`real_dispatch_enabled=false`, and zero new API cost.

**Therefore the budget gate must not reject solely because a bounded
attempt could exceed $0.10; it must still reject any paid dispatch until
a finite total expense ceiling, precise once-only paid grant, current
request-time provider pricing/routing, token exposure and private failure
evidence sink are separately verified.** Original frozen v21.4 must not
be modified to toggle a budget limit.

## Reproduction

```sh
git worktree add --detach /tmp/lumi-p44-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
  'requests>=2.31,<3' 'python-dotenv>=1.0,<2' \
  'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P44_ROOT=/tmp/lumi-p44-source
python -m unittest discover -s tests -p 'test_story_harness_p44.py' -v
python -m src.story_harness_p44 --repo-root . \
 --pinned-source-root "$STORY_HARNESS_PINNED_P44_ROOT" \
 --verify-report evidence/story_harness_p44/pinned-story-review-budget-receipt.json
```

This phase reruns the original P1→P4.3 offline source/quality/kill-switch
gates before the manual source quote/paid-record ledger review is admitted.
Local and GitHub CI tests must fail on quote/offset changes, cross-story
source hash, hidden/blocker dismissal, modified historic cost, provider
price/usage nonfinite values, forged grant, real dispatch enabled, or
English Master/Q25/state activation.

## Actual current decision

```text
stop_reason: NOT_READY_FOR_REAL_BOUNDED_QUALITY_ATTEMPT
real quality accepted: false
quality target overrun permitted: true
authorized finite paid spending ceiling: null
new paid calls: 0
new cost: $0
English Master seal / Q25 / StoryState commit: disabled
```

**Issue #288 stays open** for genuinely repairing and accepting the story
after explicitly bounded and verified paid execution. Do not silently
mark it complete because the forensic and budget preflight passes.

