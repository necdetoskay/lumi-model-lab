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

SEED_BASE = 2026092640
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"

FAMILIES = {
    "exploration_mystery": {
        "micro_arc": [
            {"density":"develop","beat":"Deniz korkuluğa yaklaşırken küçük bir serçe korkuluğa konar ve aynı anda bir tık duyulur; Deniz bir an sesin kuştan geldiğini düşünür."},
            {"density":"develop","beat":"Deniz serçeyi sessizce izler; kuş birkaç kez zıplar ama aradığı ince tık çıkmaz, sonra kanatlanıp gider."},
            {"density":"develop","beat":"Serçe gittikten sonra aynı tık bu kez yukarıdan yeniden gelir; Deniz kuşu eleyip aramayı asılı süse doğru sürdürür."},
        ],
        "insert_after": 3,
    },
    "friendship_social_problem": {
        "micro_arc": [
            {"density":"develop","beat":"Deniz ve Ece ilk uzlaşma olarak köprüyü ortaya alıp yolu onun çevresinden döndürmeyi dener."},
            {"density":"develop","beat":"Otobüs bu kez döner ama teknenin burnu köprünün kenarına takılır; ikisi de ilk ortak çözümün tam olmadığını görür."},
            {"density":"develop","beat":"Yandaki karton evi biraz geriye alabileceklerini fark ederler; bu küçük değişiklik hem yolu genişletir hem köprünün altını açar ve son düzenlemeye geçerler."},
        ],
        "insert_after": 5,
    },
    "nature_environment": {
        "micro_arc": [
            {"density":"develop","beat":"Yaprak kalkınca su akmaya başlar ama birkaç parmak ileride küçük bir çakılın önünde kısa süre toplanır."},
            {"density":"develop","beat":"Deniz çakılı kaldırmak için uzanmaz; suyun kendi yolunu bulup bulmayacağını görmek için bekler."},
            {"density":"develop","beat":"Su çakılın iki yanından incecik dolaşıp yeniden birleşir; Deniz daha fazla müdahale etmesine gerek olmadığını görür ve akışı izlemeye devam eder."},
        ],
        "insert_after": 6,
    },
}

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı premise ve ana olay örgüsünden üretilmiş iki hikâyeyi karşılaştır.
Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.

Hangi metnin mikro-yan-yay içerdiğini ve kelime sayılarını bilmiyorsun.
Uzun olanı otomatik tercih etme.

Özellikle değerlendir:
- doğal akış ve neden-sonuç,
- çocuk ajansı,
- yaş uygunluğu,
- sesli okuma,
- doğal Türkçe,
- pacing ve closure,
- mini yan olayın ana hikâyeyi gerçekten ilerletmesi,
- mini yan olayın yapıştırılmış/filler gibi görünmemesi,
- setup -> complication -> payoff bütünlüğü,
- yeni kalıcı canon, ilişki veya gereksiz karakter yükü yaratmaması.

winner yalnız A, B veya TIE.

