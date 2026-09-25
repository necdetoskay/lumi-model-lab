from __future__ import annotations
import json, os, re
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call, BENCHMARK_EDITOR_MODEL

NEUTRAL_AUDIT = r"""
Ücretli bir çocuk hikâyesi uygulamasında yayın öncesi editoryal karar ver.
Hedef tam yaş 4, yetişkin tarafından sesli okunacak doğal Türkçe çocuk edebiyatı.

ÖNEMLİ:
- Bir kusur kotan yoktur. Sonuç 0 kusur olabilir.
- Sırf farklı yazılabilir diye kusur yazma.
- Kişisel stil tercihini kusur sayma.
- Yalnız yayın öncesinde gerçekten değiştirilmesi gereken, metinde kanıtlanabilir sorunları bildir.
- Aynı kök sorunu birden fazla maddede parçalama.
- Düşük güvenli veya tartışmalı noktaları defect listesine alma.
- Metni cümle cümle kusur avına çıkarma; önce bütün olarak oku, sonra yalnız anlamlı sorunları seç.
- Severity: serious ancak yayın kalitesini belirgin bozan; moderate gerçek ama yerel sorun; minor açık ve düzeltmeye değer küçük kusur.
- Kusur yoksa verdict YAYINA_HAZIR ve defects [] döndür.
- 'top_changes' 0 ile 3 madde arasında olabilir; kusur yoksa [].

SADECE JSON:
{
  "verdict":"YAYINA_HAZIR|KUCUK_EDIT|CIDDI_EDIT|YENIDEN_YAZ",
  "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects":[
    {"quote":"birebir kısa alıntı","type":"...","severity":"critical|serious|moderate|minor","why":"...","repair":"..."}
  ],
  "scores":{
    "turkish_naturalness":1,"sentence_quality":1,"age4":1,"dialogue":1,
    "character":1,"flow":1,"read_aloud":1,"literary":1,"emotional":1,
    "originality":1,"no_llm_smell":1,"publication_readiness":1
  },
  "professional_gap":"kısa açıklama",
  "top_changes":[]
}
Skorlar 1-10.
""".strip()

def norm(s):
    return re.sub(r"\s+"," ",str(s or "").casefold()).strip(" .,!?:;\"'“”")

def overlap(a,b):
    a,b=norm(a),norm(b)
    return bool(a and b and (a in b or b in a))

def main():
    load_dotenv(); key=os.environ["OPENROUTER_API_KEY"]
    story=Path("experiments/fixtures/story_defect_locator_stories/36168417326.txt").read_text(encoding="utf-8")
    audits=[]; costs=[]
    for i in range(5):
        a,m=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=NEUTRAL_AUDIT,payload={"exact_age":4,"story":story},seed=202609300+i,max_tokens=None,request_class="editorial_audit")
        audits.append(a); costs.append(float(((m.get("cost") or {}).get("usd")) or 0))
    clusters=[]
    for i,a in enumerate(audits):
        for d in a.get("defects") or []:
            q=str(d.get("quote") or "")
            hit=next((c for c in clusters if overlap(q,c["representative_quote"])),None)
            if hit is None:
                hit={"representative_quote":q,"runs":[],"observations":[]}; clusters.append(hit)
            hit["runs"].append(i+1); hit["observations"].append({"run":i+1,**d})
    for c in clusters:
        c["frequency"]=len(set(c["runs"])); c["runs"]=sorted(set(c["runs"]))
    clusters.sort(key=lambda x:(-x["frequency"],x["representative_quote"]))
    out={
      "source_run":"36168417326","story_unchanged":True,"judge":BENCHMARK_EDITOR_MODEL,
      "audit_mode":"quota_neutral","audit_count":5,"audits":audits,
      "defects_per_run":[len(a.get("defects") or []) for a in audits],
      "defect_clusters":clusters,"cost_usd":sum(costs)
    }
    Path("runs/story-judge-quota-neutral").mkdir(parents=True,exist_ok=True)
    Path("runs/story-judge-quota-neutral/result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"defects_per_run":out["defects_per_run"],"clusters":[{"quote":c["representative_quote"],"frequency":c["frequency"]} for c in clusters],"cost_usd":out["cost_usd"]},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
