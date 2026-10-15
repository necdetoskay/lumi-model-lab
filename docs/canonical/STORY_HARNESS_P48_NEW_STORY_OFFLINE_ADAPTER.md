# Story Harness P4.8 — New 2,491-word Writer source bound to authentic offline v21 quality adapters

**Date:** 2026-10-13. **Issue:** #291. **Draft PR:** #275.
**New paid provider calls:** 0. **New cost:** $0. **Quality:** NOT ACCEPTED.

## Purpose and actual deliverable

The original frozen v21.4 paid profile is permanently tied to the
original 2,407-word Writer source SHA
`4f64a28eca70f29689e06d1baad3d3a471682bf3e4fce86dabad1c641410f636`.
Using its history, original `SCENE_REPAIR` artifacts or synthetic
`ACCEPT` for a different 2,491-word story would be false evidence.

P4.8 has actually created a **new immutable Writer source candidate**
for the P4.7 manuscript:

- Text: `evidence/story_harness_p47/offline-full-story-route-truth-revision.txt`
- Verified prose SHA-256:
  `74529205bd799f46221f22a26aeff93c4ddfe8418cbca2523d43c94e63919e28`
- New source ID: `story-writer-candidate:74529205bd799f46221f22a26aeff93c4ddfe8418cbca2523d43c94e63919e28`
- Frozen 228 real v20-compatible **new** segments (S001–S228), each
  covering the actual new prose in order. No old repaired segment
  IDs/text were silently copied.
- Source artifact:
  `evidence/story_harness_p48/new-story-writer-candidate.json`.
  It is explicitly `semantic_quality_accepted=false` and
  `model_generated=false`: P4.7 was an *assistant-authored Writer
  candidate*, not a model-generated or reviewed English Master.

P4.8's new **offline-only** profile
`configs/story_harness_p48_source_profile.json`
binds this exact source, the original approved Spine SHA, ContextPack
fingerprint, target reader age 12, original approval file SHA and
model slots (Sonnet 5.5). It cannot be used for actual paid dispatch.

## Scope remapping caveat — NOT silently approved

The original v21.4 human-approved repair scope was S159–S177 in
the original story. After real prose edits, fresh segmentation places
the return-bridge beat across **S162–S206: 45 spans**. The frozen v21
bounded-quality algorithm limits a single repair cluster to a scene
scope of at most **40 spans**.

The P4.8 candidate remaps only the central bridge mechanics to
**S167–S203: 37 spans**, not the entire beat.
The original approved **Spine textual field values** are projected
unchanged, but this NEW scene-coordinate remap is explicitly marked
`REMAP_OF_ORIGINAL_APPROVED_BEAT_NOT_HUMAN_REAPPROVED`.

Any serious problem outside S167–S203 must **REJECT** with
`REJECT_UNBOUNDED_REPAIR_SCOPE`. Do **not** silently re-label the
whole 45-span bridge scene repairable or increase the 40-span limit.
Before a future paid run, the correct reviewed scene scope must be
human-approved, or this restricted capability must remain clear to
the operator. A quality result that cannot fix an outside-scope
blocker is an honest REJECT, not an automatic failure to retry.

Source-bound selection:
`configs/story_harness_p48_remapped_scene_selection.json`.
Exact re-derived original-Spine-quoted constraints:
`evidence/story_harness_p48/candidate-remapped-constraints.json`.

## What ran with original frozen code

The new `src/story_harness_p48_offline_runner.py` runs **from the
unchanged frozen v21.4 source checkout** at Git commit
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`.
It calls the original runtime freeze verifier, genuine
`execute_paid_quality_once(simulation=True)`, original
`_load_source_story`, original approved Spine constraint derivation,
original quality engine, and the real audit / scene-repair / targeted
final **model adapter functions**, with **only fake transport callbacks**.

It uses an isolated temporary profile/Writer artifact that points to
the verified P4.7 story and new segments. The original frozen v21.4
profile is NEVER modified, nor is it spuriously declared to approve the
new story. The original freeze-verification function is used for
ORIGINAL CODE; the newly derived temporary profile is explicitly
provisional and is NOT passed as an approved paid v21.4 profile.

All model-facing calls use the authentic **lossless wire projection**:
the full new story is reconstructed and checked from the exact
228 projected segments before any mock audit reply is synthesized.

| Scenario | Original v21 bounded runtime status | Fake model attempts |
| --- | --- | ---: |
| Clean synthetic | `ACCEPT` synthetic only | 1 |
| One bounded repair (S167–S203) | `ACCEPT` synthetic only | 3 |
| Fake transport failure | `REJECT_PROVIDER_FAILURE` | 1 |
| Fake missing usage | `REJECT_PROVIDER_FAILURE` | 1 |
| Blocking issue outside repair scope | `REJECT_UNBOUNDED_REPAIR_SCOPE` | 1 |

The mock scene replacement reuses the same scene solely to test
branch routing, never to claim the physical issues were repaired.
The fake `ACCEPT` in the first two rows is **not genuine literary
or physical quality acceptance**; English Master/Q25/CANON remain
denied. No model network call, no provider retries, no paid spend.

## User budget, real-run next action

The user has approved **exceeding the old $0.10 quality *target***,
not unlimited spending or an actual single run. The discussed $0.25
total for one attempt is **a proposal** and is NOT a user-authorized
provider-side guaranteed hard cap. Current provider price, endpoint,
request-time input/token usage and worst-case charges are not verified.
The original v21 stage-specific post-usage STOP rules are not
a provider spending guarantee.

**Next: new-story paid preflight, not performed in P4.8.** It needs
a separately versioned, user-authorized paid implementation
with accurate current provider routing/pricing, a finite and consumed
one-time spending grant, an explicitly accepted new repair scope,
strict 3-call topology, diagnostic retention, and true independent
semantic audit. It must either genuine ACCEPT or REJECT/STOP.
Only an authenticated quality ACCEPT can proceed to English Master
and read-only Q25; production State writes are separately prohibited.

## Reproduce offline (no provider)

```sh
git worktree add --detach /tmp/lumi-p48-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
 'requests>=2.31,<3' 'python-dotenv>=1.0,<2' \
 'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P48_ROOT=/tmp/lumi-p48-source
python -m unittest discover -s tests -p 'test_story_harness_p48.py' -v
python -m src.story_harness_p48 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P48_ROOT" \
  --verify-report evidence/story_harness_p48/new-story-adapter-preflight.json
```

**Acceptance of P4.8** means ONLY that the actual new Writer bytes,
their 228 spans and the source-bound Spine have crossed the authentic
frozen v21 **adapter/quality engine boundary in OFFLINE mode**; no
one has yet audited or accepted story quality.

