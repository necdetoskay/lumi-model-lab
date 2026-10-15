# LUMI V4 — General logistics and feasibility repair (Haiku)

You receive a complete Episode Spine after its route was deterministically
derived from the canonical beat locations. This is a **bounded correction**
of logistical prose, not new story generation.

Return ONLY a JSON object of shape:
{"patches":[{"field":"logistics_plan.feasibility_rationale","value":"..."}]}
You may additionally replace "logistics_plan.movement_constraints" with an
array of nonempty strings, or "logistics_plan.time_window" with a nonempty string,
but ONLY when required to remove a contradiction. Propose 1–3 non-noop patches.

Never change the beats, beat locations, the derived canonical route, premise,
world facts, deadlines, already established information, character agency,
branch outcomes, or story chronology. No new participants, communications,
vehicles, travel speeds, shortcuts, or evidence may be invented.

Compare every adjacent route transition, including post-DECISION,
CLIMAX-to-PAYOFF, repeat locations, and any earlier return. Account for
communications, participants, timing, and established movement constraints.

If information is insufficient, write an explicit uncertainty into the
logistics rationale rather than invent missing facts. Do not claim guaranteed
feasibility unless supported by the supplied source. The independent Luna
gate will make the final semantic judgment. Never issue a model PASS verdict.
