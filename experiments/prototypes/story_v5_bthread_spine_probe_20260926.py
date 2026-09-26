from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED = 2026092640
WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
JUDGE_REQUEST_CLASS = "editorial_audit"

BASELINE_SPINE = base.STORY_SPINE

BTHREAD_SPINE = [
    {"density":"brief","beat":"Deniz akşamüstü balkonda üç küçük arabasını kartondan yaptığı kısa bir garajın önüne dizerken kısa bir 'tık' sesi duyar ve başını kaldırır."},
    {"density":"develop","beat":"Ses yeniden gelir ama hemen kaybolur; Deniz çevresine bakar ve kaynağını bulmaya çalışır."},
    {"density":"develop","beat":"Hafif bir esinti garajın ince karton çatısını kaldırır; Deniz çatıyı yerine koyup küçük bir taşı kenarına ağırlık yapar, fakat aradığı tık sesi yine başka taraftan gelir."},
    {"density":"develop","beat":"Deniz saksının kenarındaki ve yerdeki küçük taşlara bakar; iki taşı hafifçe birbirine dokundurur ama çıkan ses aradığı tık değildir."},
    {"density":"develop","beat":"Sonra balkon korkuluğuna yaklaşır; rüzgâr estiğinde sesin biraz daha belirginleştiğini fark eder."},
    {"density":"anchor","beat":"Asılı küçük süsün metal halkalarından biri rüzgârla sallanıp diğerine dokunur ve aynı 'tık' sesi çıkar."},
    {"density":"anchor","beat":"Deniz birkaç esintiyi izler; rüzgâr durunca tıkırtının da durduğunu davranışıyla doğrular."},
    {"density":"develop","beat":"Deniz garajına döndüğünde karton çatının taş sayesinde yerinde kaldığını görür; artık rüzgârın iki farklı şeyi iki farklı biçimde etkilediğini gözlemlemiştir, fakat anlatıcı bunu ders gibi açıklamaz."},
    {"density":"anchor","beat":"Deniz süsü çekip bırakmak yerine avucuyla hafifçe rüzgâr yapar; halkalar yeniden tıklar ve bu ses küçük bir oyuna dönüşür."},
    {"density":"anchor","beat":"Deniz arabalarını garajdan sırayla çıkarırken iki kısa tıkı 'başla' işareti gibi kullanır; sonra elini durdurup gerçek rüzgârın vereceği cevabı bekler."},
    {"density":"anchor","beat":"Kapanışta gerçek rüzgâr halkaları tıklatınca Deniz son arabayı yola çıkarır ve oyunu süsün ritmiyle sürdürür."},
]

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı ana premise'ten üretilmiş iki hikâyeyi karşılaştır.
Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.

Hangi metnin hangi spine tasarımından geldiğini ve kelime sayılarını bilmiyorsun.
Uzun olanı otomatik tercih etme.

Özellikle değerlendir:
- ana hikâye akışı ve nedensellik,
- çocuk ajansı,
- 4 yaşa uygunluk,
- sesli okuma ritmi ve doğal Türkçe,
- kapanış,
- filler/tekrar,
- varsa yan mini-arc'ın doğal kurulup ana hikâyeyle organik kesişmesi,
- yan akışın sırf metni uzatmak için eklenmiş hissi verip vermemesi,
- ana keşfi gölgeleyip gölgelemediği,
- yeni canon/ilişki icadı.

winner yalnız "A", "B" veya "TIE" olabilir.

