Repair material defects in one existing English story, preserving its human-approved plot.
You may change only allowed_span_ids. These may occur in different scenes.
Return patches with exact old_text and replacement_text for each necessary change.
old_text may be the whole current_text or one exact substring occurring only once inside
the allowed span. Everything outside that substring is automatically preserved.
Keep each replacement within its sentence or dialogue span; no newlines or scene markers.
Do not rewrite the rest of the story, invent a new route, ability, equipment, reward, or ending.
Use the full story to check interactions; preserve voice and ordinary age-12 adventure dialogue.
Treat findings as evidence to evaluate against approved_plan, not unquestionable commands.
Distinguish dimensions constrained by the plan from those left unspecified. A failed
attempt is not evidence that the attempted action succeeded. Repair genuine contradictions
consistently in all allowed spans that need changes.
For later findings, repair causal/geographic/closure contradictions with the smallest changes
that preserve the approved events. Return JSON only. No claim that the story is accepted.
Wire prose is a table: concatenate whitespace_before + current_text, then trailing_whitespace.
