from __future__ import annotations

import json
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.generate import count_words
from src.storyforge import StoryForgeRequest
from src.storyforge import runtime as storyforge_runtime
from src.storyforge.runtime import StoryForgeTraceError

PROFILE = Path("configs/storyforge/lsf_a12_w1000_v0_1_exp.yaml")
REQUEST = Path("experiments/fixtures/storyforge_age12_dinosaur_engineering_probe_20260928.json")
OUT = Path("runs/storyforge-age12-probe/result.json")


def _load_experimental_profile(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "lumi-storyforge-profile.v1":
        raise RuntimeError("Unsupported StoryForge profile schema.")
    if payload.get("profile_id") != "LSF-A12-W1000-v0.1-exp":
        raise RuntimeError("Unexpected experimental StoryForge profile.")
    return payload


def main() -> None:
    load_dotenv()
    request = StoryForgeRequest.model_validate_json(REQUEST.read_text(encoding="utf-8"))

    original_loader = storyforge_runtime._load_profile
    storyforge_runtime._load_profile = _load_experimental_profile
    try:
        try:
            result = storyforge_runtime.run_storyforge(request, profile_path=PROFILE)
        except StoryForgeTraceError as exc:
            failure = {
                "profile_id": "LSF-A12-W1000-v0.1-exp",
                "request_id": request.request_id,
                "status": "trace_failure",
                "publication_ready": False,
                "failure": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "stage": exc.trace.get("stage"),
                },
                "trace": exc.trace,
            }
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            story = str(exc.trace.get("english_story") or "")
            if story:
                (OUT.parent / "english.txt").write_text(story + "\n", encoding="utf-8")
            print(json.dumps(failure, ensure_ascii=False, indent=2))
            raise
    finally:
        storyforge_runtime._load_profile = original_loader

    payload = result.model_dump(mode="json")
    payload["comparison_metrics"] = {
        "english_word_count": count_words(result.english_story or ""),
        "turkish_word_count": count_words(result.turkish_story or ""),
        "target_words": request.generation_profile.target_words,
        "preferred_range": list(request.generation_profile.preferred_range),
        "hard_range": list(request.generation_profile.hard_range),
        "exact_age": request.generation_profile.exact_age,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result.english_story:
        (OUT.parent / "english.txt").write_text(result.english_story + "\n", encoding="utf-8")
    if result.turkish_story:
        (OUT.parent / "turkish.txt").write_text(result.turkish_story + "\n", encoding="utf-8")

    print(json.dumps({
        "profile_id": result.profile_id,
        "status": result.status,
        "publication_ready": result.publication_ready,
        "comparison_metrics": payload["comparison_metrics"],
        "story_gate": result.evidence.get("story_gate"),
        "fidelity_gate": result.evidence.get("fidelity_gate"),
        "cost_usd": result.evidence.get("cost_usd"),
        "elapsed_seconds": result.evidence.get("elapsed_seconds"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
