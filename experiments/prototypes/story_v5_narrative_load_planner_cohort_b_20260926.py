from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_v5_narrative_load_planner_20260926 as p
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED_BASE = 2026092680

FIXTURES = [
    {
        "family": "exploration_mystery",
        "premise": (
            "Deniz salonda resim yaparken aralıklı bir 'fıs fıs' sesi duyar. Ses bazen pencere tarafında, "
            "bazen masanın yanında gibi gelir. Deniz sesin kaynağını ararken pencerenin önündeki ince kâğıt "
            "şeridin kaloriferden yükselen hava ile kıpırdadığını fark eder ve hareketini kendi nefesiyle taklit eder."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz resim yaparken kısa bir 'fıs fıs' sesi duyar ve kalemini durdurur."},
            {"density":"develop","beat":"Ses tekrar gelir; Deniz masanın altına ve kalem kutusuna bakar ama kaynak orada değildir."},
            {"density":"develop","beat":"Pencere tarafına yaklaşınca ses kesilir; Deniz bir süre bekler."},
            {"density":"develop","beat":"Kalorifer yeniden ısınınca pencerenin önündeki ince kâğıt şerit hafifçe kıpırdar."},
            {"density":"anchor","beat":"Kâğıdın kenarı duvara sürtünüp aynı 'fıs fıs' sesini çıkarır ve Deniz kaynağı görür."},
            {"density":"anchor","beat":"Deniz hava durunca kâğıdın da durduğunu, hava yükselince yeniden hareket ettiğini birkaç kez izler."},
            {"density":"anchor","beat":"Deniz kâğıda dokunmadan uzaktan hafifçe üfleyip aynı hareketi kısa süre taklit eder."},
            {"density":"anchor","beat":"Kapanışta kendi iki kısa üflemesini yapar ve kâğıdın verdiği hışırtılı cevabı dinler."},
        ],
    },
    {
        "family": "friendship_social_problem",
        "premise": (
            "Deniz ve Ece oyuncak tren yolu kurar. Deniz istasyonun önünden düz bir hat geçirmek ister, Ece ise "
            "oyuncak hayvanların geçebilmesi için yola bir köprü eklemek ister. İkisi birbirinin parçasını sürekli "
            "yer değiştirince oyun durur; sonra iki ihtiyacı aynı düzende birleştirecek bir yol bulurlar."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz ve Ece yerde tren yolu kurmaya başlar; Deniz istasyonu yolun ortasına yerleştirir."},
            {"density":"develop","beat":"Ece rayların bir bölümünü kaldırıp oyuncak hayvanlar için küçük bir köprü koyar."},
            {"density":"develop","beat":"Deniz köprüyü yana alıp rayı düzeltir; Ece köprüyü geri getirir ve oyun kısa süre durur."},
            {"density":"develop","beat":"Deniz Ece'nin hayvanları yolun öbür tarafına geçirmek istediğini fark eder."},
            {"density":"anchor","beat":"Ece de Deniz'in trenin istasyona takılmadan düz gelmesini istediğini görür."},
            {"density":"anchor","beat":"İkisi niyetlerini kısa bir konuşmayla birbirine gösterir ve parçaları suçlamadan yeniden dener."},
            {"density":"anchor","beat":"Köprüyü istasyonun biraz ilerisine alıp rayı hafifçe kıvırırlar; tren geçerken hayvanlar için de yol kalır."},
            {"density":"anchor","beat":"Kapanışta tren istasyona girerken Ece'nin hayvanları köprüden karşıya geçer ve oyun birlikte sürer."},
        ],
    },
    {
        "family": "emotional_development",
        "premise": (
            "Deniz parkta Ece'ye yaptığı kum şeklini göstermek ister ama Ece dönmeden uzaklaşır. Deniz onun bakmak "
            "istemediğini düşünür. Biraz sonra Ece'nin uçup giden küçük kâğıt şapkasını yakalamaya çalıştığını görür; "
            "yanına gidip yardım eder ve geri döndüklerinde şekli birlikte tamamlarlar."
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
        "family": "nature_environment",
        "premise": (
            "Deniz yağmurdan sonra bahçedeki taş yolun bir bölümünün çabuk kuruduğunu, başka bir bölümünün ise ıslak "
            "kaldığını fark eder. Gölgeyi, zeminin eğimini ve ince su izini karşılaştırarak suyun küçük bir çukurda "
            "toplandığını görür; hiçbir şeyi kazmadan suyun kenarından dolaşıp akışın kendi kendine değişmesini izler."
        ),
        "spine": [
            {"density":"brief","beat":"Yağmurdan sonra Deniz taş yolda yan yana iki ıslak bölge fark eder."},
            {"density":"develop","beat":"Bir süre sonra bir bölüm kururken diğerinin hâlâ parlak ve ıslak kaldığını görür."},
            {"density":"develop","beat":"Önce gölgeyi karşılaştırır; iki bölümün de benzer ışık aldığını fark eder."},
            {"density":"develop","beat":"Yere daha yakından bakınca kuru tarafa doğru ince bir su izi, ıslak tarafta ise küçük bir çukur görür."},
            {"density":"anchor","beat":"Deniz çukuru ayağıyla ezmez ya da taşları kaldırmaz; kenardan dikkatlice gözler."},
            {"density":"anchor","beat":"Biriken suyun kenardan çok ince bir çizgiyle taşmaya başladığını fark eder."},
            {"density":"anchor","beat":"Su çizgisini dokunmadan takip eder ve biraz sonra ıslak bölümün de küçülmeye başladığını görür."},
            {"density":"anchor","beat":"Kapanışta çizmelerini kuru taşa basıp küçük su yolunun kıvrımını sessizce izler."},
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


def plan_for_fixture(key: str, fixture: dict, seed: int) -> tuple[dict, float]:
    plan, meta = structured_call(
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
                "spine_must_be_self_sufficient_before_writing": True,
            },
        },
        seed=seed,
        max_tokens=None,
        request_class="editorial_audit",
    )
    spine = plan.get("spine") or []
    if not (8 <= len(spine) <= 12):
        raise RuntimeError(f"{fixture['family']}:planner_spine_size_invalid:{len(spine)}")
    return plan, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def generate(key: str, fixture: dict, spine: list[dict], seed: int) -> dict:
    t0 = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=key,
        model=p.WRITER_MODEL,
        system_prompt=p.WRITER_SYSTEM,
        user_prompt=(
            f"KONU:\n{fixture['premise']}\n\n"
            f"HİKÂYE OMURGASI:\n{p.render_spine(spine)}\n\n"
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
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
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
    total_cost = 0.0

    for i, fixture in enumerate(FIXTURES):
        seed = SEED_BASE + i * 100
        plan, planner_cost = plan_for_fixture(key, fixture, seed)
        planned_spine = plan["spine"]
        baseline = generate(key, fixture, fixture["spine"], seed + 1)
        planned = generate(key, fixture, planned_spine, seed + 1)

        forward, c1 = compare(key, fixture, baseline["story"], planned["story"], seed + 2)
        reverse, c2 = compare(key, fixture, planned["story"], baseline["story"], seed + 3)

        fw = normalize(forward.get("winner"), "baseline", "planned")
        rv = normalize(reverse.get("winner"), "planned", "baseline")
        if fw == rv:
            consensus = fw
        elif fw == "TIE" and rv != "TIE":
            consensus = rv
        elif rv == "TIE" and fw != "TIE":
            consensus = fw
        else:
            consensus = "INCONCLUSIVE"

        judge_cost = c1 + c2
        case_cost = planner_cost + baseline["cost_usd"] + planned["cost_usd"] + judge_cost
        total_cost += case_cost

        cases.append({
            "family": fixture["family"],
            "premise": fixture["premise"],
            "planner_output": plan,
            "baseline": {"spine": fixture["spine"], **baseline},
            "planned": {"spine": planned_spine, **planned},
            "word_delta": planned["word_count"] - baseline["word_count"],
            "normalized_winners": {"forward": fw, "reverse": rv, "consensus": consensus},
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "cost_usd": {
                "planner": planner_cost,
                "baseline_writer": baseline["cost_usd"],
                "planned_writer": planned["cost_usd"],
                "judges": judge_cost,
                "total": case_cost,
            },
        })

    wins = {"baseline": 0, "planned": 0, "TIE": 0, "INCONCLUSIVE": 0}
    summary = []
    for case in cases:
        consensus = case["normalized_winners"]["consensus"]
        wins[consensus] = wins.get(consensus, 0) + 1
        support = case["planner_output"].get("supporting_thread") or {}
        summary.append({
            "family": case["family"],
            "planner_beats": len(case["planned"]["spine"]),
            "supporting_thread_used": bool(support.get("used")),
            "baseline_words": case["baseline"]["word_count"],
            "planned_words": case["planned"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": consensus,
            "forward_confidence": case["pairwise_forward"].get("confidence"),
            "reverse_confidence": case["pairwise_reverse"].get("confidence"),
        })

    result = {
        "experiment": "story-v5-narrative-load-planner-fresh-cohort-b-v1",
        "exact_age": 4,
        "nominal_target_words": 500,
        "families": len(cases),
        "fixture_cohort": "B",
        "planner_model": p.PLANNER_MODEL,
        "writer_model": p.WRITER_MODEL,
        "judge_model": p.JUDGE_MODEL,
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": round(sum(c["word_delta"] for c in cases) / len(cases), 2),
        "cases": cases,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-narrative-load-planner-cohort-b")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for case in cases:
        family = case["family"]
        (out / f"{family}-baseline.txt").write_text(case["baseline"]["story"] + "\n", encoding="utf-8")
        (out / f"{family}-planned.txt").write_text(case["planned"]["story"] + "\n", encoding="utf-8")
        (out / f"{family}-spine.json").write_text(
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
