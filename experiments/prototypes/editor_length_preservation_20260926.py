from __future__ import annotations
import json, os, time
from pathlib import Path
from dotenv import load_dotenv

from src.generate import count_words
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

EDITOR_MODEL="openai/gpt-5.6-sol"
FINAL_MODEL="anthropic/claude-sonnet-5"

EDITOR_SYSTEM=r"""
Sen bağımsız Türkçe çocuk kitabı editörüsün.
Görevin iyi bir draftı yeniden yazmak değil; yalnız gerçek kusurları en küçük anlamlı kapsamda düzeltmek.

Hedef: tam yaş 4, yetişkin tarafından doğal Türkçe sesli okuma.

KONTROL:
- bozuk/doğal olmayan Türkçe
- fiziksel/mantıksal tutarsızlık
- yaşa uymayan yetişkin register
- mekanik tekrar
- caregiver/teacher tonu
- savunmacı açıklama
- gereksiz iç-dünya yorumu
- verilmemiş canon
- klişe/genel kapanış
- görünür güvenlik/mekân problemi

LENGTH-PRESERVATION:
- Kaynak 475-525 bandındaysa, edit sonrası metni de mümkünse 475-525 bandında tut.
- Kusurlu kısmı gereken minimum ölçüde değiştir.
- Replacement kısalıyorsa aynı bloktaki mevcut olayın gözlemlenebilir eylem, kısa doğal diyalog, ses/duyu ayrıntısı veya geçişini koruyarak yaklaşık eşdeğer uzunlukta doğal replacement yaz.
- Yeni olay, karakter, canon veya çözüm ekleyerek kelime telafisi yapma.
- Tekrar, sıfat dolgusu veya açıklama ile uzatma.
- Critical/serious düzeltme uzunluktan önceliklidir.
- Minor stil tercihleri için gereksiz kısaltma yapma.

Her sorun için EN KÜÇÜK alan:
sentence | block | paragraph

SADECE JSON:
{
  "repairs":[
    {
      "scope":"sentence|block|paragraph",
      "old":"hikâyeden birebir alınmış metin",
      "new":"tam replacement",
      "class":"register|repetition|caregiver_teacher|defensive_exposition|read_aloud|ending|narrator_mindread|broken_turkish|logic_physical|canon|safety",
      "severity":"serious|moderate|minor",
      "why":"kısa gerekçe"
    }
  ]
}
""".strip()

FINAL_SYSTEM=r"""
Sen bağımsız son yayın kabul denetçisisin.
Yalnız yayın engelleyici kusurları ara.
Hard-fail: canon_violation, logic_or_physical_break, broken_turkish, age_mismatch,
caregiver_teacher, story_structure_break, visible_generation_artifact.
Yalnız critical/serious kusur publication_ready=false yapar.
Moderate/minor stil tercihleri bloke etmez.

SADECE JSON:
{
  "publication_ready":true,
  "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects":[],
  "summary":"tek cümle"
}
""".strip()

def apply(story:str, repairs:list[dict]):
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

def cost(meta:dict)->float:
    return float(((meta.get("cost") or {}).get("usd")) or 0)

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    src=json.loads(Path("experiments/fixtures/story_editor_length_preservation_source_36220448569.json").read_text(encoding="utf-8"))
    story=src["draft"]
    before=count_words(story)
    started=time.perf_counter()

    edit,emeta=structured_call(
      api_key=key,model=EDITOR_MODEL,system=EDITOR_SYSTEM,
      payload={
        "exact_age":4,
        "source_word_count":before,
        "preferred_range":src["preferred_range"],
        "hard_range":src["hard_range"],
        "story_spine":src["story_spine"],
        "story":story
      },
      seed=202610081,max_tokens=None,request_class="editorial_audit"
    )
    final_story,applied,skipped=apply(story,edit.get("repairs") or [])
    after=count_words(final_story)

    audit,fmeta=structured_call(
      api_key=key,model=FINAL_MODEL,system=FINAL_SYSTEM,
      payload={
        "exact_age":4,
        "hard_range":src["hard_range"],
        "preferred_range":src["preferred_range"],
        "story":final_story
      },
      seed=202610082,max_tokens=None,request_class="editorial_audit"
    )
    counts=audit.get("counts") or {}
    publication_ready=(
      src["hard_range"][0] <= after <= src["hard_range"][1]
      and int(counts.get("critical",0) or 0)==0
      and int(counts.get("serious",0) or 0)==0
      and bool(audit.get("publication_ready"))
    )

    result={
      "experiment":"editor-length-preservation-v1",
      "source_run":src["source_run"],
      "source_word_count":before,
      "source_preferred_pass":src["preferred_range"][0] <= before <= src["preferred_range"][1],
      "preferred_range":src["preferred_range"],
      "hard_range":src["hard_range"],
      "models":{"editor":EDITOR_MODEL,"final_acceptance":FINAL_MODEL},
      "provider_token_cap":None,
      "source_story":story,
      "editor_repairs":edit.get("repairs") or [],
      "applied_repairs":applied,
      "skipped_repairs":skipped,
      "final_story":final_story,
      "final_word_count":after,
      "net_word_delta":after-before,
      "final_preferred_pass":src["preferred_range"][0] <= after <= src["preferred_range"][1],
      "final_acceptance":audit,
      "publication_ready":publication_ready,
      "cost_usd":{"editor":cost(emeta),"final_acceptance":cost(fmeta)},
      "elapsed_seconds":round(time.perf_counter()-started,3)
    }
    result["cost_usd"]["total"]=sum(result["cost_usd"].values())

    out=Path("runs/editor-length-preservation")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"final.txt").write_text(final_story+"\n",encoding="utf-8")

    print(json.dumps({
      "source_words":before,
      "final_words":after,
      "net_word_delta":after-before,
      "preferred_pass":result["final_preferred_pass"],
      "repairs":len(applied),
      "skipped":len(skipped),
      "final_counts":counts,
      "publication_ready":publication_ready,
      "cost_usd":result["cost_usd"],
      "elapsed_seconds":result["elapsed_seconds"]
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
