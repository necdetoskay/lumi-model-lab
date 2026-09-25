from __future__ import annotations
import json, os, re
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call, BENCHMARK_EDITOR_MODEL, BENCHMARK_AUDIT_SYSTEM

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
  a,m=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=BENCHMARK_AUDIT_SYSTEM,payload={"exact_age":4,"story":story},seed=202609290+i,max_tokens=None,request_class="editorial_audit")
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
 out={"source_run":"36168417326","story_unchanged":True,"judge":BENCHMARK_EDITOR_MODEL,"audit_count":5,"audits":audits,"defect_clusters":clusters,"cost_usd":sum(costs)}
 Path("runs/story-judge-stability").mkdir(parents=True,exist_ok=True)
 Path("runs/story-judge-stability/result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"defects_per_run":[len(a.get("defects") or []) for a in audits],"clusters":[{"quote":c["representative_quote"],"frequency":c["frequency"],"runs":c["runs"]} for c in clusters],"cost_usd":out["cost_usd"]},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
