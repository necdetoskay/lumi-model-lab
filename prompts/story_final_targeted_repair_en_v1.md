# LUMI English Final Targeted Scene Polish v1

Repair only the prose of one already-accepted scene to address one final Haiku repair target.

This is a bounded polish operation, not a rewrite.

Rules:
- Preserve the immutable StoryContract and SceneGraph.
- Preserve the scene's state_delta exactly. Every field and list item in state_delta must remain unchanged.
- Preserve the scene's handoff, established facts, clues, objects, relationships, opened threads, and resolved threads.
- Do not introduce a new plot event, character, object, location, fact, clue, power, or solution.
- Do not remove any required event.
- Change only wording or add the smallest explanatory/observational sentence needed to resolve the supplied repair issue.
- Keep the repaired prose within the supplied scene word range.
- Preserve age appropriateness and the existing narrative voice.
- Never modify later scenes or solve a later scene's work early.

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
