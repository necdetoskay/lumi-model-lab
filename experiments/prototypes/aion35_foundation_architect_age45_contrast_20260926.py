from __future__ import annotations
import json, os, re, time
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE=Path("experiments/fixtures/aion35_foundation_architect_age45_contrast_20260926.json")
OUT=Path("runs/aion35-foundation-architect-age45-contrast/result.json")
ARCHITECT="aion-labs/aion-3.5"
BOUNDARY="anthropic/claude-sonnet-5"
DEPTH="openai/gpt-5.6-sol"
SEED=2026092841

ARCHITECT_SYSTEM=r"""
You are the LUMI Foundation Architect.

Produce candidate-only Rich Origin + reveal-safe Saga + pre-story materialization seeds for an EXACTLY 45-year-old human explorer/cartographer profile.
Do NOT write a story or actual Opportunity.
Do NOT commit canon.

Every semantic candidate must include:
- proposal_key (local, non-canonical, not UUID-like)
- source_refs copied exactly from allowed_source_pointers
- candidate_only:true

Adult lifecycle requirements:
- reflect decades of plausible prior life rather than child-scale recent play only;
- include prior role/responsibility candidates and multi-stage lived-history candidates;
- include meaningful adult relationship ROLE candidates without names/identities;
- include unresolved commitments/questions suitable to adult continuity;
- inventory may include role/profession items if plausibly grounded;
- memories/formative events may reflect work, exploration, responsibility, loss/change/unfinished commitments, but remain candidate-only and source-grounded;
- do not over-invent a full biography.

Hard boundaries:
- ordinary everyday physics only;
- OLD_QUARRY_TRAIL is RUMORED = hearsay-level awareness only;
- no claim of visiting it, no interior detail, no confirmed route/content;
- no named NPC identities;
- no DB ids/fingerprints/commit claims;
- deep_truth_candidates must be [];
- current_situation grounded_now may contain only directly supplied current facts;
- do not invent recent events/weather/messages/meetings into grounded_now;
- opportunity_source_signals only, never hooks/plots/solutions.

Return JSON only:
{
  "character_echo":{"name":"Aras","exact_age":45,"lifecycle_stage":"adulthood","broad_kind":"human","character_type":"explorer","subtype":"field-cartographer"},
  "origin":{
    "public_summary":"candidate summary",
    "life_facts":[{"proposal_key":"origin.fact.1","fact":"...","source_refs":["..."],"candidate_only":true,"creative_derivation":true}],
    "formative_events":[{"proposal_key":"origin.event.1","event":"...","character_takeaway":"...","source_refs":["..."],"candidate_only":true,"creative_derivation":true}],
    "prior_roles":[{"proposal_key":"origin.role.1","role":"...","responsibility":"...","source_refs":["..."],"candidate_only":true}],
    "prior_activities":[{"proposal_key":"origin.activity.1","activity":"...","source_refs":["..."],"candidate_only":true}],
    "meaningful_people":[{"proposal_key":"origin.person.1","role":"role-only","identity_status":"unbound_role_candidate","relationship_seed":"...","source_refs":["..."],"candidate_only":true}],
    "unresolved_questions":[{"proposal_key":"origin.question.1","question":"...","knowledge_boundary":"...","source_refs":["..."],"candidate_only":true}]
  },
  "saga":{
    "public_premise":"...",
    "long_horizon_tensions":[{"proposal_key":"saga.tension.1","tension":"...","source_refs":["..."],"candidate_only":true}],
    "deep_truth_candidates":[],
    "known_truth_proposals":[{"proposal_key":"saga.known.1","statement":"...","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
    "belief_proposals":[{"proposal_key":"saga.belief.1","statement":"...","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
    "reveal_constraints":["..."],
    "safe_breadcrumbs":[{"proposal_key":"saga.breadcrumb.1","breadcrumb":"...","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
    "open_threads":[{"proposal_key":"saga.thread.1","thread":"...","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
    "continuity_rules":["..."]
  },
  "materialization_seeds":{
    "inventory":[{"proposal_key":"inventory.1","item_concept":"...","source_class":"EVERYDAY|PERSONAL|RELATIONSHIP|TRAVEL_OR_SURVIVAL|ROLE_OR_PROFESSION|LEGACY|MYSTERY","ordinary":true,"provenance":"...","source_refs":["..."],"candidate_only":true}],
    "social_ecology":[{"proposal_key":"social.1","role":"role-only","identity_status":"unbound_role_candidate","relationship_direction":"...","reuse_preference":"reuse compatible existing NPC if one exists","source_refs":["..."],"candidate_only":true}],
    "memories":[{"proposal_key":"memory.1","memory_summary":"...","visibility":"character_known","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
    "origin_threads":[{"proposal_key":"thread.1","thread":"...","not_a_quest":true,"source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
    "current_situation":{
      "grounded_now":[{"statement":"directly supplied current fact","source_refs":["..."]}],
      "candidate_goals":[{"proposal_key":"current.goal.1","goal":"...","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
      "candidate_concerns":[{"proposal_key":"current.concern.1","concern":"...","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}],
      "rumor_safe":[{"statement":"rumor-safe statement","source_refs":["..."]}],
      "candidate_only":true
    },
    "opportunity_source_signals":[{"proposal_key":"oppsignal.1","signal_class":"origin|saga|inventory|social|memory|thread|current_situation|local_map|rumor","signal":"source material only","source_refs":["..."],"depends_on_proposals":[],"candidate_only":true}]
  },
  "provider_notes":{"assumptions":[],"risks":[]}
}

Counts:
life_facts 5-8
formative_events 3-5
prior_roles 1-3
prior_activities 2-5
meaningful_people 2-4
unresolved_questions 2-4
long_horizon_tensions 2-4
safe_breadcrumbs 3-6
open_threads 2-5
inventory 4-7
social_ecology 2-4
memories 3-6
origin_threads 2-4
opportunity_source_signals 3-6
""".strip()

