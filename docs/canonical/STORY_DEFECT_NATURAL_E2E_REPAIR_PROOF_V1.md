# LUMI — 5-Story Natural Defect Repair Proof v1

Status: **ACTIVE FOCUSED QUALIFICATION**  
Date: 2026-09-26  
Issue: **#217**

## Purpose

The synthetic five-story proof passed 5/5 and proved the mechanics of bounded repair.

This second proof asks a harder question:

> Can the same system repair serious defects that appeared naturally in Story V5 model output, without being told the gold repair location?

Large-corpus/JEV threshold work remains paused.

## Frozen proof set

- N1 — response causality: `src_cohort_a_seed2_03`
- N2 — state continuity: `src_fantastical_guard_02`
- N3 — causal logic: `src_cohort_b_04`
- N4 — closure integrity: `src_cohort_a_04`
- N5 — independently admitted clean control: `src_watering_guard_01`

The defect labels come from the frozen natural-positive review set. They are used only after blind detection to score whether the detector found the expected family and overlapping evidence span.

## Runtime contract

```text
natural full story
      |
      v
blind Sonnet detector
      |
      +-- expected family + overlapping evidence span?
      |             |
      |             v
      |      detector span IDs become
      |        repair authority
      |             |
      |             v
      |      bounded Sonnet repair
      |       only those sentences
      |             |
      |             v
      |      mechanical outside-span
      |         immutability proof
      |             |
      |             v
      |      Haiku full-story verify
      |             |
      |             v
      |            PASS
      |
      +-- clean control -> no repair -> independent verify
```

Gold repair spans are **never** sent to the repair model.

For natural defects there is no synthetic clean-source restoration shortcut. If the post-repair verifier still reports a serious/critical defect, the case does not silently pass. A second independent model may be recorded as adjudication evidence, but unresolved disagreement remains FAIL/manual.

## Success gate

Exact target: **5/5 PASS**.

A lower result is useful evidence, not a reason to relax the gate. Failed cases are inspected to determine whether the problem belongs to detection, repair scope, repair generation, or verifier reliability.
