from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

TARGETS = [500, 600, 700, 800]
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"
SEED = 2026092601

QUALITY_JUDGE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı konu ve aynı hikâye omurgasından üretilmiş taslakları tek tek değerlendiriyorsun.

Hedef okur: tam 4 yaş; metin bir yetişkin tarafından sesli okunacak.

ÖNEMLİ:
- Sana yazarın hedeflediği kelime sayısı verilmez ve verilmemelidir.
- Uzunluğu kendi başına ödüllendirme.
- Kısa ama eksiksiz bir hikâye, uzun ama dolgulu bir hikâyeden daha iyidir.
- Gereksiz tekrar, filler, aynı işlevli sahne uzatması ve açıklama kaliteyi düşürür.
- Omurgadaki olay sırasını, karakter ajansını ve doğal kapanışı korumak önemlidir.
- Yeni canon, yeni çözüm veya sırf uzatmak için yeni olay eklenmesi kusurdur.

Her boyutu 1-10 arasında puanla:
- narrative_coherence: neden-sonuç ve bütünlük
- age_fit: 4 yaş için uygunluk
- read_aloud: sesli okuma doğallığı
- child_agency: Deniz'in gözlem/eylem üzerinden ilerlemesi
- pacing: ritim ve sahne yoğunluğu dengesi
- language_naturalness: doğal Türkçe
- closure: hikâyeye özgü tatmin edici bitiş
- economy: gereksiz dolgu/tekrar olmaması
- overall_quality: bütünsel yayın kalitesi

Ayrıca filler_or_repetition_risk değerini low|medium|high olarak ver.
Serious yayın kusuru görürsen blocking_defects listesine ekle.
Sadece gerçek kusur yaz; sabit sayıda kusur üretme.

SADECE JSON:
{
  "scores": {
    "narrative_coherence": 1,
    "age_fit": 1,
    "read_aloud": 1,
    "child_agency": 1,
    "pacing": 1,
    "language_naturalness": 1,
    "closure": 1,
    "economy": 1,
    "overall_quality": 1
  },
  "filler_or_repetition_risk": "low|medium|high",
  "blocking_defects": [
    {"class": "string", "quote": "kısa birebir alıntı", "why": "kısa gerekçe"}
  ],
  "strengths": ["en fazla 3 kısa madde"],
  "summary": "tek cümle"
}
""".strip()


def writer_system(target: int) -> str:
    marker = "UZUNLUK:"
    prefix, _ = base.WRITER_SYSTEM.split(marker, 1)
    volume = f"""
ÜRETİM HACMİ:
- Yaklaşık {target} kelimelik anlatı hacmi hedefle.
- Bu sayı bir kalite hedefi değildir; doğal hikâye kalitesi sayıdan önce gelir.
- Hedefe yaklaşmak için yeni olay, yeni canon, gereksiz açıklama, sıfat dolgusu veya mekanik tekrar ekleme.
- Mevcut omurgadaki önemli anları gerektiği kadar yaşat; doğal hikâye tamamlanınca bitir.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
""".strip()
    return (prefix.rstrip() + "\n\n" + volume).strip()


def make_user_prompt() -> str:
    spine_text = "\n".join(
        f"{i+1}. [{beat['density']}] {beat['beat']}"
        for i, beat in enumerate(base.STORY_SPINE)
    )
    return (
        f"KONU:\n{base.PREMISE}\n\n"
        f"HİKÂYE OMURGASI:\n{spine_text}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )


def run_one(api_key: str, target: int) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=api_key,
        model=base.WRITER_MODEL,
        system_prompt=writer_system(target),
        user_prompt=make_user_prompt(),
        temperature=0.72,
        max_tokens=None,
        seed=SEED,
        request_class=WRITER_REQUEST_CLASS,
        structured_output=False,
    )

    scan = base.scan(story)
    judge, judge_meta = structured_call(
        api_key=api_key,
        model=base.EDITOR_MODEL,
        system=QUALITY_JUDGE_SYSTEM,
        payload={
            "exact_age": 4,
            "premise": base.PREMISE,
            "story_spine": base.STORY_SPINE,
            "story": story,
        },
        seed=SEED + 100,
        max_tokens=None,
        request_class=JUDGE_REQUEST_CLASS,
    )

    writer_cost = float(parse_cost(body).usd or 0.0)
    judge_cost = float(((judge_meta.get("cost") or {}).get("usd")) or 0.0)

    return {
        "internal_generation_target": target,
        "word_count": count_words(story),
        "scan": scan,
        "story": story,
        "quality_judge": judge,
        "writer_usage": parse_usage(body).model_dump(mode="json"),
        "writer_request_payload": payload,
        "cost_usd": {
            "writer": writer_cost,
            "judge": judge_cost,
            "total": writer_cost + judge_cost,
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()

    cases = [run_one(api_key, target) for target in TARGETS]

    ranked = sorted(
        cases,
        key=lambda item: (
            float(((item.get("quality_judge") or {}).get("scores") or {}).get("overall_quality") or 0),
            float(((item.get("quality_judge") or {}).get("scores") or {}).get("economy") or 0),
        ),
        reverse=True,
    )

    result = {
        "experiment": "story-v5-internal-length-pressure-probe-v1",
        "isolation": {
            "same_premise": True,
            "same_story_spine": True,
            "same_writer_model": base.WRITER_MODEL,
            "same_reasoning_effort": "medium",
            "same_temperature": 0.72,
            "same_seed": SEED,
            "editor_disabled": True,
            "only_intended_writer_variable": "internal_generation_target",
        },
        "premise": base.PREMISE,
        "story_spine": base.STORY_SPINE,
        "targets": TARGETS,
        "cases": cases,
        "ranking_by_blind_quality_judge": [
            {
                "internal_generation_target": item["internal_generation_target"],
                "word_count": item["word_count"],
                "overall_quality": ((item.get("quality_judge") or {}).get("scores") or {}).get("overall_quality"),
                "economy": ((item.get("quality_judge") or {}).get("scores") or {}).get("economy"),
                "filler_or_repetition_risk": (item.get("quality_judge") or {}).get("filler_or_repetition_risk"),
                "blocking_defects": len((item.get("quality_judge") or {}).get("blocking_defects") or []),
            }
            for item in ranked
        ],
        "total_cost_usd": round(sum(item["cost_usd"]["total"] for item in cases), 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-length-pressure-probe")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for item in cases:
        (out / f"target-{item['internal_generation_target']}.txt").write_text(
            item["story"] + "\n", encoding="utf-8"
        )

    print(json.dumps({
        "cases": [
            {
                "target": item["internal_generation_target"],
                "words": item["word_count"],
                "overall_quality": ((item.get("quality_judge") or {}).get("scores") or {}).get("overall_quality"),
                "economy": ((item.get("quality_judge") or {}).get("scores") or {}).get("economy"),
                "filler_risk": (item.get("quality_judge") or {}).get("filler_or_repetition_risk"),
                "blocking_defects": len((item.get("quality_judge") or {}).get("blocking_defects") or []),
                "cost_usd": item["cost_usd"]["total"],
            }
            for item in cases
        ],
        "ranking": result["ranking_by_blind_quality_judge"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
