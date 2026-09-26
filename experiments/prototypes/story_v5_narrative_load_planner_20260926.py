from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

PLANNER_MODEL = "openai/gpt-5.6-sol"
WRITER_MODEL = base.WRITER_MODEL
JUDGE_MODEL = base.EDITOR_MODEL
SEED = 2026092650

PLANNER_SYSTEM = r"""
Sen çocuk hikâyesi için yalnızca STORY SPINE tasarlayan bir planlayıcısın.
Düzyazı hikâye yazma.

Hedef okur: tam 4 yaş, yetişkin tarafından sesli okuma.
Nominal üretim hedefi yaklaşık 500 kelimedir fakat kalite kelime sayısından önemlidir.

Görevin, verilen premise'i BAŞTAN doğal olarak yeterli anlatı yüküne sahip hale getiren bir spine üretmek.
Bitmiş, ince bir spine'a sonradan filler ekleme mantığı kullanma.

NARRATIVE LOAD KURALI:
- 1 ana arc zorunlu.
- Premise doğal olarak kaldırıyorsa en fazla 1 supporting micro-thread kullan.
- Supporting thread yeni named character, aile/ilişki canon'u, dünya bilgisi veya ayrı çözüm yaratamaz.
- Supporting thread ana olayla aynı ortam/nesne/neden üzerinden organik kesişmeli.
- Supporting thread'in setup -> friction/change -> convergence/payoff izi olmalı.
- Ana arc'ı geciktirmek için boş sahne ekleme.
- Aynı işlevi tekrar eden beat ekleme.
- Her beat hikâyede yeni bir gözlem, eylem, karar, sonuç veya ilişki değişimi taşımalı.
- 4 yaş için karmaşık subplot, yetişkin muhakemesi veya açıklama dersi kurma.
- Finalde supporting thread açıksa ana arc ile doğal biçimde birleşmeli; ayrı epilog olmasın.
- EPİSTEMİK SIRA: Bir yanlış anlama, merak veya hipotez ana gerilimi taşıyorsa, karakter çözümü açıklayan kanıtı o yanlış anlamadan ÖNCE açıkça görmemeli veya bilmemeli. Bilgi karaktere doğal sırayla açılmalı.
- NEDENSEL KURAL: Spine bir fiziksel veya duygusal neden-sonuç kuralı kurduğunda sonraki beat'ler onu sebepsiz bozup geciktiremez; kural ancak spine içinde açık yeni bir neden varsa değişebilir.
- DURUM SÜREKLİLİĞİ: Toplanan, bırakılan, kapanan, taşınan veya tamamlanan bir nesne/eylem sonraki beat'te açıklamasız geri alınamaz. Bir prop sırf payoff için yeniden kullanılamaz.

Spine 8-12 beat olabilir. Beat sayısını hedef sayı için değil, anlatı yükü için seç.
Her beat:
- density: brief|develop|anchor
- function: setup|signal|hypothesis|test|complication|observation|decision|payoff|closure
- beat: tek somut olay cümlesi

SADECE JSON:
{
  "design_rationale":"kısa açıklama",
  "supporting_thread":{
    "used":true,
    "description":"kısa açıklama veya boş",
    "why_it_belongs":"kısa açıklama veya boş"
  },
  "spine":[
    {"density":"brief|develop|anchor","function":"...","beat":"..."}
  ]
}
""".strip()

WRITER_SYSTEM = (
    base.WRITER_SYSTEM.split("UZUNLUK:", 1)[0].rstrip()
    + r"""

ÜRETİM HACMİ:
- Yaklaşık 500 kelimelik anlatı hacmi hedefle.
- Bu sayı kalite hedefi değildir; doğal hikâye kalitesi sayıdan önce gelir.
- Spine'daki her beat'in hikâyedeki işlevini yaşat; beat listesini mekanik olarak prose'a çevirme.
- Spine'da kurulmuş neden-sonuç kuralını prose içinde değiştirme, geciktirme veya yeni açıklamayla yeniden yorumlama.
- Karakterin bildiği/gördüğü bilgi sırasını koru; sonradan gelecek açıklayıcı kanıtı erkenden görünür kılma.
- Toplanmış, bırakılmış, taşınmış veya tamamlanmış bir prop/eylemi açıklamasız geri alma; sırf kapanış için state'i geri sarma.
- Hedefe yaklaşmak için spine dışında yeni olay/canon/filler ekleme.
- Hikâye doğal olarak tamamlandığında bitir.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
"""
).strip()

