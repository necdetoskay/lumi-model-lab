from __future__ import annotations
import json, os, re
from difflib import SequenceMatcher
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call, BENCHMARK_EDITOR_MODEL

CANDIDATE_SYSTEM = r"""
Sen bir çocuk hikâyesi kusur ADAYI çıkarıcısısın. Nihai editoryal karar verme.
Hedef: tam yaş 4, yetişkin tarafından sesli okunacak doğal Türkçe.

Yüksek recall ile yalnızca şu sınıflarda olası kusur adaylarını bul:
- caregiver_teacher
- narrator_mindread
- defensive_negation
- translationese_register
- physical_action
- flow_closure

Her aday için metinden birebir kısa quote ver.
Kesin kusur olduğundan emin olman gerekmiyor; confidence=low|medium|high kullan.
Ama sırf farklı yazılabilir diye aday üretme. Basit görünür jest, oyunbaz çocuk mantığı,
sevimli tuhaflık veya yalnızca daha kısa yazılabilirlik tek başına aday değildir.

SADECE JSON:
{"candidates":[
  {"quote":"birebir kısa alıntı","kind":"caregiver_teacher|narrator_mindread|defensive_negation|translationese_register|physical_action|flow_closure","confidence":"low|medium|high","why":"neden şüpheli"}
]}
""".strip()

def norm(s:str)->str:
    return re.sub(r"\s+"," ",str(s or "").casefold()).strip(" .,!?:;\"'“”")

def overlap(a:str,b:str)->bool:
    a,b=norm(a),norm(b)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    aw=set(re.findall(r"[a-zçğıöşü0-9]+", a))
    bw=set(re.findall(r"[a-zçğıöşü0-9]+", b))
    if aw and bw:
        containment=len(aw & bw) / min(len(aw), len(bw))
        if containment >= 0.60:
            return True
    return SequenceMatcher(None, a, b).ratio() >= 0.70

def cluster_runs(run_candidates:list[list[dict]])->list[dict]:
    clusters=[]
    for run_idx,cands in enumerate(run_candidates, start=1):
        for cand in cands:
            q=str(cand.get("quote") or "")
            hit=next((c for c in clusters if overlap(q,c["representative_quote"])),None)
            if hit is None:
                hit={"representative_quote":q,"runs":[],"observations":[]}
                clusters.append(hit)
            hit["runs"].append(run_idx)
            hit["observations"].append({"run":run_idx,**cand})
    for c in clusters:
        c["runs"]=sorted(set(c["runs"]))
        c["frequency"]=len(c["runs"])
    return sorted(clusters,key=lambda x:(-x["frequency"],x["representative_quote"]))

def main():
    load_dotenv(); key=os.environ["OPENROUTER_API_KEY"]
    corpus=json.loads(Path("experiments/fixtures/story_defect_locator_regression.tr-age4.v0.1.json").read_text(encoding="utf-8"))
    rows=[]; cost=0.0
    totals={1:{"gold_hits":0,"nondef_hits":0},2:{"gold_hits":0,"nondef_hits":0},3:{"gold_hits":0,"nondef_hits":0}}
    gold_total=0; nondef_total=0

    for case_idx,case in enumerate(corpus["cases"]):
        rid=str(case["run_id"])
        story=Path(f"experiments/fixtures/story_defect_locator_stories/{rid}.txt").read_text(encoding="utf-8")
        run_candidates=[]
        for rep in range(3):
            out,meta=structured_call(
                api_key=key,model=BENCHMARK_EDITOR_MODEL,system=CANDIDATE_SYSTEM,
                payload={"exact_age":4,"story":story},
                seed=202609700 + case_idx*10 + rep,
                max_tokens=None,request_class="editorial_audit")
            run_candidates.append(out.get("candidates") or [])
            cost += float(((meta.get("cost") or {}).get("usd")) or 0)

        clusters=cluster_runs(run_candidates)
        gold_rows=[]
        for g in case.get("gold_findings") or []:
            gold_total += 1
            freq=max([c["frequency"] for c in clusters if overlap(g["quote"],c["representative_quote"])] or [0])
            gold_rows.append({"kind":g["kind"],"quote":g["quote"],"frequency":freq})
            for threshold in (1,2,3):
                totals[threshold]["gold_hits"] += int(freq >= threshold)

        nondef_rows=[]
        for q in case.get("known_non_defects") or []:
            nondef_total += 1
            freq=max([c["frequency"] for c in clusters if overlap(q,c["representative_quote"])] or [0])
            nondef_rows.append({"quote":q,"frequency":freq})
            for threshold in (1,2,3):
                totals[threshold]["nondef_hits"] += int(freq >= threshold)

        rows.append({
          "run_id":rid,"case":case["case"],
          "candidate_counts":[len(x) for x in run_candidates],
          "clusters":clusters,"gold":gold_rows,"known_non_defects":nondef_rows
        })

    metrics={}
    for threshold in (1,2,3):
        metrics[str(threshold)] = {
          "threshold": f"{threshold}/3",
          "gold_hits": totals[threshold]["gold_hits"],
          "gold_total": gold_total,
          "gold_recall": totals[threshold]["gold_hits"]/gold_total if gold_total else 0.0,
          "known_nondefect_hits": totals[threshold]["nondef_hits"],
          "known_nondefect_total": nondef_total,
          "known_nondefect_hit_rate": totals[threshold]["nondef_hits"]/nondef_total if nondef_total else 0.0
        }

    result={
      "judge":BENCHMARK_EDITOR_MODEL,"architecture":"three_run_candidate_consensus",
      "story_count":len(rows),"repetitions_per_story":3,
      "metrics":metrics,"cost_usd":cost,"cases":rows
    }
    Path("runs/story-judge-consensus").mkdir(parents=True,exist_ok=True)
    Path("runs/story-judge-consensus/result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"metrics":metrics,"cost_usd":cost,
      "counts":[{"run_id":x["run_id"],"candidate_counts":x["candidate_counts"]} for x in rows]},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
