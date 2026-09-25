from __future__ import annotations
import json, os
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call, apply_replacements, BENCHMARK_EDITOR_MODEL

EDITOR = r"""Sen profesyonel Türk çocuk kitabı editörüsün. Hedef tam yaş 4 ve yetişkin tarafından sesli okuma.
Metni sert ama adil değerlendir. Kusur uydurma. Her gerçek kusur için minimum müdahaleyi öner.
SADECE JSON:
{"verdict":"YAYINA_HAZIR|KUCUK_EDIT|CIDDI_EDIT|YENIDEN_YAZ","defects":[{"quote":"hikâyeden birebir kısa alıntı","type":"...","severity":"critical|serious|moderate|minor","why":"...","repair_scope":"phrase|sentence|paragraph|dialogue_exchange|scene|structural","replacement":"yalnız quote yerine geçecek minimum doğal metin"}]}
Replacement olay, canon ve anlamı gereksiz değiştirmemeli. Sorun daha geniş bağlam gerektiriyorsa replacement boş olabilir ve scope bunu göstermeli."""

BLIND = r"""Sen bağımsız profesyonel Türk çocuk kitabı editörüsün. Önceki değerlendirmeyi veya değişiklikleri bilmiyorsun.
Tam yaş 4, yetişkin sesli okuma için metni sert ama adil değerlendir; kusur uydurma.
SADECE JSON:
{"verdict":"YAYINA_HAZIR|KUCUK_EDIT|CIDDI_EDIT|YENIDEN_YAZ","counts":{"critical":0,"serious":0,"moderate":0,"minor":0},"defects":[{"quote":"birebir kısa alıntı","type":"...","severity":"critical|serious|moderate|minor","why":"..."}],"scores":{"turkish_naturalness":1,"age4":1,"dialogue":1,"flow":1,"read_aloud":1,"literary":1,"no_llm_smell":1,"publication_readiness":1}}
Skorlar 1-10."""

def main():
 load_dotenv(); key=os.environ["OPENROUTER_API_KEY"]
 story=Path("experiments/fixtures/story_defect_locator_stories/36168417326.txt").read_text(encoding="utf-8")
 edit,em=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=EDITOR,payload={"story":story},seed=202609281,max_tokens=None,request_class="editorial_audit")
 reps=[]
 for d in edit.get("defects") or []:
  q=str(d.get("quote") or ""); n=str(d.get("replacement") or "")
  if q and n and q in story and d.get("repair_scope") in {"phrase","sentence"}: reps.append({"old":q,"new":n})
 patched,applied=apply_replacements(story,reps)
 blind,bm=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=BLIND,payload={"story":patched},seed=202609282,max_tokens=None,request_class="editorial_audit")
 out={"source_run":"36168417326","before_words":len(story.split()),"editor":edit,"applied":applied,"after_words":len(patched.split()),"blind_reaudit":blind,"cost":{"editor_usd":((em.get("cost") or {}).get("usd")),"reaudit_usd":((bm.get("cost") or {}).get("usd"))},"patched_story":patched}
 Path("runs/story-editor-patch").mkdir(parents=True,exist_ok=True); Path("runs/story-editor-patch/result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"editor_defects":len(edit.get("defects") or []),"applied":len(applied),"blind_counts":blind.get("counts"),"blind_verdict":blind.get("verdict"),"cost":out["cost"]},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
