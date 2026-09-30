from __future__ import annotations

from pathlib import Path

ARCHITECT = Path("prompts/spineforge_roleplay_architect_v12.md")
AUDITOR = Path("prompts/spineforge_roleplay_auditor_v12.md")


def test_v12_architect_prompt_has_full_prompt_architecture() -> None:
    text = ARCHITECT.read_text(encoding="utf-8")
    required = [
        "## 1. ROLE",
        "## 2. MISSION",
        "## 3. INPUT AUTHORITY",
        "## 4. PRIMARY DESIGN PRINCIPLE: STORY FIRST, CONTRACT SECOND",
        "## 5. EXPERIENCE CONTRACT — NON-NEGOTIABLE",
        "## 6. AGE AND MATURITY",
        "## 7. CAUSALITY",
        "## 9. MYSTERY AND EVIDENCE DISCIPLINE",
        "## 10. DECISION QUALITY",
        "## 11. CLIMAX",
        "## 12. LOCAL PAYOFF",
        "## 14. SAGA DISCIPLINE",
        "## 15. OUTPUT FIELD DESIGN GUIDE",
        "## 16. ANTI-PATTERN LIBRARY",
        "## 17. INTERNAL QUALITY CONTROL",
        "## 18. FINAL OUTPUT RULES",
    ]
    for phrase in required:
        assert phrase in text


def test_v12_architect_prompt_contains_roleplay_and_bad_examples() -> None:
    text = ARCHITECT.read_text(encoding="utf-8")
    required = [
        "at least **three distinct modes of meaningful protagonist engagement**",
        "The protagonist must materially cause the story to move",
        "BAD:",
        "BETTER:",
        "Bad causality example",
        "Bad reversal example",
        "Bad decision example",
        "Bad climax example",
        "Generic fantasy skin",
        "Childish maturity",
        "Writer dependency",
        "Return **JSON only**",
    ]
    for phrase in required:
        assert phrase in text


def test_v12_auditor_is_adversarial_and_evidence_based() -> None:
    text = AUDITOR.read_text(encoding="utf-8")
    required = [
        "senior adversarial Story Spine Editor",
        "ACCEPT must be earned",
        "BURDEN OF PROOF",
        "ROLEPLAY_POTENTIAL",
        "CHARACTER_DRIVENNESS",
        "AUTHORITY_SAFETY",
        "SPECIFIC ANTI-PATTERNS TO HUNT",
        "BAD VS ACCEPTABLE EXAMPLES",
        "REPAIR TARGET QUALITY",
        "ACCEPTANCE RULE",
    ]
    for phrase in required:
        assert phrase in text


def test_v12_prompt_budget_is_deliberate_not_unbounded() -> None:
    architect_words = len(ARCHITECT.read_text(encoding="utf-8").split())
    auditor_words = len(AUDITOR.read_text(encoding="utf-8").split())
    assert 1800 <= architect_words <= 6000
    assert 900 <= auditor_words <= 4000
