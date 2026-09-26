from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_v5_narrative_load_planner_20260926 as p
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from experiments.prototypes import story_spine_refined_recipe_20260926 as base

SEED_BASE = 2026092700

FIXTURES = [
    {
        "id": "blocks_no_reply",
        "family": "emotional_development",
        "premise": (
            "Deniz oyun alanında Ada'ya seslenir ama Ada hemen karşılık vermez. Deniz onun kendisini duymak istemediğini sanır. "
            "Biraz sonra Ada'nın iki eliyle devrilen blokları tuttuğunu fark eder; Deniz yanına gidip ne olduğunu sorar ve birlikte "
            "oyunu yeniden kurarlar."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz oyun alanında Ada'yı görür ve el sallayarak ona seslenir."},
            {"density":"develop","beat":"Ada dönmez; Deniz'in yüzü düşer ve elini indirir."},
            {"density":"develop","beat":"Deniz bir kez daha yaklaşır ama Ada hâlâ önündeki bloklara bakmaktadır."},
            {"density":"develop","beat":"Deniz bu kez Ada'nın iki eliyle yana yatmış uzun blok kulesini tutmaya çalıştığını fark eder."},
            {"density":"anchor","beat":"Deniz 'Beni duymadın mı?' diye sorar; Ada da kule devrilmesin diye ellerini bırakamadığını söyler."},
            {"density":"anchor","beat":"Deniz önceki yorumunu değiştiren bu bilgiyi davranışıyla kabul eder ve kulenin diğer yanını tutar."},
            {"density":"anchor","beat":"İkisi kuleyi birlikte düzeltir; Ada sonra Deniz'e dönüp gecikmiş selamını verir."},
            {"density":"anchor","beat":"Kapanışta Deniz de gülerek ilk selamını yeniden yapar; bu kez Ada aynı anda karşılık verir."},
        ],
    },
    {
        "id": "paper_hat_no_reply",
        "family": "emotional_development",
        "premise": (
            "Deniz parkta Ece'ye yaptığı kum şeklini göstermek ister ama Ece dönmeden uzaklaşır. Deniz onun bakmak istemediğini düşünür. "
            "Biraz sonra Ece'nin uçup giden küçük kâğıt şapkasını yakalamaya çalıştığını görür; yanına gidip yardım eder ve geri döndüklerinde "
            "şekli birlikte tamamlarlar."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz kumda yaptığı küçük şekli Ece'ye göstermek için seslenir."},
            {"density":"develop","beat":"Ece dönmeden birkaç adım uzaklaşınca Deniz'in eli aşağı iner ve bekler."},
            {"density":"develop","beat":"Deniz onun bakmak istemediğini düşünerek kumun başına geri döner."},
            {"density":"develop","beat":"Başını kaldırınca Ece'nin rüzgârla yuvarlanan küçük kâğıt şapkasının peşinden gittiğini görür."},
            {"density":"anchor","beat":"Deniz yanına gidip şapkanın önüne geçen yolu kapatarak Ece'nin onu almasına yardım eder."},
            {"density":"anchor","beat":"Ece neden uzaklaştığını söyler; Deniz de kum şeklini göstermek istediğini kısa biçimde anlatır."},
            {"density":"anchor","beat":"Birlikte kuma dönerler ve Ece şeklin yanına küçük bir yol ekler."},
            {"density":"anchor","beat":"Kapanışta Deniz ilk göstermek istediği yeri işaret eder, Ece bu kez hemen eğilip bakar."},
        ],
    },
    {
        "id": "watering_can_busy",
        "family": "emotional_development",
        "premise": (
            "Deniz bahçede Arda'ya bulduğu düzgün taşı göstermek ister ama Arda cevap vermeden eğilip uzaklaşır. Deniz onun ilgilenmediğini sanır. "
            "Biraz sonra Arda'nın devrilmek üzere olan küçük sulama kabını ayağıyla sabitlemeye çalıştığını fark eder; Deniz yanına gidip yardım eder, "
            "sonra taşı birlikte incelerler."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz düzgün bir taş bulur ve Arda'ya göstermek için seslenir."},
            {"density":"develop","beat":"Arda dönmeden eğilip birkaç adım yana gider; Deniz'in hevesi azalır."},
            {"density":"develop","beat":"Deniz Arda'nın ilgilenmediğini düşünüp taşı avucunda çevirir."},
            {"density":"develop","beat":"Biraz sonra Arda'nın ayağıyla yana devrilen küçük sulama kabını sabitlemeye çalıştığını fark eder."},
            {"density":"anchor","beat":"Deniz yanına gidip kabı düzeltmesine yardım eder ve neden cevap vermediğini sorar."},
            {"density":"anchor","beat":"Arda kabın suyu dökülmesin diye önce onu tutmaya çalıştığını söyler."},
            {"density":"anchor","beat":"İkisi işi bitirince Deniz taşı gösterir; Arda taşın düz yüzüne yakından bakar."},
            {"density":"anchor","beat":"Kapanışta taşı çevirip ışıkta parlayan küçük noktayı birlikte fark ederler."},
        ],
    },
]

PAIRWISE_SYSTEM = p.PAIRWISE_SYSTEM


