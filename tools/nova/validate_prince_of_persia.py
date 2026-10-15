#!/usr/bin/env python3
"""NOVA Prince of Persia v0.3 independent fail-closed data-contract validator."""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from build_prince_of_persia import BASE, DOCS, ROOT, SRC

EXPECTED={"works":19,"supplementary_releases":8,"sources":29,
          "story_beats":84,"temporal_events":29,"temporal_locations":7,
          "temporal_edges":34,"ending_branches":2,"mechanics":22,
          "mechanic_evidence":72,"cross_corpus_links":27}

def jsonl(name):
    p=BASE/(name+".jsonl")
    return [json.loads(x) for x in p.read_text(encoding="utf8").splitlines() if x.strip()]

COMPARISON_LINKS = {
    ("W16", "W08"): "same_earlier_encounter_revealed",
    ("W17", "W09"): "same_tower_sighting_revealed",
    ("W20", "W10"): "same_time_slot_changed_outcome",
    ("W22", "W12"): "same_fated_location_altered_history",
    ("W12", "W02"): "bootstrap_loop_history_inference",
}

def causal_graph_errors(event_rows, edge_rows, endings):
    """Validate reveal links separately from forward causal progression."""
    errors=[]
    events={x["event_id"]:x for x in event_rows}
    if len(events)!=len(event_rows):
        errors.append("duplicate temporal node")
    adj={key:set() for key in events}
    indeg={key:0 for key in events}
    pairs={}
    for edge in edge_rows:
        u,v=edge["from_event_id"],edge["to_event_id"]
        if u not in events or v not in events:
            errors.append("orphan temporal edge: "+u+" -> "+v)
            continue
        relation=edge["relation"]
        if (u,v) in pairs:
            errors.append("duplicate directed temporal link: "+u+" -> "+v)
        pairs[u,v]=relation
        if relation=="bootstrap_loop_history_inference":
            if not (u,v)==("W12","W02") or not edge["is_temporal_loop"] or not edge["inference"]:
                errors.append("bootstrap inference must remain explicitly provisional")
        elif edge["is_temporal_loop"]:
            errors.append("undeclared bootstrap loop: "+u+" -> "+v)
        if (u,v) in COMPARISON_LINKS:
            if relation!=COMPARISON_LINKS[u,v]:
                errors.append("temporal comparison changed meaning: "+u+" -> "+v)
            if (u,v)!=("W12","W02"):
                a,b=events[u],events[v]
                if a["time_slot_id"] is None or a["time_slot_id"]!=b["time_slot_id"] or a["epoch"]!=b["epoch"]:
                    errors.append("mirrored events are not at the same time/era: "+u+" -> "+v)
                if a["worldline_variant"]!="REVISED_HISTORY" or b["worldline_variant"]!="FIRST_HISTORY":
                    errors.append("mirrored events have mixed first/revised identities: "+u+" -> "+v)
        elif relation in set(COMPARISON_LINKS.values()):
            errors.append("retrospective relation on an unapproved edge: "+u+" -> "+v)
        else:
            if v not in adj[u]:
                adj[u].add(v)
                indeg[v]+=1
    for pair,relation in COMPARISON_LINKS.items():
        if pairs.get(pair)!=relation:
            errors.append("required historical mirror missing: "+" -> ".join(pair))
    required={
        ("W23","W25"):"no_water_sword",
        ("W23","W26"):"kaileena_transferred_to_present",
        ("W24","W26"):"water_sword_required",
        ("W26","W27"):"defeat_da_haka",
        ("W27","W28"):"canonical_sequel",
    }
    for pair,relation in required.items():
        if pairs.get(pair)!=relation:
            errors.append("canonical/standard causal prerequisite missing: "+" -> ".join(pair))
    from collections import deque
    queue=deque(node for node,degree in indeg.items() if degree==0)
    n=0
    while queue:
        u=queue.popleft()
        n+=1
        for v in adj[u]:
            indeg[v]-=1
            if indeg[v]==0:queue.append(v)
    if n!=len(events):
        errors.append("forward event progression has a directed cycle")
    def reachable(a,b):
        seen={a}
        queue=deque([a])
        while queue:
            u=queue.popleft()
            if u==b:return True
            for v in adj.get(u,()):
                if v not in seen:
                    seen.add(v)
                    queue.append(v)
        return False
    if not reachable("W01","W29") or not reachable("W23","W26") or not reachable("W24","W26"):
        errors.append("canonical continuation is causally disconnected")
    if reachable("W25","W28") or reachable("W25","W29"):
        errors.append("noncanonical Kaileena-death ending leaks into canonical sequel")
    for end in endings:
        ref=set(end["referenced_events"])
        if not ref<=set(events):
            errors.append("ending references an unknown event: "+end["branch_id"])
        if end["canonical_for_next_game"]:
            if not {"W23","W24","W26","W27","W28"}<=ref:
                errors.append("canon ending missing transfer, sword, combat or sequel evidence")
            if events["W26"]["worldline_variant"]!=end["worldline"] or events["W27"]["worldline_variant"]!=end["worldline"]:
                errors.append("canon ending events belong to another worldline")
        else:
            if not {"W23","W25"}<=ref or "W28" in ref:
                errors.append("standard ending missing evidence or points into sequel")
            if events["W25"]["worldline_variant"]!=end["worldline"]:
                errors.append("standard ending event belongs to another worldline")
    return errors

