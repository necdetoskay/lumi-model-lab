# LUMI English Scene Plan Targeted Repair v1

Repair one existing six-scene LUMI StoryContract + SceneGraph. This is not a request to invent a different story.

You receive:
- the original labeled story brief;
- the current plan;
- deterministic errors, if any;
- JEV continuity evidence;
- Haiku plan scores, scene risks, and critical failures.

Rules:
- Preserve the protagonist, setting, theme, premise, central problem, required constraint IDs, and intended ending.
- Preserve all valid scene purposes and beats unless a supplied repair reason requires a local change.
- Do not replace the story with a new concept.
- Keep exactly six scenes with indexes 1 through 6.
- Keep the decisive solution/payoff in Scene 5; Scene 5 may close the central problem completely and may have open_threads_after=[] when Scene 6 is consequence-only. Scene 6 handles consequences and closure. Keep Scene 6 open_threads_after empty unless the original brief explicitly requires a future-discovery opening; if required, preserve only one bounded hook.
- Make every inference mechanically understandable from earlier evidence.
- If a later object, fact, mechanism, institution, or hook appears, establish enough prior evidence before it is needed.
- If an incorrect assumption must be corrected, explicitly schedule the concrete observation or evidence that corrects it.
- If JEV flags early resolution, move only the decisive resolution material to Scene 5 and preserve earlier investigation.
- If Haiku flags Scene 6 as an arbitrary hook, remove it unless the original brief explicitly requires a future-discovery opening; when required, seed it earlier without creating a second main plot.
- Preserve exact required_constraint_ids C1..Cn and schedule every ID in at least one scene.
- Scenes 2-6 must contain concrete prior_evidence grounded in earlier scenes.
- Keep fields concise. Do not add decorative subplots.

Return JSON only in exactly the same schema as the current plan.
