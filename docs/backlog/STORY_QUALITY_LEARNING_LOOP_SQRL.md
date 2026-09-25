# Backlog — Story Quality Learning Loop (SQRL)

Status: BACKLOG / research required before implementation
Added: 2026-09-25
Do not activate in production from this document alone.

## Goal

Turn post-generation quality evidence into controlled improvements to story writer profiles without allowing production observations to mutate active prompts directly.

Proposed loop:

Observe -> Normalize -> Aggregate -> Propose -> Regression Test -> Promote -> Monitor -> Rollback

Potential segmentation:
model x language x exact-age/age-band x story-type x length-band x failure-pattern

Research questions:
- sampling strategy for expensive independent editorial audits in production
- recurrence/confidence thresholds for promotion candidates
- negative constraints vs positive craft rules
- regression corpus design and non-regression criteria
- profile versioning, canarying, rollback and audit provenance
- preventing prompt bloat, contradictory rules and overfitting
- cost controls and risk-triggered audit escalation
- how human/editor feedback enters the same normalized evidence model

Non-negotiable safety/quality invariant:

Production observations may propose learning; production observations may never directly mutate the active writer profile.

Promotion requires offline regression evidence and explicit governed profile/version promotion.
