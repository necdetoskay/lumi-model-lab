"""Selection against frozen LAB state; outputs contain only abstract advice."""
from __future__ import annotations

import itertools

from experiments.narrative_mechanics import core as nml
from . import vault


def match(brief, state, rows, history=()):
    nml.validate(state, nml.read_json(vault.HERE / "schemas/state.schema.json"))
    nml.validate(brief, nml.read_json(vault.HERE / "schemas/brief.schema.json"))
    if brief["state_sha256"] != nml.fingerprint(state):
        raise nml.Invalid("FROZEN_STATE_MISMATCH")
    known = {r["id"] for r in rows}
    for event in history:
        nml.validate(event, nml.read_json(vault.HERE / "schemas/usage.schema.json"))
        if event["id"] not in known:
            raise nml.Invalid("UNKNOWN_USAGE")
        if event["ordinal"] > brief["ordinal"]:
            raise nml.Invalid("FUTURE_USAGE")
    recent = {e["id"] for e in history if brief["ordinal"] - e["ordinal"] <= 3}
    recent_families = {r["family"] for r in rows if r["id"] in recent}
    eligible, exclusions = [], {}
    for row in rows:
        reasons = []
        if row["status"] != "PROPOSED_LAB":
            reasons.append("WITHHELD")
        profiles = [p for p in row["profiles"] if p["age_min"] <= brief["age"] <= p["age_max"]]
        if len(profiles) != 1:
            reasons.append("AGE")
        if brief["theme"] not in row["themes"]:
            reasons.append("THEME")
        if not set(row["requires"]) <= set(state["authorized_features"]):
            reasons.append("CANON")
        if not set(row["effects"]) <= set(state["allowed_effects"]):
            reasons.append("STATE")
        if row["reveal_level"] > state["reveal_ceiling"]:
            reasons.append("REVEAL")
        if row["id"] in recent:
            reasons.append("RECENT_ID")
        if brief["strict_novelty"] and row["family"] in recent_families:
            reasons.append("RECENT_FAMILY")
        if profiles:
            profile = profiles[0]
            if set(profile["risks"]) & set(brief["forbidden_risks"]):
                reasons.append("RISK")
            if brief["age"] < 7 and (profile["risks"] or profile["profile"] != "GENTLE_LAB"):
                reasons.append("PRESCHOOL_FLOOR")
        if reasons:
            exclusions[row["id"]] = reasons
        else:
            eligible.append((row, profiles[0]))
    combos = []
    for combo in itertools.combinations(sorted(eligible, key=lambda p: p[0]["id"]), 2):
        families = {r["family"] for r, _ in combo}
        groups = {r["source_group"] for r, _ in combo}
        if len(families) < 2 or len(groups) < 2:
            continue
        ids = [r["id"] for r, _ in combo]
        rank = nml.fingerprint({"brief": brief["id"], "ids": ids, "seed": brief["seed"]})
        combos.append((rank, combo))
    chosen = min(combos, key=lambda x: x[0])[1] if combos else ()
    projection = {"schema": "nova.advice.v1", "scope": "LAB_ONLY",
                  "state_commit_authorized": False, "status": "PROPOSED" if chosen else "ABSTAIN",
                  "advice": [p["advice"] for _, p in chosen]}
    audit = {"brief_sha256": nml.fingerprint(brief), "state_sha256": nml.fingerprint(state),
             "selected_ids": [r["id"] for r, _ in chosen], "exclusions": exclusions,
             "source_groups": sorted({r["source_group"] for r, _ in chosen}),
             "projection_sha256": nml.fingerprint(projection)}
    return projection, audit