SADECE JSON:
{
  "winner":"A|B|TIE",
  "confidence":"low|medium|high",
  "scores":{
    "A":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"naturalness":1,"closure":1,"economy":1,"overall":1},
    "B":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"naturalness":1,"closure":1,"economy":1,"overall":1}
  },
  "micro_arc_quality":{"A":"none|weak|natural|strong","B":"none|weak|natural|strong"},
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
- Omurgada bir mini yan yay varsa onu özetleyip geçme; başlangıç, küçük zorluk ve sonucu doğal prose içinde görünür olsun.
- Yan yay ana hikâyeye geri bağlanmalı; ayrı bir hikâyeye dönüşmemeli.
- Omurgada olmayan yeni canon, açıklama dolgusu veya mekanik tekrar ekleme.
- Hikâye doğal olarak tamamlandığında bitir.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
"""
    ).strip()


def fixture_by_family(name: str) -> dict:
    return next(x for x in fam.FIXTURES if x["family"] == name)


def with_micro_arc(spine: list[dict], arc: list[dict], insert_after: int) -> list[dict]:
    out = []
    for idx, beat in enumerate(spine):
        out.append(dict(beat))
        if idx == insert_after:
            out.extend(dict(x) for x in arc)
    return out


def prompt(premise: str, spine: list[dict]) -> str:
    rows = "\n".join(f"{i+1}. [{b['density']}] {b['beat']}" for i,b in enumerate(spine))
    return f"KONU:\n{premise}\n\nHİKÂYE OMURGASI:\n{rows}\n\nBu omurgayı doğal bir çocuk hikâyesine dönüştür."


def generate(key: str, fixture: dict, spine: list[dict], seed: int) -> dict:
    started = time.perf_counter()
    story, body, payload = call_openrouter(
        api_key=key,
        model=base.WRITER_MODEL,
        system_prompt=writer_system(),
        user_prompt=prompt(fixture["premise"], spine),
        temperature=0.72,
        max_tokens=None,
        seed=seed,
        request_class=WRITER_REQUEST_CLASS,
        structured_output=False,
    )
    return {
        "story":story,
        "word_count":count_words(story),
        "scan":base.scan(story),
        "usage":parse_usage(body).model_dump(mode="json"),
        "request_payload":payload,
        "cost_usd":float(parse_cost(body).usd or 0.0),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }


def compare(key: str, fixture: dict, a: str, b: str, seed: int) -> tuple[dict,float]:
    result, meta = structured_call(
        api_key=key,
        model=base.EDITOR_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={"exact_age":4,"premise":fixture["premise"],"story_A":a,"story_B":b},
        seed=seed,
        max_tokens=None,
        request_class=JUDGE_REQUEST_CLASS,
    )
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def norm(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A": return a
    if raw == "B": return b
    return "TIE"


def main() -> None:
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    started=time.perf_counter()
    cases=[]
    total=0.0

    for i,(family,cfg) in enumerate(FAMILIES.items()):
        fixture=fixture_by_family(family)
        seed=SEED_BASE+i*100
        baseline_spine=fixture["spine"]
        arc_spine=with_micro_arc(baseline_spine,cfg["micro_arc"],cfg["insert_after"])

        baseline=generate(key,fixture,baseline_spine,seed)
        micro=generate(key,fixture,arc_spine,seed)
        total += baseline["cost_usd"] + micro["cost_usd"]

        fwd,c1=compare(key,fixture,baseline["story"],micro["story"],seed+11)
        rev,c2=compare(key,fixture,micro["story"],baseline["story"],seed+12)
        total += c1+c2

        fw=norm(fwd.get("winner"),"baseline","micro_arc")
        rv=norm(rev.get("winner"),"micro_arc","baseline")
        if fw==rv: consensus=fw
        elif fw=="TIE" and rv!="TIE": consensus=rv
        elif rv=="TIE" and fw!="TIE": consensus=fw
        else: consensus="INCONCLUSIVE"

        cases.append({
            "family":family,
            "baseline_spine":baseline_spine,
            "micro_arc":cfg["micro_arc"],
            "micro_arc_spine":arc_spine,
            "baseline":baseline,
            "micro_arc_story":micro,
            "word_delta":micro["word_count"]-baseline["word_count"],
            "pairwise_forward":fwd,
            "pairwise_reverse":rev,
            "normalized_winners":{"forward":fw,"reverse":rv,"consensus":consensus},
        })

    wins={"baseline":0,"micro_arc":0,"TIE":0,"INCONCLUSIVE":0}
    summary=[]
    for c in cases:
        k=c["normalized_winners"]["consensus"]
        wins[k]=wins.get(k,0)+1
        summary.append({
            "family":c["family"],
            "baseline_words":c["baseline"]["word_count"],
            "micro_arc_words":c["micro_arc_story"]["word_count"],
            "word_delta":c["word_delta"],
            "forward":c["normalized_winners"]["forward"],
            "reverse":c["normalized_winners"]["reverse"],
            "consensus":k,
            "forward_confidence":c["pairwise_forward"].get("confidence"),
            "reverse_confidence":c["pairwise_reverse"].get("confidence"),
        })

    result={
        "experiment":"story-v5-causal-micro-arc-probe-v1",
        "exact_age":4,
        "target_words":500,
        "writer":base.WRITER_MODEL,
        "judge":base.EDITOR_MODEL,
        "same_seed_within_family":True,
        "micro_arc_contract":{
            "shape":"setup -> complication -> payoff",
            "must_rejoin_main_plot":True,
            "must_change_evidence_choice_or_constraint":True,
            "durable_canon_change":False,
            "new_relationship":False,
            "purpose":"increase genuine narrative load, not prose padding",
        },
        "summary":summary,
        "consensus_wins":wins,
        "mean_word_delta":round(sum(c["word_delta"] for c in cases)/len(cases),2),
        "cases":cases,
        "total_cost_usd":round(total,6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    out=Path("runs/story-v5-causal-micro-arc")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for c in cases:
        (out/f"{c['family']}-baseline.txt").write_text(c["baseline"]["story"]+"\n",encoding="utf-8")
        (out/f"{c['family']}-micro-arc.txt").write_text(c["micro_arc_story"]["story"]+"\n",encoding="utf-8")

    print(json.dumps({
        "summary":summary,
        "consensus_wins":wins,
        "mean_word_delta":result["mean_word_delta"],
        "total_cost_usd":result["total_cost_usd"],
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
