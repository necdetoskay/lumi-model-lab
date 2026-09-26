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

SEED_BASE = 2026092690

GUARDED_PLANNER_SYSTEM = (
    p.PLANNER_SYSTEM
    + r"""

ADDITIONAL CAUSAL/STATE GUARDS:
- Once the main arc establishes a causal rule, a supporting thread may test or expose that rule but MUST NOT weaken, replace, or silently add a second cause.
- Do not invent a late hidden condition only to delay an outcome that the established causal rule says should happen.
- Do not complete an action or item-state transition and then undo it merely to reuse the object for a later beat.
- A supporting thread must not become a second explanation for the core phenomenon.
- If a supporting thread creates causal-rule ambiguity, state rollback, or extra-condition risk, OMIT the supporting thread and strengthen the main arc instead.
"""
).strip()

FIXTURES = [
    {
        "id": "glass_color_patch",
        "family": "everyday_fantastical_discovery",
        "premise": (
            "Deniz odasında duvarda küçük bir renk gölü görür. Renkler yalnız güneş cam bardaktan geçtiğinde belirir. "
            "Deniz bardağı oynatmadan farklı yerlerden bakarak ve önünü kısa süre gölgeleyerek bu görüntünün ne zaman "
            "ortaya çıktığını keşfeder; sonra oyuncağını toplar ve renklerin geri gelmesini bekler."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz odada oyuncaklarını toplarken duvarda küçük renkli bir leke görür."},
            {"density":"develop","beat":"Bulut güneşi kapatınca renkler kaybolur; Deniz duvara yaklaşınca orada boya olmadığını görür."},
            {"density":"develop","beat":"Güneş çıkınca renkler geri gelir ve Deniz masadaki cam bardağın da ışıldadığını fark eder."},
            {"density":"develop","beat":"Deniz bardağa dokunmadan önünü eliyle gölgeler; renkler kaybolur, elini çekince geri gelir."},
            {"density":"anchor","beat":"Farklı açılardan bakarak renkli şeklin yalnız belli ışık çizgisinde göründüğünü keşfeder."},
            {"density":"anchor","beat":"Renkli lekeye dokunmayı dener ama duvar normaldir; görüntü hiçbir işi sihirle çözmez."},
            {"density":"anchor","beat":"Deniz yerde kalan oyuncağını kutuya koyar ve sonra aynı yere geri dönüp güneşi bekler."},
            {"density":"anchor","beat":"Kapanışta renkler yeniden belirince Deniz sessizce bakar ve bardağı olduğu yerde bırakır."},
        ],
    },
    {
        "id": "basket_star_shadow",
        "family": "everyday_fantastical_discovery",
        "premise": (
            "Deniz öğleden sonra odasının duvarında küçük yıldız benzeri ışık parçaları görür. Güneş, pencere önündeki "
            "delikli oyuncak sepetinin kenarından geçince şekiller oluşur. Deniz sepeti taşımadan eliyle ışığı kısa süre "
            "kesip geri açarak kuralı keşfeder; sonra yerdeki kitabını yerine koyar ve şekillerin yeniden duvara düşmesini izler."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz yerdeki kitabını alırken duvarda birkaç küçük ışık şekli görür."},
            {"density":"develop","beat":"Bir bulut geçince şekiller kaybolur; duvarın normal olduğunu görür."},
            {"density":"develop","beat":"Güneş dönünce şekiller geri gelir ve pencere önündeki delikli sepetin kenarı aydınlanır."},
            {"density":"develop","beat":"Deniz sepeti taşımadan ışığın önüne elini koyar; şekiller kaybolur, elini çekince geri gelir."},
            {"density":"anchor","beat":"Biraz sağa sola geçip şekillerin ışık çizgisine göre yer değiştirdiğini gözlemler."},
            {"density":"anchor","beat":"Duvara dokunduğunda hiçbir kabarıklık veya gerçek yıldız olmadığını görür."},
            {"density":"anchor","beat":"Yerdeki kitabını rafa koyar ve ışık yolunun dışına çekilir."},
            {"density":"anchor","beat":"Kapanışta küçük şekiller yeniden belirir; Deniz sepeti yerinde bırakıp onları izler."},
        ],
    },
    {
        "id": "water_glow_ceiling",
        "family": "everyday_fantastical_discovery",
        "premise": (
            "Deniz mutfak masasındaki şeffaf su şişesinin yanında tavanda sallanan parlak bir ışık lekesi fark eder. "
            "Güneş şişedeki sudan geçtikçe leke görünür; Deniz şişeyi oynatmadan önünü kısa süre gölgeler ve ışığın "
            "kaybolup geri geldiğini görür. Sonra masadaki peçeteyi yerine bırakıp ışığın tavanda yeniden kıpırdamasını izler."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz masanın yanında tavanda parlak, kıpırdayan küçük bir leke fark eder."},
            {"density":"develop","beat":"Güneş bulutun arkasına girince leke kaybolur; tavanda normal boya dışında bir şey yoktur."},
            {"density":"develop","beat":"Güneş geri gelince leke yeniden görünür ve masadaki su şişesi de ışıldar."},
            {"density":"develop","beat":"Deniz şişeyi oynatmadan ışığın önüne elini koyar; leke kaybolur, elini çekince geri gelir."},
            {"density":"anchor","beat":"Deniz birkaç farklı noktadan bakıp ışığın şişe ile güneş aynı çizgideyken göründüğünü fark eder."},
            {"density":"anchor","beat":"Parlak lekeye uzansa da tavanda dokunabileceği bir şey olmadığını görür."},
            {"density":"anchor","beat":"Masadaki peçeteyi yerine bırakır ve ışık yolunun dışına geçer."},
            {"density":"anchor","beat":"Kapanışta leke yeniden kıpırdar; Deniz şişeyi olduğu yerde bırakıp tavandaki ışığı izler."},
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
        system=GUARDED_PLANNER_SYSTEM,
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
                "preserve_main_causal_rule": True,
                "preserve_committed_item_state": True,
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

        case_cost = plan_cost + baseline["cost_usd"] + planned["cost_usd"] + c1 + c2
        total += case_cost
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
            "cost_usd": case_cost,
        })

    wins = {"baseline": 0, "guarded_planned": 0, "TIE": 0, "INCONCLUSIVE": 0}
    summary = []
    for case in cases:
        c = case["normalized_winners"]["consensus"]
        wins[c] = wins.get(c, 0) + 1
        support = case["planner_output"].get("supporting_thread") or {}
        summary.append({
            "id": case["id"],
            "supporting_thread_used": bool(support.get("used")),
            "planner_beats": len(case["guarded_planned"]["spine"]),
            "baseline_words": case["baseline"]["word_count"],
            "planned_words": case["guarded_planned"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": c,
        })

    result = {
        "experiment": "story-v5-narrative-load-causal-guard-fantastical-v1",
        "family": "everyday_fantastical_discovery",
        "exact_age": 4,
        "fixtures": len(cases),
        "planner_model": p.PLANNER_MODEL,
        "writer_model": p.WRITER_MODEL,
        "judge_model": p.JUDGE_MODEL,
        "guard_delta": [
            "supporting thread must preserve established causal rule",
            "no late hidden condition solely to delay payoff",
            "no state rollback solely to reuse a prop",
            "omit supporting thread when those risks exist"
        ],
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": round(sum(c["word_delta"] for c in cases) / len(cases), 2),
        "cases": cases,
        "total_cost_usd": round(total, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-narrative-load-causal-guard-fantastical")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
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
