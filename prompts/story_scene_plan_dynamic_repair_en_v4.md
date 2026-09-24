# LUMI Dynamic Narrative Architect Targeted Repair v4

Repair the existing StoryContract + variable-length SceneGraph. Do not invent a different story.

You receive the original story brief, current plan, deterministic errors, JEV continuity evidence, and Haiku plan-judge evidence.

Rules:
- Preserve the protagonist, setting, theme, premise, central problem, required constraint IDs, and intended ending.
- Preserve valid scene purposes and beats unless a repair reason requires changing them.
- Scene count may change only when the evidence shows that the current decomposition itself is a defect: redundant scene, overloaded scene, missing causal step, pacing gap, premature payoff, or insufficient resolution.
- Keep 2-12 scenes with contiguous indexes starting at 1.
- Every scene must have a unique useful narrative job.
- Exactly one scene must have narrative_role "PAYOFF".
- The final scene must have narrative_role "RESOLUTION"; PAYOFF must occur before it.
- Every scene must have a positive integer relative_weight.
- Preserve exact required_constraint_ids C1..Cn and schedule every ID at least once.
- Later dependencies must be grounded in prior_evidence.
- Remove redundant narrative repetition rather than cosmetically rewording it.
- Do not optimize for a particular scene count.

Return JSON only using exactly the same schema as the current dynamic plan.
