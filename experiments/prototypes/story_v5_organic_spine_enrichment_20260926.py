from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED = 2026092620
TARGET = 500
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"

BASELINE_SPINE = base.STORY_SPINE

ENRICHED_SPINE = [
    {"density":"brief","beat":"Deniz akşamüstü balkonda oynarken kısa bir 'tık' sesi duyar ve başını kaldırır."},
    {"density":"develop","beat":"Ses yeniden gelir ama hemen kaybolur; Deniz çevresine bakar ve kaynağını bulmaya çalışır."},
    {"density":"develop","beat":"Önce yakınındaki saksının kenarına ve yerdeki küçük taşlara bakar; sesi onlardan sanır ama yeni tık başka taraftan gelir."},
    {"density":"develop","beat":"Tam saksının yanında dinlerken hafif bir esinti yerdeki kuru bir yaprağı sürükler; Deniz bir an sesi yapraktan sanır, fakat yaprak durduktan sonra tık sesi yeniden başka taraftan gelir."},
    {"density":"develop","beat":"Deniz balkon korkuluğuna yaklaşır; rüzgâr estiğinde sesin biraz daha belirginleştiğini fark eder."},
    {"density":"anchor","beat":"Asılı küçük süsün metal halkalarından biri rüzgârla sallanıp diğerine dokunur ve aynı 'tık' sesi çıkar."},
    {"density":"anchor","beat":"Deniz sesi birkaç kez dinler, rüzgâr durunca tıkırtının da durduğunu gözlemler; anlatıcı bunu açıklamaz, Deniz davranışıyla bağlantıyı kurar."},
    {"density":"develop","beat":"Biraz daha güçlü bir esinti halkaları kısa süre hızlı hızlı tıklatır; Deniz sesin rüzgârın gücüne göre değiştiğini fark eder ama bunu ders gibi açıklamaz."},
    {"density":"anchor","beat":"Deniz süsü çekip bırakmak yerine avucuyla hafifçe rüzgâr yapar; önce fazla hızlı, sonra daha yavaş deneyerek halkaların sesini kendi oyununa dönüştürür."},
    {"density":"anchor","beat":"Kapanışta Deniz kendi ritmini dener; iki kısa tık ve bir uzun bekleme yapar, sonra rüzgârın verdiği cevabı dinler."},
]

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı premise'ten üretilmiş iki hikâyeyi karşılaştır.

Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.

Sana hangi metnin hangi spine tasarımından geldiği ve kelime sayıları verilmez.
Uzun olanı otomatik olarak tercih etme.

Öncelikler:
- doğal ve tutarlı hikâye akışı,
- çocuk ajansı,
- sesli okuma ritmi,
- tam 4 yaşa uygunluk,
- doğal Türkçe,
- closure,
- filler/tekrar olmaması,
- olayların zorla eklenmiş görünmemesi,
- yan/mikro olayların ana nedensellik zincirine doğal bağlanması,
- yeni canon veya gereksiz karakter/ilişki icat edilmemesi.

winner yalnız "A", "B" veya "TIE" olabilir.

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


def make_prompt(spine: list[dict]) -> str:
    spine_text = "\n".join(
        f"{i+1}. [{beat['density']}] {beat['beat']}"
        for i, beat in enumerate(spine)
    )
    return (
        f"KONU:\n{base.PREMISE}\n\n"
        f"HİKÂYE OMURGASI:\n{spine_text}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )


def generate(api_key: str, spine: list[dict]) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=api_key,
        model=base.WRITER_MODEL,
        system_prompt=writer_system(),
        user_prompt=make_prompt(spine),
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


def judge(api_key: str, a: str, b: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=api_key,
        model=base.EDITOR_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "premise": base.PREMISE,
            "story_A": a,
            "story_B": b,
        },
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
    api_key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()

    baseline = generate(api_key, BASELINE_SPINE)
    enriched = generate(api_key, ENRICHED_SPINE)

    forward, c1 = judge(api_key, baseline["story"], enriched["story"], SEED + 1)
    reverse, c2 = judge(api_key, enriched["story"], baseline["story"], SEED + 2)

    fw = normalize(forward.get("winner"), "baseline", "enriched")
    rv = normalize(reverse.get("winner"), "enriched", "baseline")
    if fw == rv:
        consensus = fw
    elif fw == "TIE" and rv != "TIE":
        consensus = rv
    elif rv == "TIE" and fw != "TIE":
        consensus = fw
    else:
        consensus = "INCONCLUSIVE"

    result = {
        "experiment": "story-v5-organic-spine-enrichment-probe-v1",
        "premise": base.PREMISE,
        "writer": base.WRITER_MODEL,
        "judge": base.EDITOR_MODEL,
        "target_words": TARGET,
        "reasoning": "medium",
        "same_seed": True,
        "baseline": {
            "spine": BASELINE_SPINE,
            **baseline,
        },
        "enriched": {
            "spine": ENRICHED_SPINE,
            "enrichment_notes": [
                "one ambient false-clue micro-event using an ordinary dry leaf",
                "one wind-strength variation that deepens observation",
                "no new character, relationship, solution, or canon-bearing fact"
            ],
            **enriched,
        },
        "pairwise_forward": forward,
        "pairwise_reverse": reverse,
        "normalized_winners": {
            "forward": fw,
            "reverse": rv,
            "consensus": consensus,
        },
        "word_delta": enriched["word_count"] - baseline["word_count"],
        "total_cost_usd": round(baseline["cost_usd"] + enriched["cost_usd"] + c1 + c2, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-organic-spine-enrichment")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "baseline.txt").write_text(baseline["story"] + "\n", encoding="utf-8")
    (out / "enriched.txt").write_text(enriched["story"] + "\n", encoding="utf-8")

    print(json.dumps({
        "baseline_words": baseline["word_count"],
        "enriched_words": enriched["word_count"],
        "word_delta": result["word_delta"],
        "forward": fw,
        "reverse": rv,
        "consensus": consensus,
        "total_cost_usd": result["total_cost_usd"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
