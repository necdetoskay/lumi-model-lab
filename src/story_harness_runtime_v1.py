"""Mandatory Memory/Tools/Models/Prompts/State harness for B01..B10.

A prepared offline harness is NOT a paid grant. The controller refuses generic
model registry fallback and rejects stage, prompt, input and memory drift.
The same shared harness contract is required for every source and stage.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, sha as object_sha
from src.story_harness_p417_live_pilot import (
    MODEL, PROVIDER, OUTPUT_CAPS, STAGE_MAX_USD
)
from src.story_harness_p422_independent_audit import (
    OUTPUT_CAP as QUALITY_TOKENS, STAGE_COST_CAP
)
from src.story_harness_p424_q25_evidence import (
    OUTPUT_CAP as Q25_TOKENS, COST_CAP
)
from src.story_harness_frozen_cohort_v1 import CAP, TRIAL_CAP, IDS
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-complete-runtime-manifest.v1"
PATH = "configs/story_harness_runtime_v1.json"
ROLES = ("SPINEFORGE", "WRITER", "QUALITY", "Q25")
STAGES = {
    "SPINEFORGE": ("spineforge", OUTPUT_CAPS["SPINEFORGE"], STAGE_MAX_USD["SPINEFORGE"]),
    "WRITER": ("writer", OUTPUT_CAPS["WRITER"], STAGE_MAX_USD["WRITER"]),
    "QUALITY": ("independent_quality", QUALITY_TOKENS, STAGE_COST_CAP),
    "Q25": ("q25_extract", Q25_TOKENS, COST_CAP),
}
NAMES = {
    "compile_context", "spineforge", "writer", "independent_quality",
    "seal_master", "q25_extract", "final_state_read_only", "ledger", "evidence"
}
MODULES = {
    "compile_context": "src/story_harness_p416_input_bridge.py",
    "spineforge": "src/story_harness_p417_live_pilot.py",
    "writer": "src/story_harness_p417_live_pilot.py",
    "independent_quality": "src/story_harness_p422_independent_audit.py",
    "seal_master": "src/story_harness_cohort_stages_v1.py",
    "q25_extract": "src/story_harness_p424_q25_evidence.py",
    "final_state_read_only": "src/story_harness_cohort_stages_v1.py",
    "ledger": "src/story_harness_cohort_pipeline_v1.py",
    "evidence": "src/story_harness_cohort_pipeline_v1.py",
}

def require(ok, code):
    if not ok:
        raise HarnessStop("STORY_HARNESS_RUNTIME_STOP_" + code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def unique_dict(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, "DUPLICATE_JSON_KEY")
        out[k] = v
    return out

def load_manifest(root="."):
    path = Path(root) / PATH
    require(path.is_file() and not path.is_symlink() and
            0 < path.stat().st_size < 30000, "MANIFEST_MISSING")
    raw = path.read_bytes()
    data = json.loads(raw, object_pairs_hook=unique_dict)
    require(type(data) is dict and data.get("schema") == SCHEMA and
            data.get("status") == "PREPARED_NOT_FROZEN" and
            data.get("strict_harness_required") is True, "MANIFEST_SCHEMA")
    require(set(data) == {"schema","status","strict_harness_required",
                          "memory","tools","models","prompts","quality",
                          "state","finance","evidence","lifecycle"},
            "UNKNOWN_RUNTIME_SECTION")
    mem = data["memory"]
    require(mem.get("kind") == "READ_ONLY_CANONICAL_PER_CASE" and
            mem.get("source") == "configs/story_harness_p415_benchmark.json" and
            mem.get("input_compiler") == MODULES["compile_context"] and
            mem.get("working_memory") == "CASE_SCOPED_EVIDENCE_ONLY" and
            mem.get("end_state") == "READ_ONLY_PROPOSED_NOT_CANON" and
            set(mem.get("snapshot_fields",())) == {
                "canonical_state","topic","reader_age","word_targets",
                "open_obligations","unknown_facts","forbidden_state_invention"
            } and all(mem.get(k) is False for k in (
                "cross_story_retrieval", "dynamic_memory_injection",
                "allow_external_vector_db","allow_previous_case_manuscript",
                "persistent_memory_changes")), "UNSAFE_MEMORY")
    tools = data["tools"]
    require(tools.get("mode") == "ALLOWLIST_ONLY" and
            tools.get("filesystem_write") == "APPEND_ONLY_CLAIM_ROOT" and
            tools.get("provider_transport") ==
            "INJECTED_ONLY_NOT_AUTHORIZED" and
            tools.get("tool_result_schema") == "STRICT_SOURCE_BOUND" and
            all(tools.get(k) is False for k in (
                "dynamic_tool_invocation","external_browser","external_shell")),
            "UNSAFE_TOOLS")
    registry = tools.get("registry")
    require(type(registry) is list and len(registry) == len(NAMES) and
            all(type(e) is dict and set(e) == {"name","kind","module"}
                for e in registry) and
            {e["name"] for e in registry} == NAMES and
            all(e["module"] == MODULES[e["name"]] and
                e["kind"] == ("MODEL_STAGE" if e["name"] in
                {"spineforge","writer","independent_quality","q25_extract"}
                else "DETERMINISTIC")
                for e in registry), "UNTRUSTED_TOOL_MODULE")
    models = data["models"]
    require(models.get("provider") == "openrouter" and
            models.get("pinned_upstream") == PROVIDER and
            models.get("exact_model_id") == MODEL and
            models.get("profile_origin") ==
            "DEDICATED_EXACT_HARNESS_PROFILE_NOT_GENERIC_FALLBACK" and
            models.get("offline_behavior") == "SIMULATED_UNVERIFIED" and
            all(models.get(k) is False for k in (
                "dynamic_model_selection","allow_fallbacks",
                "allow_temperature_override")) and
            all(models.get(k) is True for k in (
                "strict_json_schema","require_usage","require_source_hashes")),
            "UNPINNED_MODEL")
    roles = models.get("stage_roles")
    require(type(roles) is list and tuple(x.get("stage") for x in roles) == ROLES
            and all(type(x) is dict and
                    set(x) == {"stage","tool","model","max_tokens",
                               "max_stage_usd"} and
                    x["tool"] == STAGES[x["stage"]][0] and
                    x["model"] == MODEL and
                    type(x["max_tokens"]) is int and
                    x["max_tokens"] == STAGES[x["stage"]][1] and
                    Decimal(x["max_stage_usd"]) ==
                    STAGES[x["stage"]][2] for x in roles),
            "UNTRUSTED_STAGE_MODEL")
    prompts = data["prompts"]
    require(prompts.get("mode") == "IMMUTABLE_VERSIONED_SOURCE" and
            prompts.get("generation_source") == MODULES["compile_context"] and
            prompts.get("audit_source") == MODULES["independent_quality"] and
            prompts.get("q25_source") == MODULES["q25_extract"] and
            all(prompts.get(k) is False for k in (
                "per_case_override","mid_cohort_hotfix","source_text_truncation")),
            "PROMPT_OVERRIDE")
    q = data["quality"]
    require(q.get("independent_call") is True and
            q.get("author_cannot_self_accept") is True and
            q.get("minimum_reader_score") == 4 and
            q.get("maximum_blockers") == 0 and
            q.get("scene_repair_count") == 0 and
            q.get("model_retry_count") == 0 and
            q.get("no_final_full_story_reaudit") is True and
            q.get("quality_denied_means_continue_next_case") is True and
            q.get("quality_success_needs_real_external_provenance") is True,
            "QUALITY_WEAKENED")
    st = data["state"]
    require(st.get("initial_canon_immutable") is True and
            st.get("no_live_canon_write") is True and
            st.get("final_state_mode") == "READ_ONLY" and
            st.get("provenance_required") is True and
            st.get("unknown_ownership_preserved") is True and
            st.get("unobserved_time_not_invented") is True and
            st.get("finalization_requires_master_and_q25") is True,
            "STATE_UNSAFE")
    fin = data["finance"]
    require(fin.get("aggregate_limit_usd") == "20.00" and
            fin.get("full_trial_reserve_usd") == "0.440" and
            Decimal(fin["aggregate_limit_usd"]) == CAP and
            Decimal(fin["full_trial_reserve_usd"]) == TRIAL_CAP and
            fin.get("max_provider_post_attempts_per_case") == 4 and
            fin.get("historical_ledger_reconciliation_required") is True and
            fin.get("unknown_charge_must_stop_global_batch") is True and
            fin.get("per_story_model_retry") is False and
            fin.get("payment_authorized") is False,
            "UNAUTHORIZED_PAYMENT")
    evid = data["evidence"]
    require(evid.get("hash_algo") == "sha256" and
            evid.get("durable_intent_before_post") is True and
            evid.get("exclusive_files") is True and
            evid.get("full_trace_per_story") is True and
            evid.get("source_lineage_strict") is True and
            evid.get("reported_accept_is_not_certified") is True and
            evid.get("no_secret_logging") is True and
            evid.get("posthoc_root_cause_only_after_all_ten") is True,
            "UNTRUSTED_EVIDENCE")
    lc = data["lifecycle"]
    require(lc.get("cases") == list(IDS) and
            lc.get("freeze_before_first") is True and
            lc.get("zero_change_during_round") is True and
            lc.get("changes_allowed_only_after_all_ten_attempts") is True and
            lc.get("shared_harness_for_all_cases") is True and
            lc.get("postcohort_same_inputs") is True and
            lc.get("holdout_independent") is True and
            lc.get("global_safety_stop_incomplete") is True and
            lc.get("real_batch_started") is False,
            "COHORT_ALREADY_STARTED_OR_CHANGED")
    return data, sha(raw)

class RuntimeHarness:
    """One case-scoped memory snapshot and exact fixed tool/model surface."""
    def __init__(self, root, case_id):
        self.root = Path(root)
        self.contract, self.manifest_sha256 = load_manifest(root)
        require(case_id in IDS, "UNKNOWN_CASE")
        plan = load_plan(root)
        case = next(c for c in plan["cases"] if c["id"] == case_id)
        self.pack = compile_case(case)
        self.case_id = case_id
        self.memory_snapshot_sha256 = self.pack["pack_sha256"]
        # Identify exact source bytes used by the Harness, not just display IDs.
        paths = set(MODULES.values()) | {PATH}
        self.pins = {}
        for relative in sorted(paths):
            p = self.root / relative
            require(p.is_file() and not p.is_symlink() and
                    0 < p.stat().st_size < 200000, "MISSING_TOOL_MODULE")
            self.pins[relative] = sha(p.read_bytes())
        self.story_sha256 = None
        self.spine_sha256 = None
        self.invoked = []
    def verify_immutable(self):
        data, digest = load_manifest(self.root)
        require(digest == self.manifest_sha256, "RUNTIME_CONFIG_CHANGED")
        for path, digest in self.pins.items():
            p = self.root / path
            require(p.is_file() and not p.is_symlink() and
                    sha(p.read_bytes()) == digest, "TOOL_OR_PROMPT_CHANGED")
        reloaded = next(c for c in load_plan(self.root)["cases"]
                        if c["id"] == self.case_id)
        require(compile_case(reloaded)["pack_sha256"] ==
                self.memory_snapshot_sha256, "CANON_MEMORY_DRIFT")
    def memory_view(self):
        self.verify_immutable()
        return deepcopy({field:self.pack[field] for field in
                         self.contract["memory"]["snapshot_fields"]})
    def bind_story(self, source):
        self.verify_immutable()
        require(source.get("case_id") == self.case_id and
                source["pack"]["pack_sha256"] == self.memory_snapshot_sha256 and
                type(source["story"]["story_sha256"]) is str and
                len(source["story"]["story_sha256"]) == 64 and
                source["story"].get("quality_accepted") is False,
                "CROSS_CASE_STORY_MEMORY")
        require(self.story_sha256 in (None, source["story"]["story_sha256"]),
                "STORY_MEMORY_CHANGED")
        self.story_sha256 = source["story"]["story_sha256"]
        self.spine_sha256 = source["spine"]["spine_sha256"]
    def authorize_stage(self, stage, body):
        self.verify_immutable()
        require(stage in ROLES and type(body) is dict and
                len(self.invoked) < 4 and
                stage == ROLES[len(self.invoked)], "INVALID_TOOL_STAGE_ORDER")
        require(body.get("model") == MODEL and
                body.get("provider") == {"only":[PROVIDER],
                   "allow_fallbacks":False,"require_parameters":True,
                   "max_price":{"prompt":2,"completion":10}} and
                body.get("stream") is False and
                body.get("usage") == {"include":True} and
                body.get("max_tokens") == STAGES[stage][1],
                "MODEL_ROUTING_CHANGED")
        fmt = body.get("response_format")
        require(type(fmt) is dict and fmt.get("type") == "json_schema" and
                type(fmt.get("json_schema")) is dict and
                fmt["json_schema"].get("strict") is True,
                "STRICT_SCHEMA_DISABLED")
        ident = fmt["json_schema"].get("name")
        require(ident == ({
            "SPINEFORGE":"lumi_p417_spineforge_flat_v2",
            "WRITER":"lumi_p417_writer_flat_v2",
            "QUALITY":"lumi_"+self.case_id.lower()+"_independent_initial_audit_v1",
            "Q25":"lumi_"+self.case_id.lower()+"_q25_evidence_proposal_v1",
        })[stage], "MODEL_STAGE_SCHEMA_CHANGED")
        messages = body.get("messages")
        require(type(messages) is list and len(messages) == 2 and
                messages[0].get("role") == "system" and
                messages[1].get("role") == "user", "MODEL_MESSAGES_CHANGED")
        try:
            payload = json.loads(messages[1]["content"])
        except Exception:
            raise HarnessStop("STORY_HARNESS_RUNTIME_STOP_INPUT_NOT_JSON") from None
        require(type(payload) is dict and
                payload.get("source_pack_sha256",
                     payload.get("pack_sha256")) ==
                self.memory_snapshot_sha256, "MEMORY_CROSS_STORY")
        if stage in ("SPINEFORGE","WRITER"):
            require(payload.get("canonical_state") ==
                    self.pack["canonical_state"] and
                    payload.get("reader_age") == self.pack["reader_age"] and
                    payload.get("unknown_facts") == self.pack["unknown_facts"],
                    "CANON_INPUT_NOT_EXACT")
        else:
            require(payload.get("case_id") == self.case_id and
                    self.story_sha256 is not None and
                    payload.get("story_sha256") == self.story_sha256,
                    "QUALITY_OR_Q25_MEMORY_NOT_BOUND")
        self.invoked.append(stage)
        return {
            "case_id":self.case_id, "stage":stage,
            "memory_snapshot_sha256":self.memory_snapshot_sha256,
            "harness_manifest_sha256":self.manifest_sha256,
            "approved_tool":STAGES[stage][0],
            "exact_model_id":MODEL,
        }
    def receipt(self):
        self.verify_immutable()
        return {
            "schema":SCHEMA,"case_id":self.case_id,
            "manifest_sha256":self.manifest_sha256,
            "input_memory_sha256":self.memory_snapshot_sha256,
            "model_profile":self.contract["models"]["profile_origin"],
            "model_id":MODEL,"tool_registry":sorted(NAMES),
            "pinned_module_sha256":dict(self.pins),
            "no_cross_case_memory":True,"paid_calls_authorized":0,
            "production_state_write_authorized":False,
        }

def create_harness(repo_root, case_id):
    return RuntimeHarness(repo_root, case_id)
