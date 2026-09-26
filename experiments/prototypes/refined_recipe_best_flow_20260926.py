from __future__ import annotations
import json, os, re, time
from pathlib import Path
from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

WRITER_MODEL = "anthropic/claude-sonnet-5"
EDITOR_MODEL = "openai/gpt-5.6-sol"
FINAL_JUDGE_MODEL = "anthropic/claude-sonnet-5"

WRITER_SYSTEM = r"""
Sen Türkçe yazan, deneyimli bir çocuk kitabı yazarısın.
Tam 4 yaşındaki bir çocuğa bir yetişkin tarafından sesli okunacak doğal, sıcak ve eğlenceli bir hikâye yaz.

HİKÂYE:
Deniz adında 4 yaşındaki bir çocuk yağmurlu bir öğleden sonra salonda karton kutudan bir otobüs yapıyor.
Oyuncak ayısını ve birkaç oyuncağını otobüse bindiriyor. Otobüsün kartondan yaptığı bir tekeri sürekli yerinden çıkıyor.
Deniz bunu kendi çocukça fikirleriyle oyunun içinde çözmeye çalışsın; süreç bir yetişkinin problem çözme dersi gibi görünmesin.
Annesi yanında olsun, oyuna katılsın ve gerektiğinde yardım etsin; ama cevabı bilen öğretmen gibi yönlendirmesin.
Hikâye sonunda otobüs kısa bir "sefer" yapabilsin ve kapanış Deniz'e özgü somut, komik bir anla bitsin.

SERT KISITLAR:
1. Şu yetişkin/edebî kalıpları kullanma:
   "razı oldu", "dikkatini verdi", "dikkatini topladı", "büründü", "geriledi",
   "sonuç olarak", "içinden geçirdi", "derin bir nefes aldı", "gözleri parladı".
   "aslında", "adeta" kullanma. "sanki" en fazla 1 kez.

2. ŞABLON TEKRARI KONTROLÜ:
   Aynı anlatı işlevini gören cümle veya paragraf iskeletini mekanik biçimde tekrar etme.
   Özellikle her yeni "durak" veya denemeyi sürekli aynı [eylem/listesi + sonuç/olumsuzlama] yapısıyla kurma.
   Aynı iskelet iki kez kullanılabilir; sonraki benzer anlarda anlatımı doğal biçimde çeşitlendir:
   doğrudan eylem, diyalog, ses, kısa gözlem veya küçük sürpriz kullan.
   Ancak çocuğun oyunu, ritim, tekrar eden espri veya bilinçli motif amacı taşıyan tekrarları sırf tekrar diye bozma.
   Ayrıca "eskisi gibi/kadar ... değildi" ve "artık ... değildi" türü karşılaştırma kalıplarını toplamda en fazla 1 kez kullan.

3. Anne Deniz'in hayal gücünü gerçeklik dersi vererek düzeltmesin.
   "Hayır, öyle olmaz", "... ağzı olmaz ki", "arabalar kendi kendine gitmez" gibi mantık düzeltmeleri kurma.
   Anne oyuna katılsın, şaşırsın, gülsün veya doğal bir cevap versin.
   Sokratik soru zinciri, sınav tonu, "değil mi?" ile doğrulatma kullanma.

4. Önceki bir kısıtla çelişmemek için "ama ... değil", "sadece ..." gibi savunmacı açıklamalar ekleme.
   Eylemi baştan tutarlı yaz.

5. Bir cümlede ikiden fazla eylemi art arda virgülle sıralama.
   Cümleler sesli okumada tek nefeste doğal gelsin.

6. Kapanış genel ders, güvence veya slogan olmasın.
   Hikâyeye özgü somut bir hareket, tekrar eden espri veya Deniz'in kısa sözüyle bitsin.

7. Register baştan sona sade ve somut kalsın.
   Anlatıcı karakterlerin zihnini açıklamasın; gözlemlenebilir eylem ve diyalog yaz.

8. En fazla 1-2 somut, yaşa uygun benzetme kullan.

9. Canon uydurma:
   Hikâyede belirtilmeyen kardeş, büyükanne, öğretmen vb. yeni aile/ilişki karakterleri icat etme.

UZUNLUK:
- Hedef: 475-525 kelime.
- Hard aralık: 375-625 kelime.
- 375 kelimenin altında bitirme.

Sadece bitmiş hikâyeyi ver. İlk satır başlık olsun.
""".strip()

