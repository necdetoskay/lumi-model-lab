from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

TARGETS = [500, 700]
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"
BASE_SEED = 2026092610

FIXTURES = [
    {
        "family": "exploration_mystery",
        "premise": base.PREMISE,
        "spine": base.STORY_SPINE,
    },
    {
        "family": "friendship_social_problem",
        "premise": (
            "Deniz ve Ece yerde büyük bir karton kasaba kurar. Deniz köprüyü bir yere, Ece yolu başka bir yere taşır; "
            "ikisi de diğerinin oyunu bozduğunu sanır. Birbirlerinin ne yapmaya çalıştığını görünce köprü ile yolu "
            "birleştiren yeni bir düzen kurarlar."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz ve Ece yerde karton evler, bir yol ve küçük bir köprüyle kasaba kurmaya başlar."},
            {"density":"develop","beat":"Deniz köprüyü yolun önüne koyar; kısa süre sonra Ece köprüyü başka yere taşır."},
            {"density":"develop","beat":"Deniz köprüyü geri koyar; Ece de yolu çevirir ve ikisi oyunun bozulduğunu düşünür."},
            {"density":"develop","beat":"Deniz Ece'nin elindeki oyuncak otobüsün dönmek için geniş bir yere ihtiyaç duyduğunu fark eder."},
            {"density":"anchor","beat":"Ece de Deniz'in köprünün altından oyuncak teknesini geçirmek istediğini görür."},
            {"density":"anchor","beat":"İkisi kısa ve doğal bir konuşmayla ne yapmaya çalıştıklarını birbirine gösterir; kimse suçlu ilan edilmez."},
            {"density":"anchor","beat":"Yolu kıvırıp köprüyü biraz yana alarak hem otobüsün dönebildiği hem teknenin geçebildiği yeni düzeni birlikte kurarlar."},
            {"density":"anchor","beat":"Kapanışta otobüs köprüye yaklaşırken tekne alttan geçer; ikisi aynı anda kendi araçlarına ses verip güler."},
        ],
    },
    {
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
        "family": "everyday_fantastical_discovery",
        "premise": (
            "Deniz apartman avlusunda mavi bir taşın üstüne güneş vurduğunda duvarda minicik bir yıldız kapısı belirdiğini fark eder. "
            "Kapı yalnız ışık belirli açıdayken görünür ve hiçbir şeyi taşımıyor ya da çözmüyordur. Deniz kuralı birkaç kez dener, "
            "sonra oyuncağını toplamayı unutmadan bu küçük sırrı bir süre daha izlemeyi seçer."
        ),
        "spine": [
            {"density":"brief","beat":"Deniz avluda oyuncağını toplarken duvarda bir anlığına küçük parlak bir yıldız şekli görür."},
            {"density":"develop","beat":"Bulut güneşi kapatınca şekil kaybolur; Deniz duvara yaklaşsa da hiçbir kapı bulamaz."},
            {"density":"develop","beat":"Güneş yeniden çıkınca yıldız şekli geri gelir ve Deniz yerdeki mavi taşın da parladığını fark eder."},
            {"density":"develop","beat":"Deniz taşın önünü eliyle gölgeler; yıldız kaybolur, elini çekince tekrar görünür."},
            {"density":"anchor","beat":"Taşı yerinden oynatmadan farklı açılardan bakar ve yalnız belli ışık açısında yıldızın belirdiğini anlar."},
            {"density":"anchor","beat":"Deniz yıldız şekline dokunmayı dener ama duvar normaldir; bu küçük tuhaflık onun işini sihirle yapmaz."},
            {"density":"anchor","beat":"Yerde kalan oyuncağını toplar, sonra geri dönüp ışığın yeniden doğru yere gelmesini bekler."},
            {"density":"anchor","beat":"Kapanışta yıldız bir kez daha görünür; Deniz sessizce 'Yarın yine bakarım' deyip mavi taşı olduğu yerde bırakır."},
        ],
    },
    {
        "family": "nature_environment",
        "premise": (
            "Yağmurdan sonra Deniz bahçedeki iki küçük su birikintisinden birinin çabuk küçüldüğünü, diğerinin ise kaldığını fark eder. "
            "Toprak, yaprak ve ince su yolunu gözlemleyerek farkın nereden geldiğini anlar; canlıları rahatsız etmeden yalnızca gevşek "
            "bir yaprağı kenara alır ve suyun yeniden akmasını izler."
        ),
        "spine": [
            {"density":"brief","beat":"Yağmurdan sonra Deniz bahçede yan yana iki küçük su birikintisi görür."},
            {"density":"develop","beat":"Bir süre sonra birinin küçüldüğünü, diğerinin neredeyse aynı kaldığını fark eder."},
            {"density":"develop","beat":"Deniz önce güneşe bakar; iki birikintinin de benzer ışık aldığını görür."},
            {"density":"develop","beat":"Sonra toprağın kenarında birinden çıkan ince su izini, diğerinde ise yaprakla kapanmış küçük oluğu fark eder."},
            {"density":"anchor","beat":"Oluğun yanında küçük bir böcek gördüğü için toprağı kazmaz ve etrafı dağıtmaz."},
            {"density":"anchor","beat":"Yalnızca oluğun üstünde duran gevşek yaprağı iki parmağıyla kenara alır."},
            {"density":"anchor","beat":"Su ince bir çizgi halinde yeniden akmaya başlar; Deniz iki birikintiyi biraz daha izleyip farkı karşılaştırır."},
            {"density":"anchor","beat":"Kapanışta yaprağı yakındaki kuru toprağa bırakır ve akan suyun yaptığı minicik kıvrımı sessizce takip eder."},
        ],
    },
]

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı premise ve aynı story spine'dan üretilmiş iki hikâyeyi karşılaştır.

Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.

