from __future__ import annotations
import json, os, re, time
from pathlib import Path
from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

WRITER_MODEL="anthropic/claude-sonnet-5"
EDITOR_MODEL="openai/gpt-5.6-sol"
FINAL_JUDGE_MODEL="anthropic/claude-sonnet-5"

PREMISE="""Deniz, yağmurdan sonra bahçede suyla dolmuş küçük bir çukuru fark eder. Çukurun yanında mahsur kalmış oyuncak bir tekne bulur ve teknenin yeniden yüzebilmesi için çevredeki doğal malzemelerle küçük bir su yolu açmaya çalışır."""

STORY_SPINE=[
  "Yağmurdan sonra Deniz bahçedeki yeni su birikintisini fark eder.",
  "Küçük oyuncak teknenin yaprakların arasında sıkıştığını görür.",
  "Tekneyi hareket ettirmeyi dener; kısa süre ilerler ama yeniden takılır.",
  "Deniz tekne için suyun devam edebileceği küçük bir yol açmayı düşünür ve çevresindeki basit malzemelerle dener.",
  "İlk denemesi istediği gibi çalışmaz; Deniz başka bir yol arar.",
  "Yeni denemesinde su küçük bir yol boyunca ilerler ve tekne yeniden yüzmeye başlar. Anne yalnızca yanında yardım eder; çözümü Deniz bulur.",
  "Deniz yolun sonundaki belirli bir yaprağı veya taşı liman yapar; teknenin oraya varmasıyla oyun devam eder."
]

WRITER_SYSTEM=r"""
Sen Türkçe yazan, deneyimli bir çocuk kitabı yazarısın.
Tam 4 yaşındaki bir çocuğa bir yetişkin tarafından sesli okunacak doğal, sıcak ve eğlenceli bir hikâye yaz.

Sana bir HİKÂYE OMURGASI verilecek. Omurga düzyazı değildir ve sahne planı değildir.
Omurganın olay sırasını ve neden-sonuç ilişkisini koru; fakat onu madde madde prose'a çevirme.
Diyalogları, küçük ayrıntıları, ritmi ve doğal geçişleri sen yarat.
Omurgada olmayan yeni aile/ilişki canon'u icat etme.
Anne çözümü bulan öğretmen olmasın; gerekiyorsa fiziksel olarak yardım etsin ama ana fikir Deniz'den gelsin.

SERT KISITLAR:
1. Şu yetişkin/edebî kalıpları kullanma:
   "razı oldu", "dikkatini verdi", "dikkatini topladı", "büründü", "geriledi",
   "sonuç olarak", "içinden geçirdi", "derin bir nefes aldı", "gözleri parladı".
   "aslında", "adeta" kullanma. "sanki" en fazla 1 kez.

2. ŞABLON TEKRARI KONTROLÜ:
   Aynı anlatı işlevini gören cümle veya paragraf iskeletini mekanik biçimde tekrar etme.
   Özellikle her yeni denemeyi aynı [eylem + sonuç/olumsuzlama] yapısıyla kurma.
   Aynı iskelet iki kez kullanılabilir; sonraki benzer anlarda doğal biçimde çeşitlendir.
   Ancak çocuk oyunu, ritim, tekrar eden espri veya bilinçli motif amacı taşıyan tekrarları sırf tekrar diye bozma.

3. Anne Deniz'in hayal gücünü gerçeklik dersi vererek düzeltmesin.
   Sokratik soru zinciri kurmasın; "ne yapmalı dersin?", "sence ne yapabiliriz?",
   "neden olabilir?", "değil mi?" gibi çözümü çocuğa sınav sorusu gibi sorduran kalıpları kullanma.
   Oyuna katılsın, şaşırsın, gülsün veya kısa ve doğal biçimde yardım etsin.

4. Önceki bir kısıtla çelişmemek için savunmacı açıklamalar ekleme.
   Eylemi baştan tutarlı yaz.

5. Bir cümlede ikiden fazla eylemi art arda virgülle sıralama.
   Cümleler sesli okumada tek nefeste doğal gelsin.

6. Kapanış genel ders, güvence veya slogan olmasın.
   Hikâyeye özgü somut bir hareket, tekrar eden espri veya Deniz'in kısa sözüyle bitsin.

7. Register baştan sona sade ve somut kalsın.
   Anlatıcı karakterlerin zihnini açıklamasın; gözlemlenebilir eylem ve diyalog yaz.

8. En fazla 1-2 somut, yaşa uygun benzetme kullan.

9. Türkçe ek/iyelik uyumuna özellikle dikkat et; doğal olmayan sözcük dizimi üretme.

UZUNLUK:
- Hedef: 475-525 kelime.
- Hard aralık: 375-625 kelime.
- 375 kelimenin altında bitirme.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
""".strip()

