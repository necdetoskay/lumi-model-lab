from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE = Path("experiments/fixtures/aion35_foundation_architect_qualification_02_20260926.json")
OUT = Path("runs/aion35-foundation-architect-qualification-02/result.json")

ARCHITECT_MODEL = "aion-labs/aion-3.5"
PROVENANCE_VALIDATOR = "anthropic/claude-sonnet-5"
BOUNDARY_VALIDATOR = "openai/gpt-5.6-sol"
SEED = 2026092821

ARCHITECT_SYSTEM = r"""
You are the LUMI Foundation Architect.

You propose candidate Origin + reveal-safe Saga + PRE-STORY MATERIALIZATION SEEDS.
You do NOT generate actual Opportunities, StoryIntent, StoryContract or story prose.
You do NOT commit canon.

Every generated semantic candidate MUST have:
- proposal_key: a local non-canonical key unique inside this response;
- source_refs: exact JSON pointers copied from allowed_source_pointers;
- candidate_only: true.

Local proposal_key is NOT a database id and MUST NOT look like a UUID.

You may creatively derive age-appropriate lived-history candidates from supplied preferences/world facts, but they remain candidates until application validation.

CRITICAL:
- exact age 4 / childhood;
- GARDEN_GATE is RUMORED only;
- no fact beyond GARDEN_GATE;
- no magic/impossible technology;
- trusted caregiver exists but identity/name/family relation is unknown;
- other NPCs may only be role candidates, identity unbound;
- no deep Saga truth supplied => deep_truth_candidates MUST be [];
- no database IDs, UUIDs, fingerprints or commit claims;
- current_situation MUST NOT invent recent events, weather, messages, meetings, "yesterday", "earlier", "recently", "these days", or NPC actions unless directly supplied;
- actual Opportunity generation belongs to A4. Return opportunity_source_signals only, not hooks, plots or solutions.

Return JSON only:
{
  "character_echo": {
    "name":"Deniz",
    "exact_age":4,
    "lifecycle_stage":"childhood",
    "broad_kind":"human",
    "character_type":"explorer",
    "subtype":"curious-child"
  },
  "origin": {
    "public_summary":"candidate summary",
    "life_facts":[
      {
        "proposal_key":"origin.fact.1",
        "fact":"candidate fact",
        "epistemic_class":"character_known|character_belief|public_candidate",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true,
        "creative_derivation":true
      }
    ],
    "formative_events":[
      {
        "proposal_key":"origin.event.1",
        "event":"small prior event candidate",
        "character_takeaway":"bounded takeaway",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true,
        "creative_derivation":true
      }
    ],
    "prior_activities":[
      {
        "proposal_key":"origin.activity.1",
        "activity":"age-appropriate activity candidate",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true
      }
    ],
    "meaningful_people":[
      {
        "proposal_key":"origin.person.1",
        "role":"role only",
        "identity_status":"unbound_role_candidate",
        "relationship_seed":"bounded candidate",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true
      }
    ],
    "unresolved_questions":[
      {
        "proposal_key":"origin.question.1",
        "question":"child-scale unresolved question",
        "knowledge_boundary":"what is known vs unknown",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true
      }
    ]
  },
  "saga": {
    "public_premise":"candidate premise",
    "long_horizon_tensions":[
      {
        "proposal_key":"saga.tension.1",
        "tension":"child-scale long horizon tension",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true
      }
    ],
    "deep_truth_candidates":[],
    "known_truth_proposals":[
      {
        "proposal_key":"saga.known.1",
        "statement":"candidate known truth",
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ],
    "belief_proposals":[
      {
        "proposal_key":"saga.belief.1",
        "statement":"candidate belief",
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ],
    "reveal_constraints":["explicit hard reveal rules"],
    "safe_breadcrumbs":[
      {
        "proposal_key":"saga.breadcrumb.1",
        "breadcrumb":"safe reusable signal candidate",
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ],
    "open_threads":[
      {
        "proposal_key":"saga.thread.1",
        "thread":"open question/tension candidate",
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ],
    "continuity_rules":["future continuity rules"]
  },
  "materialization_seeds": {
    "inventory":[
      {
        "proposal_key":"inventory.1",
        "item_concept":"ordinary item candidate",
        "source_class":"EVERYDAY|PERSONAL|RELATIONSHIP|TRAVEL_OR_SURVIVAL|ROLE_OR_PROFESSION|LEGACY|MYSTERY",
        "ordinary":true,
        "provenance":"brief",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true
      }
    ],
    "social_ecology":[
      {
        "proposal_key":"social.1",
        "role":"role-only candidate",
        "identity_status":"unbound_role_candidate",
        "relationship_direction":"bounded candidate",
        "reuse_preference":"reuse compatible existing NPC if one exists",
        "source_refs":["exact allowed pointer"],
        "candidate_only":true
      }
    ],
    "memories":[
      {
        "proposal_key":"memory.1",
        "memory_summary":"age-appropriate candidate memory",
        "visibility":"character_known",
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ],
    "origin_threads":[
      {
        "proposal_key":"thread.1",
        "thread":"latent question/tension",
        "not_a_quest":true,
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ],
    "current_situation": {
      "grounded_now":[
        {
          "statement":"ONLY directly supplied current fact",
          "source_refs":["exact allowed pointer"]
        }
      ],
      "candidate_goals":[
        {
          "proposal_key":"current.goal.1",
          "goal":"small candidate goal",
          "source_refs":["exact allowed pointer"],
          "depends_on_proposals":[],
          "candidate_only":true
        }
      ],
      "candidate_concerns":[
        {
          "proposal_key":"current.concern.1",
          "concern":"small candidate concern",
          "source_refs":["exact allowed pointer"],
          "depends_on_proposals":[],
          "candidate_only":true
        }
      ],
      "rumor_safe":[
        {
          "statement":"only supplied rumor-safe material",
          "source_refs":["exact allowed pointer"]
        }
      ],
      "candidate_only":true
    },
    "opportunity_source_signals":[
      {
        "proposal_key":"oppsignal.1",
        "signal_class":"origin|saga|inventory|social|memory|thread|current_situation|local_map|rumor",
        "signal":"source material that A4 could later consume",
        "source_refs":["exact allowed pointer"],
        "depends_on_proposals":[],
        "candidate_only":true
      }
    ]
  },
  "provider_notes":{
    "assumptions":[],
    "risks":[]
  }
}

BOUNDED COUNTS:
- life_facts 3-6
- formative_events 1-3
- prior_activities 1-4
- meaningful_people 1-3
- unresolved_questions 1-3
- long_horizon_tensions 1-3
- safe_breadcrumbs 3-6
- open_threads 2-4
- continuity_rules 3-6
- inventory 2-5
- social_ecology 1-3
- memories 2-4
- origin_threads 1-3
- opportunity_source_signals 2-5

Do not fabricate "recent" chronology.
""".strip()