Sana hangi metnin hangi üretim ayarından geldiği, hedef kelime sayısı veya gerçek kelime sayısı verilmez.
Uzun olanı otomatik olarak tercih etme. Kısa ama tamamlanmış ve canlı bir hikâye daha iyi olabilir.

Öncelikler:
1. doğal ve tutarlı hikâye akışı,
2. çocuk ajansı,
3. tam 4 yaşa uygunluk,
4. sesli okuma ritmi,
5. doğal Türkçe,
6. closure,
7. filler/tekrar olmaması,
8. premise ve spine'a sadakat,
9. yeni canon veya sırf uzatmak için yeni olay eklememek,
10. fiziksel mantık ve çocuk güvenliği.

winner yalnız "A", "B" veya "TIE" olabilir.
TIE ancak kalite farkı gerçekten küçükse kullan.
Serious kusurları ayrı yaz.

SADECE JSON:
{
  "winner":"A|B|TIE",
  "confidence":"low|medium|high",
  "scores":{
    "A":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"language":1,"closure":1,"economy":1,"overall":1},
    "B":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"language":1,"closure":1,"economy":1,"overall":1}
  },
  "filler_risk":{"A":"low|medium|high","B":"low|medium|high"},
  "serious_defects":{"A":[],"B":[]},
  "why":"en fazla üç kısa cümle"
}
""".strip()


def writer_system(target: int) -> str:
    prefix, _ = base.WRITER_SYSTEM.split("UZUNLUK:", 1)
    return (
        prefix.rstrip()
        + f"""

