# Story Harness P4.5 — Actual offline bridge-scene rewrite (unreviewed)

**Date:** 2026-10-13. **Draft PR:** #275. **Parent issue:** #288.
**Real provider calls:** 0. **New spend:** $0. **StoryState/Q25/English Master:** NO.

## Finally creating a real prose candidate

The original island story **The Island That Wasn't on Any Map** is 2,407
English words. It was not accepted by the historical real quality run
`37230896244` (`REJECT_PROVIDER_FAILURE`). P4.4 exposed five
source-grounded preliminary physical/spatial defects in the return
root-bridge sequence, including problems left in the earlier paid scene
repair.

This phase **does rewrite the prose**. The newly authored **370-word**
replacement is stored as immutable, reviewable text:

- `evidence/story_harness_p45/offline-editorial-bridge-scene.txt`
- SHA-256 of scene content (without terminal newline):
  `d74f171ac816336b2e2254763e1d22fff4507f5c5c3f89184481775d3964998c`
- Complete 2,494-word story:
  `evidence/story_harness_p45/offline-editorial-full-story.txt`
- New complete story text SHA-256 (excluding terminal newline):
  `141b21ca68d1160e540e1c33bc9b47fb35bbc1a7ce027df391e3a76f708de156`

This draft was written **offline by the assistant/editor**, not by the
original paid model and not by a separately authenticated independent
reviewer. It is **not a semantic quality ACCEPT** or a sealed English
Master, even if structural checks pass.

## Actual source-pinned rewrite, not just a hand-written join

The original SHA-frozen v21.4
`src.spineforge_v21_bounded_quality.apply_scene_rewrite` processes
the full frozen 199-span cycle-10 Writer source and its authentic
`SCENE-072-078` cluster. It replaces **exactly S159–S177** at original
character offsets **9993 through 11495**. Prefix up to S158 and suffix
starting S178 remain byte-for-byte unchanged. The updated text receives a fresh complete-story segmentation.

Original `build_targeted_final_audit_payload` also validates the
repaired-scene-plus-boundaries shape, approved Spine, S158/S178 boundaries,
and prohibitions on full-story final reaudits and repeated repair.
**Only the payload is built — no model final audit was performed.**

## What the new scene actually changes

The scene keeps the same Spine escape beat and the emotional/canon payoff,
but makes six specific spatial/causal actions visible:

1. **BANK:** Arda and Nisa begin on the inland bank. The broken root
   bridge's *far* shoreward end remains attached; the near end has
   pulled loose. Their flight corridor is closing.
2. **SWING:** Arda knots the route line to a sound trunk, passes its
   running length over a thick bough extending past the middle of the gap,
   attaches the free end to Nisa's harness and swings her toward the
   lower opposite ledge. Nisa unclips, wraps the end around a stout root, and knots it securely on the far bank on the shoreward side.
3. **CROSS:** Arda clips to the guide line and uses the still-attached
   root span for footholds to cross toward her.
4. **LOAD:** A splintering root snags the line ahead of his harness as
   the bridge falls and pulls him away from Nisa; its tension jams his safety clip; he cuts the loaded section to release that force, then opens the slack clip.
5. **TRUST:** She has already secured the rope at the far root and now catches both hands while he is still hanging. His choice is to trust her help; immediately afterward unchanged S178 describes
   him pulling up onto solid root.
6. **LOSS:** The useful route line is severed, leaving one inaccessible half hanging on each bank. The costly escape and last launch
   proceed without it.

These six steps are tested for exact source-bound markers in increasing
textual order. Such static checks are **not proof of physical
realism, natural prose, age appropriateness, or plot excellence**.
Independent semantic literary and causality review can still reject
this candidate, and other story-wide issues may remain.

## Quality, cost, and scope boundaries remain closed

This manuscript **does not** modify any original v20/v21 historic
artifact, Spine approval, ContextPack, canonical state or production
LUMI. It does not replay or reclassify the historic paid failed
`FINAL_AUDIT`. It is a *new editorial candidate* for separate review.

The user has permitted exceeding the former $0.10 quality target.
**$0.25 is only a proposed finite total for one future paid attempt**,
not yet a paid execution grant or guaranteed provider-side hard cap.
No current real provider quote or exact request-time worst-case
cost has been verified. No real model requests or paid retries are
dispatched. Real English Master seal and Q25 gates stay closed.

## Reproduce

```sh
git worktree add --detach /tmp/lumi-p45-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
  'requests>=2.31,<3' 'python-dotenv>=1.0,<2' \
  'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P45_ROOT=/tmp/lumi-p45-source
python -m unittest discover -s tests -p 'test_story_harness_p45.py' -v
python -m src.story_harness_p45 --repo-root . \
 --pinned-source-root "$STORY_HARNESS_PINNED_P45_ROOT" \
 --verify-report evidence/story_harness_p45/pinned-editorial-rewrite-receipt.json
```

Canonical immutable manifest:
`configs/story_harness_p45_editorial_bridge_candidate.json`.
Original source, failed paid history, editorial bytes, full candidate,
no-certification decision and no-provider ledger are all SHA-pinned.

**Next meaningful action:** independent semantic review of the **new full
story**, focusing on physical rope/bridge geometry, characters' positions,
12-year-old reader engagement and the hero's moral choice. If it rejects,
revise this editorial candidate offline without claiming a real v21
model ACCEPT. The single user-approved paid attempt, if later launched,
must be a separate source- and cost-bounded process with real
authorization and provider evidence.

