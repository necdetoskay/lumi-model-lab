# SpineForge v21 — Targeted Final Scene Audit

Audit only the repaired scene plus its immutable entry/exit boundaries and supplied Spine/canon invariants.

Do not re-audit untouched parts of the story. They were already audited and are immutable.

Check whether the repaired scene:
- resolves every original blocking defect;
- is physically and causally coherent as one event chain;
- preserves object, character, spatial, temporal, knowledge, and canon state;
- preserves required Spine beats and decisive-action ownership;
- enters from the supplied boundary state and exits into the supplied boundary state.

Minor editorial/style issues are advisory and cannot cause another repair.

Final routing is bounded:
- zero blocking findings -> ACCEPT;
- one or more blocking findings -> REJECT_NON_CONVERGENT.

A second repair is forbidden.
Return JSON only.

Wire format: prose is sent once as a segment table with columns span_id, whitespace_before, current_text. Read current_text in order and use the adjacent span_id for findings. Concatenating whitespace_before + current_text for all rows, then trailing_whitespace, reconstructs the exact original prose field named by replaces_text_field. Approved constraint quotes remain authoritative even when the duplicate canon_invariants list is empty.
