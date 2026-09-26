from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE = Path("experiments/fixtures/aion35_foundation_architect_qualification_01_20260926.json")
OUT = Path("runs/aion35-foundation-architect-qualification-01/result.json")

ARCHITECT_MODEL = "aion-labs/aion-3.5"
PRIMARY_VALIDATOR = "anthropic/claude-sonnet-5"
SECONDARY_VALIDATOR = "openai/gpt-5.6-sol"
SEED = 2026092811

ARCHITECT_SYSTEM = r"""
You are the LUMI Foundation Architect.

Your task is NOT to write a story.
Your task is NOT to commit canon.
Your task is to propose one structured candidate Foundation package for a newly tracked Character BEFORE Story #1.

The application, not you:
- owns canonical IDs;
- validates every proposal;
- decides visibility/knowledge;
- commits through Foundation, Saga, Inventory, NPC/Relationship, Memory, Thread, Current Situation and Opportunity owners.

You receive authoritative onboarding/world input.
Treat it as immutable.

CRITICAL BOUNDARIES:
1. Exact age/lifecycle matters. A 4-year-old must have a believable CHILD-SCALE prior life, not adult work/travel/professional history.
2. Character creation is tracking start, not birth. The Character may have prior age-appropriate lived experiences.
3. Do not invent canonical world locations beyond supplied ones.
4. GARDEN_GATE is RUMORED only. Do not reveal or assert what lies beyond it.
5. Do not invent magic, supernatural abilities, impossible technology or fantasy facts.
6. No hidden/deep Saga truth was supplied. Therefore deep_truth_candidates MUST be [] in this qualification.
7. A trusted caregiver exists, but no identity/name is supplied. You may propose a caregiver ROLE seed, but do not invent a name or family history.
8. No specific friend/NPC identity was supplied. You may propose role-only social candidates (for example a familiar courtyard child), but identities remain unbound candidates.
9. No possession was supplied as canonical. Inventory entries are candidate concepts only, grounded in age/preferences/current habitat. Favor ordinary items.
10. No memory was supplied as canonical. Memories are candidate pre-story memories only and must remain age-appropriate, ordinary and compatible with supplied world facts.
11. Do not create database IDs, UUIDs, canonical entity IDs, commit refs or fake fingerprints.
12. Do not claim anything was persisted/committed/accepted.
13. Opportunity seeds are HOOKS only, not full plots and not solutions.
14. Richness is useful only when source/provenance remains inspectable. Avoid generic filler.

OUTPUT JSON ONLY with this exact top-level shape:
{
  "character_echo": {
    "name": "Deniz",
    "exact_age": 4,
    "lifecycle_stage": "childhood",
    "broad_kind": "human",
    "character_type": "explorer",
    "subtype": "curious-child"
  },
  "origin": {
    "public_summary": "bounded summary",
    "life_facts": [
      {
        "fact": "candidate lived-life fact",
        "epistemic_class": "character_known|character_belief|public_candidate",
        "source_basis": ["exact supplied input basis"],
        "why_age_fit": "brief"
      }
    ],
    "formative_events": [
      {
        "event": "small prior event",
        "character_takeaway": "what Deniz remembers/believes from it",
        "source_basis": ["supplied basis"],
        "why_age_fit": "brief"
      }
    ],
    "prior_activities": [
      {
        "activity": "age-appropriate recurring/previous activity",
        "source_basis": ["supplied basis"]
      }
    ],
    "meaningful_people": [
      {
        "role": "role-only candidate",
        "identity_status": "unbound_role_candidate",
        "relationship_seed": "bounded relationship direction",
        "source_basis": ["supplied basis"]
      }
    ],
    "unresolved_questions": [
      {
        "question": "child-scale unresolved question",
        "knowledge_boundary": "what Deniz does/does not know",
        "source_basis": ["supplied basis"]
      }
    ]
  },
  "saga": {
    "public_premise": "long-horizon but child-scale premise",
    "long_horizon_tensions": [
      {
        "tension": "open-ended long-horizon tension",
        "safe_for_first_story": true,
        "source_basis": ["supplied basis"]
      }
    ],
    "deep_truth_candidates": [],
    "character_known_truths": ["only things supported by input/origin candidate evidence"],
    "character_beliefs": ["bounded belief candidates"],
    "reveal_constraints": ["explicit reveal/knowledge rules"],
    "safe_breadcrumbs": [
      {
        "breadcrumb": "small safe reusable signal",
        "source_basis": ["supplied basis"],
        "reveal_safety": "why it does not leak hidden truth"
      }
    ],
    "open_threads": [
      {
        "thread": "open-ended question/tension, not an established fact",
        "source_basis": ["supplied basis"]
      }
    ],
    "continuity_rules": ["rules future stories must preserve"]
  },
  "downstream_seeds": {
    "inventory": [
      {
        "item_concept": "ordinary candidate item",
        "source_class": "EVERYDAY|PERSONAL|RELATIONSHIP|TRAVEL_OR_SURVIVAL|ROLE_OR_PROFESSION|LEGACY|MYSTERY",
        "ordinary": true,
        "provenance": "why this item is plausible from supplied basis",
        "canonical_status": "candidate_only"
      }
    ],
    "social_ecology": [
      {
        "role": "role-only candidate",
        "identity_status": "unbound_role_candidate",
        "relationship_direction": "bounded proposal",
        "reuse_preference": "reuse compatible existing NPC if one exists",
        "source_basis": ["supplied basis"],
        "canonical_status": "candidate_only"
      }
    ],
    "memories": [
      {
        "memory_summary": "bounded age-appropriate candidate memory",
        "visibility": "character_known",
        "source_basis": ["supplied basis"],
        "why_age_fit": "brief",
        "canonical_status": "candidate_only"
      }
    ],
    "origin_threads": [
      {
        "thread": "latent question/tension",
        "not_a_quest": true,
        "source_basis": ["supplied basis"],
        "canonical_status": "candidate_only"
      }
    ],
    "current_situation": {
      "summary": "what life looks like immediately before Story #1",
      "current_goals": ["small current goal"],
      "current_concerns": ["small current concern"],
      "recent_signals": ["source-grounded signal"],
      "rumors": ["only supplied rumor-safe material, or empty"],
      "source_basis": ["supplied basis"],
      "canonical_status": "candidate_only"
    },
    "initial_opportunities": [
      {
        "family": "exploration|social|personal|mystery|responsibility|world_event",
        "public_hook": "one spoiler-safe hook",
        "source_basis": ["specific proposed origin/saga/pre-story basis"],
        "why_character_specific": "why this belongs to Deniz",
        "reveal_safety": "why it respects knowledge boundaries",
        "canonical_status": "candidate_only"
      }
    ]
  },
  "intentional_sparse": [
    {
      "capability": "capability name",
      "reason": "only when sparse is genuinely justified"
    }
  ],
  "provider_notes": {
    "assumptions": ["explicit assumptions, no hidden claims"],
    "risks": ["candidate areas requiring application validation"]
  }
}

BOUNDED COUNTS:
- origin.life_facts: 3-6
- origin.formative_events: 1-3
- origin.prior_activities: 1-4
- origin.meaningful_people: 1-3
- origin.unresolved_questions: 1-3
- saga.long_horizon_tensions: 1-3
- saga.safe_breadcrumbs: 3-6
- saga.open_threads: 2-4
- saga.continuity_rules: 3-6
- downstream_seeds.inventory: 2-5
- downstream_seeds.social_ecology: 1-3
- downstream_seeds.memories: 2-4
- downstream_seeds.origin_threads: 1-3
- downstream_seeds.initial_opportunities: EXACTLY 3 and materially diverse

Do not inflate counts just to hit maxima.
""".strip()

