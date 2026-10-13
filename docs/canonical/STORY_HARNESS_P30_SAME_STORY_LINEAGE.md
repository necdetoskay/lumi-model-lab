# Story Harness P3.0 — Real same-story SpineForge → Writer #3 evidence; Q25 missing STOP

**Status:** Experimental / PR #275 Draft. Source snapshot: 2026-10-13. No production write, main merge, model call or paid execution.

## What P3.0 actually proves

Source: clean Git checkout of experiment commit
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`.
All listed Writer files, historical failed audit and original verifier module
have separately pinned SHA-256 values in `src/story_harness_p30.py`.
Source files are never rewritten by this run. The archived P1 SpineForge source
is byte-matched to the same pinned commit.

The harness **actually reruns** the genuine
`src.spineforge_v19_validator.validate_narrative_spine()` (P2.2) on the original
12-year-old island ContextPack, approved V20.2 Spine and reader obligations.
It then **actually reruns** the original
`src.spineforge_v20_story_audit_artifact.load_verified_writer_story_artifact()`
against the historical frozen Writer #3 manifest, story, result and envelope.

All four identity fields match between the approved Spine, the immutable Writer
manifest, and the real Writer result: `approval_id`, `spine_hash`,
`context_pack_id`, `context_fingerprint`. The Writer result and envelope
both say `writer_generated`. The exact story text file matches the original
Writer result (ignoring only trailing newlines per the original validator);
the story SHA is `e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f`.
The frozen original manifest records 2324 words, attempt 3, run
`36965340665`. It grants no new generation or downstream execution permission.

### Source evidence

| Original source | SHA-256 |
| --- | --- |
| `evidence/spineforge-v20-human-review/36910614976-approved.json` | `72cd2ecc973884415747aed93e721c2fbb32617901c24884142585b9c54254a3` |
| `evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json` | `aa78b74d4a2548f46d599aec2ee9abbbfb52aaa18c0bac2d03ed4a5b4f87ea13` |
| `evidence/spineforge-v20-paid-writer/36965340665/age12-island-v20-writer3-story.txt` | `e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f` |
| `evidence/spineforge-v20-paid-writer/36965340665/age12-island-v20-writer3-result.json` | `e5245b9cb0d81c6d395aa2cf69c3324f9d65f7df41809b314dfc0175b1094951` |
| `evidence/spineforge-v20-paid-writer/36965340665/age12-island-v20-writer3-envelope.json` | `e6f504e26be08325cf304cecfc5f7953d1ca9a494a48c1ff33b048dba5e44cf5` |
| `evidence/spineforge-v20-paid-story-audit/36969500342/qualification-report.json` | `eeb20809307a135d725c30d2d2a76209add2e4bae2e2e457526eef7b734edb6c` |
| `src/spineforge_v20_story_audit_artifact.py` | `8e57f788f78d0b16cc121655bfec1b918e560067d746f85732db59418d484414` |

These hashes are integrity pins for original Git bytes, **not digital signatures**
proving who reviewed/approved the historical story.

The archived audit qualification shares **both** Writer story SHA and
Writer artifact ID. Its original quality-gate *qualification* is
`FAIL_KNOWN_DEFECT_MISSED`, `qualification_pass=false`, with 0/1
target findings matched. **It stays RED.** This report is replayed as an
immutable historical record; the original audit quality test/model is NOT
rerun and does not certify that the Writer story is a deliverable.

## Mandatory fail-closed Q25 stop

The separately frozen historical Q25 KITE-01 and GREENHOUSE-01 attempts
are not this island story. **No pinned and verified Q25 source/prose/raw
extraction/ledger for this same island Writer #3 story has been provided in
this cohort.** No inferred link, fabricated Q25 field or semantic state
certification is allowed. P3.0 outputs:

- `same_story_spine_to_writer_confirmed=true`
- `same_story_q25_evidence_present=false`
- `same_story_q25_handoff_verified=false`
- `stop_reason=MISSING_SAME_STORY_Q25_ARTIFACT`
- `state=STOPPED_MISSING_SAME_STORY_Q25`
- All new writer/Q25/downstream/canonical execution authority **false**
- `provider_calls=0`, `provider_cost_usd=0`

This is not a global claim that no Q25 artifact could ever exist; it is a
precise stop for the **version-pinned admissible evidence cohort**.
Future Q25 requires a separately qualified same-story input, explicit
user authorization before any **billable** run and independent source/
semantic/terminal-state acceptance. The existing KITE and GREENHOUSE
replays must never be silently reinterpreted as this Writer's results.

## Reproduce without providers

```sh
git worktree add --detach /tmp/lumi-p30-pinned 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7'
export STORY_HARNESS_PINNED_P3_ROOT=/tmp/lumi-p30-pinned
python -m unittest discover -s tests -p 'test_story_harness_p30.py' -v
python -m src.story_harness_p30 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P3_ROOT" \
  --verify-report evidence/story_harness_p30/pinned-same-story-lineage-receipt.json
```

Receipt must exactly match a fresh rerun of BOTH original validators plus
archived audit and all pinned source hashes. Wrong run, wrong context,
forged `ACCEPT`, reversed story identity, edited Writer bytes, swapped
Spine and false Q25/canonical authorization fail closed.

**Limitations:** archived historical model output, not a new model run;
human identity unauthenticated; original model quality/audit not rerun;
no semantic quality or complete StoryState assertion; not a production
harness or Writer/Q25 runtime. Next phase should require an actual pinned
same-story Q25 request and review qualification, NOT invent one.

