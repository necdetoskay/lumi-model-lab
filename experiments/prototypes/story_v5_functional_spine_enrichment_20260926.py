from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED = 2026092630
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"

BASELINE_SPINE = base.STORY_SPINE

FUNCTIONAL_SPINE = [
    {"density":"brief","beat":"Deniz akşamüstü balkonda oynarken kısa bir 'tık' sesi duyar ve başını kaldırır."},
    {"density":"develop","beat":"Ses yeniden gelir ama hemen kaybolur; Deniz çevresine bakar ve kaynağını bulmaya çalışır."},
    {"density":"develop","beat":"Önce yakınındaki saksının kenarına ve yerdeki küçük taşlara bakar; sesi onlardan sanır."},
    {"density":"develop","beat":"Deniz iki küçük taşı hafifçe birbirine dokundurup çıkan sesi dinler; bu ses aradığı ince tık değildir ve tam ardından gerçek tık başka taraftan gelir."},
    {"density":"develop","beat":"Deniz balkon korkuluğuna yaklaşır; rüzgâr estiğinde sesin biraz daha belirginleştiğini fark eder."},
    {"density":"develop","beat":"Tam kaynağı bulmaya çalışırken rüzgâr kısa süre durur ve tık sesi de kaybolur; Deniz acele etmeden aynı yerde bekler."},
    {"density":"anchor","beat":"Yeni bir esinti geldiğinde asılı küçük süsün metal halkalarından biri sallanıp diğerine dokunur ve aynı 'tık' sesi çıkar."},
    {"density":"anchor","beat":"Deniz birkaç esintiyi daha izler; rüzgâr durunca tıkırtının da durduğunu davranışıyla doğrular, anlatıcı bağlantıyı ders gibi açıklamaz."},
    {"density":"anchor","beat":"Deniz süsü çekip bırakmak yerine avucuyla hafifçe rüzgâr yapar; önce hızlı hareketin karışık sesini, sonra yavaş hareketin tek tek tıklarını deneyerek sesi oyuna dönüştürür."},
    {"density":"anchor","beat":"Kapanışta Deniz kendi ritmini dener; iki kısa tık ve bir uzun bekleme yapar, sonra gerçek rüzgârın verdiği cevabı dinler."},
]

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı premise'ten, aynı ana olay örgüsünden üretilmiş iki hikâyeyi karşılaştır.
Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.

Hangi metnin hangi spine tasarımından geldiğini ve kelime sayılarını bilmiyorsun.
Uzun olanı otomatik tercih etme.

Özellikle değerlendir:
- doğal nedensellik ve akış,
- çocuk ajansı,
- yaş uygunluğu ve sesli okuma ritmi,
- doğal Türkçe,
- kapanış,
- gereksiz tekrar/filler,
- eklenen mikro-zorlukların ana arayışı gerçekten ilerletip ilerletmediği,
- olayların sonradan kelime doldurmak için eklenmiş hissi verip vermediği,
- yeni canon/ilişki icadı olup olmadığı.

winner yalnız "A", "B" veya "TIE".

SADECE JSON:
{
  "winner":"A|B|TIE",
  "confidence":"low|medium|high",
  "scores":{
    "A":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"naturalness":1,"closure":1,"economy":1,"overall":1},
    "B":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"naturalness":1,"closure":1,"economy":1,"overall":1}
  },
  "forced_or_filler_risk":{"A":"low|medium|high","B":"low|medium|high"},
  "serious_defects":{"A":[],"B":[]},
  "why":"en fazla üç kısa cümle"
}
""".strip()


def writer_system() -> str:
    prefix, _ = base.WRITER_SYSTEM.split("UZUNLUK:", 1)
    return (
        prefix.rstrip()
        + """

ÜRETİM HACMİ:
- Yaklaşık 500 kelimelik anlatı hacmi hedefle.
- Bu sayı kalite hedefi değildir; doğal hikâye kalitesi sayıdan önce gelir.
- Omurgadaki her anlamlı olayı doğal prose içinde yaşat.
- Hedefe yaklaşmak için omurgada olmayan yeni olay, canon, açıklama dolgusu veya mekanik tekrar ekleme.
- Hikâye doğal olarak tamamlandığında bitir.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
"""
    ).strip()


def prompt(spine: list[dict]) -> str:
    rows = "\n".join(
        f"{i+1}. [{b['density']}] {b['beat']}" for i, b in enumerate(spine)
    )
    return (
        f"KONU:\n{base.PREMISE}\n\n"
        f"HİKÂYE OMURGASI:\n{rows}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )


def generate(key: str, spine: list[dict]) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=key,
        model=base.WRITER_MODEL,
        system_prompt=writer_system(),
        user_prompt=prompt(spine),
        temperature=0.72,
        max_tokens=None,
        seed=SEED,
        request_class=WRITER_REQUEST_CLASS,
        structured_output=False,
    )
    return {
        "story": story,
        "word_count": count_words(story),
        "scan": base.scan(story),
        "usage": parse_usage(body).model_dump(mode="json"),
        "request_payload": payload,
        "cost_usd": float(parse_cost(body).usd or 0.0),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def compare(key: str, a: str, b: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=key,
        model=base.EDITOR_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={"exact_age":4,"premise":base.PREMISE,"story_A":a,"story_B":b},
        seed=seed,
        max_tokens=None,
        request_class=JUDGE_REQUEST_CLASS,
    )
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def normalize(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a
    if raw == "B":
        return b
    return "TIE"


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()

    baseline = generate(key, BASELINE_SPINE)
    functional = generate(key, FUNCTIONAL_SPINE)

    forward, c1 = compare(key, baseline["story"], functional["story"], SEED + 1)
    reverse, c2 = compare(key, functional["story"], baseline["story"], SEED + 2)

    fw = normalize(forward.get("winner"), "baseline", "functional")
    rv = normalize(reverse.get("winner"), "functional", "baseline")
    if fw == rv:
        consensus = fw
    elif fw == "TIE" and rv != "TIE":
        consensus = rv
    elif rv == "TIE" and fw != "TIE":
        consensus = fw
    else:
        consensus = "INCONCLUSIVE"

    result = {
        "experiment":"story-v5-functional-spine-enrichment-probe-v2",
        "premise":base.PREMISE,
        "target_words":500,
        "same_seed":True,
        "baseline":{"spine":BASELINE_SPINE, **baseline},
        "functional_enrichment":{
            "spine":FUNCTIONAL_SPINE,
            "contract":{
                "new_named_character":False,
                "new_relationship":False,
                "new_solution":False,
                "new_canon_bearing_fact":False,
                "micro_arc_must_advance_main_causality":True,
                "micro_arc":"hypothesis -> test -> rejection; uncertainty -> wait -> confirming evidence"
            },
            **functional,
        },
        "pairwise_forward":forward,
        "pairwise_reverse":reverse,
        "normalized_winners":{"forward":fw,"reverse":rv,"consensus":consensus},
        "word_delta":functional["word_count"] - baseline["word_count"],
        "total_cost_usd":round(baseline["cost_usd"] + functional["cost_usd"] + c1 + c2,6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    out=Path("runs/story-v5-functional-spine-enrichment")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"baseline.txt").write_text(baseline["story"]+"\n",encoding="utf-8")
    (out/"functional.txt").write_text(functional["story"]+"\n",encoding="utf-8")

    print(json.dumps({
        "baseline_words":baseline["word_count"],
        "functional_words":functional["word_count"],
        "word_delta":result["word_delta"],
        "forward":fw,
        "reverse":rv,
        "consensus":consensus,
        "total_cost_usd":result["total_cost_usd"],
    },ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
