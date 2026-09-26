from __future__ import annotations

import json
from pathlib import Path

from src.story_defect_corpus import build_mutation_source_rows
from src.story_defect_detection import segment_story

OUT = Path("experiments/fixtures/story_defect_response_supplement.tr-age4.v2.json")

VARIANTS = [
    "Tam o sırada Deniz'in hemen yanında küçük bir zil çaldı. Deniz iki eli dolu olduğu için zilin sesini duyamadı. Ellerindekileri yere bırakınca zil yeniden çaldı; bu kez sesi duyup başını çevirdi.",
    "Yakındaki küçük çan net ve yüksek bir ses çıkardı. Deniz elleri dolu olduğu için bu sesi işitemedi. Ellerini boşaltınca çan bir kez daha çaldı ve Deniz hemen sese döndü.",
    "Deniz'in yanı başında küçük bir zil çaldı. Deniz iki eli de dolu olduğu için sesi duyamadı. Ellerindekileri bıraktığında zil yeniden çaldı; bu kez sesi duydu ve başını çevirdi.",
]


def inject_after_anchor(story: str, paragraph: str, source_index: int) -> str:
    paragraphs = story.split("\n\n")
    if len(paragraphs) <= 2:
        index = 1
    else:
        # Keep the self-contained event inside the story rather than before setup.
        index = 1 + (source_index % max(1, min(3, len(paragraphs) - 1)))
    paragraphs.insert(index, paragraph)
    return "\n\n".join(paragraphs)


def span_ids(story: str, paragraph: str) -> list[str]:
    parts = [row["text"] for row in segment_story(paragraph)]
    rows = segment_story(story)
    found: list[str] = []
    for part in parts:
        matches = [row["id"] for row in rows if part in row["text"]]
        if len(matches) != 1:
            raise RuntimeError(f"response_v2_span_not_unique:{part!r}:{matches}")
        found.extend(matches)
    return sorted(set(found))


def main() -> None:
    sources = build_mutation_source_rows()
    cases = []
    for index, source in enumerate(sources):
        paragraph = VARIANTS[index % len(VARIANTS)]
        text = inject_after_anchor(source["story"], paragraph, index)
        cases.append({
            "case_id": f"{source['source_id']}__response_busy_hands_hearing_supplement_v2",
            "source_id": source["source_id"],
            "family": source["family"],
            "dataset_split": source["dataset_split"],
            "text": text,
            "mutation": {
                "recipe_id": "response_busy_hands_hearing_supplement_v2",
                "injected_text": paragraph,
                "controlled_single_defect": True,
                "self_contained_event": True,
                "design_note": "Second ring resolves the local event; intended defect is only the claim that full hands prevent hearing.",
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
        "schema_version": "story-defect-response-supplement.v2",
        "status": "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION",
        "qualification_evidence": False,
        "purpose": "Naturalized, self-contained response-causality supplement after v1 revealed dangling-thread artifacts.",
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
