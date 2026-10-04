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
