# P4.6 — Full-manuscript editorial revision (gliders, turnaround timing)

**2026-10-13.** Parent P4.5 GitHub commit: `ad9c2316`. Experimental
P4.6 issue: #289. No real model call, no paid cost, no accepted English Master.

## What changed

The original **2,494-word P4.5 story** passed all technical source checks
but a complete editorial reading exposed a continuity defect **outside**
the protected bridge scene: Arda unfastens the expedition line that had
restrained one glider in strong winds; neither glider was then described
as secured until both were used for takeoff. The story also treated the
camp as an extended voluntary diversion **after** a pledged immediate
turnaround, stretching the closing flight corridor.

P4.6 produces a separately versioned **2,482-word full-manuscript
authorial candidate**, not a second v21 scene repair:

1. **GLIDER_TETHERS:** Nisa secures *both* gliders to separate living
   roots with their landing tethers, tests both knots, then Arda removes
   his expedition route line. The gliders can plausibly remain available
   for the final launch. The tether gear is a small editorial detail
   added to the fiction; its availability has not been verified
   independently against every Spine inventory field.
2. **TURNAROUND_CAMP:** The characters turn towards the shore before
   they encounter the camp **directly beside the return trail**.
   Nisa verbally insists on their agreed signal; Arda's temptation is
   shorter and more clearly an intentional risk.
3. **JOURNAL_URGENCY:** Arda flips quickly through knot sketches instead
   of prolonged browsing. The journal's unfinished departure entry,
   glider tag, distant stone gate, decision to return and mystery
   cliffhanger remain.
4. **TURNAROUND_BEAT:** Replace a long lingering pause with a heartbeat.

All four changes are replayed as exact-text substitutions using
the complete immutable P4.5 manuscript; each has independently pinned
original/replacement SHA and original character offset.
Everything else is unchanged. In particular, the **370-word P4.5
bridge sequence** remains *byte-for-byte identical* and retained as
an unreviewed **candidate**, not an accepted quality result.

The full new artifact is
`evidence/story_harness_p46/offline-full-story-writer-revision.txt`.
The manifest containing all four exact changes is
`configs/story_harness_p46_full_story_editorial.json`.
Deterministic replay and no-provider proof:
`src/story_harness_p46.py`,
`tests/test_story_harness_p46.py`, and
`evidence/story_harness_p46/writer-revision-proof.json`.

## Quality review status: still open

| Dimension | Editorial finding, not a signed acceptance |
| --- | --- |
| Character continuity | Nisa and Arda maintain separate points of view/agency through the decision, crossing and escape |
| Physical/causal | The new bridge anchor/clip/cut sequence is explicitly stated; branch capacity, dynamic rope friction and falling root forces still need independent expert/semantic evaluation |
| Inventory/state | Both gliders are now described as independently restrained while the route line is carried inland |
| Time | Camp and journal detour is shortened after their turnaround pledge; precise time remaining is still unknown |
| Narrative/age | Adventure/mystery, argument and trust arc remain; whether pacing, dialogue and prose actually engage a 12-year-old remains untested independently |
| Canon/Spine | Original scene and mystery/gate beats are preserved; full causal/spine assessment is not signed off |
| English Master/Q25 | **DENIED** until a genuine independently evaluated semantic-quality acceptance |

Static string/cryptographic correctness, a human editorial opinion from
the author, and offline fake-provider `ACCEPT` do **not** equal actual
v21 semantic-quality `ACCEPT`.

## Boundaries

This **full Writer-level editorial candidate** is intentionally distinct
from the original v21 single-scene-repair operation. It does not consume
an additional v21 quality call, create a new v21 repair, modify the
original source or any locked P4.5 artifact. A later genuine quality
run would take this full manuscript as a new input and start at initial
audit with fresh provenance. It must not silently reuse P4.5's previous
model audit or repair receipt.

The user allowed exceeding the former $0.10 cost target; $0.25 remains
a proposed, not authorized, total for one possible future paid run.
Current production/provider dispatch and Q25 remain OFF. No work
changes main or production.

## Reproduction

```sh
python -m unittest discover -s tests -p 'test_story_harness_p46.py' -v
python -m src.story_harness_p46 --repo-root . \
  --verify-receipt evidence/story_harness_p46/writer-revision-proof.json
```