def validate():
    problems=[]
    def chk(ok,reason):
        if not ok:problems.append(reason)
    meta=json.loads((BASE/"manifest.json").read_text(encoding="utf8"))
    catalog=json.loads((SRC/"prince_of_persia_catalog.json").read_text(encoding="utf8"))
    temporal=json.loads((SRC/"warrior_within_temporal.json").read_text(encoding="utf8"))
    mechanism_source=json.loads((SRC/"prince_mechanics.json").read_text(encoding="utf8"))
    data={name:jsonl(name) for name in EXPECTED}
    for name,expected in EXPECTED.items():
        chk(len(data[name])==expected,f"{name}: {len(data[name])} != {expected}")
        chk(meta.get("counts",{}).get(name)==expected,"manifest count mismatch: "+name)
    for p in sorted(SRC.glob("*.json")):
        path=str(p.relative_to(ROOT))
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        chk(meta.get("hashes",{}).get(path)==sha,"source hash mismatch: "+path)
    chk(meta.get("schema_version")=="0.3.0","schema version mismatch")
    chk(meta.get("quality_effect")=="not_evaluated" and meta.get("story_quality_trials")==0
        and meta.get("new_paid_model_calls")==0 and meta.get("lumi_production_modified") is False,
        "false paid trial or LUMI production status")
    chk(not jsonl("quality_evaluations") and not jsonl("lumi_usage_history"),
        "Unperformed evaluations/usage must remain empty")

    works=data["works"];wids={x["work_id"] for x in works}
    chk(len(wids)==len(works),"duplicate work ids")
    chk(works==catalog["works"],"compiled works drift from canonical sources")
    releases=data["supplementary_releases"]
    chk(releases==catalog["secondary_releases"],"derivative releases drift from canonical")
    by_source={s["source_id"]:s for s in data["sources"]}
    chk(len(by_source)==len(data["sources"]),"source ID duplicate")
    chk(data["sources"]==catalog["sources"],"compiled sources drift")
    chk(all(re.match(r"^https://",s.get("url","")) for s in by_source.values()),"source URL not HTTPS")
    chk(all(s.get("verification")=="web_search_or_open_retrieved" for s in by_source.values()),
        "source labeled as more strongly verified than search/open")
    chk(all(w.get("lumi_canon") is False and w.get("quality_effect")=="not_evaluated"
        and w.get("editorial_stage")=="sourced_first_pass" for w in works),
        "unsupported work promotion")
    chk(all(3<=len(w.get("beats_tr",[]))<=6 for w in works),"unknown story synopsis depth")
    chk(all(len(w.get("story_overview_tr",""))>=240 for w in works),
        "story synopses too short")
    chk(all(set(w.get("source_ids",[]))<=set(by_source) and len(w.get("source_ids",[]))>=2
        for w in works),"story source reference invalid")
    chk(all(set(x.get("source_ids",[]))<=set(by_source)
        and (x.get("parent_work_id") is None or x["parent_work_id"] in wids)
        for x in releases),"derivative source or parent invalid")
    canceled=[x for x in releases if x.get("class")=="cancelled_not_released"]
    chk(len(canceled)==1 and canceled[0]["release_id"]=="SOT-REMAKE-CANCELLED",
        "2026 remake cancellation cannot be counted as shipped game")
    chk("SOT-REMAKE-CANCELLED" not in wids,"cancelled remake is in analysis units")
    pairs={(x["work_id"],x["ordinal"]) for x in data["story_beats"]}
    chk(len(pairs)==len(data["story_beats"]),"duplicate story beat order")
    beats={x["beat_id"]:x for x in data["story_beats"]}
    chk(len(beats)==len(data["story_beats"]),"duplicate story beat ID")
    chk(all(x["work_id"] in wids and x["source_ids"]
        and set(x["source_ids"])<=set(by_source) for x in beats.values()),"orphan story beat")
    for w in works:
        subset=[b for b in data["story_beats"] if b["work_id"]==w["work_id"]]
        chk([x["ordinal"] for x in subset]==list(range(1,len(w["beats_tr"])+1)),
            w["work_id"]+" story beat order changed")
        chk([x["observed_event_tr"] for x in subset]==w["beats_tr"],
            w["work_id"]+" story beat content drift")
        chk((DOCS/"works"/(w["work_id"].lower()+".md")).is_file(),
            w["work_id"]+" story document missing")
    source_event={x["event_id"]:x for x in temporal["events"]}
    events={x["event_id"]:x for x in data["temporal_events"]}
    chk(len(events)==len(data["temporal_events"]),"duplicate temporal event IDs")
    chk(data["temporal_events"]==temporal["events"],"temporal events drift")
    chk([x["player_reveal_order"] for x in temporal["events"]]==list(range(1,30)),
        "player reveal sequence not contiguous")
    chk(len(set(x["location_id"] for x in data["temporal_locations"]))==7,
        "time locations duplicate")
    chk(data["temporal_locations"]==temporal["locations"],"temporal location drift")
    chk(data["temporal_edges"]==temporal["edges"],"temporal graph drift")
    problems.extend(causal_graph_errors(data["temporal_events"],data["temporal_edges"],data["ending_branches"]))
    chk(all(x["from_event_id"] in events and x["to_event_id"] in events
        for x in data["temporal_edges"]),"temporal graph has orphan nodes")
    chk(len({(x["from_event_id"],x["to_event_id"],x["relation"])
        for x in data["temporal_edges"]})==len(data["temporal_edges"]),
        "temporal graph duplicate")
    chk(all(x.get("inference") is True for x in data["temporal_edges"]
        if x.get("is_temporal_loop")),"speculative loop falsely marked fact")
    chk(all(x.get("scope")=="observed_event_not_rule"
        and x.get("source_ids") and set(x["source_ids"])<=set(by_source)
        and len(x.get("epistemic_state_before_tr",""))>60
        and len(x.get("state_delta_tr",""))>=24
        for x in events.values()),"temporal event lacks provenance/knowledge/State")
    chk(all(x.get("epoch") in temporal["time_epochs"]
        and x.get("worldline_variant") in temporal["worldline_variants"]
        for x in events.values()),"unknown time epoch or worldline variant")
    chk(all(x["time_slot_id"]==events["W16"]["time_slot_id"]
        for x in (events["W08"],events["W16"])),"first Wraith encounter has no common time slot")
    chk(events["W10"]["time_slot_id"]==events["W19"]["time_slot_id"]==
        events["W20"]["time_slot_id"],"Dahaka intersections not aligned")
    chk(events["W10"]["worldline_variant"] != events["W20"]["worldline_variant"],
        "revised Dahaka result overwritten onto first history")
    chk("wraith_dead" in events["W10"]["state_delta_tr"]
        and "wraith_survives" in events["W20"]["state_delta_tr"],
        "first and revised Dahaka outcomes merged")
    chk(events["W15"]["actor_version"]=="PRINCE" and
        events["W16"]["actor_version"]=="SAND_WRAITH",
        "mask transformation and returned self confused")
    chk("ISLAND_PAST"==events["W12"]["epoch"] and
        "ISLAND_PRESENT"==events["W25"]["epoch"],
        "Kaileena temporal death location confused")
    chk(events["W24"]["epoch"]=="ISLAND_PAST"
        and events["W24"]["analysis_order_not_required_gameplay_order"] is True
        and events["W24"]["earliest_documented_acquisition_before_mask"] is True
        and events["W24"]["actor_version"]=="PRINCE",
        "Water Sword acquisition timeline incorrectly marked as today/required linear event")
    chk(events["W28"]["worldline_variant"]=="CANON_TRANSFER" and
        events["W29"]["worldline_variant"]=="CANON_TRANSFER",
        "Two Thrones should only follow canonical branch")
    endings=data["ending_branches"]
    chk(endings==temporal["ending_branches"],"ending branch canonical drift")
    chk(len({x["branch_id"] for x in endings})==2,"ending ID collision")
    true_end=[x for x in endings if x["canonical_for_next_game"]]
    false_end=[x for x in endings if not x["canonical_for_next_game"]]
    chk(len(true_end)==len(false_end)==1,"two endings may not both be canon")
    if true_end and false_end:
        chk("life_upgrades == 9" in true_end[0]["condition"] and
            "water_sword_obtained == true" in true_end[0]["condition"],
            "Water Sword nine-upgrade prerequisite not preserved")
        chk("water_sword_obtained == false" in false_end[0]["condition"],
            "standard-ending guard is inaccurate")
        chk("kaileena_alive=true" in true_end[0]["state_outcome"] and
            "kaileena_alive=false" in false_end[0]["state_outcome"],
            "ending worlds are accidentally merged")

    original_cm=[json.loads(row) for row in
        (ROOT/"data/nova/v0.2/mechanisms.jsonl").read_text(encoding="utf8").splitlines()
        if row.strip()]
    cm_ids={x["mechanic_id"] for x in original_cm}
    new=data["mechanics"]
    chk(new==mechanism_source["mechanics"],"compiled mechanic drift")
    chk([x["mechanic_id"] for x in new]==[f"POP-{x:03d}" for x in range(1,23)],
        "mechanic IDs not unique and ordered")
    chk(not cm_ids.intersection({x["mechanic_id"] for x in new}),
        "mechanic ID collides with existing NOVA")
    all_anchor_ids=set(events)|set(beats)
    chk(all(m["evidence_anchors"] and set(m["evidence_anchors"])<=all_anchor_ids
        and m.get("guardrail_tr") and len(m["guardrail_tr"])>=70
        and len(m.get("abstraction_tr",""))>=75
        and m.get("quality_effect")=="not_evaluated"
        and m.get("lumi_canon") is False
        and set(m["related_cm_ids"])<=cm_ids
        for m in new),"mechanic source/guardrails not valid")
    evidence=data["mechanic_evidence"]
    pairs={(x["mechanic_id"],x["anchor_id"]) for x in evidence}
    expect={(m["mechanic_id"],k) for m in new for k in m["evidence_anchors"]}
    chk(len(pairs)==len(evidence) and pairs==expect,
        "mechanic-to-observation evidence incomplete")
    for x in evidence:
        if x["anchor_id"] in events:
            origin=events[x["anchor_id"]];sid=origin["source_ids"];wid="WW-2004"
        else:
            origin=beats[x["anchor_id"]];sid=origin["source_ids"];wid=origin["work_id"]
        chk(x["source_ids"]==sid and x["work_id"]==wid,"evidence wrong source work: "+x["evidence_id"])
        chk(x.get("mechanism_inference") is True and
            x.get("quality_effect")=="not_evaluated","mechanic evidence falsely proves quality")
    links=data["cross_corpus_links"]
    chk(len({(l["from_id"],l["to_existing_id"]) for l in links})==len(links),
        "cross version link duplicates")
    chk(all(l["from_id"] in {x["mechanic_id"] for x in new}
        and l["to_existing_id"] in cm_ids
        and l["quality_effect"]=="not_evaluated"
        for l in links),"cross version link invalid")
    for page in ("README.md","WARRIOR_WITHIN_TIME_MODEL.md",
                 "TEMPORAL_LOCATIONS.md","MECHANICS_INDEX.md",
                 "CONTINUITY_FIREWALL.md","SOURCES.md"):
        chk((DOCS/page).is_file() and (DOCS/page).stat().st_size>500,"missing research doc: "+page)
    return {
        "status":"PASS" if not problems else "FAIL",
        "scope":"STRUCTURE_PROVENANCE_CAUSAL_BRANCH_FIREWALL_NOT_STORY_QUALITY",
        "source_research_cutoff":catalog.get("research_cutoff_date"),
        "counts":{k:len(v) for k,v in data.items()},
        "old_cm_mechanisms_unchanged":len(cm_ids),
        "independent_quality_ab_trials":0,
        "new_paid_api_calls":0,
        "main_and_lumi_production_untouched_by_this_validator":True,
        "limitations":[
            "All stories are first-pass sourced Turkish paraphrases, not independent expert editorial audits.",
            "No gameplay capture or game-file extraction; source URLs might be blocked or changed.",
            "Warrior Within temporal edges include explicit inference links; game does not specify complete paradox physics.",
            "No story-generation runs and no assessment of causal narrative quality."
        ],
        "errors":problems
    }

if __name__=="__main__":
    try:r=validate()
    except Exception as exc:r={"status":"FAIL","fatal":repr(exc)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r["status"]=="PASS" else 1)
