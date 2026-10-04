# SpineForge v21 — Initial Blocking Story Audit

Audit the immutable story for publication-blocking defects. Do not rewrite.

Find only material defects in:
physical feasibility, causal logic, state continuity, epistemic order, spatial consistency, temporal consistency, response causality, closure integrity, canon integrity, age suitability, spine fidelity, narrative coherence.

Routing rules:
- moderate, serious, or critical defects in those families may block;
- minor defects never trigger repair by themselves;
- language/style polish is advisory and must not trigger repair;
- do not hunt for optional improvements;
- do not report a finding whose own explanation says the text is acceptable;
- prefer one finding that describes one causal defect over multiple wording-level symptoms.

For every finding return family, severity, repair_scope, span_ids, exact_text, and reason.
Return JSON only.

Wire format: prose is sent once as a segment table with columns span_id, whitespace_before, current_text. Read current_text in order and use the adjacent span_id for findings. Concatenating whitespace_before + current_text for all rows, then trailing_whitespace, reconstructs the exact original prose field named by replaces_text_field. Approved constraint quotes remain authoritative even when the duplicate canon_invariants list is empty.
