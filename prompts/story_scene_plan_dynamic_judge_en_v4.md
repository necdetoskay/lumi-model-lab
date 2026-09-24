# LUMI Dynamic SceneGraph Judge v4

Evaluate an English LUMI StoryContract + variable-length SceneGraph before prose is written. The scene count is chosen by the Narrative Architect and must be judged for fitness, not against a preferred fixed number.

Score each criterion 1-5:
- causal_continuity: each scene follows from accepted prior state and materially enables, constrains, or resolves later work;
- protagonist_goal_continuity: the protagonist's central goal remains coherent;
- constraint_coverage: required brief constraints are preserved and schedulable;
- information_progression: clues, knowledge, decisions, and consequences accumulate without reset or redundant mini-stories;
- no_unexplained_dependencies: later events rely only on established or explicitly scheduled setup;
- no_early_resolution: the decisive solution is not completed before the scene labeled PAYOFF;
- ending_coherence: PAYOFF is earned, the final RESOLUTION follows from it, and the main thread closes coherently.

Also assess whether the chosen scene decomposition is structurally justified. A scene count is defective only when scenes are redundant, microscopically fragmented, overloaded with incompatible jobs, or missing a causal step. Do not penalize a plan merely for having more or fewer scenes than another story.

Critical failures:
- contradiction with earlier state;
- a required constraint cannot be satisfied;
- decisive resolution before PAYOFF;
- unexplained dependency required for a later scene;
- redundant/disconnected episodes rather than one story;
- no valid PAYOFF followed by final RESOLUTION.

Return JSON only:
{
  "scores": {
    "causal_continuity": 1,
    "protagonist_goal_continuity": 1,
    "constraint_coverage": 1,
    "information_progression": 1,
    "no_unexplained_dependencies": 1,
    "no_early_resolution": 1,
    "ending_coherence": 1
  },
  "critical_failures": [],
  "scene_risks": [{"scene": 1, "risk": ""}],
  "summary": ""
}
