"""Independent paired experiment runner. Fixtures never establish story quality."""
from __future__ import annotations

import math
from pathlib import Path
import random
import statistics

from experiments.narrative_mechanics import core as nml
from . import vault
from .match import match

DIMENSIONS = ("interest", "causality", "decision_cost", "character", "closure", "originality")
GATES = ("age", "canon", "state", "originality")


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(nml.canonical(value) + b"\n")


def load_inputs():
    rows, upstream, release = vault.load()
    state = nml.read_json(vault.DATA / "state.v1.json")
    nml.validate(state, nml.read_json(vault.HERE / "schemas/state.schema.json"))
    if nml.sha(nml.safe_path(nml.ROOT, state["source_path"]).read_bytes()) != state["source_sha256"]:
        raise nml.Invalid("STATE_SOURCE_CHANGED")
    briefs = nml.read_json(vault.DATA / "briefs.v1.json")
    if len(briefs) != 16 or len({b["id"] for b in briefs}) != 16:
        raise nml.Invalid("BRIEF_COVERAGE")
    expected = {(a, t) for a in (4, 10, 25, 40) for t in ("exploration", "friendship", "mystery", "crisis")}
    if {(b["age"], b["theme"]) for b in briefs} != expected:
        raise nml.Invalid("BRIEF_BALANCE")
    for brief in briefs:
        match(brief, state, rows)
    return rows, state, briefs, release


