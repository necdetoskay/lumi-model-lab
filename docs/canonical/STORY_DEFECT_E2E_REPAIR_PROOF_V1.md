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


## Final runtime proof — run 36248897175

Result: **5/5 PASS**  
Total paid cost: **$0.063909**  
Elapsed model/runtime proof time: **46.947 s**

Evidence branch:

`evidence/story-defect-e2e-repair-proof-36248897175`

Evidence file:

`experiments/results/story-defect-e2e-repair-proof/36248897175/result.json`

### Case results

- **P1 response causality — PASS**
  - blind Sonnet detector found the serious `response_causality` defect at the frozen gold span;
  - minimal repair deleted the unnecessary faulty call/hearing block;
  - Haiku full-story verifier returned zero serious/critical findings.

- **P2 state continuity — PASS**
  - detector found the unexplained object-state reset;
  - minimal repair deleted only the unsupported reset sentence;
  - Haiku returned zero serious/critical findings.

- **P3 physical feasibility — PASS**
  - detector found the impossible solid-glass traversal as critical;
  - bounded repair replaced only that impossible action with an already-supported light interaction;
  - Haiku returned zero serious/critical findings.

- **P4 closure integrity — PASS with independent verifier adjudication**
  - detector found the injected post-closure reopening tail;
  - minimal repair deleted only that tail;
  - the repaired story restored the independently admitted clean source;
  - Haiku nevertheless produced a new closure finding against the restored clean source;
  - independent GPT-5.6 Luna blind verification returned zero serious/critical findings;
  - because the repair restored the frozen admitted-clean story and the second independent verifier did not confirm Haiku's claim, the Haiku finding was recorded as a single-verifier false positive rather than silently accepted or ignored.

- **P5 clean control — PASS**
  - Sonnet detector returned zero serious/critical findings;
  - repair was skipped;
  - Haiku independent verification also returned zero serious/critical findings.

## Runtime lessons frozen by this proof

1. **Detection can be separated from generation.** The frozen generator was not modified.
2. **Local repair is viable.** All repaired cases changed only the bounded defective block; unrelated prose remained byte-for-byte unchanged.
3. **Deletion is often the safest repair.** Response, state, and closure cases were fixed by removing unnecessary defective text rather than inventing new prose.
4. **Repair must not self-certify.** Every repaired full story was checked by another model.
5. **A single verifier is not ground truth.** A verifier false positive occurred on the restored clean closure source.
6. **Verifier disagreement must be explicit.** It may be resolved only through independent evidence/adjudication; it must never be converted silently to PASS.
7. **Clean stories must remain untouched.** The clean control generated no repair call.

## Decision

The focused five-story proof is complete.

This result proves the **mechanical product loop** for the tested defect classes:

`detect -> locate -> bounded local repair -> whole-story reverify -> explicit disagreement handling`.

It does **not** prove universal defect recall or authorize returning immediately to large-corpus threshold optimization.

The next qualification should remain small and understandable: repeat the same loop on **naturally occurring Story V5 defects**, where the broken text was produced by the model rather than synthetically injected.
