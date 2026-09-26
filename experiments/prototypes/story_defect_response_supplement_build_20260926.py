from __future__ import annotations

import json
from pathlib import Path

from src.story_defect_corpus import build_mutation_source_rows
from src.story_defect_detection import segment_story

OUT = Path("experiments/fixtures/story_defect_response_supplement.tr-age4.v1.json")

VARIANTS = [
    "Deniz'in hemen yanında küçük bir zil yüksek sesle çaldı. Deniz iki eli dolu olduğu için zilin sesini duyamadı.",
    "Yakındaki küçük çan net ve yüksek bir ses çıkardı. Deniz iki eli dolu olduğu için bu sesi işitemedi.",
    "Deniz'in yanı başında küçük bir zil çaldı. Deniz elleri dolu olduğu için sesi duyamadı.",
]


def inject(story: str, paragraph: str) -> str:
    paragraphs = story.split("\n\n")
    index = 1 if len(paragraphs) > 1 else len(paragraphs)
    paragraphs.insert(index, paragraph)
    return "\n\n".join(paragraphs)


def span_ids(story: str, paragraph: str) -> list[str]:
    parts = [row["text"] for row in segment_story(paragraph)]
    rows = segment_story(story)
    found: list[str] = []
    for part in parts:
        matches = [row["id"] for row in rows if part in row["text"]]
        if len(matches) != 1:
            raise RuntimeError(f"response_span_not_unique:{part!r}:{matches}")
        found.extend(matches)
    return sorted(set(found))


def main() -> None:
    sources = build_mutation_source_rows()
    cases = []
    for index, source in enumerate(sources):
        paragraph = VARIANTS[index % len(VARIANTS)]
        text = inject(source["story"], paragraph)
        cases.append({
            "case_id": f"{source['source_id']}__response_busy_hands_hearing_supplement",
            "source_id": source["source_id"],
            "family": source["family"],
            "dataset_split": source["dataset_split"],
            "text": text,
            "mutation": {
                "recipe_id": "response_busy_hands_hearing_supplement",
                "injected_text": paragraph,
                "controlled_single_defect": True,
            },
            "gold": {
                "defect_present": True,
                "family": "response_causality",
                "severity": "serious",
                "span_ids": span_ids(text, paragraph),
                "repair_scope": "LOCAL_REPAIR",
                "validation_status": "PENDING_INDEPENDENT_VALIDATION",
            },
        })

    payload = {
        "schema_version": "story-defect-response-supplement.v1",
        "status": "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION",
        "qualification_evidence": False,
        "purpose": "Raise independently validated response_causality coverage above D1 priority-family minimum.",
        "source_count": len(sources),
        "case_count": len(cases),
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "case_count": len(cases),
        "calibration": sum(1 for c in cases if c["dataset_split"] == "calibration"),
        "held_out": sum(1 for c in cases if c["dataset_split"] == "held_out"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
