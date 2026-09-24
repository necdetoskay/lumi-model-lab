# LUMI English Final Targeted Scene Polish v1

Repair only the prose of one already-accepted repair scene to address one final Haiku repair target. The defect may be observed in a later scene; when that happens, add only the smallest earlier setup/foreshadowing needed to make the later moment earned.

This is a bounded polish operation, not a rewrite.

Rules:
- Preserve the immutable StoryContract and SceneGraph.
- Preserve the scene's state_delta exactly. Every field and list item in state_delta must remain unchanged.
- Preserve the scene's handoff, established facts, clues, objects, relationships, opened threads, and resolved threads.
- Do not introduce a new plot event, character, object, location, fact, clue, power, or solution.
- Do not remove any required event.
- Change only wording or add the smallest explanatory/observational sentence needed to resolve the supplied repair issue.
- Treat repair_issue as an acceptance contract, not a suggestion. If it quotes misleading, contradictory, or ambiguous wording, remove or rewrite that wording at its first occurrence; do not leave the cited wording unchanged and rely on a later sentence to clarify it.
- If repair_issue supplies a recommended replacement or an explicit intended meaning, implement that meaning directly unless doing so would violate immutable state.
- On strict_retry=true, assume the previous polish was judged insufficient. Make the smallest stronger wording change that eliminates the exact residual ambiguity; do not merely paraphrase the previous repair.
- Before returning, self-check the repaired prose against repair_issue and ensure a careful reader cannot still make the interpretation the judge flagged.
- Never duplicate an adjacent passage or sentence sequence while polishing. If prior_attempt_errors reports final_repair_adjacent_duplicate_sequence, remove the repeated copy and return one canonical occurrence only.
- Treat prior_attempt_errors as binding feedback from the previous bounded attempt; correct those errors instead of repeating the same edit.
- Keep the repaired prose within the supplied scene word range.
- Preserve age appropriateness and the existing narrative voice.
- Never modify later scenes or solve a later scene's work early.
- When observed_scene_context is supplied, use it only to understand the later defect; edit only the current repair scene.
- If repairing earlier setup, add only information that is compatible with existing canon and already implied by the immutable SceneGraph; do not create a new clue, object, rule, or plot event.
- You may make an already-implied relationship between existing facts, clues, observations, or actions explicit in narration or dialogue. This is clarification, not a new fact, when every component already exists in the immutable state/SceneGraph.
- For a missing causal bridge, recognition, or reasoning step, state the relationship directly before the dependent action or handoff. Do not rely on the reader to infer the exact connection the judge flagged.
- For temporal ambiguity, rewrite the local sequence so prerequisite actions visibly occur before their consequence.

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
