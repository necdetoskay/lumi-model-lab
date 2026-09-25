from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

PATH=Path("experiments/results/story-quality-regression-matrix.tr-age4.json")

def main():
    data=json.loads(PATH.read_text(encoding="utf-8"))
    counts=Counter()
    cases_by_signal={}
    for case in data["cases"]:
        for signal in set(case.get("signals", [])):
            counts[signal]+=1
            cases_by_signal.setdefault(signal,[]).append(case["case"])
    ranked=[]
    for signal,count in counts.most_common():
        families={c.split("-")[0] for c in cases_by_signal[signal]}
        ranked.append({"signal":signal,"case_count":count,"cases":cases_by_signal[signal],"distinct_case_prefixes":len(families),"promotion_candidate":count>=data["promotion_policy"]["candidate_min_independent_cases"]})
    print(json.dumps({"runs":len(data["cases"]),"ranked_signals":ranked},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