BOUNDARY_SYSTEM=r"""
Validate the adult Foundation Architect candidate package.
Serious/critical only.

Check:
- exact age/lifecycle correctness;
- candidate-only authority;
- exact source provenance;
- no named NPCs or DB ids;
- no RUMORED upgrade beyond hearsay;
- no deep Saga truth;
- grounded_now contains only supplied current facts;
- no actual Opportunity hook/plot/solution;
- no unsupported current chronology;
- no contradiction/physics break;
- package is usable by downstream materializers.

Return JSON only:
{"valid":true,"downstream_usable":true,"counts":{"critical":0,"serious":0},"defects":[],"summary":"brief"}
""".strip()

DEPTH_SYSTEM=r"""
Judge whether this 45-year-old Foundation Architect output has materially deeper lived-life structure than the supplied age-4 control summary.

Do NOT reward verbosity alone.
PASS requires adult-scale semantics, not just more bullets:
- at least one plausible prior role/responsibility candidate;
- multi-stage/multi-year lived-history candidates;
- adult relationship-role candidates without invented identities;
- unresolved adult commitment/question with continuity potential;
- role/provenance inventory;
- memories/formative events reflecting adult responsibility/work/exploration/long-term choices;
- still bounded, candidate-only, and not a complete invented biography.

Return JSON only:
{
  "adult_depth_pass":true,
  "counts":{"critical":0,"serious":0},
  "defects":[{"severity":"critical|serious","class":"childlike_depth|missing_adult_role|missing_commitment|missing_provenance|overinvented_biography|other","why":"brief"}],
  "evidence":{"adult_scale_dimensions":["..."],"contrast_with_child":["..."]},
  "summary":"brief"
}
""".strip()

def leaf_pointers(v:Any,p="$")->set[str]:
    out=set()
    if isinstance(v,dict):
        for k,x in v.items():
            c=f"{p}.{k}"
            if isinstance(x,(dict,list)): out|=leaf_pointers(x,c)
            else: out.add(c)
    elif isinstance(v,list):
        for i,x in enumerate(v):
            c=f"{p}[{i}]"
            if isinstance(x,(dict,list)): out|=leaf_pointers(x,c)
            else: out.add(c)
    return out

def collect(v:Any)->list[dict[str,Any]]:
    out=[]
    if isinstance(v,dict):
        if "proposal_key" in v: out.append(v)
        for x in v.values(): out+=collect(x)
    elif isinstance(v,list):
        for x in v: out+=collect(x)
    return out