ÜRETİM HACMİ:
- Yaklaşık {target} kelimelik anlatı hacmi hedefle.
- Bu sayı kalite hedefi değildir; doğal hikâye kalitesi sayıdan önce gelir.
- Hedefe yaklaşmak için yeni olay, yeni canon, açıklama dolgusu, sıfat dolgusu veya mekanik tekrar ekleme.
- Omurgadaki önemli anları gerektiği kadar yaşat; doğal hikâye tamamlanınca bitir.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
"""
    ).strip()


def user_prompt(fixture: dict) -> str:
    spine = "\n".join(
        f"{i+1}. [{b['density']}] {b['beat']}" for i, b in enumerate(fixture["spine"])
    )
    return (
        f"KONU:\n{fixture['premise']}\n\n"
        f"HİKÂYE OMURGASI:\n{spine}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )


def generate(api_key: str, fixture: dict, target: int, seed: int) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=api_key,
        model=base.WRITER_MODEL,
        system_prompt=writer_system(target),
        user_prompt=user_prompt(fixture),
        temperature=0.72,
        max_tokens=None,
        seed=seed,
        request_class=WRITER_REQUEST_CLASS,
        structured_output=False,
    )
    return {
        "target": target,
        "story": story,
        "word_count": count_words(story),
        "scan": base.scan(story),
        "usage": parse_usage(body).model_dump(mode="json"),
        "request_payload": payload,
        "cost_usd": float(parse_cost(body).usd or 0.0),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def pairwise(api_key: str, fixture: dict, story_a: str, story_b: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=api_key,
        model=base.EDITOR_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "premise": fixture["premise"],
            "story_spine": fixture["spine"],
            "story_A": story_a,
            "story_B": story_b,
        },
        seed=seed,
        max_tokens=None,
        request_class=JUDGE_REQUEST_CLASS,
    )
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def normalize_winner(raw: str, a_target: int, b_target: int) -> int | str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a_target
    if raw == "B":
        return b_target
    return "TIE"


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()
    cases = []
    total_cost = 0.0

    for index, fixture in enumerate(FIXTURES):
        family_seed = BASE_SEED + index * 100
        drafts = {}
        for target in TARGETS:
            item = generate(api_key, fixture, target, family_seed)
            drafts[target] = item
            total_cost += item["cost_usd"]

        forward, forward_cost = pairwise(
            api_key, fixture, drafts[500]["story"], drafts[700]["story"], family_seed + 21
        )
        reverse, reverse_cost = pairwise(
            api_key, fixture, drafts[700]["story"], drafts[500]["story"], family_seed + 22
        )
        total_cost += forward_cost + reverse_cost

        forward_normalized = normalize_winner(forward.get("winner"), 500, 700)
        reverse_normalized = normalize_winner(reverse.get("winner"), 700, 500)

        if forward_normalized == reverse_normalized:
            consensus = forward_normalized
        elif forward_normalized == "TIE" and reverse_normalized in TARGETS:
            consensus = reverse_normalized
        elif reverse_normalized == "TIE" and forward_normalized in TARGETS:
            consensus = forward_normalized
        else:
            consensus = "INCONCLUSIVE"

        cases.append({
            "family": fixture["family"],
            "premise": fixture["premise"],
            "story_spine": fixture["spine"],
            "drafts": {"500": drafts[500], "700": drafts[700]},
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "normalized_winners": {
                "forward": forward_normalized,
                "reverse": reverse_normalized,
                "consensus": consensus,
            },
            "judge_cost_usd": forward_cost + reverse_cost,
        })

    summary = []
    wins = {"500": 0, "700": 0, "TIE": 0, "INCONCLUSIVE": 0}
    for case in cases:
        c = case["normalized_winners"]["consensus"]
        wins[str(c)] = wins.get(str(c), 0) + 1
        summary.append({
            "family": case["family"],
            "words_500": case["drafts"]["500"]["word_count"],
            "words_700": case["drafts"]["700"]["word_count"],
            "delta_words": case["drafts"]["700"]["word_count"] - case["drafts"]["500"]["word_count"],
            "forward_winner": case["normalized_winners"]["forward"],
            "reverse_winner": case["normalized_winners"]["reverse"],
            "consensus": c,
            "forward_confidence": case["pairwise_forward"].get("confidence"),
            "reverse_confidence": case["pairwise_reverse"].get("confidence"),
        })

    result = {
        "experiment": "story-v5-length-pressure-family-pairwise-v1",
        "isolation": {
            "exact_age": 4,
            "targets": TARGETS,
            "same_writer_model": base.WRITER_MODEL,
            "same_reasoning_effort": "medium",
            "same_temperature": 0.72,
            "same_seed_within_family": True,
            "editor_disabled": True,
            "blind_pairwise_judge": base.EDITOR_MODEL,
            "order_swapped": True,
        },
        "summary": summary,
        "consensus_wins": wins,
        "cases": cases,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-length-pressure-family-pairwise")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for case in cases:
        family = case["family"]
        for target in TARGETS:
            (out / f"{family}-{target}.txt").write_text(
                case["drafts"][str(target)]["story"] + "\n", encoding="utf-8"
            )

    print(json.dumps({
        "summary": summary,
        "consensus_wins": wins,
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
