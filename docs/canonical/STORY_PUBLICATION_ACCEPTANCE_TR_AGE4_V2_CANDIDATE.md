# LUMI Story Publication Acceptance Contract — TR Exact Age 4 v2 Candidate

Status: QUALIFICATION CANDIDATE — NOT YET CANONICAL

This candidate revises only the relationship between story length and publication acceptance. The frozen v1 contract remains the current canonical reference until the v2 candidate passes regression and is explicitly promoted.

## 1. Decision

For Turkish exact-age-4 stories, story quality is primary and word count is secondary.

The writer keeps an internal soft generation target of approximately 500 words. That target is a pressure signal for drafting, not a deterministic publication requirement.

A final story MUST NOT fail publication solely because its word count is outside the former 375–625 hard band.

Length may contribute to a blocking decision only when the actual text materially exhibits an existing blocking defect, for example:
- age_mismatch,
- story_structure_break,
- broken_turkish,
- logic_or_physical_break.

A short but complete, coherent, age-appropriate story can pass. A longer story that reaches a numeric target through filler, repetition, unsafe invention, new canon, or damaged pacing can fail through the relevant quality class.

## 2. Why v1 needs revision

The frozen v1 contract treats 375–625 words as a deterministic hard gate around a nominal 500-word target.

Controlled Story V5 experiments show that this conflates two different concepts:
1. generation pressure — how much narrative volume the writer is encouraged to produce;
2. publication quality — whether the resulting story is actually good enough to deliver.

### Evidence A — single-story pressure probe

Run 36223914525 held premise, eight-beat spine, writer model, reasoning, temperature and seed constant while varying only internal generation target.

Observed outputs:
- target 500 → 333 words, blind quality 9/10, low filler risk;
- target 600 → 340 words, quality 8/10;
- target 700 → 453 words, quality 7/10 with blocking defects;
- target 800 → 430 words, quality 8/10.

This proved that a higher internal target can increase output length, but more words do not reliably improve quality.

### Evidence B — five-family 500-vs-700 blind pairwise probe

Run 36224302173 used exact age 4 across five distinct story families with the same writer model and medium reasoning. Each family produced a 500-pressure and 700-pressure draft. A blind judge compared both orders.

Consensus:
- 500 pressure won 3 families;
- 700 pressure won 1 family;
- 1 family was position-sensitive / inconclusive.

Observed word counts ranged below the old 375-word minimum in several candidate stories that nevertheless beat their longer counterpart in blind quality comparison.

This is repeated cross-family evidence that the old deterministic minimum can reject the better story.

## 3. Generation policy

The generation target remains approximately 500 words for this profile.

The writer instruction is:
- treat 500 as a soft narrative-volume target;
- do not add new events, canon, explanation, adjective filler, or mechanical repetition to approach the number;
- finish when the story is naturally complete.

There is no automatic 1.4× or 700-word multiplier. The five-family test did not support a universal higher pressure setting.

Future model profiles may learn family-specific generation pressure if repeated evidence shows a stable benefit.

## 4. Publication gate

Blocking classes remain:
1. canon_violation
2. logic_or_physical_break
3. broken_turkish
4. age_mismatch
5. caregiver_teacher
6. story_structure_break
7. visible_generation_artifact

Only critical or serious findings block publication.

Removed from v1:
- hard_length_failure as an independent blocking class.

Added as non-blocking evidence:
- length_deviation.

Length deviation is retained for analytics, model profiling, cost analysis, and future calibration. It is not ignored; it is simply no longer allowed to substitute for a quality judgment.

## 5. Repair policy

The bounded repair policy remains unchanged:
1. generate draft;
2. run at most one local edit pass for concrete defects;
3. run one independent final acceptance check;
4. stop.

A short story is not expanded merely to satisfy a numeric target. Any repair must address an actual quality defect.

## 6. Promotion gate

This candidate MUST NOT replace v1 as canonical until:
- deterministic contract tests are green;
- candidate regression confirms that length deviation alone cannot fail;
- existing non-length hard-fail behavior remains unchanged;
- no regression reintroduces recursive repair or editor authority drift.

After those checks pass, promotion requires an explicit versioned canonical decision.