VALIDATOR_SYSTEM = r"""
You validate one LUMI Foundation Architect candidate package.

Report serious/critical defects only.

Hard checks:
- exact age 4 / child-scale;
- all semantic output remains candidate-only except direct grounded_now/rumor-safe statements;
- every source_ref must point to authoritative onboarding/world input supplied in allowed_source_pointers;
- creative derivation is allowed for Origin/Memory candidates, but NOT for grounded_now recent/current facts;
- current_situation may not invent recent chronology, weather, NPC actions/messages/meetings, possession-in-hand, or events absent from authoritative input;
- no actual Opportunity hook, plot, solution, title, conflict/resolution sequence; only source signals for A4;
- no deep Saga truth;
- no GARDEN_GATE reveal;
- no named/identified caregiver or NPC;
- no DB IDs/UUIDs/fingerprints/commit claims;
- proposed inventory/social/memory/thread candidates may depend on each other only through explicit local proposal dependencies;
- do not treat unmaterialized candidate inventory/relationship/memory as current fact;
- no adult profession/travel/life history;
- output must be concrete enough for downstream materializers, not generic filler.

Defect classes:
age_lifecycle_mismatch
unsupported_current_state
unsupported_durable_canon
epistemic_leak
saga_reveal_leak
social_identity_invention
provenance_failure
candidate_as_fact
scope_violation
opportunity_scope_violation
domain_authority_violation
downstream_unusable
internal_contradiction

Return JSON only:
{
  "valid":true,
  "downstream_usable":true,
  "counts":{"critical":0,"serious":0},
  "defects":[
    {
      "severity":"critical|serious",
      "class":"age_lifecycle_mismatch|unsupported_current_state|unsupported_durable_canon|epistemic_leak|saga_reveal_leak|social_identity_invention|provenance_failure|candidate_as_fact|scope_violation|opportunity_scope_violation|domain_authority_violation|downstream_unusable|internal_contradiction",
      "path":"json path",
      "why":"brief"
    }
  ],
  "strengths":["up to five"],
  "summary":"brief"
}
""".strip()


