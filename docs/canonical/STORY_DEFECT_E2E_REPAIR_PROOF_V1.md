# LUMI — 5-Story End-to-End Repair Proof v1

Status: **ACTIVE FOCUSED QUALIFICATION**  
Date: 2026-09-26  
Issue: #216

## Decision

Large-corpus/JEV threshold work is paused.

The immediate product question is smaller and more important:

> Can LUMI reliably find a serious story defect, change only the broken local span, and independently prove that the repaired full story is clean?

The proof uses four independently validated serious defect cases from D1 plus one independently admitted clean story.

## Frozen proof set

- P1 — response causality
- P2 — state continuity
- P3 — physical feasibility
- P4 — closure integrity
- P5 — clean control

Canonical fixture:

`experiments/fixtures/story_defect_e2e_repair_proof.v1.json`

## Runtime chain

```text
full story
   |
   v
blind strong detector (Sonnet 5)
   |
   +-- clean -> NO REPAIR
   |
   +-- serious defect + exact span
              |
              v
       bounded local repair
       exact target block only
              |
              v
    mechanically prove outside
      target block unchanged
              |
              v
 blind independent full-story
 verifier (Haiku 4.5)
              |
              v
             PASS
```

Gold labels are never sent to the detector or post-repair verifier. They are used only after the call to score whether the detector found the expected defect.

## Local repair invariant

The repair model cannot rewrite the story.

For defective cases, the harness extracts the exact injected defective block from the frozen corpus. The model returns only replacement text for that block. The harness performs exactly one deterministic string replacement.

Therefore all prose outside the target block remains byte-for-byte unchanged.

## Pass gate

All five cases must pass.

For each defect case:

1. detector finds the expected family;
2. detector span overlaps frozen gold span;
3. only target block changes;
4. independent full-story verifier finds zero serious/critical semantic defects.

For clean control:

1. detector finds zero serious/critical semantic defects;
2. repair is skipped;
3. independent verifier also finds zero serious/critical semantic defects.

A 4/5 or 3/5 result is not hidden. The failed case is inspected and the runtime policy is improved before scale work resumes.
