#!/usr/bin/env python3
"""Fail-closed NOVA v0.4 Prototype first-pass research integrity validator."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sys
from build_prototype import ROOT,BASE,SRC,DOCS,EXPECTED_TABLES

EXPECTED={"works":1,"sources":9,"story_events":16,"mechanics":12,"mechanic_evidence":30,"prior_links":20}
REFERENCE_LOWER_CONFIDENCE={"PRT-E12","PRT-E13","PRT-E14","PRT-E16"}
DOCUMENTS=("README.md","EVENTS.md","MECHANICS.md","SOURCES.md","FIREWALL.md")

def rows(table):
    path=BASE/(table+".jsonl")
    return [json.loads(x) for x in path.read_text(encoding="utf8").splitlines() if x.strip()]

def check():
    errors=[]
    def ck(ok,message):
        if not ok:errors.append(message)
    canon=json.loads(SRC.read_text(encoding="utf8"))
    manifest=json.loads((BASE/"manifest.json").read_text(encoding="utf8"))
    data={k:rows(k) for k in EXPECTED_TABLES}
    for k,n in EXPECTED.items():
        ck(len(data[k])==n,f"{k} has {len(data[k])}, expected {n}")
        ck(manifest.get("counts",{}).get(k)==n,"Manifest table mismatch "+k)
        if k in canon:
            ck(data[k]==canon[k],"Derived drift from canonical "+k)
    ck(manifest.get("source_sha256")==hashlib.sha256(SRC.read_bytes()).hexdigest(),"Source SHA mismatch")
    ck(manifest.get("schema_version")=="0.4.0-research-first-pass","Schema version changed")
    ck(canon.get("scope")=="prototype_2009_only","Sequel or another franchise mixed into Prototype first pass")
    ck(canon.get("quality_effect")==manifest.get("quality_effect")=="not_evaluated","Unproven quality promotion")
    ck(canon.get("story_quality_trials")==manifest.get("story_quality_trials")==0,"False story trials")
    ck(canon.get("paid_api_calls")==manifest.get("paid_model_calls")==0,"False paid calls")
    ck(canon.get("lumi_production_modified") is False and manifest.get("lumi_production_modified") is False,
       "Production modification flag changed")
    ck(canon.get("lumi_canon") is False,"NOVA analysis promoted to LUMI canon")
    ck(not rows("quality_evaluations") and not rows("lumi_usage_history"),"Unperformed evaluations or production use must be empty")
    works=data["works"]
    ck(len({w["work_id"] for w in works})==1 and works[0]["work_id"]=="PROTOTYPE-2009",
       "Incorrect work or sequel included")
    ck(all(w.get("lumi_canon") is False and w.get("quality_effect")=="not_evaluated"
           and w.get("editorial_stage")=="sourced_first_pass" for w in works),"False work promotion")
    sources={s["source_id"]:s for s in data["sources"]}
    ck(len(sources)==len(data["sources"]),"Source IDs duplicated")
    ck(all(s.get("url","").startswith("https://") and
           s.get("verification")=="web_search_result_or_open_retrieved" for s in sources.values()),
       "Source URL/provenance overclaimed")
    ck(any(s.get("source_class")=="primary_marketing" for s in sources.values()),"No publisher source")
    ck(any(s.get("source_class")=="contemporary_walkthrough" for s in sources.values()),"No guide provenance")
    events={e["event_id"]:e for e in data["story_events"]}
    ck(len(events)==16 and len(events)==len(data["story_events"]),"Event IDs duplicated")
    ck([e["event_id"] for e in data["story_events"]]==[f"PRT-E{i:02d}" for i in range(1,17)],
       "Event ID sequence changed")
    ck(all(e["source_ids"] and len(set(e["source_ids"]))>=2 and set(e["source_ids"])<=set(sources)
         and len(e.get("observed_event_tr",""))>80 and e.get("editorial_stage")=="sourced_first_pass"
         for e in events.values()),"Event source/text/editorial state invalid")
    ck(all(events[k]["evidence_strength"]=="secondary_or_community_not_independently_audited"
           for k in REFERENCE_LOWER_CONFIDENCE),"Plot twist incorrectly promoted to strong provenance")
    ck(all(e.get("chronological_order") is None or isinstance(e["chronological_order"],(str,int))
         for e in events.values()),"False forced chronology")
    ids={m["mechanic_id"] for m in data["mechanics"]}
    ck(len(ids)==len(data["mechanics"]) and
       [m["mechanic_id"] for m in data["mechanics"]]==[f"PRT-{i:03d}" for i in range(1,13)],
       "Mechanic ids collide or are out of sequence")
    prior=json.loads((ROOT/"data/nova/v0.3/source_records/prince_mechanics.json").read_text(encoding="utf8"))
    pop_ids={x["mechanic_id"] for x in prior["mechanics"]}
    ck(not ids.intersection(pop_ids),"Prototype IDs collide with Prince of Persia")
    for m in data["mechanics"]:
        ck(len(m["evidence_anchors"])>=2 and set(m["evidence_anchors"])<=set(events),
           m["mechanic_id"]+" evidence anchors broken")
        ck(m["related_pop_ids"] and set(m["related_pop_ids"])<=pop_ids,
           m["mechanic_id"]+" cross-corpus refs broken")
        ck(len(m.get("abstraction_tr",""))>=90 and len(m.get("guardrail_tr",""))>=80 and
           m.get("mechanism_inference") is True and m.get("quality_effect")=="not_evaluated"
           and m.get("lumi_canon") is False,
           m["mechanic_id"]+" inference guardrails invalid")
        ck(m.get("copyright_guardrail") and m.get("editorial_stage")=="sourced_first_pass",
           m["mechanic_id"]+" copyright/edit status invalid")
    evidence=data["mechanic_evidence"]
    expected={(m["mechanic_id"],a) for m in data["mechanics"] for a in m["evidence_anchors"]}
    seen={(x["mechanic_id"],x["event_id"]) for x in evidence}
    ck(len(seen)==len(evidence) and expected==seen,"Event->mechanic evidence missing/duplicated")
    for x in evidence:
        ck(x["event_id"] in events and x["mechanic_id"] in ids and
           x["source_ids"]==events[x["event_id"]]["source_ids"] and
           x["observed_event_tr"]==events[x["event_id"]]["observed_event_tr"]
           and x.get("mechanism_inference") is True and x.get("lumi_canon") is False,
           "Invalid evidence source: "+x["evidence_id"])
    links=data["prior_links"]
    expected_links={(m["mechanic_id"],r) for m in data["mechanics"] for r in m["related_pop_ids"]}
    ck({(x["mechanic_id"],x["prior_mechanic_id"]) for x in links}==expected_links
       and len(links)==len(expected_links),"Cross-version links missing or duplicated")
    ck(all(l["mechanic_id"] in ids and l["prior_mechanic_id"] in pop_ids and
           l["quality_effect"]=="not_evaluated" for l in links),
       "Invalid source/prior cross-links")
    ck(all((DOCS/name).is_file() and (DOCS/name).stat().st_size>250 for name in DOCUMENTS),
       "Generated documentation missing")
    ck("Prototype 2" in "\n".join(canon.get("continuity_firewall",[])),"Prototype 2 firewall missing")
    return {"status":"PASS" if not errors else "FAIL",
      "scope":"FIRST_PASS_OFFLINE_STRUCTURE_PROVENANCE_NOT_EXPERT_EDITORIAL_AUDIT_OR_STORY_QUALITY",
      "counts":{k:len(v) for k,v in data.items()},
      "low_confidence_plot_events":sorted(REFERENCE_LOWER_CONFIDENCE),
      "new_paid_calls":0,"story_quality_trials":0,"lumi_production_modified":False,
      "errors":errors}

if __name__=="__main__":
    try:result=check()
    except Exception as exc:result={"status":"FAIL","fatal":repr(exc)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result["status"]=="PASS" else 1)