def leaf_pointers(value: Any, prefix: str = "$") -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            child = f"{prefix}.{k}"
            if isinstance(v, (dict, list)):
                out |= leaf_pointers(v, child)
            else:
                out.add(child)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            child = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                out |= leaf_pointers(v, child)
            else:
                out.add(child)
    return out


def collect_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "proposal_key" in value:
            rows.append(value)
        for child in value.values():
            rows.extend(collect_rows(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(collect_rows(child))
    return rows


def all_source_refs(value: Any, path: str = "$") -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            p = f"{path}.{k}"
            if k == "source_refs" and isinstance(v, list):
                refs.extend((p, str(x)) for x in v)
            else:
                refs.extend(all_source_refs(v, p))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            refs.extend(all_source_refs(child, f"{path}[{i}]"))
    return refs


def deterministic_check(payload: dict[str, Any], allowed: set[str]) -> list[str]:
    errors: list[str] = []

    # canonical IDs/UUIDs are forbidden; local proposal_key is the only allowed identity field.
    def walk_keys(value: Any, path: str = "$"):
        if isinstance(value, dict):
            for key, child in value.items():
                kl = key.casefold()
                if key != "proposal_key" and (kl == "id" or kl.endswith("_id") or kl == "uuid" or kl.endswith("_uuid") or "fingerprint" in kl):
                    errors.append(f"forbidden_identity_field:{path}.{key}")
                walk_keys(child, f"{path}.{key}")
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk_keys(child, f"{path}[{i}]")
    walk_keys(payload)

    rows = collect_rows(payload)
    proposal_keys = [str(x.get("proposal_key") or "") for x in rows]
    if not proposal_keys or any(not x for x in proposal_keys):
        errors.append("proposal_keys_missing")
    if len(proposal_keys) != len(set(proposal_keys)):
        errors.append("proposal_keys_duplicate")
    uuidish = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-")
    for key in proposal_keys:
        if uuidish.match(key):
            errors.append(f"proposal_key_uuidish:{key}")

    for path, ref in all_source_refs(payload):
        if ref not in allowed:
            errors.append(f"invalid_source_ref:{path}:{ref}")

    for row in rows:
        if row.get("candidate_only") is not True:
            errors.append(f"candidate_only_missing:{row.get('proposal_key')}")

    saga = payload.get("saga") or {}
    if saga.get("deep_truth_candidates") != []:
        errors.append("deep_truth_candidates_must_be_empty")

    ms = payload.get("materialization_seeds") or {}
    if "initial_opportunities" in ms:
        errors.append("actual_opportunity_generation_forbidden")
    signals = ms.get("opportunity_source_signals")
    if not isinstance(signals, list) or not 2 <= len(signals) <= 5:
        errors.append("opportunity_source_signals_count")

    current = ms.get("current_situation") or {}
    if current.get("candidate_only") is not True:
        errors.append("current_situation_candidate_only")
    text = json.dumps(current, ensure_ascii=False).casefold()
    for token in ("yesterday", "earlier", "recently", "these past days", "today the", "waved yesterday"):
        if token in text:
            errors.append(f"unsupported_recent_chronology_token:{token}")

    families = {
        "life_facts": (payload.get("origin") or {}).get("life_facts"),
        "formative_events": (payload.get("origin") or {}).get("formative_events"),
        "prior_activities": (payload.get("origin") or {}).get("prior_activities"),
        "meaningful_people": (payload.get("origin") or {}).get("meaningful_people"),
        "unresolved_questions": (payload.get("origin") or {}).get("unresolved_questions"),
        "inventory": ms.get("inventory"),
        "social_ecology": ms.get("social_ecology"),
        "memories": ms.get("memories"),
        "origin_threads": ms.get("origin_threads"),
    }
    bounds = {
        "life_facts":(3,6),"formative_events":(1,3),"prior_activities":(1,4),
        "meaningful_people":(1,3),"unresolved_questions":(1,3),
        "inventory":(2,5),"social_ecology":(1,3),"memories":(2,4),"origin_threads":(1,3),
    }
    for name, value in families.items():
        if not isinstance(value, list):
            errors.append(f"{name}:not_list")
            continue
        lo, hi = bounds[name]
        if not lo <= len(value) <= hi:
            errors.append(f"{name}:count={len(value)} expected={lo}-{hi}")

    for i,row in enumerate((payload.get("origin") or {}).get("meaningful_people") or []):
        if row.get("identity_status") != "unbound_role_candidate":
            errors.append(f"origin.meaningful_people[{i}].identity_status")
    for i,row in enumerate(ms.get("social_ecology") or []):
        if row.get("identity_status") != "unbound_role_candidate":
            errors.append(f"materialization_seeds.social_ecology[{i}].identity_status")

    return errors


def validator_pass(v: dict[str, Any]) -> bool:
    c=v.get("counts") or {}
    return bool(v.get("valid")) and bool(v.get("downstream_usable")) and int(c.get("critical",0) or 0)==0 and int(c.get("serious",0) or 0)==0


def usd(meta: dict[str, Any] | None) -> float:
    return float((((meta or {}).get("cost") or {}).get("usd")) or 0.0)


def main():
    load_dotenv()
    api_key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    allowed=leaf_pointers(fixture["source_authority"], "$.source_authority")
    payload={**fixture, "allowed_source_pointers":sorted(allowed)}
    started=time.perf_counter()

    foundation, architect_meta=structured_call(
        api_key=api_key, model=ARCHITECT_MODEL, system=ARCHITECT_SYSTEM,
        payload=payload, seed=SEED, max_tokens=None, request_class="story_planning"
    )
    deterministic_errors=deterministic_check(foundation, allowed)

    vp={
        "fixture":fixture,
        "allowed_source_pointers":sorted(allowed),
        "candidate_foundation":foundation,
        "deterministic_errors":deterministic_errors,
    }
    provenance, provenance_meta=structured_call(
        api_key=api_key, model=PROVENANCE_VALIDATOR, system=VALIDATOR_SYSTEM,
        payload=vp, seed=SEED+1, max_tokens=3600, request_class="editorial_audit"
    )
    boundary, boundary_meta=structured_call(
        api_key=api_key, model=BOUNDARY_VALIDATOR, system=VALIDATOR_SYSTEM,
        payload=vp, seed=SEED+2, max_tokens=3600, request_class="editorial_audit"
    )

    passed=not deterministic_errors and validator_pass(provenance) and validator_pass(boundary)
    result={
        "schema_version":"aion35-foundation-architect-qualification-result.v2",
        "qualification_id":fixture["qualification_id"],
        "models":{
            "architect":ARCHITECT_MODEL,
            "provenance_validator":PROVENANCE_VALIDATOR,
            "boundary_validator":BOUNDARY_VALIDATOR,
        },
        "candidate_foundation":foundation,
        "deterministic_errors":deterministic_errors,
        "provenance_validation":provenance,
        "boundary_validation":boundary,
        "qualification_pass":passed,
        "cost_usd":{
            "architect":usd(architect_meta),
            "provenance_validator":usd(provenance_meta),
            "boundary_validator":usd(boundary_meta),
        },
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    result["cost_usd"]["total"]=sum(result["cost_usd"].values())
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"foundation.json").write_text(json.dumps(foundation,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "qualification_pass":passed,
        "deterministic_errors":deterministic_errors,
        "provenance_validation":provenance,
        "boundary_validation":boundary,
        "cost_usd":result["cost_usd"],
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
