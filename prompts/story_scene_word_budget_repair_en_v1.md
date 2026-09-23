# LUMI English Scene Word-Budget Repair v1

Adjust only the prose length of one already-valid scene envelope.

This is not a story rewrite and not a continuity repair.

Rules:
- Preserve state_delta exactly. Every field and list item must remain unchanged.
- Preserve every required event, clue, fact, decision, handoff, and scene purpose.
- Do not introduce a new character, object, location, fact, clue, power, subplot, or solution.
- If mode is COMPRESS, shorten wording, combine redundant sentences, remove repeated sensory detail, and tighten dialogue without deleting required events.
- If mode is EXPAND, add only non-plot-bearing action, observation, dialogue texture, consequences, or sensory detail that is already implied by the scene.
- Aim for the preferred word range, not the hard boundary.
- Never modify later-scene work or solve a later event early.
- Keep the prose natural and age-appropriate.

Return JSON only using exactly the same scene-envelope shape:
{
  "prose": "",
  "state_delta": {
    "location": "",
    "character_goal": "",
    "knowledge_gained": [""],
    "facts_established": [""],
    "clues_added": [""],
    "objects_changed": [""],
    "relationships_changed": [""],
    "threads_opened": [""],
    "threads_resolved": [""],
    "handoff_state": ""
  }
}