EDITOR_SYSTEM=r"""
Sen bağımsız Türkçe çocuk kitabı editörüsün.
Tam yeniden yazım yapma; yalnız gerçek kusurları en küçük anlamlı kapsamda düzelt.

Kontrol et:
1. yetişkin/resmî/edebî register,
2. mekanik anlatı iskeleti tekrarı; bilinçli ritim/oyun tekrarını kusur sayma,
3. ebeveynin çocuğun hayalini düzeltmesi veya öğretmen/sınav tonu,
   özellikle "ne yapmalı dersin?", "sence ne yapabiliriz?", "neden olabilir?",
   "değil mi?" gibi çözümü çocuğa sınav sorusu gibi sorduran kalıplar,
4. savunmacı iç-tutarlılık açıklamaları,
5. aşırı eylem yığılması / sesli okuma sorunu,
6. klişe/genel kapanış,
7. gereksiz iç-dünya yorumu,
8. register tutarsızlığı,
9. bozuk/doğal olmayan Türkçe; özellikle iyelik, ek uyumu ve sözcük dizimi,
10. fiziksel/mantıksal tutarsızlık,
11. verilmemiş aile/ilişki/canon bilgisi,
12. hard uzunluk 375-625.

Her gerçek sorun için EN KÜÇÜK alanı seç:
- sentence: tek cümle
- block: bağlantılı 2-4 cümle
- paragraph: paragraf anlam/akışı

Tüm hikâyeyi yeniden yazma.
Minor stil tercihlerini düzeltmek zorunda değilsin.
Draft hard aralık içindeyse yaptığın replacement'lar final metni 375 kelimenin altına DÜŞÜRMEMELİ.
Mümkünse toplam uzunluğu drafta yakın tut; yalnız kusuru çözmek için gereken kadar değiştir.

SADECE JSON:
{
  "repairs":[
    {
      "scope":"sentence|block|paragraph",
      "old":"hikâyeden birebir alınmış metin",
      "new":"tam replacement",
      "class":"register|repetition|caregiver_teacher|defensive_exposition|read_aloud|ending|narrator_mindread|broken_turkish|logic_physical|canon|length",
      "severity":"serious|moderate|minor",
      "why":"kısa gerekçe"
    }
  ]
}
""".strip()

FINAL_SYSTEM=r"""
Sen bağımsız son yayın kabul denetçisisin. Bu bir edebiyat eleştirisi değildir.
Yalnız yayın engelleyici kusurları ara.

Hedef: tam yaş 4, yetişkin tarafından Türkçe sesli okuma.

Hard-fail sınıfları:
- canon_violation
- logic_or_physical_break
- broken_turkish
- age_mismatch
- caregiver_teacher
- story_structure_break
- visible_generation_artifact

caregiver_teacher özellikle ebeveynin art arda yönlendirici/sınav soruları ile çözümü çocuktan çekip almasını kapsar.

Yalnız critical veya serious kusur publication_ready=false yapar.
Moderate/minor stil ve cila tercihleri BLOKE ETMEZ.
Kusur yoksa defects boş olsun. Sabit sayıda kusur üretme.

SADECE JSON:
{
  "publication_ready":true,
  "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects":[
    {
      "quote":"birebir kısa alıntı",
      "class":"canon_violation|logic_or_physical_break|broken_turkish|age_mismatch|caregiver_teacher|story_structure_break|visible_generation_artifact",
      "severity":"critical|serious|moderate|minor",
      "why":"kısa gerekçe"
    }
  ],
  "summary":"tek cümle"
}
""".strip()

BANNED=["razı oldu","dikkatini verdi","dikkatini topladı","büründü","sonuç olarak","içinden geçirdi","derin bir nefes aldı","gözleri parladı","adeta"]

def usd(body:dict)->float:
    return float(parse_cost(body).usd or 0.0)

def scan(story:str)->dict:
    lower=story.casefold()
    words=count_words(story)
    return {
      "word_count":words,
      "length_pass":375 <= words <= 625,
      "preferred_length_pass":475 <= words <= 525,
      "banned_hits":[x for x in BANNED if x.casefold() in lower],
      "sanki_count":len(re.findall(r"\bsanki\b",lower)),
      "socratic_phrase_hits":[p for p in ["ne yapmalı dersin","sence ne yapabiliriz","neden olabilir","değil mi"] if p in lower],
    }

