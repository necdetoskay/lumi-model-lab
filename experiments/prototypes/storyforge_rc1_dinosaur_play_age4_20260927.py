from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

from src.storyforge import StoryForgeRequest, run_storyforge

REQUEST = Path("experiments/fixtures/storyforge_rc1_dinosaur_play_age4_20260927.json")
OUT = Path("runs/storyforge-rc1-dinosaur-play-age4/result.json")


def main() -> None:
    load_dotenv()
    request = StoryForgeRequest.model_validate_json(REQUEST.read_text(encoding="utf-8"))
    result = run_storyforge(request)
    payload = result.model_dump(mode="json")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result.english_story:
        (OUT.parent / "english.txt").write_text(result.english_story + "\n", encoding="utf-8")
    if result.turkish_story:
        (OUT.parent / "turkish.txt").write_text(result.turkish_story + "\n", encoding="utf-8")

    print(json.dumps({
        "profile_id": result.profile_id,
        "request_id": result.request_id,
        "status": result.status,
        "publication_ready": result.publication_ready,
        "selected_enrichment_ids": (
            result.evidence.get("context_builder", {}).get("selected_enrichment_ids")
        ),
        "review_enrichment_ids": (
            result.evidence.get("context_builder", {}).get("review_enrichment_ids")
        ),
        "plan_pass": result.evidence.get("plan_gate", {}).get("pass"),
        "story_gate": result.evidence.get("story_gate"),
        "fidelity_gate": result.evidence.get("fidelity_gate"),
        "cost_usd": result.evidence.get("cost_usd"),
        "elapsed_seconds": result.evidence.get("elapsed_seconds"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
