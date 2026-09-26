from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_v5_length_pressure_family_pairwise_20260926 as fam
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED_BASE = 2026092630
TARGET = 500
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"

ENRICHMENTS = {
    "exploration_mystery": [
        {"after": 2, "beat": {"density":"develop","beat":"Tam saksının yanında dinlerken hafif bir esinti yerdeki kuru bir yaprağı sürükler; Deniz bir an sesi yapraktan sanır, fakat yaprak durduktan sonra tık sesi yeniden başka taraftan gelir."}},
        {"after": 5, "beat": {"density":"develop","beat":"Biraz daha güçlü bir esinti halkaları kısa süre daha hızlı tıklatır; Deniz sesin rüzgârın şiddetine göre değiştiğini davranışıyla fark eder."}},
    ],
    "friendship_social_problem": [
        {"after": 2, "beat": {"density":"develop","beat":"Deniz köprüyü geri koyarken oyuncak teknesi daralan yerde takılır; Ece de otobüsünü döndürmeye çalışırken aynı anda sıkışır, böylece iki ihtiyaç görünür hale gelir."}},
        {"after": 5, "beat": {"density":"develop","beat":"İlk ortak düzenlemeleri tam yetmez; otobüs döner ama teknenin burnu köprüye sürtünür, bu yüzden ikisi küçük bir ikinci ayar yapar."}},
    ],
    "emotional_development": [
        {"after": 2, "beat": {"density":"develop","beat":"Deniz tam uzaklaşacakken Ada'nın ayağıyla düşen küçük bir bloğu kendine doğru çekmeye çalıştığını görür; bu, Ada'nın neden dönmediğine dair ilk somut ipucudur."}},
        {"after": 5, "beat": {"density":"develop","beat":"Kuleyi birlikte doğrulturken bir blok yeniden kayar; Deniz bu kez Ada söylemeden elini uzatıp destek olur ve aralarındaki yanlış anlamanın çözüldüğü davranışla görünür."}},
    ],
    "everyday_fantastical_discovery": [
        {"after": 2, "beat": {"density":"develop","beat":"Deniz duvarın yanında duran parlak metal bir kapağın da ışık yansıttığını fark eder ve yıldızın ondan gelip gelmediğini kısa bir denemeyle kontrol eder; yansıma farklıdır."}},
        {"after": 5, "beat": {"density":"develop","beat":"Bulut ince bir an güneşi yarım kapatınca yıldız soluklaşıp küçülür; Deniz etkinin yalnız var-yok değil, ışığın gücüne göre de değiştiğini görür."}},
    ],
    "nature_environment": [
        {"after": 2, "beat": {"density":"develop","beat":"Deniz önce bir taşın gölge yapıp yapmadığını kontrol eder; taşı yerinden oynatmadan iki birikintinin kenarındaki ışığı karşılaştırır ve bunun farkı açıklamadığını görür."}},
        {"after": 6, "beat": {"density":"develop","beat":"Yaprak kaldırılınca su hemen düz gitmez; küçük bir çakılın çevresinden kıvrılarak akar, Deniz de dokunmadan yolunu takip eder."}},
    ],
}

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı premise'ten, aynı yaş hedefiyle üretilmiş iki hikâyeyi karşılaştır.

Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.
Sana hangi metnin zenginleştirilmiş spine'dan geldiği ve kelime sayıları verilmez.
Uzun olanı otomatik olarak tercih etme.

Öncelikler:
- doğal ve tutarlı hikâye akışı,
- çocuk ajansı,
- tam 4 yaşa uygunluk,
- sesli okuma ritmi,
- doğal Türkçe,
- closure,
- filler/tekrar olmaması,
- mikro olayların ana nedensellik zincirine organik bağlanması,
- olayların sırf metni uzatmak için eklenmiş görünmemesi,
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


def enriched_spine(family: str, baseline: list[dict]) -> list[dict]:
    inserts = ENRICHMENTS[family]
    out: list[dict] = []
    for idx, beat in enumerate(baseline):
        out.append(dict(beat))
        for ins in inserts:
            if ins["after"] == idx:
                out.append(dict(ins["beat"]))
    return out


def make_prompt(premise: str, spine: list[dict]) -> str:
    spine_text = "\n".join(
        f"{i+1}. [{beat['density']}] {beat['beat']}"
        for i, beat in enumerate(spine)
    )
    return (
        f"KONU:\n{premise}\n\n"
        f"HİKÂYE OMURGASI:\n{spine_text}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )


def generate(api_key: str, fixture: dict, spine: list[dict], seed: int) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=api_key,
        model=base.WRITER_MODEL,
        system_prompt=writer_system(),
        user_prompt=make_prompt(fixture["premise"], spine),
        temperature=0.72,
        max_tokens=None,
        seed=seed,
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


def judge(api_key: str, premise: str, a: str, b: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=api_key,
        model=base.EDITOR_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "premise": premise,
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
    cases = []
    total_cost = 0.0

    for i, fixture in enumerate(fam.FIXTURES):
        family = fixture["family"]
        seed = SEED_BASE + i * 100
        baseline_spine = fixture["spine"]
        richer_spine = enriched_spine(family, baseline_spine)

        baseline = generate(api_key, fixture, baseline_spine, seed)
        enriched = generate(api_key, fixture, richer_spine, seed)
        total_cost += baseline["cost_usd"] + enriched["cost_usd"]

        forward, c1 = judge(api_key, fixture["premise"], baseline["story"], enriched["story"], seed + 11)
        reverse, c2 = judge(api_key, fixture["premise"], enriched["story"], baseline["story"], seed + 12)
        total_cost += c1 + c2

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

        cases.append({
            "family": family,
            "baseline_spine": baseline_spine,
            "enriched_spine": richer_spine,
            "baseline": baseline,
            "enriched": enriched,
            "word_delta": enriched["word_count"] - baseline["word_count"],
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "normalized_winners": {
                "forward": fw,
                "reverse": rv,
                "consensus": consensus,
            },
            "judge_cost_usd": c1 + c2,
        })

    wins = {"baseline": 0, "enriched": 0, "TIE": 0, "INCONCLUSIVE": 0}
    summary = []
    for case in cases:
        consensus = case["normalized_winners"]["consensus"]
        wins[consensus] = wins.get(consensus, 0) + 1
        summary.append({
            "family": case["family"],
            "baseline_words": case["baseline"]["word_count"],
            "enriched_words": case["enriched"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": consensus,
            "forward_confidence": case["pairwise_forward"].get("confidence"),
            "reverse_confidence": case["pairwise_reverse"].get("confidence"),
            "baseline_filler_risk": case["pairwise_forward"].get("forced_or_filler_risk", {}).get("A"),
            "enriched_filler_risk": case["pairwise_forward"].get("forced_or_filler_risk", {}).get("B"),
        })

    deltas = [case["word_delta"] for case in cases]
    result = {
        "experiment": "story-v5-organic-spine-enrichment-multifamily-v1",
        "exact_age": 4,
        "target_words": TARGET,
        "writer": base.WRITER_MODEL,
        "judge": base.EDITOR_MODEL,
        "same_seed_within_family": True,
        "families": len(cases),
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": round(sum(deltas) / len(deltas), 2),
        "cases": cases,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-organic-spine-enrichment-multifamily")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for case in cases:
        family = case["family"]
        (out / f"{family}-baseline.txt").write_text(case["baseline"]["story"] + "\n", encoding="utf-8")
        (out / f"{family}-enriched.txt").write_text(case["enriched"]["story"] + "\n", encoding="utf-8")

    print(json.dumps({
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": result["mean_word_delta"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