SADECE JSON:
{
  "winner":"A|B|TIE",
  "confidence":"low|medium|high",
  "scores":{
    "A":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"naturalness":1,"closure":1,"economy":1,"overall":1},
    "B":{"coherence":1,"age_fit":1,"read_aloud":1,"agency":1,"pacing":1,"naturalness":1,"closure":1,"economy":1,"overall":1}
  },
  "b_thread_fit":{"A":"none|weak|natural|excellent","B":"none|weak|natural|excellent"},
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
- Omurgadaki ana olay ile varsa gündelik yan mini-arc'ı doğal prose içinde yaşat.
- Yan mini-arc ana hikâyeyi kesmemeli veya ayrı bir hikâyeye dönüşmemeli.
- Hedefe yaklaşmak için omurgada olmayan yeni olay, canon, açıklama dolgusu veya mekanik tekrar ekleme.
- Hikâye doğal olarak tamamlandığında bitir.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
"""
    ).strip()


def prompt(spine: list[dict]) -> str:
    rows = "\n".join(f"{i+1}. [{b['density']}] {b['beat']}" for i,b in enumerate(spine))
    return (
        f"KONU:\n{base.PREMISE}\n\n"
        f"HİKÂYE OMURGASI:\n{rows}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )


def generate(key: str, spine: list[dict]) -> dict:
    started=time.perf_counter()
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
        "story":story,
        "word_count":count_words(story),
        "scan":base.scan(story),
        "usage":parse_usage(body).model_dump(mode="json"),
        "request_payload":payload,
        "cost_usd":float(parse_cost(body).usd or 0.0),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }


def compare(key: str, a: str, b: str, seed: int) -> tuple[dict,float]:
    result,meta=structured_call(
        api_key=key,
        model=base.EDITOR_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={"exact_age":4,"premise":base.PREMISE,"story_A":a,"story_B":b},
        seed=seed,
        max_tokens=None,
        request_class=JUDGE_REQUEST_CLASS,
    )
    return result,float(((meta.get("cost") or {}).get("usd")) or 0.0)


def normalize(raw: str, a: str, b: str) -> str:
    raw=str(raw or "").upper()
    if raw=="A": return a
    if raw=="B": return b
    return "TIE"


def main() -> None:
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    started=time.perf_counter()

    baseline=generate(key,BASELINE_SPINE)
    bthread=generate(key,BTHREAD_SPINE)

    forward,c1=compare(key,baseline["story"],bthread["story"],SEED+1)
    reverse,c2=compare(key,bthread["story"],baseline["story"],SEED+2)

    fw=normalize(forward.get("winner"),"baseline","bthread")
    rv=normalize(reverse.get("winner"),"bthread","baseline")
    if fw==rv:
        consensus=fw
    elif fw=="TIE" and rv!="TIE":
        consensus=rv
    elif rv=="TIE" and fw!="TIE":
        consensus=fw
    else:
        consensus="INCONCLUSIVE"

    result={
        "experiment":"story-v5-bthread-spine-probe-v1",
        "premise":base.PREMISE,
        "target_words":500,
        "same_seed":True,
        "baseline":{"spine":BASELINE_SPINE,**baseline},
        "bthread":{
            "spine":BTHREAD_SPINE,
            "contract":{
                "thread":"toy-car cardboard garage",
                "canon_bearing":False,
                "new_named_character":False,
                "setup":"cardboard garage during existing play",
                "complication":"wind lifts roof; Deniz stabilizes it",
                "intersection":"wind becomes shared causal element with tık mystery",
                "payoff":"tık rhythm becomes start signal for car play",
                "must_not_solve_main_mystery":True
            },
            **bthread,
        },
        "pairwise_forward":forward,
        "pairwise_reverse":reverse,
        "normalized_winners":{"forward":fw,"reverse":rv,"consensus":consensus},
        "word_delta":bthread["word_count"]-baseline["word_count"],
        "total_cost_usd":round(baseline["cost_usd"]+bthread["cost_usd"]+c1+c2,6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    out=Path("runs/story-v5-bthread-spine-probe")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"baseline.txt").write_text(baseline["story"]+"\n",encoding="utf-8")
    (out/"bthread.txt").write_text(bthread["story"]+"\n",encoding="utf-8")
    print(json.dumps({
        "baseline_words":baseline["word_count"],
        "bthread_words":bthread["word_count"],
        "word_delta":result["word_delta"],
        "forward":fw,
        "reverse":rv,
        "consensus":consensus,
        "total_cost_usd":result["total_cost_usd"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
