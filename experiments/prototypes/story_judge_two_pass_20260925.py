from __future__ import annotations
import json, os, re
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call, BENCHMARK_EDITOR_MODEL

CANDIDATE_SYSTEM = r"""
Sen bir çocuk hikâyesi kusur ADAYI çıkarıcısısın. Nihai editoryal karar verme.
Hedef: tam yaş 4, yetişkin tarafından sesli okunacak doğal Türkçe.

Görevin yüksek recall ile yalnızca şu sınıflarda olası kusur adaylarını bulmak:
- caregiver_teacher
- narrator_mindread
- defensive_negation
- translationese_register
- physical_action
- flow_closure

Her aday için metinden birebir kısa quote ver.
Bir adayın kesin kusur olduğundan emin olman gerekmiyor; confidence=low|medium|high kullan.
Ama sırf farklı yazılabilir diye aday üretme. Basit görünür jest, oyunbaz çocuk mantığı,
sevimli tuhaflık veya yalnızca daha kısa yazılabilirlik tek başına aday değildir.

SADECE JSON:
{
  "candidates":[
    {"quote":"birebir kısa alıntı","kind":"caregiver_teacher|narrator_mindread|defensive_negation|translationese_register|physical_action|flow_closure","confidence":"low|medium|high","why":"neden şüpheli"}
  ]
}
""".strip()

VERIFY_SYSTEM = r"""
Sen ikinci aşama çocuk hikâyesi editoryal DOĞRULAYICISISIN.
Sana hikâye ve başka bir modelin çıkardığı kusur adayları verilecek.
Her adayı bağımsız değerlendir; aday çıkarıcının kararını kabul etmek zorunda değilsin.

Hedef: tam yaş 4, yetişkin tarafından sesli okunacak doğal Türkçe.

Bir adayı accept=true yap ancak:
- quote gerçekten metinde varsa,
- sorun metinde kanıtlanabiliyorsa,
- yayın öncesi düzeltmeye değer gerçek bir kusursa.

Kriterler:
caregiver_teacher: yetişkin oyuna/hayale katılmak yerine mantık dersi verir, cevabı yönlendirir veya öğretmen gibi sorgular.
narrator_mindread: görünür davranış yerine niyet/duygu/düşünceyi dışarıdan kesinler veya yetişkin ironik yorum ekler.
defensive_negation: doğal eylem yerine "yapmadı ama/sadece..." tarzı savunmacı açıklama.
translationese_register: Türkçede belirgin çeviri kokusu ya da yaşa göre belirgin yetişkin/resmi register.
physical_action: gerçekten fiziksel/mekânsal olarak tutarsız veya anlaşılmaz eylem; sırf riskli olması yetmez.
flow_closure: ana olaydan kopuk işlevsiz yan olay ya da açıkça yarım/zayıf kapanış.

Basit jest, oyunbaz çocuk mantığı, sevimli tuhaflık, kısa betimleme veya kişisel stil tercihi kusur değildir.

SADECE JSON:
{
  "decisions":[
    {"quote":"aday quote","kind":"aday kind","accept":true,"severity":"serious|moderate|minor","why":"kısa gerekçe"}
  ]
}
""".strip()

def norm(s:str)->str:
    return re.sub(r"\s+"," ",str(s or "").casefold()).strip(" .,!?:;\"'“”")

def overlap(a:str,b:str)->bool:
    a,b=norm(a),norm(b)
    return bool(a and b and (a in b or b in a))

def main():
    load_dotenv(); key=os.environ["OPENROUTER_API_KEY"]
    corpus=json.loads(Path("experiments/fixtures/story_defect_locator_regression.tr-age4.v0.1.json").read_text(encoding="utf-8"))
    rows=[]; raw_hit=final_hit=gold_total=nondef_hit=nondef_total=0; cost=0.0
    for idx,case in enumerate(corpus["cases"]):
        rid=str(case["run_id"])
        story=Path(f"experiments/fixtures/story_defect_locator_stories/{rid}.txt").read_text(encoding="utf-8")
        cand,cm=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=CANDIDATE_SYSTEM,payload={"exact_age":4,"story":story},seed=202609500+idx,max_tokens=None,request_class="editorial_audit")
        candidates=cand.get("candidates") or []
        ver,vm=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=VERIFY_SYSTEM,payload={"exact_age":4,"story":story,"candidates":candidates},seed=202609600+idx,max_tokens=None,request_class="editorial_audit")
        decisions=ver.get("decisions") or []
        accepted=[d for d in decisions if d.get("accept") is True]
        cost += float(((cm.get("cost") or {}).get("usd")) or 0) + float(((vm.get("cost") or {}).get("usd")) or 0)

        gh=[]
        for g in case.get("gold_findings") or []:
            raw=any(overlap(g["quote"],c.get("quote","")) for c in candidates)
            fin=any(overlap(g["quote"],d.get("quote","")) for d in accepted)
            gh.append({"kind":g["kind"],"quote":g["quote"],"raw_hit":raw,"final_hit":fin})
            gold_total+=1; raw_hit+=int(raw); final_hit+=int(fin)

        nh=[]
        for q in case.get("known_non_defects") or []:
            fin=any(overlap(q,d.get("quote","")) for d in accepted)
            nh.append({"quote":q,"final_hit":fin})
            nondef_total+=1; nondef_hit+=int(fin)

        rows.append({
          "run_id":rid,"case":case["case"],
          "candidate_count":len(candidates),"accepted_count":len(accepted),
          "gold":gh,"known_non_defects":nh,
          "candidates":candidates,"decisions":decisions
        })

    out={
      "judge":BENCHMARK_EDITOR_MODEL,"story_count":len(rows),"architecture":"candidate_then_verify",
      "raw_gold_hits":raw_hit,"final_gold_hits":final_hit,"gold_total":gold_total,
      "raw_gold_recall":raw_hit/gold_total if gold_total else 0.0,
      "final_gold_recall":final_hit/gold_total if gold_total else 0.0,
      "known_nondefect_hits":nondef_hit,"known_nondefect_total":nondef_total,
      "known_nondefect_hit_rate":nondef_hit/nondef_total if nondef_total else 0.0,
      "cost_usd":cost,"cases":rows
    }
    Path("runs/story-judge-two-pass").mkdir(parents=True,exist_ok=True)
    Path("runs/story-judge-two-pass/result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({
      "raw_gold_recall":out["raw_gold_recall"],"final_gold_recall":out["final_gold_recall"],
      "known_nondefect_hit_rate":out["known_nondefect_hit_rate"],
      "counts":[{"run_id":x["run_id"],"candidates":x["candidate_count"],"accepted":x["accepted_count"]} for x in rows],
      "cost_usd":cost
    },ensure_ascii=False,indent=2))

if __name__=="__main__": main()