EDITOR_SYSTEM = r"""
Sen bağımsız Türkçe çocuk kitabı editörüsün.
Sana 4 yaş için yazılmış bir hikâye verilecek.

Amaç tam yeniden yazım DEĞİL; yalnız gerçek kusurları en küçük anlamlı kapsamda düzeltmek.

Kontrol et:
1. yetişkin/resmî/edebî register,
2. mekanik anlatı iskeleti tekrarı: aynı anlatı işlevini gören [eylem/listesi + sonuç/olumsuzlama] kalıbı veya benzer sözdizimi gereksiz biçimde yineleniyor mu? Bilinçli ritim, çocuk oyunu veya tekrar eden espri ise kusur sayma,
3. ebeveynin çocuğun hayalini düzeltmesi veya öğretmen/sınav tonu,
4. savunmacı iç-tutarlılık açıklamaları,
5. bir cümlede aşırı eylem yığılması / sesli okuma sorunu,
6. klişe/genel kapanış,
7. anlatıcının gereksiz iç-dünya yorumu,
8. register tutarsızlığı,
9. bozuk/doğal olmayan Türkçe,
10. fiziksel/mantıksal tutarsızlık,
11. hikâyede verilmemiş aile/ilişki/canon bilgisi,
12. hard uzunluk 375-625.

Her gerçek sorun için değiştirilmesi gereken EN KÜÇÜK alanı seç:
- sentence: tek cümle yeterliyse
- block: bağlantılı 2-4 cümle gerekiyorsa
- paragraph: paragrafın anlamı/akışı bozuksa

Tüm hikâyeyi yeniden yazma.
Minor stil tercihlerini düzeltmek zorunda değilsin.
Eğer hikâye hard minimumun altındaysa, yeni olay icat etmeden mevcut arama/oyun akışını doğal bir kısa blokla genişletebilirsin.

SADECE JSON:
{
  "repairs": [
    {
      "scope": "sentence|block|paragraph",
      "old": "hikâyeden birebir alınmış değiştirilecek metin",
      "new": "tam replacement metni",
      "class": "register|repetition|caregiver_teacher|defensive_exposition|read_aloud|ending|narrator_mindread|broken_turkish|logic_physical|canon|length",
      "severity": "serious|moderate|minor",
      "why": "kısa gerekçe"
    }
  ]
}
""".strip()

