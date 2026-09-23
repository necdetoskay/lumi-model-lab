# LUMI Scene Plan Continuity Judge v1

Evaluate an English six-scene LUMI story plan before any scene prose is written.

Score every criterion from 1 to 5:
- causal_continuity: each scene follows from the previous state and materially enables the next;
- protagonist_goal_continuity: the protagonist's goal remains stable and actions are motivated by it;
- constraint_coverage: every important brief constraint is preserved and scheduled;
- information_progression: clues, knowledge, decisions, and consequences accumulate without resets or redundant mini-stories;
- no_unexplained_dependencies: later events do not depend on unexplained new characters, objects, locations, facts, or powers;
- no_early_resolution: the central problem is not fully solved before Scene 5;
- ending_coherence: Scene 5 delivers the decisive payoff and Scene 6 resolves consequences consistently.

Critical failures:
- contradiction with an earlier established state;
- a required brief constraint cannot be satisfied from the plan;
- central problem solved before Scene 5;
- unexplained dependency that is necessary for a later scene;
- six scenes function as disconnected episodes rather than one story.

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