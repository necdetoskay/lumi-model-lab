from __future__ import annotations
import json, os, re
from difflib import SequenceMatcher
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SONNET="anthropic/claude-sonnet-5"
SOL="openai/gpt-5.6-sol"

JUDGE_SYSTEM=r"""
Sen bağımsız son YAYIN KABUL denetçisisin.
Aynı frozen acceptance sözleşmesini uygula. Bu bir edebiyat eleştirisi değildir.

Hedef: tam yaş 4, yetişkin tarafından Türkçe sesli okuma.

Yalnız şu hard-fail sınıflarını değerlendir:
- canon_violation
- logic_or_physical_break
- broken_turkish
- age_mismatch
- caregiver_teacher
- story_structure_break
- visible_generation_artifact

Bir kusur ancak critical veya serious ise hard fail adayıdır.
Moderate/minor stil veya cila gözlemleri publication kararını BLOKE ETMEZ.
Basit görünür jest, oyunbaz çocuk mantığı, daha kısa/güzel yazılabilirlik, küçük ritim tercihi
ve alternatif kelime tercihi hard fail değildir.

Kusur yoksa defects boş olabilir. Sabit sayıda kusur üretme.

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

def norm(s:str)->str:
    return re.sub(r"\s+"," ",str(s or "").casefold()).strip(" .,!?:;\"'“”")

def overlap(a:str,b:str)->bool:
    a,b=norm(a),norm(b)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    aw=set(re.findall(r"[a-zçğıöşü0-9]+",a))
    bw=set(re.findall(r"[a-zçğıöşü0-9]+",b))
    if aw and bw and len(aw & bw)/min(len(aw),len(bw)) >= 0.65:
        return True
    return SequenceMatcher(None,a,b).ratio() >= 0.72

def blocking(a:dict)->list[dict]:
    return [d for d in (a.get("defects") or []) if str(d.get("severity","")).lower() in {"critical","serious"}]

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    story=Path("experiments/fixtures/story_defect_locator_stories/36168417326.txt").read_text(encoding="utf-8").strip()

    sonnet,sm=structured_call(
        api_key=key,model=SONNET,system=JUDGE_SYSTEM,
        payload={"exact_age":4,"story":story},
        seed=202609801,max_tokens=None,request_class="editorial_audit")
    sol,xm=structured_call(
        api_key=key,model=SOL,system=JUDGE_SYSTEM,
        payload={"exact_age":4,"story":story},
        seed=202609802,max_tokens=None,request_class="editorial_audit")

    sa=blocking(sonnet); sb=blocking(sol)
    consensus=[]
    sonnet_only=[]
    sol_only=[]
    matched_b=set()

    for a in sa:
        hit=None
        for j,b in enumerate(sb):
            if j in matched_b: continue
            same_class=(a.get("class")==b.get("class"))
            if same_class and overlap(a.get("quote",""),b.get("quote","")):
                hit=(j,b); break
        if hit:
            j,b=hit; matched_b.add(j)
            consensus.append({
                "class":a.get("class"),
                "sonnet_quote":a.get("quote"),
                "sol_quote":b.get("quote"),
                "sonnet_severity":a.get("severity"),
                "sol_severity":b.get("severity"),
                "sonnet_why":a.get("why"),
                "sol_why":b.get("why")
            })
        else:
            sonnet_only.append(a)

    for j,b in enumerate(sb):
        if j not in matched_b:
            sol_only.append(b)

    result={
      "source_run":"36168417326",
      "story_unchanged":True,
      "acceptance_contract":"story-publication-acceptance.v1",
      "judges":[SONNET,SOL],
      "sonnet":sonnet,
      "sol":sol,
      "sonnet_blocking_count":len(sa),
      "sol_blocking_count":len(sb),
      "consensus_blocking_count":len(consensus),
      "consensus_blocking":consensus,
      "sonnet_only_blocking":sonnet_only,
      "sol_only_blocking":sol_only,
      "consensus_publication_ready":len(consensus)==0,
      "cost_usd":{
        "sonnet":float(((sm.get("cost") or {}).get("usd")) or 0),
        "sol":float(((xm.get("cost") or {}).get("usd")) or 0)
      }
    }
    result["cost_usd"]["total"]=result["cost_usd"]["sonnet"]+result["cost_usd"]["sol"]
    Path("runs/story-dual-judge").mkdir(parents=True,exist_ok=True)
    Path("runs/story-dual-judge/result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({
      "sonnet_blocking_count":result["sonnet_blocking_count"],
      "sol_blocking_count":result["sol_blocking_count"],
      "consensus_blocking_count":result["consensus_blocking_count"],
      "consensus_publication_ready":result["consensus_publication_ready"],
      "consensus_blocking":result["consensus_blocking"],
      "cost_usd":result["cost_usd"]
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