def normalize(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a
    if raw == "B":
        return b
    return "TIE"


def render_spine(spine: list[dict]) -> str:
    return "\n".join(
        f"{i+1}. [{b.get('density','develop')}] [{b.get('function','beat')}] {b['beat']}"
        for i, b in enumerate(spine)
    )


def plan_fixture(key: str, fixture: dict, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=key,
        model=p.PLANNER_MODEL,
        system=p.PLANNER_SYSTEM,
        payload={
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "nominal_target_words": 500,
            "story_family": fixture["family"],
            "premise": fixture["premise"],
            "constraints": {
                "no_new_named_character": True,
                "no_new_relationship_canon": True,
                "supporting_thread_optional": True,
                "quality_over_word_count": True,
                "preserve_epistemic_order": True,
                "do_not_reveal_explanation_before_misunderstanding": True,
            },
        },
        seed=seed,
        max_tokens=None,
        request_class="editorial_audit",
    )
    spine = result.get("spine") or []
    if not (8 <= len(spine) <= 12):
        raise RuntimeError(f"{fixture['id']}:planner_spine_size_invalid:{len(spine)}")
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def generate(key: str, fixture: dict, spine: list[dict], seed: int) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=key,
        model=p.WRITER_MODEL,
        system_prompt=p.WRITER_SYSTEM,
        user_prompt=(
            f"KONU:\n{fixture['premise']}\n\n"
            f"HİKÂYE OMURGASI:\n{render_spine(spine)}\n\n"
            "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
        ),
        temperature=0.72,
        max_tokens=None,
        seed=seed,
        request_class="teacher_story_medium_reasoning",
        structured_output=False,
    )
    return {
        "story": story,
        "word_count": count_words(story),
        "scan": base.scan(story),
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost_usd": float(parse_cost(body).usd or 0.0),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "request_payload": payload,
    }


def compare(key: str, fixture: dict, a: str, b: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=key,
        model=p.JUDGE_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "story_family": fixture["family"],
            "premise": fixture["premise"],
            "story_A": a,
            "story_B": b,
        },
        seed=seed,
        max_tokens=None,
        request_class="editorial_audit",
    )
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()
    cases = []
    total = 0.0

    for i, fixture in enumerate(FIXTURES):
        seed = SEED_BASE + i * 100
        plan, plan_cost = plan_fixture(key, fixture, seed)
        baseline = generate(key, fixture, fixture["spine"], seed + 1)
        planned = generate(key, fixture, plan["spine"], seed + 1)
        forward, c1 = compare(key, fixture, baseline["story"], planned["story"], seed + 2)
        reverse, c2 = compare(key, fixture, planned["story"], baseline["story"], seed + 3)

        fw = normalize(forward.get("winner"), "baseline", "guarded_planned")
        rv = normalize(reverse.get("winner"), "guarded_planned", "baseline")
        if fw == rv:
            consensus = fw
        elif fw == "TIE" and rv != "TIE":
            consensus = rv
        elif rv == "TIE" and fw != "TIE":
            consensus = fw
        else:
            consensus = "INCONCLUSIVE"

        cost = plan_cost + baseline["cost_usd"] + planned["cost_usd"] + c1 + c2
        total += cost
        cases.append({
            "id": fixture["id"],
            "family": fixture["family"],
            "planner_output": plan,
            "baseline": {"spine": fixture["spine"], **baseline},
            "guarded_planned": {"spine": plan["spine"], **planned},
            "word_delta": planned["word_count"] - baseline["word_count"],
            "normalized_winners": {"forward": fw, "reverse": rv, "consensus": consensus},
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "cost_usd": cost,
        })

    wins = {"baseline": 0, "guarded_planned": 0, "TIE": 0, "INCONCLUSIVE": 0}
    summary = []
    for case in cases:
        c = case["normalized_winners"]["consensus"]
        wins[c] = wins.get(c, 0) + 1
        summary.append({
            "id": case["id"],
            "planner_beats": len(case["guarded_planned"]["spine"]),
            "supporting_thread_used": bool((case["planner_output"].get("supporting_thread") or {}).get("used")),
            "baseline_words": case["baseline"]["word_count"],
            "planned_words": case["guarded_planned"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": c,
        })

    result = {
        "experiment": "story-v5-narrative-load-epistemic-guard-emotional-v1",
        "family": "emotional_development",
        "exact_age": 4,
        "fixtures": len(cases),
        "guard_delta": [
            "preserve epistemic order",
            "do not reveal explanatory evidence before misunderstanding is formed",
            "new evidence must naturally revise the character's interpretation"
        ],
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": round(sum(c["word_delta"] for c in cases) / len(cases), 2),
        "cases": cases,
        "total_cost_usd": round(total, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-narrative-load-epistemic-guard-emotional")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for case in cases:
        (out / f"{case['id']}-baseline.txt").write_text(case["baseline"]["story"] + "\n", encoding="utf-8")
        (out / f"{case['id']}-guarded.txt").write_text(case["guarded_planned"]["story"] + "\n", encoding="utf-8")
        (out / f"{case['id']}-spine.json").write_text(
            json.dumps(case["planner_output"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps({
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": result["mean_word_delta"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
