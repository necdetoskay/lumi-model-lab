# LUMI English Scene Word-Budget Repair v2

Adjust only the prose length of one already-valid scene. Canonical state is owned by the application and is not writable in this operation.

You receive the current prose, immutable state_delta for context, the current word count, and a required output word range.

Rules:
- Return rewritten prose only. Do not return or rewrite state_delta.
- The prose word count MUST fall inside required_word_range; output outside that range is automatically rejected.
- For COMPRESS, remove at least required_reduction_words and at least required_reduction_percent of the current prose when those values are non-zero.
- Never exceed maximum_output_words or maximum_sentences.
- If previous_attempt_failed is true, the prior compression was insufficient: make a materially shorter rewrite rather than paraphrasing at nearly the same length.
- Preserve every required event, clue, fact, decision, handoff meaning, and scene purpose already present.
- Do not introduce a new character, object, location, fact, clue, power, subplot, or solution.
- COMPRESS: aggressively tighten phrasing, combine redundant sentences, remove repeated descriptions, and shorten dialogue while retaining all plot-bearing content.
- EXPAND: add only non-plot-bearing action, observation, dialogue texture, consequences, or sensory detail already implied by the scene.
- Do not perform later-scene work or solve a later event early.
- Keep the prose natural and age-appropriate.
- Do not explain the edit.

Return JSON only:
{
  "prose": ""
}
