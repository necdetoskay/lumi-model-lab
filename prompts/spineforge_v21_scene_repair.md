# SpineForge v21 — Bounded Scene Repair

Rewrite exactly one bounded scene from an immutable English story.

You receive:
- immutable source story identity and hash;
- one contiguous scene cluster;
- immutable entry and exit boundary context;
- blocking findings only;
- approved Spine obligations and canon invariants;
- non-blocking editorial advisories for awareness only.

Your job is to make the entire scene causally and physically coherent as one event chain.

Hard rules:
- Rewrite the scene as a whole; do not patch findings sentence-by-sentence.
- Preserve premise, scene purpose, character identities, canon, approved branch, and ending intent.
- Preserve every required Spine beat assigned to this scene.
- Do not change text outside the scene cluster.
- Entry state and exit state are immutable contracts.
- Resolve all blocking findings together, including object state, position, cause, action, and consequence.
- Do not optimize for minor stylistic polish.
- Do not introduce a new durable fact, location, item, relationship, or plot branch.
- Return one replacement scene, not individual sentence patches.

Before returning, mentally simulate the scene in order:
1. Where is each character?
2. Where is each relevant object?
3. What is attached to what?
4. What force/action causes each state change?
5. Who performs the required decisive action?
6. Does the resulting state match the immutable exit boundary?

Return JSON only:
{
  "replacement_scene": "complete replacement prose for the bounded scene",
  "resolved_blocking_finding_indexes": [0],
  "preserved_invariants": ["brief invariant"],
  "summary": "brief summary"
}

Wire format: prose is sent once as a segment table with columns span_id, whitespace_before, current_text. Read current_text in order and use the adjacent span_id for findings. Concatenating whitespace_before + current_text for all rows, then trailing_whitespace, reconstructs the exact original prose field named by replaces_text_field. Approved constraint quotes remain authoritative even when the duplicate canon_invariants list is empty.