PAIRWISE_SYSTEM = r"""
Sen bağımsız bir Türkçe çocuk kitabı kalite yargıcısın.
Aynı premise'ten üretilmiş iki bitmiş hikâyeyi karşılaştır.
Hedef okur tam 4 yaş ve metin yetişkin tarafından sesli okunacak.
Hangi spine/planner yolundan geldiklerini ve kelime sayılarını bilmiyorsun.
Uzun metni otomatik tercih etme.

Değerlendir:
- doğal nedensellik ve coherence,
- çocuk ajansı,
- yaş uygunluğu,
- sesli okuma,
- doğal Türkçe,
- pacing,
- closure,
- economy/filler,
- olayların organikliği,
- supporting thread varsa ana hikâyeye gerçekten ait hissedip hissetmediği.

winner yalnız A|B|TIE.

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


def render_spine(spine: list[dict]) -> str:
    return "\n".join(
        f"{i+1}. [{b.get('density','develop')}] [{b.get('function','beat')}] {b['beat']}"
        for i,b in enumerate(spine)
    )


def generate_story(key: str, spine: list[dict], seed: int) -> dict:
    started=time.perf_counter()
    story,body,payload=call_openrouter(
        api_key=key,
        model=WRITER_MODEL,
        system_prompt=WRITER_SYSTEM,
        user_prompt=(
            f"KONU:\n{base.PREMISE}\n\n"
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
        "story":story,
        "word_count":count_words(story),
        "scan":base.scan(story),
        "usage":parse_usage(body).model_dump(mode="json"),
        "cost_usd":float(parse_cost(body).usd or 0.0),
        "elapsed_seconds":round(time.perf_counter()-started,3),
        "request_payload":payload,
    }


def pairwise(key: str, a: str, b: str, seed: int) -> tuple[dict,float]:
    result,meta=structured_call(
        api_key=key,
        model=JUDGE_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={"exact_age":4,"premise":base.PREMISE,"story_A":a,"story_B":b},
        seed=seed,
        max_tokens=None,
        request_class="editorial_audit",
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

    plan,plan_meta=structured_call(
        api_key=key,
        model=PLANNER_MODEL,
        system=PLANNER_SYSTEM,
        payload={
            "exact_age":4,
            "reading_mode":"READ_ALOUD",
            "nominal_target_words":500,
            "premise":base.PREMISE,
            "constraints":{
                "no_new_named_character":True,
                "no_new_relationship_canon":True,
                "supporting_thread_optional":True,
                "quality_over_word_count":True
            }
        },
        seed=SEED,
        max_tokens=None,
        request_class="editorial_audit",
    )
    planned_spine=plan.get("spine") or []
    if not (8 <= len(planned_spine) <= 12):
        raise RuntimeError(f"planner_spine_size_invalid:{len(planned_spine)}")

    baseline=generate_story(key,base.STORY_SPINE,SEED+1)
    planned=generate_story(key,planned_spine,SEED+1)

    forward,c1=pairwise(key,baseline["story"],planned["story"],SEED+2)
    reverse,c2=pairwise(key,planned["story"],baseline["story"],SEED+3)

    fw=normalize(forward.get("winner"),"baseline","planned")
    rv=normalize(reverse.get("winner"),"planned","baseline")
    if fw==rv:
        consensus=fw
    elif fw=="TIE" and rv!="TIE":
        consensus=rv
    elif rv=="TIE" and fw!="TIE":
        consensus=fw
    else:
        consensus="INCONCLUSIVE"

    plan_cost=float(((plan_meta.get("cost") or {}).get("usd")) or 0.0)
    result={
        "experiment":"story-v5-narrative-load-planner-probe-v1",
        "premise":base.PREMISE,
        "planner_model":PLANNER_MODEL,
        "writer_model":WRITER_MODEL,
        "judge_model":JUDGE_MODEL,
        "planner_output":plan,
        "baseline":{"spine":base.STORY_SPINE,**baseline},
        "planned":{"spine":planned_spine,**planned},
        "word_delta":planned["word_count"]-baseline["word_count"],
        "pairwise_forward":forward,
        "pairwise_reverse":reverse,
        "normalized_winners":{"forward":fw,"reverse":rv,"consensus":consensus},
        "cost_usd":{
            "planner":plan_cost,
            "baseline_writer":baseline["cost_usd"],
            "planned_writer":planned["cost_usd"],
            "judges":c1+c2,
        },
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    result["cost_usd"]["total"]=round(sum(result["cost_usd"].values()),6)

    out=Path("runs/story-v5-narrative-load-planner")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"baseline.txt").write_text(baseline["story"]+"\n",encoding="utf-8")
    (out/"planned.txt").write_text(planned["story"]+"\n",encoding="utf-8")
    (out/"planned-spine.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print(json.dumps({
        "planner_beats":len(planned_spine),
        "supporting_thread":plan.get("supporting_thread"),
        "baseline_words":baseline["word_count"],
        "planned_words":planned["word_count"],
        "word_delta":result["word_delta"],
        "forward":fw,
        "reverse":rv,
        "consensus":consensus,
        "cost_usd":result["cost_usd"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