FINAL_SYSTEM = r"""
Sen bağımsız son yayın kabul denetçisisin.
Bu bir edebiyat eleştirisi değildir; yalnız yayın engelleyici kusurları ara.

Hedef: tam yaş 4, yetişkin tarafından Türkçe sesli okuma.

Hard-fail sınıfları:
- canon_violation
- logic_or_physical_break
- broken_turkish
- age_mismatch
- caregiver_teacher
- story_structure_break
- visible_generation_artifact

Yalnız critical veya serious kusur publication_ready=false yapar.
Moderate/minor stil ve cila tercihleri BLOKE ETMEZ.
Kusur yoksa defects boş olsun. Sabit sayıda kusur üretme.

SADECE JSON:
{
  "publication_ready": true,
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
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

BANNED = [
    "razı oldu","dikkatini verdi","dikkatini topladı","büründü","sonuç olarak",
    "içinden geçirdi","derin bir nefes aldı","gözleri parladı","adeta"
]

def usd(body: dict) -> float:
    return float(parse_cost(body).usd or 0.0)

def deterministic_scan(story: str) -> dict:
    lower=story.casefold()
    banned_hits=[x for x in BANNED if x.casefold() in lower]
    sanki_count=len(re.findall(r"\bsanki\b", lower))
    comparison_hits=len(re.findall(r"\b(?:eskisi gibi|eskisi kadar|artık .{0,30}? değildi)\b", lower))
    words=count_words(story)
    return {
        "word_count":words,
        "length_pass":375 <= words <= 625,
        "banned_hits":banned_hits,
        "sanki_count":sanki_count,
        "comparison_pattern_count":comparison_hits,
    }

def apply_repairs(story: str, repairs: list[dict]) -> tuple[str,list[dict],list[dict]]:
    current=story
    applied=[]
    skipped=[]
    for r in repairs:
        old=str(r.get("old") or "")
        new=str(r.get("new") or "")
        if not old or not new or old==new:
            skipped.append({**r,"skip_reason":"empty_or_noop"})
            continue
        if old not in current:
            skipped.append({**r,"skip_reason":"old_not_found"})
            continue
        current=current.replace(old,new,1)
        applied.append(r)
    return current, applied, skipped

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    started=time.perf_counter()

    draft,writer_body,writer_payload=call_openrouter(
        api_key=key,model=WRITER_MODEL,
        system_prompt=WRITER_SYSTEM,
        user_prompt="Hikâyeyi şimdi yaz.",
        temperature=0.72,max_tokens=None,seed=None,
        request_class="teacher_story",structured_output=False,
    )
    scan_before=deterministic_scan(draft)

    edit,edit_meta=structured_call(
        api_key=key,model=EDITOR_MODEL,system=EDITOR_SYSTEM,
        payload={"exact_age":4,"target_words":500,"hard_range":[375,625],"deterministic_scan":scan_before,"story":draft},
        seed=202609961,max_tokens=None,request_class="editorial_audit",
    )
    final_story,applied,skipped=apply_repairs(draft,edit.get("repairs") or [])
    scan_after=deterministic_scan(final_story)

    final_audit,final_meta=structured_call(
        api_key=key,model=FINAL_JUDGE_MODEL,system=FINAL_SYSTEM,
        payload={"exact_age":4,"hard_range":[375,625],"story":final_story},
        seed=202609962,max_tokens=None,request_class="editorial_audit",
    )

    counts=final_audit.get("counts") or {}
    publication_ready=(
        scan_after["length_pass"]
        and int(counts.get("critical",0) or 0)==0
        and int(counts.get("serious",0) or 0)==0
        and bool(final_audit.get("publication_ready"))
    )

    result={
      "experiment":"refined-recipe-best-flow-v2-template-repetition",
      "models":{"writer":WRITER_MODEL,"editor":EDITOR_MODEL,"final_acceptance":FINAL_JUDGE_MODEL},
      "provider_token_cap":None,
      "draft":draft,
      "draft_scan":scan_before,
      "editor_repairs":edit.get("repairs") or [],
      "applied_repairs":applied,
      "skipped_repairs":skipped,
      "final_story":final_story,
      "final_scan":scan_after,
      "final_acceptance":final_audit,
      "publication_ready":publication_ready,
      "cost_usd":{
        "writer":usd(writer_body),
        "editor":float(((edit_meta.get("cost") or {}).get("usd")) or 0),
        "final_acceptance":float(((final_meta.get("cost") or {}).get("usd")) or 0),
      },
      "elapsed_seconds":round(time.perf_counter()-started,3),
      "writer_usage":parse_usage(writer_body).model_dump(mode="json"),
      "writer_request_payload":writer_payload,
    }
    result["cost_usd"]["total"]=sum(result["cost_usd"].values())

    out=Path("runs/refined-recipe-best-flow")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"draft.txt").write_text(draft+"\n",encoding="utf-8")
    (out/"final.txt").write_text(final_story+"\n",encoding="utf-8")

    print(json.dumps({
      "draft_words":scan_before["word_count"],
      "final_words":scan_after["word_count"],
      "applied_repairs":len(applied),
      "skipped_repairs":len(skipped),
      "final_counts":counts,
      "publication_ready":publication_ready,
      "cost_usd":result["cost_usd"],
      "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