def refs(v:Any,p="$")->list[tuple[str,str]]:
    out=[]
    if isinstance(v,dict):
        for k,x in v.items():
            q=f"{p}.{k}"
            if k=="source_refs" and isinstance(x,list): out += [(q,str(a)) for a in x]
            else: out += refs(x,q)
    elif isinstance(v,list):
        for i,x in enumerate(v): out += refs(x,f"{p}[{i}]")
    return out

def det_check(v:dict[str,Any],allowed:set[str])->list[str]:
    e=[]
    rows=collect(v)
    keys=[str(x.get("proposal_key") or "") for x in rows]
    if not keys or len(keys)!=len(set(keys)): e.append("proposal_key_missing_or_duplicate")
    uuidish=re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-")
    if any(uuidish.match(k) for k in keys): e.append("uuidish_proposal_key")
    for row in rows:
        if row.get("candidate_only") is not True: e.append(f"candidate_only_missing:{row.get('proposal_key')}")
    for p,r in refs(v):
        if r not in allowed: e.append(f"invalid_source_ref:{p}:{r}")
    if (v.get("saga") or {}).get("deep_truth_candidates") != []: e.append("deep_truth_must_be_empty")
    ms=v.get("materialization_seeds") or {}
    if "initial_opportunities" in ms: e.append("actual_opportunity_forbidden")
    c=ms.get("current_situation") or {}
    txt=json.dumps(c,ensure_ascii=False).casefold()
    for token in ("yesterday","recently","earlier today","last week","this morning","just received"):
        if token in txt: e.append(f"unsupported_current_chronology:{token}")
    echo=v.get("character_echo") or {}
    expected={"name":"Aras","exact_age":45,"lifecycle_stage":"adulthood","broad_kind":"human","character_type":"explorer","subtype":"field-cartographer"}
    for k,x in expected.items():
        if echo.get(k)!=x: e.append(f"echo_mismatch:{k}")
    return e

def ok(v:dict[str,Any])->bool:
    c=v.get("counts") or {}
    return bool(v.get("valid",v.get("adult_depth_pass"))) and int(c.get("critical",0) or 0)==0 and int(c.get("serious",0) or 0)==0

def usd(m): return float((((m or {}).get("cost") or {}).get("usd")) or 0)

def main():
    load_dotenv()
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    allowed=leaf_pointers(fixture["source_authority"],"$.source_authority")
    payload={**fixture,"allowed_source_pointers":sorted(allowed)}
    start=time.perf_counter()
    foundation,am=structured_call(api_key=os.environ["OPENROUTER_API_KEY"],model=ARCHITECT,system=ARCHITECT_SYSTEM,payload=payload,seed=SEED,max_tokens=None,request_class="story_planning")
    det=det_check(foundation,allowed)
    common={"fixture":fixture,"candidate_foundation":foundation,"deterministic_errors":det}
    boundary,bm=structured_call(api_key=os.environ["OPENROUTER_API_KEY"],model=BOUNDARY,system=BOUNDARY_SYSTEM,payload=common,seed=SEED+1,max_tokens=3400,request_class="editorial_audit")
    depth,dm=structured_call(api_key=os.environ["OPENROUTER_API_KEY"],model=DEPTH,system=DEPTH_SYSTEM,payload={**common,"age4_control_summary":fixture["contrast_requirement"]["child_control_summary"],"adult_requirements":fixture["contrast_requirement"]["adult_must_show"]},seed=SEED+2,max_tokens=2800,request_class="editorial_audit")
    passed=not det and ok(boundary) and ok(depth)
    result={"schema_version":"foundation-architect-age45-contrast-result.v1","qualification_id":fixture["qualification_id"],"candidate_foundation":foundation,"deterministic_errors":det,"boundary_validation":boundary,"depth_validation":depth,"qualification_pass":passed,"cost_usd":{"architect":usd(am),"boundary":usd(bm),"depth":usd(dm)},"elapsed_seconds":round(time.perf_counter()-start,3)}
    result["cost_usd"]["total"]=sum(result["cost_usd"].values())
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"foundation.json").write_text(json.dumps(foundation,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"qualification_pass":passed,"deterministic_errors":det,"boundary_validation":boundary,"depth_validation":depth,"cost_usd":result["cost_usd"],"elapsed_seconds":result["elapsed_seconds"]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
