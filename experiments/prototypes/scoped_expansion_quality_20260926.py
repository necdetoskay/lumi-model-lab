from __future__ import annotations
import json, os, time
from pathlib import Path
from dotenv import load_dotenv

from src.generate import count_words
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

EXPANDER_MODEL="anthropic/claude-sonnet-5"
EDITOR_MODEL="openai/gpt-5.6-sol"
FINAL_MODEL="anthropic/claude-sonnet-5"

EXPAND_SYSTEM=r"""
Sen Türkçe çocuk kitabı yazar-editörüsün.
Görevin mevcut hikâyeyi YENİDEN YAZMAK değil; yalnızca kısa kalan develop/anchor anlarını doğal biçimde biraz genişletmek.

KURALLAR:
- Yeni olay, yeni beat, yeni karakter, yeni canon, yeni çözüm EKLEME.
- Story Spine sırasını ve sonucu değiştirme.
- Başlangıç ve kapanışı değiştirmek zorunda değilsin.
- Yalnız 1-3 mevcut blok üzerinde çalış.
- Her replacement mevcut hikâyeden birebir bir "old" blok ve onun genişletilmiş "new" karşılığını içersin.
- Genişletme somut çocuk eylemi, kısa doğal diyalog, yaşa uygun duyusal ayrıntı veya neden-sonuç geçişiyle yapılmalı.
- Aynı bilgiyi tekrar etme; sıfat doldurma; açıklayıcı/öğretici paragraf ekleme.
- Anne çözümü bulan öğretmen olmasın.
- Register 4 yaşa uygun ve sesli okumada doğal kalsın.
- Toplam net artış hedefi yaklaşık 70-100 kelime.
- Tek geçiş yap; hedefe ulaşamadın diye yeni olay uydurma.

SADECE JSON:
{
  "replacements":[
    {
      "old":"hikâyeden birebir alınmış blok",
      "new":"aynı olayın doğal biçimde genişletilmiş hali",
      "reason":"neden bu blok genişletildi"
    }
  ]
}
""".strip()

EDITOR_SYSTEM=r"""
Sen bağımsız Türkçe çocuk kitabı editörüsün.
Tam yeniden yazım yapma; yalnız gerçek kusurları en küçük anlamlı kapsamda düzelt.

Kontrol et:
- bozuk/doğal olmayan Türkçe
- fiziksel/mantıksal tutarsızlık
- yetişkin/resmî register
- mekanik tekrar
- caregiver/teacher tonu
- savunmacı açıklama
- gereksiz iç-dünya yorumu
- canon uydurma
- klişe kapanış

Expansion ile eklenen metni özellikle denetle: dolgu, tekrar veya ton kayması varsa düzelt.
Hikâye 450 kelime üstündeyse sırf kısaltmak için metin silme.

SADECE JSON:
{
  "repairs":[
    {
      "old":"birebir metin",
      "new":"replacement",
      "class":"broken_turkish|logic_physical|register|repetition|caregiver_teacher|defensive_exposition|narrator_mindread|canon|ending",
      "severity":"serious|moderate|minor",
      "why":"kısa gerekçe"
    }
  ]
}
""".strip()

FINAL_SYSTEM=r"""
Sen bağımsız son yayın kabul denetçisisin.
Yalnız critical/serious yayın engelleyici kusurları ara:
canon_violation, logic_or_physical_break, broken_turkish, age_mismatch,
caregiver_teacher, story_structure_break, visible_generation_artifact.
Moderate/minor stil tercihleri bloke etmez.

SADECE JSON:
{
  "publication_ready":true,
  "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects":[],
  "summary":"tek cümle"
}
""".strip()