VALIDATOR_SYSTEM = r"""
You are an independent LUMI Foundation Architect qualification validator.

The provider output is CANDIDATE EVIDENCE ONLY.
Judge whether it is safe and useful as upstream material for Rich Origin + reveal-safe Saga + later Pre-Story Life materialization.

Report ONLY serious/critical defects in these classes:
- age_lifecycle_mismatch
- unsupported_durable_canon
- world_or_physics_conflict
- epistemic_leak
- saga_reveal_leak
- social_identity_invention
- provenance_failure
- domain_authority_violation
- overgeneration
- downstream_unusable
- opportunity_generic_or_ungrounded
- internal_contradiction

Qualification-specific rules:
- exact age is 4; no adult work/professional/travel history.
- ordinary prior child experiences are allowed as candidates when explicitly marked candidate/proposed and plausibly derived from input.
- no deep Saga truth was supplied, so deep_truth_candidates must be empty.
- GARDEN_GATE remains RUMORED; no output may claim what lies beyond.
- caregiver may be a role-only candidate; no caregiver identity/name/family history may be invented.
- no other NPC identity may be invented.
- inventory must be candidate-only, mostly ordinary and age/world compatible.
- memories must be candidate-only, child-scale and must not smuggle hidden facts.
- Origin Threads are latent questions/tensions, not quests or established truths.
- Current Situation may summarize supplied/current candidate material but may not become a second World truth store.
- initial Opportunities are hooks only, must be grounded and materially diverse, and must not reveal forbidden knowledge.
- no provider-selected DB ids/fingerprints/commit claims.
- "rich" does not mean maximally detailed. Penalize excessive unsupported biography.
- do not fail harmless wording/style issues.

Return JSON only:
{
  "valid": true,
  "downstream_usable": true,
  "counts": {"critical":0,"serious":0},
  "defects": [
    {
      "severity":"critical|serious",
      "class":"age_lifecycle_mismatch|unsupported_durable_canon|world_or_physics_conflict|epistemic_leak|saga_reveal_leak|social_identity_invention|provenance_failure|domain_authority_violation|overgeneration|downstream_unusable|opportunity_generic_or_ungrounded|internal_contradiction",
      "path":"JSON path or section",
      "why":"brief evidence-based reason"
    }
  ],
  "strengths":[
    "up to 5 concrete useful properties"
  ],
  "summary":"brief"
}
""".strip()