def apply_repairs(story:str,repairs:list[dict])->tuple[str,list[dict],list[dict]]:
    current=story
    applied=[]
    skipped=[]
    for r in repairs:
        old=str(r.get("old") or "")
        new=str(r.get("new") or "")
        if not old or not new or old==new:
            skipped.append({**r,"skip_reason":"empty_or_noop"}); continue
        if old not in current:
            skipped.append({**r,"skip_reason":"old_not_found"}); continue
        current=current.replace(old,new,1)
        applied.append(r)
    return current,applied,skipped

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    started=time.perf_counter()

    spine_text="\n".join(f"{i+1}. {b}" for i,b in enumerate(STORY_SPINE))
    user_prompt=f"""KONU:\n{PREMISE}\n\nHİKÂYE OMURGASI:\n{spine_text}\n\nBu omurgayı doğal bir çocuk hikâyesine dönüştür."""

    draft,writer_body,writer_payload=call_openrouter(
      api_key=key,model=WRITER_MODEL,system_prompt=WRITER_SYSTEM,user_prompt=user_prompt,
      temperature=0.72,max_tokens=None,seed=None,request_class="teacher_story",structured_output=False
    )
    before=scan(draft)

    edit,edit_meta=structured_call(
      api_key=key,model=EDITOR_MODEL,system=EDITOR_SYSTEM,
      payload={"exact_age":4,"target_words":500,"hard_range":[375,625],"story_spine":STORY_SPINE,"deterministic_scan":before,"story":draft},
      seed=202610011,max_tokens=None,request_class="editorial_audit"
    )
    final_story,applied,skipped=apply_repairs(draft,edit.get("repairs") or [])
    after=scan(final_story)

    final_audit,final_meta=structured_call(
      api_key=key,model=FINAL_JUDGE_MODEL,system=FINAL_SYSTEM,
      payload={"exact_age":4,"hard_range":[375,625],"story_spine":STORY_SPINE,"story":final_story},
      seed=202610012,max_tokens=None,request_class="editorial_audit"
    )
    counts=final_audit.get("counts") or {}
    publication_ready=(
      after["length_pass"]
      and int(counts.get("critical",0) or 0)==0
      and int(counts.get("serious",0) or 0)==0
      and bool(final_audit.get("publication_ready"))
    )

    result={
      "experiment":"story-spine-refined-recipe-v1",
      "premise":PREMISE,
      "story_spine":STORY_SPINE,
      "spine_contract":{
        "dialogue":False,"prose":False,"new_canon":False,"psychology_explanation":False,
        "theme_message":False,"scene_quota":False,"word_quota_per_beat":False
      },
      "models":{"writer":WRITER_MODEL,"editor":EDITOR_MODEL,"final_acceptance":FINAL_JUDGE_MODEL},
      "provider_token_cap":None,
      "draft":draft,"draft_scan":before,
      "editor_repairs":edit.get("repairs") or [],"applied_repairs":applied,"skipped_repairs":skipped,
      "final_story":final_story,"final_scan":after,
      "final_acceptance":final_audit,"publication_ready":publication_ready,
      "cost_usd":{
        "writer":usd(writer_body),
        "editor":float(((edit_meta.get("cost") or {}).get("usd")) or 0),
        "final_acceptance":float(((final_meta.get("cost") or {}).get("usd")) or 0)
      },
      "elapsed_seconds":round(time.perf_counter()-started,3),
      "writer_usage":parse_usage(writer_body).model_dump(mode="json"),
      "writer_request_payload":writer_payload
    }
    result["cost_usd"]["total"]=sum(result["cost_usd"].values())

    out=Path("runs/story-spine-refined-recipe")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"draft.txt").write_text(draft+"\n",encoding="utf-8")
    (out/"final.txt").write_text(final_story+"\n",encoding="utf-8")
    (out/"spine.txt").write_text(spine_text+"\n",encoding="utf-8")

    print(json.dumps({
      "draft_words":before["word_count"],"final_words":after["word_count"],
      "preferred_length_pass":after["preferred_length_pass"],
      "applied_repairs":len(applied),"skipped_repairs":len(skipped),
      "final_counts":counts,"publication_ready":publication_ready,
      "cost_usd":result["cost_usd"],"elapsed_seconds":result["elapsed_seconds"]
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
