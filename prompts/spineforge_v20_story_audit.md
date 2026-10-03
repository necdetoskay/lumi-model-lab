# SpineForge v20 — Stage 5 Primary Story Audit v3

Audit the frozen finished story. Do not rewrite it.

You receive the immutable Writer artifact identity, a deterministic reveal-safe authority projection, the approved NarrativeSpine, and sentence segments.

Evaluate these 13 families exactly once and in this exact order:
physical_feasibility, causal_logic, state_continuity, epistemic_order, spatial_consistency, temporal_consistency, response_causality, closure_integrity, canon_integrity, language_naturalness, age_suitability, spine_fidelity, narrative_coherence.

The user payload also contains required_evaluation_families and required_evaluation_family_count. They are a hard output contract. Before returning JSON, verify that evaluations has exactly 13 rows, in exactly that order, with no omitted, duplicated, or extra family. Never stop after canon_integrity; the final four families are mandatory.

Each family may contain MULTIPLE concrete findings. Do not stop after the first defect in a family.

A finding must be something that should actually be changed. Do not report personal taste, harmless optional polish, compatible interpretations, or a point whose own explanation says it is acceptable.

For language_naturalness, inspect every sentence for non-native, literal, malformed, awkward, or idiomatically unnatural English. Intentional figurative language is not automatically a defect.

Repair scope:
- LOCAL_REPAIR: bounded exact-span edits can fix it without changing story events, canon, branch choice, or structure.
- STRUCTURAL_REPAIR: multiple passages/events need restructuring while the approved Spine remains valid.
- REPLAN: the approved Spine/path itself is invalid.
- NO_REPAIR: rarely; prefer present=false if no change is needed.

Severity: minor, moderate, serious, critical.

Every concrete finding requires:
- severity
- repair_scope
- span_ids
- exact_text copied verbatim from the frozen story
- concrete reason

Keep the response compact:
- clean-family reason: at most 12 words;
- finding reason: at most 35 words;
- summary: at most 60 words;
- exact_text: copy only the smallest story span that proves the defect.

Return JSON only:
{
  "evaluations": [
    {
      "family": "physical_feasibility",
      "present": false,
      "findings": [],
      "reason": "brief clean reason"
    },
    {
      "family": "language_naturalness",
      "present": true,
      "findings": [
        {
          "severity": "minor",
          "repair_scope": "LOCAL_REPAIR",
          "span_ids": ["S001"],
          "exact_text": "exact story substring",
          "reason": "brief concrete reason"
        }
      ],
      "reason": ""
    }
  ],
  "summary": "brief audit summary"
}
