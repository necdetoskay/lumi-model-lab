from __future__ import annotations

from pathlib import Path
from typing import Any

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19 import run as run_v19
from src.spineforge_v19_obligations import ReaderStoryObligationsV1


DEFAULT_ARCHITECT_PROMPT = Path("prompts/spineforge_v20_narrative_architect.md")


def run(
    *,
    context_pack: SpineContextPackV1,
    obligations: ReaderStoryObligationsV1,
    api_key: str,
    architect_call_fn=None,
    gate_call_fn=None,
    architect_prompt: str | None = None,
    gate_prompt: str | None = None,
) -> dict[str, Any]:
    result = run_v19(
        context_pack=context_pack,
        obligations=obligations,
        api_key=api_key,
        architect_call_fn=architect_call_fn,
        gate_call_fn=gate_call_fn,
        architect_prompt=architect_prompt
        or DEFAULT_ARCHITECT_PROMPT.read_text(encoding="utf-8").strip(),
        gate_prompt=gate_prompt,
    )
    result = dict(result)
    result["schema"] = "spineforge-v20-evidence.v1"
    result["runtime_revision_family"] = "SPINEFORGE-STORY-FIRST-v20"
    result["generation_topology"] = [
        "SONNET_STORY_FIRST_NARRATIVE_SPINE_ARCHITECT",
        "DETERMINISTIC_AUTHORITY_AND_OBLIGATION_VALIDATION",
        "LUNA_COMPACT_ADVERSARIAL_PRODUCT_GATE",
        "STOP_FOR_HUMAN_REVIEW",
    ]
    return result