def cost_usd(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    return float(((meta.get("cost") or {}).get("usd")) or 0.0)


def walk_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_l = key.casefold()
            if key_l == "id" or key_l.endswith("_id") or key_l == "uuid" or key_l.endswith("_uuid"):
                hits.append(f"{path}.{key}")
            hits.extend(walk_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            hits.extend(walk_keys(child, f"{path}[{i}]"))
    return hits


def require_list_range(errors: list[str], obj: dict[str, Any], key: str, lo: int, hi: int, path: str) -> None:
    value = obj.get(key)
    if not isinstance(value, list):
        errors.append(f"{path}.{key}:not_list")
        return
    if not lo <= len(value) <= hi:
        errors.append(f"{path}.{key}:count={len(value)} expected={lo}-{hi}")


def deterministic_check(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_top = {
        "character_echo",
        "origin",
        "saga",
        "downstream_seeds",
        "intentional_sparse",
        "provider_notes",
    }
    missing = sorted(expected_top - set(payload))
    if missing:
        errors.append(f"missing_top:{missing}")

    echo = payload.get("character_echo") or {}
    expected_echo = {
        "name":"Deniz",
        "exact_age":4,
        "lifecycle_stage":"childhood",
        "broad_kind":"human",
        "character_type":"explorer",
        "subtype":"curious-child",
    }
    for key, expected in expected_echo.items():
        if echo.get(key) != expected:
            errors.append(f"character_echo.{key}:{echo.get(key)!r}!={expected!r}")

    id_keys = walk_keys(payload)
    if id_keys:
        errors.append(f"provider_owned_id_keys:{id_keys}")

    origin = payload.get("origin") or {}
    if not isinstance(origin.get("public_summary"), str) or not origin["public_summary"].strip():
        errors.append("origin.public_summary:missing")
    require_list_range(errors, origin, "life_facts", 3, 6, "origin")
    require_list_range(errors, origin, "formative_events", 1, 3, "origin")
    require_list_range(errors, origin, "prior_activities", 1, 4, "origin")
    require_list_range(errors, origin, "meaningful_people", 1, 3, "origin")
    require_list_range(errors, origin, "unresolved_questions", 1, 3, "origin")

    for i, row in enumerate(origin.get("meaningful_people") or []):
        if row.get("identity_status") != "unbound_role_candidate":
            errors.append(f"origin.meaningful_people[{i}].identity_status")

    saga = payload.get("saga") or {}
    if not isinstance(saga.get("public_premise"), str) or not saga["public_premise"].strip():
        errors.append("saga.public_premise:missing")
    require_list_range(errors, saga, "long_horizon_tensions", 1, 3, "saga")
    require_list_range(errors, saga, "safe_breadcrumbs", 3, 6, "saga")
    require_list_range(errors, saga, "open_threads", 2, 4, "saga")
    require_list_range(errors, saga, "continuity_rules", 3, 6, "saga")
    deep = saga.get("deep_truth_candidates")
    if deep != []:
        errors.append(f"saga.deep_truth_candidates:must_be_empty got={deep!r}")

    ds = payload.get("downstream_seeds") or {}
    require_list_range(errors, ds, "inventory", 2, 5, "downstream_seeds")
    require_list_range(errors, ds, "social_ecology", 1, 3, "downstream_seeds")
    require_list_range(errors, ds, "memories", 2, 4, "downstream_seeds")
    require_list_range(errors, ds, "origin_threads", 1, 3, "downstream_seeds")
    require_list_range(errors, ds, "initial_opportunities", 3, 3, "downstream_seeds")

    for i, row in enumerate(ds.get("inventory") or []):
        if row.get("canonical_status") != "candidate_only":
            errors.append(f"downstream_seeds.inventory[{i}].canonical_status")
        if row.get("ordinary") is not True:
            errors.append(f"downstream_seeds.inventory[{i}].ordinary_not_true")

    for key in ("social_ecology","memories","origin_threads","initial_opportunities"):
        for i, row in enumerate(ds.get(key) or []):
            if row.get("canonical_status") != "candidate_only":
                errors.append(f"downstream_seeds.{key}[{i}].canonical_status")

    for i, row in enumerate(ds.get("social_ecology") or []):
        if row.get("identity_status") != "unbound_role_candidate":
            errors.append(f"downstream_seeds.social_ecology[{i}].identity_status")

    current = ds.get("current_situation")
    if not isinstance(current, dict):
        errors.append("downstream_seeds.current_situation:missing")
    else:
        if current.get("canonical_status") != "candidate_only":
            errors.append("downstream_seeds.current_situation.canonical_status")
        if not str(current.get("summary") or "").strip():
            errors.append("downstream_seeds.current_situation.summary:missing")

    opportunities = ds.get("initial_opportunities") or []
    families = {str(x.get("family") or "") for x in opportunities}
    if len(families) < 2:
        errors.append(f"initial_opportunities:not_diverse families={sorted(families)}")

    return errors


def validator_pass(result: dict[str, Any]) -> bool:
    counts = result.get("counts") or {}
    return (
        bool(result.get("valid"))
        and bool(result.get("downstream_usable"))
        and int(counts.get("critical", 0) or 0) == 0
        and int(counts.get("serious", 0) or 0) == 0
    )


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    started = time.perf_counter()

    foundation, architect_meta = structured_call(
        api_key=api_key,
        model=ARCHITECT_MODEL,
        system=ARCHITECT_SYSTEM,
        payload=fixture,
        seed=SEED,
        max_tokens=None,
        request_class="story_planning",
    )

    deterministic_errors = deterministic_check(foundation)

    validation_payload = {
        "qualification_fixture": fixture,
        "candidate_foundation": foundation,
        "deterministic_errors": deterministic_errors,
    }
    primary, primary_meta = structured_call(
        api_key=api_key,
        model=PRIMARY_VALIDATOR,
        system=VALIDATOR_SYSTEM,
        payload=validation_payload,
        seed=SEED + 1,
        max_tokens=3200,
        request_class="editorial_audit",
    )
    secondary, secondary_meta = structured_call(
        api_key=api_key,
        model=SECONDARY_VALIDATOR,
        system=VALIDATOR_SYSTEM,
        payload=validation_payload,
        seed=SEED + 2,
        max_tokens=3200,
        request_class="editorial_audit",
    )

    qualification_pass = (
        not deterministic_errors
        and validator_pass(primary)
        and validator_pass(secondary)
    )

    result = {
        "schema_version":"aion35-foundation-architect-qualification-result.v1",
        "qualification_id":fixture["qualification_id"],
        "models":{
            "architect":ARCHITECT_MODEL,
            "primary_validator":PRIMARY_VALIDATOR,
            "secondary_validator":SECONDARY_VALIDATOR,
        },
        "seed":SEED,
        "fixture":fixture,
        "candidate_foundation":foundation,
        "deterministic_errors":deterministic_errors,
        "primary_validation":primary,
        "secondary_validation":secondary,
        "qualification_pass":qualification_pass,
        "cost_usd":{
            "architect":cost_usd(architect_meta),
            "primary_validator":cost_usd(primary_meta),
            "secondary_validator":cost_usd(secondary_meta),
        },
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    result["cost_usd"]["total"] = sum(result["cost_usd"].values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"foundation.json").write_text(json.dumps(foundation,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    print(json.dumps({
        "qualification_pass":qualification_pass,
        "deterministic_errors":deterministic_errors,
        "primary_validation":primary,
        "secondary_validation":secondary,
        "cost_usd":result["cost_usd"],
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