def prepare(rows, state, briefs, seed, repeats=1):
    if type(seed) is not int or type(repeats) is not int or not 1 <= repeats <= 10:
        raise nml.Invalid("EXPERIMENT_PARAMETERS")
    rng = random.Random(seed)
    assignments, requests = [], []
    # Exactly balanced within each age stratum; randomized order, identical context.
    for age in (4, 10, 25, 40):
        stratum = [(b, rep) for b in briefs if b["age"] == age for rep in range(repeats)]
        orders = [True, False] * (len(stratum) // 2)
        rng.shuffle(orders)
        for (brief, rep), on_first in zip(stratum, orders):
            projection, audit = match(brief, state, rows)
            if projection["status"] != "PROPOSED":
                raise nml.Invalid("NO_FEASIBLE_PILOT_SELECTION")
            pair_id = f"{brief['id']}-R{rep + 1}"
            # The generator receives allowlisted LAB facts, not audit metadata,
            # forbidden franchise names, or fixture continuation examples.
            public_brief = {k: brief[k] for k in ("id", "age", "theme", "task", "max_words")}
            common = {"brief": public_brief, "state": {"facts": state["facts"]}, "temperature": 0,
                      "max_words": brief["max_words"], "generation_seed": 4000 + rep,
                      "instruction": "Write an original complete Turkish story. Respect the frozen LAB facts and age constraints. No new powers, named entities or world rules."}
            for slot, on in (("A", on_first), ("B", not on_first)):
                sample_id = pair_id + "-" + slot
                # Model sees only abstract advice, never the vault or source evidence.
                requests.append({"sample_id": sample_id, "common": common,
                                 "advice": projection["advice"] if on else []})
                assignments.append({"sample_id": sample_id, "pair_id": pair_id, "arm": "ON" if on else "OFF",
                                    "brief_id": brief["id"], "age": age, "replicate": rep,
                                    "theme": brief["theme"], "state_sha256": nml.fingerprint(state),
                                    "common_sha256": nml.fingerprint(common), "request_sha256": nml.fingerprint(requests[-1]),
                                    "selected_ids": audit["selected_ids"] if on else []})
    rng.shuffle(requests)
    return requests, assignments


def fixture_story(request):
    """Deliberately synthetic narrative renderer, never a model-quality experiment."""
    brief = next(b for b in nml.read_json(vault.DATA / "briefs.v1.json") if b["id"] == request["common"]["brief"]["id"])
    opening, obstacle, close = brief["fixture_beats"]
    # Uses selection as an input, demonstrating propagation without claiming benefit.
    if request["advice"]:
        middle = "Lina hemen karar vermedi. Bora ile Mira'nın görüşlerini dinledi. Birlikte küçük bir deneme yaptılar. İlk fikir uymayınca planı değiştirdiler. Bunun için biraz zaman ayırdılar."
    else:
        middle = "Lina ne yapabileceklerini düşündü. Bora ile Mira da yanındaydı. Birlikte bir plan yaptılar. Plan üzerinde çalıştılar. Bir süre sonra işlerini tamamladılar."
    return " ".join([opening, obstacle, middle, close])


def lexical_gates(text, state, archive_texts=()):
    words = vault.tokens(text)
    phrases = [vault.tokens(term) for term in state["forbidden_terms"]]
    reasons = ["FORBIDDEN_TERM"] if any(
        words[i:i+len(p)] == p for p in phrases for i in range(len(words)-len(p)+1)) else []
    grams = {tuple(words[i:i + 8]) for i in range(max(0, len(words) - 7))}
    for source in archive_texts:
        sw = vault.tokens(source)
        if grams & {tuple(sw[i:i + 8]) for i in range(max(0, len(sw) - 7))}:
            reasons.append("SOURCE_COPY")
            break
    return reasons


def blind_packet(stories, assignments):
    if {s["sample_id"] for s in stories} != {a["sample_id"] for a in assignments} or len(stories) != len(assignments):
        raise nml.Invalid("STORY_COVERAGE")
    packet = []
    for story in sorted(stories, key=lambda x: x["sample_id"]):
        if not story["text"].strip():
            raise nml.Invalid("EMPTY_STORY")
        packet.append({"sample_id": story["sample_id"], "text": story["text"],
                       "story_sha256": nml.sha(story["text"].encode("utf-8"))})
    return packet


def wilson(wins, n):
    if not n:
        return [0.0, 1.0]
    z = 1.959963984540054
    p = wins / n
    centre = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return [round(centre-half, 6), round(centre+half, 6)]


def score(packet, assignments, ballots, *, fixture):
    if type(fixture) is not bool:
        raise nml.Invalid("EXPERIMENT_MODE")
    by_sample = {s["sample_id"]: s for s in packet}
    if len(by_sample) != len(packet) or set(by_sample) != {a["sample_id"] for a in assignments}:
        raise nml.Invalid("PACKET_COVERAGE")
    if len(assignments) != len(packet) or any(nml.sha(s["text"].encode()) != s["story_sha256"] for s in packet):
        raise nml.Invalid("STORY_HASH_OR_ASSIGNMENT_DUPLICATE")
    expected_briefs = {b["id"]: b for b in nml.read_json(vault.DATA / "briefs.v1.json")}
    observed = set()
    for a in assignments:
        brief = expected_briefs.get(a["brief_id"])
        if not brief or a["age"] != brief["age"] or a["theme"] != brief["theme"] or a["state_sha256"] != brief["state_sha256"]:
            raise nml.Invalid("ASSIGNMENT_BRIEF_BINDING")
        identity = (a["brief_id"], a["replicate"], a["arm"])
        if identity in observed:
            raise nml.Invalid("DUPLICATE_TRIAL")
        observed.add(identity)
    replicates = {a["replicate"] for a in assignments}
    if observed != {(b, r, arm) for b in expected_briefs for r in replicates for arm in ("ON", "OFF")}:
        raise nml.Invalid("UNBALANCED_TRIAL_COVERAGE")
    scores, reviewers, identities = {}, set(), set()
    for ballot in ballots:
        nml.validate(ballot, nml.read_json(vault.HERE / "schemas/ballot.schema.json"))
        sid = ballot["sample_id"]
        if sid not in by_sample or ballot["story_sha256"] != by_sample[sid]["story_sha256"]:
            raise nml.Invalid("BALLOT_STORY_BINDING")
        identity = (sid, ballot["reviewer"])
        if identity in identities:
            raise nml.Invalid("DUPLICATE_BALLOT")
        identities.add(identity)
        if ballot["kind"] != ("SYNTHETIC" if fixture else "HUMAN") or not ballot["independent"]:
            raise nml.Invalid("INDEPENDENT_REVIEW_REQUIRED")
        if ballot["saw_allocation"] or ballot["is_story_author"]:
            raise nml.Invalid("BLINDING_OR_AUTHOR_CONFLICT")
        reviewers.add(ballot["reviewer"])
        scores.setdefault(sid, []).append(ballot)
    if len(reviewers) != 2 or any({b["reviewer"] for b in scores.get(sid, [])} != reviewers for sid in by_sample):
        raise nml.Invalid("TWO_COMPLETE_REVIEWERS_REQUIRED")
    pairs = {}
    for a in assignments:
        pair = pairs.setdefault(a["pair_id"], {})
        if a["arm"] in pair:
            raise nml.Invalid("DUPLICATE_ARM")
        pair[a["arm"]] = a
    deltas, failures, disagreement = [], [], []
    for sid, reviews in scores.items():
        for gate in GATES:
            if not all(r["gates"][gate] for r in reviews):
                failures.append({"sample_id": sid, "gate": gate})
        if any(abs(reviews[0]["scores"][d]-reviews[1]["scores"][d]) > 1 for d in DIMENSIONS):
            disagreement.append(sid)
    strata, clusters = {}, {}
    for pair in pairs.values():
        if set(pair) != {"ON", "OFF"} or pair["ON"]["common_sha256"] != pair["OFF"]["common_sha256"]:
            raise nml.Invalid("UNPAIRED_CONTEXT")
        avg = {arm: statistics.mean(v for r in scores[a["sample_id"]] for v in r["scores"].values())
               for arm, a in pair.items()}
        delta = avg["ON"] - avg["OFF"]
        deltas.append(delta)
        strata.setdefault(str(pair["ON"]["age"]), []).append(delta)
        clusters.setdefault(pair["ON"]["brief_id"], []).append(delta)
    wins, ties = sum(d > 0 for d in deltas), sum(d == 0 for d in deltas)
    interval = wilson(wins, len(deltas))  # Ties count against benefit; report explicitly.
    cluster_wins = sum(statistics.mean(v) > 0 for v in clusters.values())
    cluster_interval = wilson(cluster_wins, len(clusters))
    criterion = (len(deltas) >= 48 and set(strata) == {"4", "10", "25", "40"}
                 and all(len(v) >= 12 and statistics.mean(v) >= 0 for v in strata.values())
                 and cluster_interval[0] > 0.5 and statistics.mean(deltas) >= 0.3
                 and not failures and not disagreement)
    return {"schema": "nova.evaluation.v1", "mode": "FIXTURE" if fixture else "HUMAN_RATED",
            "pairs": len(deltas), "reviewers": len(reviewers), "wins": wins, "ties": ties,
            "losses": len(deltas)-wins-ties, "win_rate_ci95": interval,
            "brief_clusters": len(clusters), "winning_brief_clusters": cluster_wins,
            "brief_cluster_win_rate_ci95": cluster_interval,
            "mean_delta": round(statistics.mean(deltas), 6),
            "age_mean_deltas": {a: round(statistics.mean(v), 6) for a, v in strata.items()},
            "red_gate_failures": failures, "adjudication_required": disagreement,
            "quality_status": "NOT_ESTABLISHED_FIXTURE" if fixture else ("PILOT_THRESHOLD_MET" if criterion else "NOT_ESTABLISHED"),
            "integration_authorized": False, "state_commit_authorized": False}


def dry_run(directory):
    directory = Path(directory)
    if directory.exists():
        raise nml.Invalid("OUTPUT_EXISTS_USE_NEW_DIRECTORY")
    rows, state, briefs, release = load_inputs()
    requests, allocation = prepare(rows, state, briefs, seed=1701)
    stories = [{"sample_id": r["sample_id"], "text": fixture_story(r)} for r in requests]
    packet = blind_packet(stories, allocation)
    archive = [p.read_text(encoding="utf-8") for a in nml.ARCHIVES for p in (nml.ROOT / a).rglob("S*.md")]
    for sample in packet:
        if lexical_gates(sample["text"], state, archive):
            raise nml.Invalid("FIXTURE_LEXICAL_GATE")
    ballots = [{"schema": "nova.ballot.v1", "sample_id": s["sample_id"], "story_sha256": s["story_sha256"],
                "reviewer": reviewer, "kind": "SYNTHETIC", "independent": True,
                "saw_allocation": False, "is_story_author": False,
                "scores": {d: 3 for d in DIMENSIONS}, "gates": {g: True for g in GATES},
                "notes": "Fixture-only arithmetic and completeness test; no semantic judgment occurred."}
               for s in packet for reviewer in ("fixture-rater-1", "fixture-rater-2")]
    report = score(packet, allocation, ballots, fixture=True)
    report.update({"engineering_status": "PASS", "provider_calls": 0, "paid_usd": 0,
                   "source_episodes": 314, "pilot_mechanics": len(rows), "briefs": len(briefs),
                   "selection_success": 16, "selection_attempts": 16,
                   "release_sha256": nml.fingerprint(release), "state_sha256": nml.fingerprint(state),
                   "budget_authorized": False, "duplicate_report": vault.duplicate_report(rows)})
    directory.mkdir(parents=True)
    vault.build_index(directory / "vault.sqlite", rows, release)
    for name, value in (("requests.private.json", requests), ("allocation.private.json", allocation),
                        ("blind-packet.json", packet), ("ballots.fixture.json", ballots), ("report.json", report)):
        write_new(directory / name, value)
    hashes = {p.name: nml.sha(p.read_bytes()) for p in directory.glob("*.json")}
    write_new(directory / "artifact-hashes.json", hashes)
    return report
