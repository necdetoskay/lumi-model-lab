from __future__ import annotations
import json, os, re
from pathlib import Path
from dotenv import load_dotenv
from story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call, BENCHMARK_EDITOR_MODEL, BENCHMARK_AUDIT_SYSTEM

QUOTA_NEUTRAL = r"""
Ücretli bir çocuk hikâyesi uygulamasında yayın öncesi editoryal karar ver.
Hedef tam yaş 4, yetişkin tarafından sesli okunacak doğal Türkçe çocuk edebiyatı.
Bir kusur kotan yoktur; 0 kusur olabilir. Sırf farklı yazılabilir diye kusur yazma.
Kişisel stil tercihini kusur sayma. Yalnız yayın öncesinde gerçekten değiştirilmesi gereken,
metinde kanıtlanabilir sorunları bildir. Düşük güvenli veya tartışmalı noktaları defect listesine alma.
Önce metni bütün olarak oku; sonra yalnız anlamlı sorunları seç.
SADECE JSON:
{"verdict":"YAYINA_HAZIR|KUCUK_EDIT|CIDDI_EDIT|YENIDEN_YAZ",
 "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
 "defects":[{"quote":"birebir kısa alıntı","type":"...","severity":"critical|serious|moderate|minor","why":"...","repair":"..."}],
 "scores":{"turkish_naturalness":1,"sentence_quality":1,"age4":1,"dialogue":1,"character":1,"flow":1,"read_aloud":1,"literary":1,"emotional":1,"originality":1,"no_llm_smell":1,"publication_readiness":1},
 "professional_gap":"kısa açıklama","top_changes":[]}
Skorlar 1-10. Kusur yoksa defects [].
""".strip()

CALIBRATED = r"""
Ücretli bir çocuk hikâyesi uygulamasında yayın öncesi editoryal karar ver.
Hedef tam yaş 4, yetişkin tarafından sesli okunacak doğal Türkçe çocuk edebiyatı.

KALİBRASYON:
- Kusur kotası yok; sonuç 0 kusur olabilir.
- Sırf başka türlü yazılabilir diye kusur üretme.
- Ama gerçek bir kusuru da "stil tercihi" diyerek geçme.
- Bir madde ancak metinde birebir alıntıyla gösterilebilen ve yayın öncesi düzeltmeye değer bir etki yaratıyorsa defect olsun.
- Aynı kök problemi bölüp birkaç kusur yazma.

Özellikle şu gerçek hata sınıflarını aktif olarak kontrol et:
1) caregiver_teacher: yetişkin çocuğun hayal/oyun önermesini mantık dersiyle düzeltir, cevabı yönlendiren öğretmen soruları sorar veya oyuna katılmak yerine açıklama yapar.
2) narrator_mindread: görünür eylem yerine karakterin niyetini/duygusunu dışarıdan kesinleyen anlatıcı yorumu.
3) defensive_negation: doğal eylemi anlatmak yerine "yapmadı ama/sadece..." gibi savunmacı açıklama.
4) translationese/register: Türkçede doğal olmayan çeviri kokusu veya yaşa göre belirgin yetişkin register.
5) physical_action: gerçekten fiziksel/mekânsal olarak tutarsız ya da anlaşılmaz eylem. Sırf güvenlik riski var diye kusur sayma.
6) flow/closure: ana olaydan kopuk işlevsiz yan olay veya açıkça zayıf/yarım kalan kapanış.

Şunları tek başına kusur sayma:
- görünür basit jestler,
- çocuğun oyunbaz mantık sıçraması,
- sevimli tuhaflık,
- kısa liste/betimleme,
- sırf daha kısa yazılabilir olması.

SADECE JSON:
{"verdict":"YAYINA_HAZIR|KUCUK_EDIT|CIDDI_EDIT|YENIDEN_YAZ",
 "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
 "defects":[{"quote":"birebir kısa alıntı","type":"...","severity":"critical|serious|moderate|minor","why":"...","repair":"..."}],
 "scores":{"turkish_naturalness":1,"sentence_quality":1,"age4":1,"dialogue":1,"character":1,"flow":1,"read_aloud":1,"literary":1,"emotional":1,"originality":1,"no_llm_smell":1,"publication_readiness":1},
 "professional_gap":"kısa açıklama","top_changes":[]}
Skorlar 1-10. Kusur yoksa defects [].
""".strip()

def norm(s:str)->str:
    return re.sub(r"\s+"," ",str(s or "").casefold()).strip(" .,!?:;\"'“”")

def overlap(a:str,b:str)->bool:
    a,b=norm(a),norm(b)
    return bool(a and b and (a in b or b in a))

def evaluate_mode(key, mode_name, system, cases):
    rows=[]; total_gold=0; hit_gold=0; total_nondef=0; hit_nondef=0; cost=0.0
    for idx,case in enumerate(cases):
        rid=str(case["run_id"])
        story=Path(f"experiments/fixtures/story_defect_locator_stories/{rid}.txt").read_text(encoding="utf-8")
        audit,meta=structured_call(api_key=key,model=BENCHMARK_EDITOR_MODEL,system=system,payload={"exact_age":4,"story":story},seed=202609400+idx,max_tokens=None,request_class="editorial_audit")
        cost += float(((meta.get("cost") or {}).get("usd")) or 0)
        defects=audit.get("defects") or []
        gold=case.get("gold_findings") or []
        nondefs=case.get("known_non_defects") or []
        gh=[]
        for g in gold:
            matched=any(overlap(g["quote"], d.get("quote","")) for d in defects)
            gh.append({"kind":g["kind"],"quote":g["quote"],"hit":matched})
            total_gold+=1; hit_gold+=int(matched)
        nh=[]
        for q in nondefs:
            matched=any(overlap(q,d.get("quote","")) for d in defects)
            nh.append({"quote":q,"hit":matched})
            total_nondef+=1; hit_nondef+=int(matched)
        rows.append({"run_id":rid,"case":case["case"],"verdict":audit.get("verdict"),"defect_count":len(defects),"gold":gh,"known_non_defects":nh,"audit":audit})
    return {"mode":mode_name,"gold_hits":hit_gold,"gold_total":total_gold,"gold_recall":hit_gold/total_gold if total_gold else None,
            "known_nondefect_hits":hit_nondef,"known_nondefect_total":total_nondef,
            "known_nondefect_hit_rate":hit_nondef/total_nondef if total_nondef else 0.0,
            "cost_usd":cost,"cases":rows}

def main():
    load_dotenv(); key=os.environ["OPENROUTER_API_KEY"]
    corpus=json.loads(Path("experiments/fixtures/story_defect_locator_regression.tr-age4.v0.1.json").read_text(encoding="utf-8"))
    cases=corpus["cases"]
    results=[
      evaluate_mode(key,"legacy",BENCHMARK_AUDIT_SYSTEM,cases),
      evaluate_mode(key,"quota_neutral",QUOTA_NEUTRAL,cases),
      evaluate_mode(key,"calibrated",CALIBRATED,cases),
    ]
    out={"judge":BENCHMARK_EDITOR_MODEL,"story_count":len(cases),"single_seed_per_story":True,"results":results}
    Path("runs/story-judge-calibration").mkdir(parents=True,exist_ok=True)
    Path("runs/story-judge-calibration/result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps([{"mode":r["mode"],"gold_recall":r["gold_recall"],"known_nondefect_hit_rate":r["known_nondefect_hit_rate"],"defects_per_case":[x["defect_count"] for x in r["cases"]],"cost_usd":r["cost_usd"]} for r in results],ensure_ascii=False,indent=2))
if __name__=="__main__": main()
