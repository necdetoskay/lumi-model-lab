from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.story_defect_corpus import build_mutation_source_rows
from src.story_defect_detection import segment_story
from src.story_defect_mutation_matrix import load_mutation_matrix, mutation_recipes
from src.story_defect_mutation_protocol import apply_single_patch


OUT = Path("experiments/fixtures/story_defect_corpus.tr-age4.synthetic.v1.json")


DEFECT_SENTENCES: dict[str, str] = {
    "physical_impossible_affordance": (
        "Deniz yerinden hiç kıpırdamadan birkaç metre ötedeki nesneyi eliyle alıp yanına getirdi."
    ),
    "physical_unsupported_motion": (
        "Deniz ayaklarını hiç oynatmadan bir anda bulunduğu yerin öteki tarafına geçti."
    ),
    "causal_rule_inversion": (
        "Hiçbir koşul değişmediği hâlde, sırf Deniz istediği için biraz önce işe yaramayan şey bu kez hemen işe yaradı."
    ),
    "causal_missing_prerequisite": (
        "Gerekli adımı henüz yapmamıştı ama sonuç çoktan gerçekleşmişti."
    ),
    "state_object_reset": (
        "Az önce bıraktığı şey, kimse dokunmadığı hâlde yeniden Deniz'in elindeydi."
    ),
    "state_completed_action_undone": (
        "Az önce tamamladığı iş, arada hiçbir şey olmadan yeniden yapılmamış hâline dönmüştü."
    ),
    "state_unexplained_reappearance": (
        "Biraz önce ortadan kaldırdığı nesne, kimse getirmediği hâlde aynı yerde yeniden belirdi."
    ),
    "epistemic_knowledge_before_evidence": (
        "Deniz henüz bakmamıştı ve kimse ona söylememişti; yine de orada tam olarak ne olduğunu biliyordu."
    ),
    "spatial_incompatible_location": (
        "Deniz aynı anda hem bulunduğu yerde kaldı hem de birkaç metre ötedeki noktadan oyuncağını tuttu."
    ),
    "temporal_order_contradiction": (
        "Bunu daha yapmadan önce, yaptığı şeyin sonucunu çoktan görmüş olduğunu söyledi."
    ),
    "response_perception_conflation": (
        "İki eli dolu olduğu için kendisine seslenildiğini duyamadı."
    ),
    "closure_post_terminal_action": (
        "Her şey bitmişti; sonra Deniz aynı sorunu en baştan çözmek için yeniden işe koyuldu."
    ),
    "canon_durable_fact_contradiction": (
        "Deniz'in dört yaşında olduğu biliniyordu ama anlatıcı onun aslında yedi yaşında olduğunu söyledi."
    ),
    "physical_solid_barrier_violation": (
        "Deniz kapalı ve sağlam camın içinden elini geçirip öteki taraftaki şeyi aldı."
    ),
    "causal_effect_without_cause": (
        "Ortada yeni bir neden ya da değişiklik yoktu ama sonuç kendiliğinden tersine döndü."
    ),
}


def choose_anchor(segments: list[dict[str, Any]], recipe_index: int) -> dict[str, Any]:
    if not segments:
        raise RuntimeError("source_story_has_no_segments")
    # Keep closure mutation on the final sentence; spread all other mutations across
    # the interior so detector position cannot become a shortcut.
    if recipe_index == 11:
        return segments[-1]
    if len(segments) <= 2:
        return segments[0]
    interior = segments[1:-1]
    return interior[recipe_index % len(interior)]


def create_variant(
    source: dict[str, Any],
    recipe: dict[str, Any],
    recipe_index: int,
) -> dict[str, Any]:
    story = str(source["story"])
    segments = segment_story(story)
    anchor = choose_anchor(segments, recipe_index)
    injected = DEFECT_SENTENCES[recipe["id"]]
    before = anchor["text"]
    after = before + " " + injected
    mutated = apply_single_patch(story, before, after)
    mutated_segments = segment_story(mutated)

    injected_span_ids = [
        row["id"]
        for row in mutated_segments
        if injected in row["text"] or row["text"] == injected
    ]
    if not injected_span_ids:
        # Sentence segmentation may keep the original and injected sentence adjacent
        # only if punctuation is malformed; fail closed instead of guessing gold.
        raise RuntimeError(
            f"gold_span_not_found:{source['source_id']}:{recipe['id']}"
        )

    return {
        "case_id": f"{source['source_id']}__{recipe['id']}",
        "source_id": source["source_id"],
        "scenario_group": source["scenario_group"],
        "dataset_split": source["dataset_split"],
        "family": source["family"],
        "variant": "corrupt",
        "synthetic_status": "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION",
        "mutation": {
            "recipe_id": recipe["id"],
            "intended_family": recipe["family"],
            "intended_severity": recipe["severity"],
            "difficulty": recipe["difficulty"],
            "repair_scope": recipe["repair_scope"],
            "before_text": before,
            "after_text": after,
            "injected_text": injected,
            "source_anchor_span_id": anchor["id"],
        },
        "text": mutated,
        "gold": {
            "defect_present": True,
            "family": recipe["family"],
            "severity": recipe["severity"],
            "span_ids": injected_span_ids,
            "repair_scope": recipe["repair_scope"],
            "validation_status": "PENDING_INDEPENDENT_VALIDATION",
        },
        "provenance": source["provenance"],
    }


def main() -> None:
    sources = build_mutation_source_rows()
    matrix = load_mutation_matrix()
    recipes = mutation_recipes(matrix)

    cases = []
    for source in sources:
        for recipe_index, recipe in enumerate(recipes):
            cases.append(create_variant(source, recipe, recipe_index))

    expected = len(sources) * len(recipes)
    if len(cases) != expected:
        raise RuntimeError(f"case_count_mismatch:{len(cases)}:{expected}")

    by_family: dict[str, int] = {}
    by_split: dict[str, int] = {}
    for case in cases:
        family = case["gold"]["family"]
        split = case["dataset_split"]
        by_family[family] = by_family.get(family, 0) + 1
        by_split[split] = by_split.get(split, 0) + 1

    result = {
        "schema_version": "story-defect-corpus.synthetic.v1",
        "status": "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION",
        "created_at": "2026-09-26",
        "qualification_evidence": False,
        "purpose": (
            "Ready-to-run defect detector development corpus. Gold intent comes from "
            "controlled single-span mutations, but independent semantic validation is "
            "required before promotion or threshold qualification."
        ),
        "frozen_generator_profile": "configs/story_planner_profiles/tr_age4_narrative_load.v1.json",
        "source_admission": "experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json",
        "mutation_matrix": "experiments/fixtures/story_defect_mutation_matrix.tr-age4.v1.json",
        "summary": {
            "clean_source_count": len(sources),
            "recipes_per_source": len(recipes),
            "corrupt_case_count": len(cases),
            "by_defect_family": dict(sorted(by_family.items())),
            "by_dataset_split": dict(sorted(by_split.items())),
        },
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
