"""P4.16 dynamic state+topic → spine/writer request compiler, no model calls.

Use exact immutable synthetic inputs from P4.15; never reinterpret unknown
canonical facts as established. Compatible with a future trusted provider
callback seam, but currently only compiles state-bound prompts and strict
request contracts. Original frozen v21 validation not modified.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_p415_benchmark import case_fingerprint, load_plan
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p416-state-topic-generation-pack.v1"
SPINE_MODEL_REQUEST = "lumi.story-harness-p416-spine-request.v1"
WRITER_MODEL_REQUEST = "lumi.story-harness-p416-writer-request.v1"
AGE_WORD_TARGETS = {
    4: (300, 600),
    10: (800, 1400),
    12: (1600, 2500),
    25: (1800, 2800),
    40: (1800, 2800),
}
UNSAFE_MARKERS = re.compile(r"<\|im_(start|end)\|>|\[INST\]|</?system>", re.I)


def _must(test, why):
    if not test:
        raise HarnessStop(why)


def sha(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def compile_case(case):
    """Immutable by value; caller mutation cannot edit canonical source."""
    _must(type(case) is dict and "input" in case and "id" in case,
          "Missing benchmark input identity")
    payload = deepcopy(case["input"])
    _must(type(payload) is dict and
          set(payload) == {"topic", "reader_age", "canonical_state"},
          "Wrong source fields")
    source = payload["canonical_state"]
    character = source["protagonist"]
    _must(type(payload["topic"]) is str and
          not UNSAFE_MARKERS.search(payload["topic"]) and
          not payload["topic"].strip().startswith(("{", "[", "SYSTEM:")),
          "Injected topic instead of narrative topic")
    _must(type(source["locations"]) is list
          and character["location"] in source["locations"]
          and type(character["known_locations"]) is list
          and set(character["known_locations"]).issubset(set(source["locations"]))
          and type(source["open_obligations"]) is list
          and len(source["open_obligations"]) >= 2,
          "Inconsistent canonical character state")
    age = payload["reader_age"]
    _must(type(age) is int and age in AGE_WORD_TARGETS,
          "Unsupported target age")
    source_hash, topic_hash = sha(source), sha(payload["topic"])
    _must(case_fingerprint(case) == sha(payload), "Story input changed during compilation")
    core = {
        "source_case_id": case["id"],
        "case_input_sha256": case_fingerprint(case),
        "canonical_state_sha256": source_hash,
        "topic_sha256": topic_hash,
        "canonical_state": source,
        "topic": payload["topic"],
        "reader_age": age,
        "word_targets": {"min": AGE_WORD_TARGETS[age][0],
                         "max": AGE_WORD_TARGETS[age][1]},
        "forbidden_state_invention": case["forbidden_state_invention"],
        "open_obligations": list(source["open_obligations"]),
        "unknown_facts": list(source["unknown_facts"]),
        "no_manual_prose_edits": True,
    }
    return {**core, "schema": SCHEMA, "pack_sha256": sha(core)}


def verify_pack(pack):
    _must(type(pack) is dict and pack.get("schema") == SCHEMA
          and type(pack.get("pack_sha256")) is str,
          "Invalid Story input pack")
    p = {k: deepcopy(v) for k, v in pack.items()
         if k not in ("schema", "pack_sha256")}
    _must(sha(p) == pack["pack_sha256"], "Story input pack mutated")
    _must(sha(pack["canonical_state"]) == pack["canonical_state_sha256"],
          "Canon changed after freeze")
    _must(sha(pack["topic"]) == pack["topic_sha256"],
          "Topic changed after freeze")
    _must(pack["reader_age"] in AGE_WORD_TARGETS
          and (pack["word_targets"]["min"], pack["word_targets"]["max"]) ==
              AGE_WORD_TARGETS[pack["reader_age"]],
          "Age profile altered")
    return pack


def build_spine_request(pack):
    verify_pack(pack)
    system = (
        "You are SpineForge, a creative story architect. Plan a genuinely engaging "
        "character-driven story, not an engineering exercise. Ground EVERY scene "
        "in the supplied Canon and protagonist knowledge. Preserve physical, "
        "causal, temporal and ownership continuity. Unknown facts are not known. "
        "Scene actions and consequences must connect; protagonists make "
        "meaningful decisions. Every open obligation must be addressed or "
        "explicitly remain open. Return one valid JSON object matching schema."
    )
    data = {
        "pack_sha256": pack["pack_sha256"],
        "story_topic": pack["topic"],
        "reader_age": pack["reader_age"],
        "word_targets": pack["word_targets"],
        "canonical_state": pack["canonical_state"],
        "unknown_facts": pack["unknown_facts"],
        "open_obligations": pack["open_obligations"],
        "forbidden_state_invention": pack["forbidden_state_invention"],
        "scene_count": {"minimum": 4, "maximum": 8},
    }
    return {
        "schema": SPINE_MODEL_REQUEST,
        "stage": "SPINEFORGE",
        "source_pack_sha256": pack["pack_sha256"],
        "system_prompt": system,
        "user_prompt": canonical_json(data).decode("utf-8"),
        "strict_json": True,
        "provider_dispatch_allowed": False,
        "real_model_calls_performed": 0,
        "input_model_cost_usd": "0",
    }


def approve_spine_for_writer(pack, spine):
    verify_pack(pack)
    _must(type(spine) is dict and set(spine) ==
          {"source_pack_sha256", "beats", "spine_summary"},
          "Unexpected scene planner result")
    _must(spine["source_pack_sha256"] == pack["pack_sha256"],
          "Cross-state/other-topic Spine substitution")
    beats = spine["beats"]
    _must(type(beats) is list and 4 <= len(beats) <= 8,
          "Invalid number of story beats")
    valid_locations = set(pack["canonical_state"]["locations"])
    for i, beat in enumerate(beats, 1):
        _must(type(beat) is dict and set(beat) ==
              {"id", "location", "goal", "choice", "consequence",
               "obligation_reference"},
              "Unexpected spine beat shape")
        _must(beat["id"] == f"BEAT_{i:02d}"
              and beat["location"] in valid_locations
              and all(type(beat[x]) is str and
                      8 <= len(beat[x].strip()) <= 1200
                      for x in ("goal", "choice", "consequence"))
              and (beat["obligation_reference"] is None or
                   beat["obligation_reference"] in pack["open_obligations"]),
              "Incorrect scene identity, location or ungrounded obligation")
    _must(beats[0]["location"] == pack["canonical_state"]["protagonist"]["location"],
          "First beat teleports the protagonist")
    _must(type(spine["spine_summary"]) is str and
          len(spine["spine_summary"].strip()) >= 16,
          "Spine lacks dramatic throughline")
    _must(any(x["obligation_reference"] in pack["open_obligations"]
              for x in beats),
          "Spine ignores all open canonical obligations")
    return {"schema": "lumi.story-harness-p416-source-anchored-spine.v1",
            "source_pack_sha256": pack["pack_sha256"],
            "spine_sha256": sha(spine), "spine": deepcopy(spine),
            "original_model_provenance_authenticated": False,
            "independent_spine_validation_accepted": False}


def build_writer_request(pack, prepared_spine):
    verify_pack(pack)
    _must(type(prepared_spine) is dict and
          prepared_spine.get("source_pack_sha256") == pack["pack_sha256"]
          and prepared_spine.get("spine_sha256") ==
              sha(prepared_spine.get("spine"))
          and prepared_spine.get("original_model_provenance_authenticated") is False
          and prepared_spine.get("independent_spine_validation_accepted") is False,
          "Untrusted/mixed Spine-to-Writer lineage")
    system = (
        "You are the character-driven LUMI story Writer, not a technical "
        "summarizer. Write vivid English narrative prose with inner life, "
        "dramatic decisions, believable dialogue and curiosity. Turn each "
        "approved beat into immersive events rather than checklist narration. "
        "Keep one continuous time and physical world, obey canonical "
        "ownership/knowledge and never resolve an unknown fact without a "
        "shown cause. Match reader age and target word range. Maintain scene "
        "order, plausible travel and all obligations. Return the story body "
        "and corresponding beat references in a strict JSON object."
    )
    data = {
        "source_pack_sha256": pack["pack_sha256"],
        "approved_spine_sha256": prepared_spine["spine_sha256"],
        "approved_beats": prepared_spine["spine"]["beats"],
        "reader_age": pack["reader_age"],
        "topic": pack["topic"],
        "word_targets": pack["word_targets"],
        "canonical_state": pack["canonical_state"],
        "forbidden_state_invention": pack["forbidden_state_invention"],
        "unknown_facts": pack["unknown_facts"],
        "open_obligations": pack["open_obligations"],
    }
    return {
        "schema": WRITER_MODEL_REQUEST,
        "stage": "WRITER",
        "source_pack_sha256": pack["pack_sha256"],
        "spine_sha256": prepared_spine["spine_sha256"],
        "system_prompt": system,
        "user_prompt": canonical_json(data).decode("utf-8"),
        "strict_json": True,
        "provider_dispatch_allowed": False,
        "real_model_calls_performed": 0,
        "input_model_cost_usd": "0",
        "writer_text_sha256": None,
        "quality_accepted": False,
        "english_master_authorized": False,
        "q25_authorized": False,
        "state_write_authorized": False,
    }


def offline_status(repo_root="."):
    plan = load_plan(repo_root)
    items = []
    for case in plan["cases"]:
        pack = compile_case(case)
        spine = build_spine_request(pack)
        items.append({"id": case["id"], "age": pack["reader_age"],
                      "topic_sha256": pack["topic_sha256"],
                      "state_sha256": pack["canonical_state_sha256"],
                      "pack_sha256": pack["pack_sha256"],
                      "spine_request_source_sha256": spine["source_pack_sha256"]})
    return {
        "schema": "lumi.story-harness-p416-input-bridge-offline.v1",
        "distinct_state_topic_inputs": len(items),
        "inputs": items,
        "spine_writer_prompt_compilation_available": True,
        "live_spineforge_connected": False,
        "live_writer_connected": False,
        "independent_quality_accepted": False,
        "full_state_topic_pipeline_completed": False,
        "new_model_calls": 0, "new_model_cost_usd": "0",
        "budget_total_cap_usd": "10.00",
        "stop_reason": "P416_DYNAMIC_INPUT_COMPILED_MODEL_TRANSPORT_MISSING",
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    args = p.parse_args()
    print(json.dumps(offline_status(args.repo_root), sort_keys=True, indent=2))