def apply(story:str, items:list[dict], old_key:str="old", new_key:str="new"):
    current=story
    applied=[]
    skipped=[]
    for item in items:
        old=str(item.get(old_key) or "")
        new=str(item.get(new_key) or "")
        if not old or not new or old==new:
            skipped.append({**item,"skip_reason":"empty_or_noop"}); continue
        if old not in current:
            skipped.append({**item,"skip_reason":"old_not_found"}); continue
        current=current.replace(old,new,1)
        applied.append(item)
    return current,applied,skipped

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    src=json.loads(Path("experiments/fixtures/story_spine_expansion_source_36219332570.json").read_text(encoding="utf-8"))
    draft=src["draft"]
    started=time.perf_counter()

    expansion,emeta=structured_call(
      api_key=key,model=EXPANDER_MODEL,system=EXPAND_SYSTEM,
      payload={
        "exact_age":4,
        "source_word_count":count_words(draft),
        "target_after_expansion":[455,500],
        "story_spine":src["story_spine"],
        "story":draft
      },
      seed=202610051,max_tokens=None,request_class="editorial_audit"
    )
    expanded,expanded_applied,expanded_skipped=apply(draft, expansion.get("replacements") or [])
    expanded_words=count_words(expanded)

    edit,edit_meta=structured_call(
      api_key=key,model=EDITOR_MODEL,system=EDITOR_SYSTEM,
      payload={
        "exact_age":4,
        "story_spine":src["story_spine"],
        "source_word_count":count_words(draft),
        "expanded_word_count":expanded_words,
        "story":expanded
      },
      seed=202610052,max_tokens=None,request_class="editorial_audit"
    )
    final_story,editor_applied,editor_skipped=apply(expanded, edit.get("repairs") or [])
    final_words=count_words(final_story)

    final_audit,fmeta=structured_call(
      api_key=key,model=FINAL_MODEL,system=FINAL_SYSTEM,
      payload={"exact_age":4,"hard_range":[375,625],"story":final_story},
      seed=202610053,max_tokens=None,request_class="editorial_audit"
    )
    counts=final_audit.get("counts") or {}
    publication_ready=(375 <= final_words <= 625
      and int(counts.get("critical",0) or 0)==0
      and int(counts.get("serious",0) or 0)==0
      and bool(final_audit.get("publication_ready")))

    def meta_cost(meta):
      return float(((meta.get("cost") or {}).get("usd")) or 0)

    result={
      "experiment":"scoped-expansion-quality-preservation-v1",
      "source_run":src["source_run"],
      "source_word_count":count_words(draft),
      "target_after_expansion":[455,500],
      "models":{"expander":EXPANDER_MODEL,"editor":EDITOR_MODEL,"final_acceptance":FINAL_MODEL},
      "provider_token_cap":None,
      "source_story":draft,
      "expansion_replacements":expansion.get("replacements") or [],
      "expansion_applied":expanded_applied,
      "expansion_skipped":expanded_skipped,
      "expanded_story":expanded,
      "expanded_word_count":expanded_words,
      "net_expansion_words":expanded_words-count_words(draft),
      "editor_repairs":edit.get("repairs") or [],
      "editor_applied":editor_applied,
      "editor_skipped":editor_skipped,
      "final_story":final_story,
      "final_word_count":final_words,
      "final_acceptance":final_audit,
      "publication_ready":publication_ready,
      "cost_usd":{
        "expansion":meta_cost(emeta),
        "editor":meta_cost(edit_meta),
        "final_acceptance":meta_cost(fmeta)
      },
      "elapsed_seconds":round(time.perf_counter()-started,3)
    }
    result["cost_usd"]["total"]=sum(result["cost_usd"].values())

    out=Path("runs/scoped-expansion-quality")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"expanded.txt").write_text(expanded+"\n",encoding="utf-8")
    (out/"final.txt").write_text(final_story+"\n",encoding="utf-8")
    print(json.dumps({
      "source_words":result["source_word_count"],
      "expanded_words":expanded_words,
      "net_expansion_words":result["net_expansion_words"],
      "final_words":final_words,
      "expansion_patches":len(expanded_applied),
      "editor_repairs":len(editor_applied),
      "publication_ready":publication_ready,
      "final_counts":counts,
      "cost_usd":result["cost_usd"],
      "elapsed_seconds":result["elapsed_seconds"]
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
