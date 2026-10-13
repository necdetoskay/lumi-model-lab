# Story Harness P4.7 — Source-bound Writer route correction and quality-runner STOP

**2026-10-13.** Draft PR #275, issue #290. Source commit
`bcc351899bc3396618546bbddac506baedb632cb`. No paid calls or
production/main changes.

## What is actually different

The 2,482-word P4.6 Writer-level candidate contains an inaccurate
sentence during Arda's bridge escape:

> The rope had marked every turn back to the shore. Without it, they'd never find the same way again.

Earlier chapters say **someone else's old knots** mark the route across
the forest. Arda's expedition rope had been used to stabilize a glider,
then coiled on his shoulder. It had not been unrolled to mark every turn.

The new English P4.7 candidate substitutes just one line:

> The old explorers' knots showed the way. This was Arda's own line, the one he'd promised to bring home. To reach Nisa, he'd have to let it go.

This retains the emotional sacrifice without inventing a separate
navigation function for Arda's rope. The literal old and new text,
source offset, per-quote hashes, old/new full-story hashes, and the
frozen P4.6 source commit are listed in
`configs/story_harness_p47_route_truth_revision.json`.

The new, complete **2,491-word** manuscript is
`evidence/story_harness_p47/offline-full-story-route-truth-revision.txt`.
Its SHA-256, excluding its terminal newline, is:

```
74529205bd799f46221f22a26aeff93c4ddfe8418cbca2523d43c94e63919e28
```

Deterministic source replay confirms the **only** difference against
P4.6 is this single source-anchored authorial substitution. This does
not mutate the original v20/v21 source, P4.5/P4.6 evidence, or the
production Canon. This is a new Writer draft, **not a second paid
scene-repair call**.

## Provisional literary and causal review — NOT independent acceptance

`evidence/story_harness_p47/offline-editorial-review-brief.json`
contains six source-quote-anchored editorial observations:

| ID | Provisional status | Required follow-up |
| --- | --- | --- |
| ROUTE_TRUTH | Editorial fix applied | Verify sacrifice and trail wording matches the real preceding actions |
| LOAD_CAPACITY | Needs independent review | Verify the bough can sustain a swinging human and sliding rope |
| SAFETY_SLIDER | Needs independent review | Inspect whether the harness clip can move on the line as described and why it jams under load |
| GLIDER_EQUIPMENT | Needs independent review | The invented two landing tethers must be allowed by actual Spine/inventory/Canon |
| TURNAROUND_PRESSURE | Needs independent review | Reconcile time needed for journal/camp stop and escape with a narrowing flight corridor |
| AGE_AND_AGENCY | Needs independent review | Judge age-12 pacing, character motivations, agency, dialogue, and literary engagement |

These are **author-side editorial questions**, not an independent
semantic auditor's results or a guarantee of safety/physical realism.
Five remain open. The bridge repair is not certified simply because
SHA/structural tests pass.

## Crucial actual paid-source gate

The actual original frozen **v21.4** provider adapter profile in
source commit `2eb3d825b5baf8f0f16ccb23805f619d433c7236`
binds the paid runner to an **older island story SHA**:

```
4f64a28eca70f29689e06d1baad3d3a471682bf3e4fce86dabad1c641410f636
```

The **new** P4.7 story SHA is different. The original frozen runner's
quality receipts/SCENE_REPAIR artifacts cannot be reused as a
genuine audit of this new story. P4.7 explicitly confirms this SHA
mismatch against the pinned frozen profile and **stops**:

```text
status = OFFLINE_WRITER_CANDIDATE_UNREVIEWED
new_quality_model_profile_required = true
original_frozen_model_runner_reusable_for_new_story = false
independent_semantic_quality_accept = false
stop_reason = NEW_STORY_SHA_REQUIRES_SEPARATE_QUALITY_RUNNER_QUALIFICATION
```

**Required next step, not performed here:** explicitly version a NEW
source-aware v21.5+ quality run profile for the P4.7 full manuscript,
its actual approved Spine/ContextPack, request time, model endpoint and
provider pricing. Run dry-run callback and lineage checks, confirm
finite one-attempt spending cap and authenticated user grant, then
only with separate authorization dispatch a real Initial Audit →
zero-or-one Scene Repair → Targeted Final Audit. No retries, no full
story final re-audit, no transfer of a previous synthetic ACCEPT.
After authentic validated `ACCEPT`, a separately authenticated
English Master seal/Q25 read-only admission may be considered.

**Spending policy:** user has allowed exceeding the old $0.10 quality
target. The discussed $0.25 per-attempt amount is a **proposal only**,
not an approved grant and not a provider-side hard spend ceiling.
Provider calls now: **0**, new spend **$0**.

## Reproduce

```sh
git worktree add --detach /tmp/lumi-p47-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
export STORY_HARNESS_PINNED_P47_ROOT=/tmp/lumi-p47-source
python -m unittest discover -s tests -p 'test_story_harness_p47.py' -v
python -m src.story_harness_p47 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P47_ROOT" \
  --verify-report evidence/story_harness_p47/pinned-route-truth-preflight.json
```

CI runs the original P1–P4.6 Story Harness checks plus this source
replay/provisional editorial review, and confirms real paid/provider,
English Master, Q25 and Canonical State gates are **off**.

