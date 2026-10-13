# Story Harness P3.2 — English Master admission boundary (frozen island history)

**Status:** experimental, Draft PR #275; issue #283. **Date:** 2026-10-13.
No paid model calls, no Writer/repair/reaudit continuation, no English
Master seal, Q25 extraction, translation or production state write.

## Question: is there a real accepted English Master for this story?

**Not in the explicitly qualified historical cohort.** P3.2 first
reexecutes P3.1, which reexecutes the original pinned deterministic
SpineForge / Writer evidence validators. It then reads the exact immutable
historical cycle 10 files at Git source commit
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`, pinned by
`configs/story_harness_p32_english_master_admission.json` and its
independently embedded SHA-256. No inference/model audit is rerun.

| Question | Source evidence | P3.2 verdict |
| --- | --- | --- |
| Same-story Writer → audits → cycles 3–10? | P3.1 original source-byte/typed lineage replay | Integrity verified |
| Last actual story quality decision? | Cycle 9 finished reaudit | `LOCAL_REPAIR_REQUIRED` |
| Is cycle 10 an approved English Master? | Cycle 10 immutable repaired story/product | **No** — just a new repair |
| Does cycle 10 have an ACCEPT reaudit? | Original `next-state.json`, next-handoff | **No** — `REAUDIT` / `READY_NOT_AUTHORIZED` |
| May future ACCEPT *route* to English Master sealing? | Source-pinned original `paid_story_quality_loop_once.py` AST, frozen C10 handoff | Yes, **conditional policy only**, not a real event |
| Is there a registered immutable seal? | Frozen seal registry + Git-tree inventory of 152 `evidence/spineforge-v20*` files | **No** in this qualified cohort |
| Does another story have ACCEPT? | Pinned Lighthouse `LIGHTHOUSE-COMPLETION-06-20261005/result.json` | Yes, **unrelated**; forbidden as island seal |
| Is story/Q25 admission authorized? | All of the above, no same-story accepted source/seal | **No** — hard STOP |

The frozen cycle 10 source story text hash and file hash are checked
separately. Original `product`, `reaudit handoff`, and `NextState`
must all agree about the same artifact ID, SHA, paths, stage 25, cycle 10
and immutable source bytes.

## Critical separation of authority

- `next_stage_on_accept=ENGLISH_MASTER_SEAL` is a **policy branch**
  encoded in the historical contract. It does not mean that the branch
  ran or that the story's last audit returned ACCEPT.
- `qualification_pass=true` on an audit's known-defect test measures
  the **audit test**, not the actual story acceptance gate.
- `repair_generated` / `FROZEN` confirms an immutable *candidate*.
  It cannot qualify the story's semantic/age/canon/roleplay or causal
  quality. The same is true for a next-handoff in
  `READY_NOT_AUTHORIZED` state.
- Even an actual future quality ACCEPT only makes a story *eligible*
  for a separately versioned and source-bound immutable English Master
  seal step. Q25 requires that seal and independently validated same-story
  source, not merely an ACCEPT label.

## Future English Master acceptance contract (not yet granted)

The next version may admit a story only after **all** conditions hold:

1. Same-story Spine hash, context ID/fingerprint, approval ID, original
   Writer and all later repaired-story artifact IDs and SHA values are
   independently verified from a clean pinned source cohort.
2. There is a real **completed full-story reaudit** on the exact newest
   candidate story, with an authenticated `decision=ACCEPT` and no
   terminal quality blocker. Any incomplete, failed, mismatched or
   `LOCAL_REPAIR_REQUIRED` reaudit stops.
3. The accepted English prose bytes are immutable; exact text SHA and
   source artifact/run identifiers appear in a versioned English Master
   seal manifest that is source-pinned and independently reverified.
4. That sealed manifest matches the same StorySpine and accepted story
   SHA; any different source (including an unrelated Lighthouse story)
   is refused, even if its status says ACCEPT.
5. Only a separate Q25 admission gate can produce a read-only Q25
   input. It must not permit automatic retries, paid API calls, writing
   canonical StoryState, starting another story, or production mutation.

**No input in the P3.2 pinned cohort satisfies 2–4.** The explicit
accepted-reudit, seal and Q25 allowlists are empty and SHA-pinned.
Adding arbitrary JSON or changing a status field **cannot** upgrade
this frozen historical attempt to success. A new audited/versioned
source manifest and authorizations are required for a future real
accepted candidate. This phase intentionally has no fabricated
positive story-quality ACCEPT fixture.

## Actual outcome

```text
stop_reason: ENGLISH_MASTER_NOT_ADMISSIBLE
state: STOPPED_UNSEALED_UNACCEPTED_STORY
historical_english_master_artifact_found: false
last_completed_reaudit_cycle: 9
cycle_10_next_action: REAUDIT
english_master_story_accepted: false
english_master_seal_execution_authorized: false
q25_extraction_authorized: false
final_story_state_authorized: false
state_commit_authorized: false
provider_calls: 0
provider_cost_usd: "0"
```

Original reported historical model costs from old episodes are **not**
new spend. Replaying historical reports does not authenticate original
reviewer identity or reproduce any model's semantic judgment. Scanning
152 Git-tracked source paths proves a narrow **committed-file cohort**
fact, not that no English Master exists anywhere in other branches,
untracked artifacts, or future runs.

## Reproduction ($0 and fail-closed)

```sh
git worktree add --detach /tmp/lumi-p32-pinned 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7'
export STORY_HARNESS_PINNED_P32_ROOT=/tmp/lumi-p32-pinned
python -m unittest discover -s tests -p 'test_story_harness_p32.py' -v
python -m src.story_harness_p32 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P32_ROOT" \
  --verify-report evidence/story_harness_p32/pinned-english-master-denial-receipt.json
```

CI fresh-replays P1–P3.2, compares the immutable exact denial receipt,
and exercises negative cases: invented cycle 10 ACCEPT, relaxed re-audit
policy, forged seal, Lighthouse cross-story substitution, unsigned or
newly inserted artifacts, altered source hashes, changed branch/commit,
Q25/State authorization and manual alteration of the final receipt.

**Follow-up:** only after a genuine bounded quality pass produces an
immutable ACCEPTed story should we version a seal producer and a
read-only Q25 request adapter. Do not try to fix this with another
unbounded multi-cycle repair loop.

