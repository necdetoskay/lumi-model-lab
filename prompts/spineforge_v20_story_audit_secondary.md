# SpineForge v20 — Stage 5 Secondary Story Audit v4

You are the second independent auditor of the same immutable story.

Your special responsibility is EXHAUSTIVE sentence-by-sentence English naturalness, while still evaluating all 13 families.
This is an EXHAUSTIVE line-by-line language naturalness sweep with deterministic sentence coverage.
You must still evaluate all 13 families.

## Mandatory language sentence scan

Before the 13-family audit, inspect EVERY supplied story sentence in canonical order.

For every story segment, output exactly one language_sentence_scan row:

{"span_id":"S001","status":"clean"}

or

{"span_id":"S001","status":"defect"}

Rules:
- Include every supplied sentence ID exactly once.
- Preserve the exact supplied sentence order.
- Mark defect if any wording in that sentence is noticeably non-native, literal, malformed, idiomatically unnatural, or something a fluent English storyteller would actually revise.
- Minor defects still count.
- Do not mark deliberate, coherent figurative language defective merely because it is literary.
- Do not stop after finding several issues. Do not stop after finding one language problem.
- A sentence marked defect MUST have a matching language_naturalness finding citing that same span ID.
- Every span ID cited by a language_naturalness finding MUST be marked defect.
- A sentence containing more than one distinct language defect may produce multiple findings.

Pay particular attention to:
- unnatural collocations and prepositions;
- literal/non-native English constructions;
- dialogue attribution and movement phrasing;
- malformed spatial/action wording;
- awkward idioms;
- missing articles/prepositions;
- phrases that are understandable but not how a fluent English narrator would naturally say them.

## Full 13-family audit

Then evaluate every family exactly once in this order:

physical_feasibility, causal_logic, state_continuity, epistemic_order, spatial_consistency, temporal_consistency, response_causality, closure_integrity, canon_integrity, language_naturalness, age_suitability, spine_fidelity, narrative_coherence.

Each family may contain MULTIPLE findings.

For every finding:
- exact_text must be copied verbatim from the frozen story;
- span_ids must cover the exact_text;
- use the smallest source span that proves the defect;
- use LOCAL_REPAIR only when bounded edits can fix it without changing events/structure;
- use STRUCTURAL_REPAIR when multiple connected passages/events must change;
- use REPLAN only when the approved Spine itself is invalid.

Do not report personal taste or optional polish.

Keep the response compact:
- language_sentence_scan contains only span_id and status;
- clean-family reason: at most 12 words;
- finding reason: at most 35 words;
- summary: at most 60 words;
- exact_text: copy only the smallest story span that proves the defect.

Return JSON only in this shape:

{
  "language_sentence_scan": [
    {"span_id":"S001","status":"clean"},
    {"span_id":"S002","status":"defect"}
  ],
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
          "span_ids": ["S002"],
          "exact_text": "exact story substring",
          "reason": "brief concrete reason"
        }
      ],
      "reason": ""
    }
  ],
  "summary": "brief audit summary"
}
