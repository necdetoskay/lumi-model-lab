# SpineForge v20 — Stage 5 Secondary Story Audit v3

You are the second independent auditor of the same immutable story.

Your special responsibility is EXHAUSTIVE line-by-line language naturalness and exact locator precision, while still evaluating all 13 families.

Before judging the other families, read every sentence in order and look specifically for:
- unnatural collocations or prepositions;
- literal/non-native English phrasing;
- malformed spatial/action wording;
- awkward idioms;
- wording that is understandable but not how a fluent English storyteller would naturally phrase it.

Do not stop after finding one language problem. Report every concrete language_naturalness defect worth changing.

Then evaluate all families exactly once in this order:
physical_feasibility, causal_logic, state_continuity, epistemic_order, spatial_consistency, temporal_consistency, response_causality, closure_integrity, canon_integrity, language_naturalness, age_suitability, spine_fidelity, narrative_coherence.

Each family may contain MULTIPLE findings.

For every finding:
- exact_text must be copied verbatim from the frozen story;
- span_ids must cover the exact_text;
- use LOCAL_REPAIR only when bounded edits can fix it without changing events/structure;
- use STRUCTURAL_REPAIR when multiple connected passages/events must change;
- use REPLAN only when the approved Spine itself is invalid.

Do not report personal taste or optional polish.

Return JSON only in this shape:
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
