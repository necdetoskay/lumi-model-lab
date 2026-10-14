#!/usr/bin/env python3
"""NOVA v0.1 offline source/evidence contract validator (Python stdlib only)."""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/nova/v0.1"
DOCS = ROOT / "docs/research/stargate-universe"


def read_jsonl(name):
    path = BASE / name
    entries = []
    for i, line in enumerate(path.read_text(encoding="utf8").splitlines(), 1):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{name}:{i}: {exc}") from exc
    return entries


def validate():
    errors = []
    works = read_jsonl("works.jsonl")
    episodes = read_jsonl("episodes.jsonl")
    analyses = read_jsonl("analyses.jsonl")
    sources = read_jsonl("source_manifest.jsonl")
    mechanics = read_jsonl("mechanics.jsonl")
    evidence = read_jsonl("mechanic_evidence.jsonl")
    usage_history = read_jsonl("usage_history.jsonl")
    evaluations = read_jsonl("evaluations.jsonl")

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(len(works) == 1 and works[0].get("work_id") == "stargate-universe", "Work record mismatch")
    check(len(episodes) == len(analyses) == len(sources) == 40, "40-episode coverage incomplete")
    check(len(mechanics) >= 10, "Mechanic inventory unexpectedly small")
    check(len(evidence) == 80, "Every episode must have two mechanic-evidence links")
    check(len(usage_history) == 0, "Usage history must not claim actual LUMI use")
    check(len(evaluations) == 0, "No story-quality experiment has been performed")
    expected = {f"SGU-S{s:02d}E{e:02d}" for s in (1, 2) for e in range(1, 21)}
    by_ep = {x.get("episode_id"): x for x in episodes}
    by_an = {x.get("episode_id"): x for x in analyses}
    by_source = {x.get("episode_id"): x for x in sources}
    by_mech = {x.get("mechanic_id"): x for x in mechanics}
    check(set(by_ep) == set(by_an) == set(by_source) == expected, "Episode/source/analysis IDs mismatch")
    check(all(len({row.get(key) for row in coll}) == len(coll) for key, coll in (
        ("episode_id", episodes), ("analysis_id", analyses), ("mechanic_id", mechanics),
        ("evidence_id", evidence), ("episode_id", sources))), "Duplicate entity IDs")
    check(all(x.get("schema_version") == "0.1.0" for x in analyses + mechanics + works + evidence),
          "Schema version drift")
    check(all(x.get("not_lumi_canon") is True for x in analyses), "LUMI canon firewall missing")
    check(all(x.get("lumi_canon") is False for x in works), "Work marked as LUMI canon")
    check(all(x.get("quality_effect") == "not_evaluated" for x in mechanics), "Unproven story quality claim")
    files = sorted(DOCS.glob("season-*/*.md"))
    check(len(files) == 40, f"Archive pages: {len(files)} (expected 40)")
    by_season = collections.Counter(x.get("season") for x in episodes)
    check(by_season == {1: 20, 2: 20}, "Season coverage mismatch")
    for episode_id in sorted(expected):
        ep = by_ep.get(episode_id, {})
        a = by_an.get(episode_id, {})
        s = by_source.get(episode_id, {})
        match = re.fullmatch(r"SGU-S(\d\d)E(\d\d)", episode_id)
        if not match:
            check(False, f"{episode_id}: malformed ID")
            continue
        season, number = int(match[1]), int(match[2])
        check((ep.get("season"), ep.get("episode")) == (season, number),
              f"{episode_id}: incorrect sequence")
        check(bool(ep.get("title_original")), f"{episode_id}: title absent")
        check(ep.get("source_status") == "primary_retrieved_http_200", f"{episode_id}: unchecked source")
        check(s.get("source_url", "").startswith("https://stargate-sg1-solutions.com/wiki/"),
              f"{episode_id}: source link absent")
        check(bool(re.fullmatch(r"[a-f0-9]{64}", s.get("sha256", ""))), f"{episode_id}: source hash invalid")
        check(a.get("source_url") == ep.get("archive_source") == s.get("source_url"),
              f"{episode_id}: source linkage mismatch")
        check(a.get("analysis_status") == "evidence_mapped_first_pass",
              f"{episode_id}: invalid review claim")
        required = ("observed_trigger", "observed_turn", "observed_decision",
                    "observed_cost", "observed_resolution")
        check(all(len(a.get(k, "").strip()) >= 35 for k in required),
              f"{episode_id}: incomplete scene observation")
        mids = a.get("mechanic_ids", [])
        check(len(mids) == 2 and len(set(mids)) == 2 and set(mids).issubset(by_mech),
              f"{episode_id}: mechanic references invalid")
        check(sum(x.get("episode_id") == episode_id for x in evidence) == 2,
              f"{episode_id}: missing evidence mapping")
        check(sum(x.name.startswith(f"S{season:02d}E{number:02d}-") for x in files) == 1,
              f"{episode_id}: wrong episode markdown page count")
        if (season, number) in {(1, 1), (1, 2)}:
            check(ep.get("summary_shared_across_parts") is True and ep.get("reference_scope") == "episode",
                  f"{episode_id}: shared first-two-part source limitations not documented")
    use_counts = collections.Counter(x.get("mechanic_id") for x in evidence)
    check(len({x.get("evidence_id") for x in evidence}) == len(evidence), "Duplicate evidence links")
    for row in evidence:
        episode_id, mid = row.get("episode_id"), row.get("mechanic_id")
        check(episode_id in expected and mid in by_mech, "Orphan evidence reference")
        check(row.get("analysis_id") == "NOVA-" + str(episode_id), "Evidence without analysis")
        if episode_id in by_ep:
            check(row.get("source_url") == by_ep[episode_id].get("archive_source"),
                  "Evidence source mismatch")
        check(row.get("classification_is_interpretive") is True, "Inference not flagged")
        check(len(row.get("observed_fact_paraphrase_tr", "")) > 30,
              "Missing sourced observation for mechanic")
    for mid, m in by_mech.items():
        check(m.get("evidence_count") == use_counts[mid], f"{mid}: evidence count drift")
        maturity = "corroborated_in_source_corpus" if use_counts[mid] >= 2 else "single_episode_candidate"
        check(m.get("maturity") == maturity, f"{mid}: invalid maturity")
        check(m.get("scope") == "narrative_pattern_not_world_canon", f"{mid}: canon scope leak")
        check(bool(m.get("application_guardrail_tr")), f"{mid}: no application guardrail")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "scope": "STRUCTURAL_AND_SOURCE_LINKAGE_ONLY",
        "episodes": len(episodes),
        "analyses": len(analyses),
        "seasons": dict(by_season),
        "source_manifests": len(sources),
        "mechanics": len(mechanics),
        "mechanics_with_multiple_episode_examples": sum(x.get("evidence_count", 0) >= 2 for x in mechanics),
        "evidence_links": len(evidence),
        "story_quality_evaluations": len(evaluations),
        "lumi_usage_records": len(usage_history),
        "notes": [
            "Source URLs were fetched HTTP 200 during the research pass; this script does not refetch live URLs.",
            "Evidence observations were manually paraphrased; individual scene claims have not had a second independent editorial audit.",
            "Evidence frequency is not causal proof that adding a mechanism improves generated stories.",
            "No OpenRouter calls, no LUMI Harness integration, no production change."
        ],
        "errors": errors,
    }
    return report


if __name__ == "__main__":
    try:
        report = validate()
    except Exception as exc:
        report = {"status": "FAIL", "fatal_error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["status"] == "PASS" else 1)
