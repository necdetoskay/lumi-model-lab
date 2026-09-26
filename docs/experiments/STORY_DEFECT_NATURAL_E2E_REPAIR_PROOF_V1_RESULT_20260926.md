# LUMI — Natural Defect Repair Proof v1 Result

Date: 2026-09-26  
Issue: #217  
Branch: `experiment/story-v5-whole-draft-prototype-20260924`

## Verdict

**Qualification gate NOT PASSED.**

The proof was executed case-by-case instead of being declared green from CI status alone.

Final disposition:

| Case | Expected | Result | Evidence | Disposition |
|---|---|---|---|---|
| N1_RESPONSE | response_causality / LOCAL_REPAIR | PASS | run 36250729181 | Valid proof case |
| N2_STATE | state_continuity / LOCAL_REPAIR | PASS | run 36250844261 | Valid proof case |
| N3_CAUSAL | causal_logic / STRUCTURAL_REPAIR | FAIL at detection | run 36250931810 | GOLD_DISPUTED |
| N4_CLOSURE | closure_integrity / LOCAL_REPAIR | FAIL at detection | run 36252767660 | GOLD_DISPUTED |
| N5_CLEAN | clean control | PASS | run 36252926448 | Valid clean proof |

The required 5/5 gate was therefore **not** met.

## What was actually proven

### N1 — response causality

- blind Sonnet detector found the expected serious family;
- selected span overlapped frozen gold;
- repair scope matched `LOCAL_REPAIR`;
- only detector-authorized sentences changed;
- same-defect recheck passed;
- full-story regression passed;
- no outside-span mutation occurred.

Final changed sentence IDs: `S010`, `S017`.

### N2 — state continuity

- blind Sonnet detector found the expected serious family;
- exact frozen spans `S029`, `S037` were identified;
- repair scope matched `LOCAL_REPAIR`;
- only `S037` changed;
- same-defect recheck passed;
- full-story regression passed.

### N5 — clean control

- primary blind Sonnet audit: zero serious/critical findings;
- family-by-family blind Sonnet confirmation: zero serious/critical findings;
- blind Luna diagnostic adjudication: zero serious/critical findings;
- repair skipped;
- Haiku full-story verification: zero serious/critical findings.

This is evidence that the higher-recall detector path did not automatically mutate the clean control.

## Why N3 is not a qualified detector miss

Frozen gold claimed that after Deniz moved outside the light path, the colors should have returned immediately and their delayed return broke the established causal rule.

However:

- primary blind Sonnet audit found no serious/critical defect;
- independent family-by-family Sonnet audit found no serious/critical defect;
- blind GPT-5.6 Luna adjudication found no serious/critical defect.

The story explicitly introduces a possible change in sunlight/cloud state before the colors return. That makes the original blocking label insufficiently robust for a qualification gold case.

Disposition: **GOLD_DISPUTED — remove from the next proof set; do not tune the detector to this example.**

## Why N4 is not a qualified detector miss

Frozen gold classified the final toy action as a serious `closure_integrity` defect.

After fixing the checklist parser so that `moderate` findings do not crash the run:

- primary blind Sonnet audit found no serious/critical defect;
- independent family-by-family Sonnet audit found no serious/critical defect;
- blind GPT-5.6 Luna adjudication found no serious/critical defect.

The final action may weaken the ending, but the evidence does not support treating it as a robust serious/critical publication blocker.

Disposition: **GOLD_DISPUTED — remove from the next proof set; do not force the model to reproduce the old label.**

## Important system corrections discovered during v1

1. CI job success is not proof PASS; archived result JSON is authoritative.
2. A zero detector result now requires an independent blind family-by-family confirmation.
3. Non-blocking `minor/moderate` checklist findings are ignored rather than treated as parser/runtime errors.
4. Repair authority remains detector-selected spans only; gold spans are scoring-only.
5. Local repair supports bounded retry from same-defect verifier feedback without widening the authorized span.
6. Same-defect recheck is separate from full-story regression.
7. Character misunderstanding is distinguished from narrator/story causal error.
8. Structural repair support exists for future genuinely structural gold cases.

## Next gate

Do **not** resume JEV threshold work, 200-case corpus work, or broad optimization yet.

Create **Natural Defect Repair Proof v1.1** with:

- N1 and N2 retained as validated defect cases;
- N5 retained as clean control;
- N3 and N4 replaced by two independently adjudicated, naturally occurring serious/critical Story V5 defects;
- replacement cases frozen before the repair run;
- exact same detect → span → scope → bounded repair → same-defect recheck → full regression chain;
- success target remains **5/5**.

If the existing frozen source pool cannot supply two unambiguous replacements, generate only the minimum number of new Story V5 outputs required to obtain two independently adjudicated natural positives. Do not turn this into a large-corpus exercise.
