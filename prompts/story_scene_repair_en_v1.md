# LUMI English Scene Local Repair v1

Repair exactly one scene while preserving the immutable StoryContract, SceneGraph, already-accepted ContinuityLedger, and all valid events in the scene.

You receive the current scene envelope and explicit repair reasons.

Rules:
- Change only what is necessary to satisfy the repair reasons.
- Never alter StoryContract facts, the current scene purpose, or events reserved for later scenes.
- Never introduce a new character, object, location, fact, or power without established prior evidence.
- Preserve valid clues, facts, and handoff intent.
- If the scene is too short, expand action, observation, dialogue, consequences, or sensory detail without adding new plot events.
- If too long, compress phrasing and redundant detail without deleting required events.
- If continuity is weak, repair setup/payoff links using only facts already available in the ledger or SceneContract.
- Keep the prose natural and age-appropriate.

Return the same JSON shape as the scene writer:
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
