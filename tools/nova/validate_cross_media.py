#!/usr/bin/env python3
"""NOVA v0.2: fail-closed cross-media corpus validator; no model API calls."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/nova/v0.2"
DOCS = ROOT / "docs/research/nova-cross-media"
ORDER = ("01-hades", "02-outer-wilds", "03-the-witcher-3", "04-arrival", "05-12-angry-men")
EXPECTED_WORKS = ("HADES-2020", "OUTER-WILDS-2019", "WITCHER3-2015", "ARRIVAL-2016", "12-ANGRY-MEN-1957")
FILES = ("works", "story_beats", "mechanisms", "mechanic_evidence", "decisions", "sources")


def read_jsonl(name):
    value = []
    for number, line in enumerate((BASE / (name + ".jsonl")).read_text(encoding="utf8").splitlines(), start=1):
        if line.strip():
            try:
                value.append(json.loads(line))
            except Exception as exc:
                raise ValueError(f"{name}.jsonl:{number}: {exc}") from exc
    return value


def check():
    errors = []
    def assert_(condition, message):
        if not condition:
            errors.append(message)
    canonical = []
    for slug in ORDER:
        path = BASE / "source_records" / (slug + ".json")
        assert_(path.is_file(), "Missing work canonical record: " + slug)
        if path.is_file():
            canonical.append(json.loads(path.read_text(encoding="utf8")))
    assert_(len(canonical) == 5, "Exactly five sequenced source records required")
    expected = {
        "works": [dict(work_id=x["work_id"], title=x["title"]) for x in canonical],
        "story_beats": [dict(work_id=x["work_id"], **b) for x in canonical for b in x["beats"]],
        "mechanisms": [dict(work_id=x["work_id"], **a) for x in canonical for a in x["analysis"]],
        "mechanic_evidence": [],
        "decisions": [dict(work_id=x["work_id"], **d) for x in canonical for d in x["decisions"]],
        "sources": [dict(work_id=x["work_id"], **s) for x in canonical for s in x["sources"]],
    }
    by_work = {}
    for r in canonical:
        wid = r["work_id"]
        assert_(wid not in by_work, "Duplicate work ID: " + wid)
        by_work[wid] = r
        assert_(r.get("nonlinear") == (r.get("medium") == "interactive_video_game"),
                wid + ": incorrect medium/interactivity flag")
        assert_(len(r.get("scope", "")) >= 70, wid + ": insufficient scope")
        assert_(len(r.get("ending_scope", "")) >= 80, wid + ": ambiguous ending coverage")
        assert_(len(r.get("beats", [])) >= 8, wid + ": insufficient narrative event coverage")
        total_words = sum(len(b.get("description", "").split()) for b in r["beats"])
        assert_(600 <= total_words <= 2000, wid + ": insufficient full-story content: " + str(total_words))
        assert_(len(r.get("analysis", [])) >= 6, wid + ": not enough independent narrative mechanisms")
        assert_(len(r.get("decisions", [])) >= 4, wid + ": decision graph incomplete")
        assert_(len(r.get("sources", [])) >= 2, wid + ": weak source list")
        beat_ids = [b["beat_id"] for b in r["beats"]]
        source_ids = [s["source_id"] for s in r["sources"]]
        mech_ids = [m["mechanic_id"] for m in r["analysis"]]
        decision_ids = [d["decision_id"] for d in r["decisions"]]
        assert_(len(beat_ids) == len(set(beat_ids)), wid + ": duplicate beat")
        assert_(len(source_ids) == len(set(source_ids)), wid + ": duplicate source")
        assert_(len(mech_ids) == len(set(mech_ids)), wid + ": duplicate mechanic")
        assert_(len(decision_ids) == len(set(decision_ids)), wid + ": duplicate decision")
        for b in r["beats"]:
            assert_(len(b["description"].split()) >= 55, wid + ": skeletal narrative beat " + b["beat_id"])
            assert_(bool(b.get("source_ids")) and set(b["source_ids"]) <= set(source_ids),
                    wid + ": ungrounded beat " + b["beat_id"])
        for s in r["sources"]:
            assert_(s.get("url", "").startswith("https://"), wid + ": insecure/missing source URL")
            assert_(s.get("verification") in {"web_search_retrieved", "web_open_retrieved",
                    "cross_reference_url_not_live_verified"}, wid + ": unsupported verification claim")
            assert_(len(s.get("claim_scope", "")) > 20, wid + ": vague source scope")
        for a in r["analysis"]:
            assert_(len(a.get("abstraction", "")) >= 65 and len(a.get("observed", "")) >= 65,
                    wid + ": incomplete mechanism " + a["mechanic_id"])
            assert_(len(a.get("guardrail", "")) >= 50, wid + ": no real re-use guardrail " + a["mechanic_id"])
            assert_(bool(a["beat_ids"]) and set(a["beat_ids"]) <= set(beat_ids),
                    wid + ": mechanism without evidence beats " + a["mechanic_id"])
            assert_(bool(a["source_ids"]) and set(a["source_ids"]) <= set(source_ids),
                    wid + ": mechanic has missing provenance " + a["mechanic_id"])
            for bid in a["beat_ids"]:
                beat = next(b for b in r["beats"] if b["beat_id"] == bid)
                assert_(bool(set(beat["source_ids"]) & set(a["source_ids"])),
                        wid + ": evidence/source do not intersect for " + a["mechanic_id"] + "/" + bid)
                expected["mechanic_evidence"].append({
                    "evidence_id": wid + ":" + a["mechanic_id"] + ":" + bid,
                    "work_id": wid, "mechanic_id": a["mechanic_id"], "beat_id": bid,
                })
        for d in r["decisions"]:
            assert_(bool(d["source_ids"]) and set(d["source_ids"]) <= set(source_ids),
                    wid + ": decision missing provenance " + d["decision_id"])
            assert_(len(d.get("precondition", "")) >= 30 and len(d.get("effect", "")) >= 35,
                    wid + ": decision has no concrete prerequisite/effect " + d["decision_id"])
            if r["nonlinear"]:
                assert_(not d["decision_kind"].startswith("diegetic_"),
                        wid + ": game marked as only linear-film choice")
            else:
                assert_(d["decision_kind"].startswith("diegetic_"),
                        wid + ": movie incorrectly marked as interactive player choice")
        for name in ("STORY.md", "NARRATIVE_ANALYSIS.md", "DECISIONS.md", "SOURCES.md"):
            page = DOCS / r["slug"] / name
            assert_(page.is_file() and page.stat().st_size > 400, wid + ": generated document missing " + name)
        for bad in ("lumi_canon=true", "quality_effect=validated", "story_quality=PASS"):
            assert_(all(bad not in (DOCS / r["slug"] / name).read_text(encoding="utf8")
                  for name in ("STORY.md", "NARRATIVE_ANALYSIS.md")),
                    wid + ": invalid certification language " + bad)

    actual = {name: read_jsonl(name) for name in FILES}
    assert_(len(actual["works"]) == 5, "Wrong work count")
    assert_(tuple(x["work_id"] for x in actual["works"]) == EXPECTED_WORKS,
            "Work processing order changed")
    fields = {"works": ("work_id",), "story_beats": ("work_id", "beat_id"),
              "mechanisms": ("work_id", "mechanic_id"),
              "mechanic_evidence": ("evidence_id",), "decisions": ("work_id", "decision_id"),
              "sources": ("work_id", "source_id")}
    for name in FILES:
        keys = fields[name]
        ids = [tuple(x.get(k) for k in keys) for x in actual[name]]
        assert_(len(ids) == len(set(ids)), name + ": duplicate primary key")
        assert_(len(actual[name]) == len(expected[name]), name + ": count mismatch")
        for entry in actual[name]:
            assert_(entry.get("work_id") in by_work, name + ": unknown work reference")
        if name in {"story_beats", "decisions", "sources"}:
            assert_([tuple(x[k] for k in keys) for x in actual[name]] ==
                    [tuple(x[k] for k in keys) for x in expected[name]],
                    name + ": canonical materialization order drift")
    expected_links = {x["evidence_id"] for x in expected["mechanic_evidence"]}
    assert_(expected_links == {x["evidence_id"] for x in actual["mechanic_evidence"]},
            "Unlinked or extra narrative evidence")
    for m in actual["mechanisms"]:
        assert_(m.get("quality_effect") == "not_evaluated" and m.get("lumi_canon") is False,
                "Unsupported causal quality/canon claim: " + m.get("mechanic_id", "?"))
    for w in actual["works"]:
        assert_(w.get("lumi_canon") is False and w.get("status") == "first_pass_sourced",
                "Research evidence prematurely treated as production canon")
    for e in actual["mechanic_evidence"]:
        assert_(e.get("inference") is True and e.get("causal_quality_effect") == "not_evaluated",
                "Mechanic evidence falsely marked causal proof")
    links = read_jsonl("cross_media_links")
    available_mechanics = {x["mechanic_id"]: x["work_id"] for x in actual["mechanisms"]}
    assert_(len(links) == 7, "Seven explicit cross-media comparison links expected")
    assert_(len({x["link_id"] for x in links}) == len(links), "Duplicate comparison ID")
    for link in links:
        l, r = link["left"], link["right"]
        assert_(l in available_mechanics and r in available_mechanics, "Orphan cross-media mechanism link")
        if l in available_mechanics and r in available_mechanics:
            assert_(available_mechanics[l] != available_mechanics[r], "Cross-media link only within one work")
        assert_(link.get("quality_effect") == "not_evaluated", "Cross-media comparison overstated")
        assert_(bool(link.get("difference")) and bool(link.get("lumi_guardrail")),
                "Comparison lacks difference/guardrail")
    http = json.loads((BASE / "SOURCE_HTTP_CHECK.json").read_text(encoding="utf8"))
    http_rows = http.get("results", [])
    known_source_ids = {x["source_id"] for x in actual["sources"]}
    assert_(len(http_rows) == 25 and {x.get("source_id") for x in http_rows} == known_source_ids,
            "HTTP check manifest missing source IDs")
    code_counts = Counter(str(x.get("status")) for x in http_rows)
    assert_(code_counts == {"200": 16, "403": 8, "202": 1},
            "Unexpected current CI HTTP source observation distribution")

    manifest = json.loads((BASE / "manifest.json").read_text(encoding="utf8"))
    assert_(manifest.get("schema_version") == "0.2.0", "Schema drift")
    assert_(manifest.get("actual_story_trials") == 0 and
            manifest.get("quality_effect") == "not_evaluated", "Incorrect story trial count")
    assert_(manifest.get("lumi_production_modified") is False, "Unexpected LUMI mutation")
    assert_((DOCS / "README.md").is_file(), "Catalog missing")
    # Explicitly verify every claimed record is backed by one accessible local page.
    assert_(len(list(DOCS.glob("*/STORY.md"))) == 5, "Story page count mismatch")
    assert_(len(list(DOCS.glob("*/NARRATIVE_ANALYSIS.md"))) == 5, "Analysis page count mismatch")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "scope": "STRUCTURAL_SOURCE_LINKAGE_AND_RESEARCH_ONLY",
        "works": len(actual["works"]),
        "story_beats": len(actual["story_beats"]),
        "mechanics": len(actual["mechanisms"]),
        "mechanic_evidence": len(actual["mechanic_evidence"]),
        "decision_nodes": len(actual["decisions"]),
        "source_records": len(actual["sources"]),
        "cross_media_comparisons": len(links),
        "ci_source_http_results": dict(code_counts),
        "full_story_words": {r["work_id"]: sum(len(b["description"].split()) for b in r["beats"]) for r in canonical},
        "main_lumi_canon_changed": False,
        "independent_story_quality_trials": 0,
        "limitations": [
            "Source presence does not prove that each individual story claim was independently editorially audited.",
            "Model-like mechanism abstractions are interpretations, not observed effects on new stories.",
            "Game/player choice and film/diegetic choice are intentionally distinct.",
            "No production LUMI integration or paid story generation."
        ],
        "errors": errors,
    }
    return report


if __name__ == "__main__":
    try:
        result = check()
    except Exception as exc:
        result = {"status": "FAIL", "fatal": repr(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "PASS" else 1)
