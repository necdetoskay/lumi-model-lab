# LUMI English Story Scene Planner v1

You are creating the immutable narrative plan for one LUMI story.
Write the plan in English. The six scenes are one causal story, not independent mini-stories.

Rules:
- Preserve every fact and constraint in the brief. Every required constraint is labeled C1, C2, ...; copy those IDs exactly into story_contract.required_constraint_ids and schedule every ID in at least one scene.constraint_ids.
- Keep one central protagonist goal and one central problem from Scene 1 through Scene 6.
- Every scene starts from the state produced by the previous scene.
- Every scene must materially cause, enable, or constrain the next scene.
- Clues, observations, decisions, and consequences must accumulate; do not reset knowledge.
- Do not fully solve the central problem before Scene 5.
- Scene 5 contains the decisive application/payoff.
- Scene 6 resolves consequences and closes the main thread. Leave open_threads_after empty unless the story brief explicitly requires a future-discovery opening; if it does, keep only one small bounded hook.
- Do not introduce disposable characters, objects, locations, facts, powers, or subplots.
- Each handoff states the concrete unresolved state inherited by the next scene.
- For Scenes 2-6, prior_evidence must name concrete setup already established in earlier scenes for any inference, clue, object, or fact the scene depends on.
- must_not_do explicitly protects against contradiction, premature resolution, or later-scene leakage.
- Keep the plan concise: purpose/entry_state/handoff should each be at most 30 words; each beat, must_include, must_not_do, and prior_evidence item should be at most 24 words.
- Use 2-3 beats per scene and no more than 3 prior_evidence items per scene.

Return JSON only with this shape:
{
  "story_title": "",
  "story_contract": {
    "protagonist_goal": "",
    "central_problem": "",
    "solution_principle": "",
    "theme_thread": "",
    "ending_state": "",
    "required_constraint_ids": ["C1"],
    "prohibited_events": [""]
  },
  "scenes": [
    {
      "index": 1,
      "purpose": "",
      "entry_state": "",
      "beats": ["", ""],
      "must_include": [""],
      "must_not_do": [""],
      "constraint_ids": ["C1"],
      "prior_evidence": [""],
      "handoff": "",
      "open_threads_after": [""]
    }
  ]
}

Return exactly six scene objects with indexes 1 through 6.