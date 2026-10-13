"""P3.1 immutable historical quality-chain ledger. No model, no repair, no ACCEPT.

Only the P3.0 actual Spine/Writer deterministic gates are reexecuted.
P3.1 verifies archived audit/repair/reaudit byte integrity and typed lineage
against a fixed evidence cohort; historical model quality gates are NOT rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from src.story_harness_p30 import qualify as qualify_writer, STORY_SHA, EXPECTED_ARTIFACT_ID
from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA = "lumi.story-harness-p31-real-quality-lineage.v1"
MANIFEST = "configs/story_harness_p31_pinned_quality_cohort.json"
MANIFEST_SHA = "0942d631989f12018dfb50ae8e309e5d40f08b48039925150a1b98c3c8adadcb"
REPAIR_RUNS = {3:37112601598, 4:37114732160, 5:37118698592, 6:37120885185,
               7:37125599738, 8:37196489485, 9:37203303622, 10:37204419845}
REAUDIT_RUNS = {3:37113502767, 4:37118083538, 5:37119148378, 6:37124277479,
                7:37194766432, 8:37196986989, 9:37203770084}
FAILED_RUNS = {4:37117361651, 7:37126453862}
WRITER_ID = EXPECTED_ARTIFACT_ID
WRITER_SHA = STORY_SHA

def _must(condition, description):
    if not condition:
        raise HarnessStop(description)


def _verified_manifest(base: Path, manifest):
    raw = secure_artifact(base, MANIFEST)
    _must(digest(raw) == MANIFEST_SHA, "P3.1 frozen inventory manifest checksum changed")
    expected = load_json(raw)
    _must(expected == manifest, "P3.1 source inventory/case identity is not pinned")
    _must(expected["schema"] == "lumi.story-harness-p31-pinned-quality-cohort.v1"
          and expected["source_commit"] == PINNED_SOURCE_COMMIT,
          "P3.1 source manifest schema or Git commit changed")
    _must([a["run"] for a in expected["original_audits"]] ==
          [36969500342,36990160527], "Audit attempts are not pinned")
    _must([a["cycle"] for a in expected["cycles"]] == list(REPAIR_RUNS),
          "Repair cycle ordering changed")
    _must([(a["cycle"],a["run"]) for a in expected["failed_reaudit_attempts"]] ==
          list(FAILED_RUNS.items()), "Historical failed attempts mutated")
    for row in expected["cycles"]:
        c=row["cycle"]
        _must(row["repair_run"] == REPAIR_RUNS[c], "Repair run was substituted")
        _must(row.get("reaudit_run") == REAUDIT_RUNS.get(c),
              "Reaudit run was substituted, hidden, or invented")
        _must(set(row) ==
              ({"cycle","repair_run","repair_result","repair_product",
                "repair_story","repair_handoff"} |
               ({"reaudit_run","reaudit_result","reaudit_product","reaudit_handoff"} if c<10 else set())),
              "Incomplete or excess immutable cycle roles")
    _must(set(expected["anchors"]) ==
          {"stage6_repair_product","stage6_repaired_story",
           "stage7_reaudit_product","cycle2_repair_product",
           "cycle2_repaired_story","cycle2_reaudit_product"},
          "Missing cycle2 identity anchor")


def _source_file(root: Path, role, *, kind="json"):
    """Safe source path, fixed SHA, no symlink components/alternate revisions."""
    _must(isinstance(role,dict) and set(role)=={"path","sha256"},
          "Invalid pinned source role entry")
    rel=role["path"]
    _must(isinstance(rel,str) and rel.startswith("evidence/")
          and "\\" not in rel and ".." not in Path(rel).parts
          and not Path(rel).is_absolute()
          and Path(rel).suffix==("." + kind),
          "Unsafe or wrong source artifact path")
    target=root
    for part in Path(rel).parts:
        target=target/part
        _must(not target.is_symlink(), "Symlinked history is not acceptable")
    _must(target.is_file() and target.resolve().is_relative_to(root)
          and target.stat().st_size <= 200000,
          "Missing or oversized pinned quality evidence")
    raw=target.read_bytes()
    _must(digest(raw)==role["sha256"],"Pinned audit/repair/reaudit bytes mismatch")
    return raw if kind=="txt" else load_json(raw)


def _source_role(root, role, match_path=None, kind="json"):
    if match_path is not None:
        _must(role["path"] == match_path, "Pinned quality role path mismatch")
    return _source_file(root,role,kind=kind)


def _same_identity(data, ident):
    for k,v in ident.items():
        _must(data.get(k)==v, "Cross-stage Spine/Writer identity changed: "+k)


def _check_original_audits(source, payload, identity):
    records=[]
    for row,run,index,verdict,qual in zip(
        payload["original_audits"],[36969500342,36990160527],
        [1,8],["FAIL_KNOWN_DEFECT_MISSED","PASS"],[False,True]
    ):
        d=f"evidence/spineforge-v20-paid-story-audit/{run}"
        audit=_source_role(source,row["audit_result"],f"{d}/age12-island-v20-story-audit{index}-result.json")
        qualification=_source_role(source,row["qualification"],f"{d}/qualification-report.json")
        a=audit["audit_artifact"]
        for obj in (audit,a,qualification):
            _must(obj["source_story_sha256"]==WRITER_SHA and
                  obj["source_artifact_id"]==WRITER_ID,
                  "Audit did not consume the original same-story Writer artifact")
        _same_identity(a,{k:v for k,v in identity.items() if k != "approval_id"})
        _must(audit["status"]=="audit_completed" and
              a["decision"]=="LOCAL_REPAIR_REQUIRED" and
              a["next_stage"]=="STORY_LOCAL_REPAIR" and
              a["source_story_mutated"] is False and
              audit["state_commit_executed"] is False,
              "Original model audit decision/authority was promoted")
        _must(qualification["status"]==verdict and
              qualification["qualification_pass"] is qual and
              qualification["target_count"]==1 and
              qualification["matched_target_count"] == int(qual),
              "Audit qualification is not equivalent to story quality acceptance")
        records.append({"run":run,"qualification":verdict,
                        "qualification_pass":qual,
                        "story_audit_decision":a["decision"],
                        "story_audit_next_stage":a["next_stage"],
                        "source_story_sha256":WRITER_SHA,
                        "story_audit_artifact_id":a["artifact_id"],
                        "historical_report_only":True})
    return records


def _check_cycle2_anchor(source, payload, audit8_id):
    anchor=payload["anchors"]
    stage6=_source_file(source,anchor["stage6_repair_product"])
    stage6_story=_source_file(source,anchor["stage6_repaired_story"],kind="txt")
    stage7=_source_file(source,anchor["stage7_reaudit_product"])
    cycle2=_source_file(source,anchor["cycle2_repair_product"])
    cycle2_story=_source_file(source,anchor["cycle2_repaired_story"],kind="txt")
    reaudit2=_source_file(source,anchor["cycle2_reaudit_product"])
    _must(stage6["schema"]=="spineforge-v20-story-local-repair-artifact.v1"
          and stage6["status"]=="FROZEN" and stage6["immutable"] is True
          and stage6["source_writer_artifact_id"]==WRITER_ID
          and stage6["source_story_sha256"]==WRITER_SHA
          and stage6["source_audit_artifact_id"]==audit8_id
          and stage6["repaired_story_path"]==anchor["stage6_repaired_story"]["path"]
          and stage6["repaired_story_file_sha256"]==anchor["stage6_repaired_story"]["sha256"]
          and digest(stage6_story.rstrip(b"\n"))==stage6["repaired_story_text_sha256"],
          "Cannot prove Stage6 repair descended from Writer #3 and Audit8")
    _must(stage7["schema"]=="spineforge-v20-story-reaudit-product.v1"
          and stage7["stage"]==7 and stage7["status"]=="FROZEN"
          and stage7["immutable"] is True
          and stage7["source_stage6_artifact_id"]==stage6["artifact_id"]
          and stage7["source_stage6_artifact_path"]==anchor["stage6_repair_product"]["path"]
          and stage7["source_stage6_artifact_sha256"]==anchor["stage6_repair_product"]["sha256"]
          and stage7["source_repaired_story_text_sha256"]==stage6["repaired_story_text_sha256"]
          and stage7["decision"]=="LOCAL_REPAIR_REQUIRED"
          and stage7["next_stage"]=="STORY_LOCAL_REPAIR",
          "Stage7 re-audit is not bound to Stage6 repaired story")
    _must(cycle2["schema"]=="spineforge-v20-story-local-repair-cycle2-artifact.v1"
          and cycle2["status"]=="FROZEN" and cycle2["immutable"] is True
          and cycle2["source_stage7_product_artifact_id"]==stage7["artifact_id"]
          and cycle2["source_stage7_reaudit_artifact_id"]==stage7["embedded_reaudit_artifact_id"]
          and cycle2["source_stage6_artifact_id"]==stage6["artifact_id"]
          and cycle2["source_story_sha256"]==stage6["repaired_story_text_sha256"]
          and cycle2["repaired_story_path"]==anchor["cycle2_repaired_story"]["path"]
          and cycle2["repaired_story_file_sha256"]==anchor["cycle2_repaired_story"]["sha256"]
          and digest(cycle2_story.rstrip(b"\n"))==cycle2["repaired_story_text_sha256"],
          "Cannot prove historical Stage6 -> Stage7 -> Stage8 chain")
    _must(reaudit2["source_story_text_sha256"]==cycle2["repaired_story_text_sha256"]
          and reaudit2["source_story_artifact_id"]==cycle2["artifact_id"]
          and reaudit2["source_story_artifact_sha256"]==anchor["cycle2_repair_product"]["sha256"]
          and reaudit2["decision"]=="LOCAL_REPAIR_REQUIRED"
          and reaudit2["next_stage"]=="STORY_LOCAL_REPAIR"
          and reaudit2["status"]=="FROZEN" and reaudit2["immutable"] is True
          and reaudit2["cycle_index"]==2,
          "Cannot establish historical cycle2 -> cycle3 root")
    return {"story_id":cycle2["artifact_id"],"story_sha":cycle2["repaired_story_text_sha256"],
            "reaudit_id":reaudit2["artifact_id"],
            "reaudit_embedded":reaudit2["embedded_reaudit_artifact_id"]}


def _check_cycles(source,payload,previous,identity):
    events=[]
    for row in payload["cycles"]:
        c=row["cycle"]
        base=f"evidence/spineforge-v20-paid-writer/{REPAIR_RUNS[c]}/age12-island-v20-story-quality-repair-c{c}"
        r=_source_role(source,row["repair_result"],base+"-result.json")
        p=_source_role(source,row["repair_product"],base+"-product.json")
        h=_source_role(source,row["repair_handoff"],base+"-next-handoff.json")
        raw=_source_role(source,row["repair_story"],base+"-story.txt",kind="txt")
        _must(r["status"]=="repair_generated" and
              r["repair_cycle_index"]==c and p["repair_cycle_index"]==c and
              p["status"]=="FROZEN" and p["immutable"] is True and
              r["source_story_mutated"] is False and p["source_story_mutated"] is False,
              "Repaired story step is not a qualified immutable historical output")
        _must(r["source_story_artifact_id"]==previous["story_id"] and
              r["source_story_sha256"]==previous["story_sha"] and
              r["source_reaudit_product_artifact_id"]==previous["reaudit_id"] and
              r["source_reaudit_artifact_id"]==previous["reaudit_embedded"] and
              p["source_story_artifact_id"]==previous["story_id"] and
              p["source_reaudit_product_artifact_id"]==previous["reaudit_id"],
              "Previous-cycle Writer/Reaudit source lineage has a gap or substitute")
        _must(r["repaired_story_sha256"]==digest(r["repaired_story"].encode("utf8"))
              and r["repaired_story"]==raw.decode("utf8").rstrip("\n")
              and p["repaired_story_text_sha256"]==r["repaired_story_sha256"]
              and p["repaired_story_file_sha256"]==row["repair_story"]["sha256"],
              "Repaired story bytes/text were replaced")
        _must(p["result_path"]==row["repair_result"]["path"]
              and p["result_sha256"]==row["repair_result"]["sha256"]
              and h["source_story_artifact_id"]==p["artifact_id"]
              and h["source_story_artifact_sha256"]==row["repair_product"]["sha256"]
              and h["source_story_artifact_path"]==row["repair_product"]["path"]
              and h["repaired_story_text_sha256"]==r["repaired_story_sha256"]
              and h["repaired_story_file_sha256"]==row["repair_story"]["sha256"]
              and h["status"]=="READY_NOT_AUTHORIZED"
              and h["paid_execution_authorized"] is False,
              "Repair -> Reaudit handoff was promoted or renamed")
        _same_identity(h,identity)
        _must(r["next_stage"]=="STORY_REAUDIT"
              and r["reaudit_executed"] is False
              and r["state_commit_executed"] is False,
              "Historical repair cannot itself approve story quality")
        event={"cycle":c,"repair_run":row["repair_run"],
               "source_story_sha256":r["source_story_sha256"],
               "repaired_story_sha256":r["repaired_story_sha256"],
               "repaired_story_artifact_id":p["artifact_id"],
               "repair_status":r["status"],
               "reaudit_result_scope":"HISTORICAL_REPORT_ONLY"}
        if c in REAUDIT_RUNS:
            audit_base=f"evidence/spineforge-v20-paid-writer/{REAUDIT_RUNS[c]}/age12-island-v20-story-quality-reaudit-c{c}"
            rr=_source_role(source,row["reaudit_result"],audit_base+"-result.json")
            rp=_source_role(source,row["reaudit_product"],audit_base+"-product.json")
            rh=_source_role(source,row["reaudit_handoff"],audit_base+"-next-handoff.json")
            ra=rr["reaudit_artifact"]
            for obj in (rr,rp,ra):
                _must(obj["source_story_artifact_id"]==p["artifact_id"],
                      "Reaudit consumed a different repaired story")
            _same_identity(ra,identity)
            _must(rr["status"]=="reaudit_completed" and
                  rr["cycle_index"]==c and rp["cycle_index"]==c
                  and ra["cycle_index"]==c and
                  rr["source_repaired_story_sha256"]==r["repaired_story_sha256"] and
                  rp["source_story_text_sha256"]==r["repaired_story_sha256"] and
                  ra["source_repaired_story_sha256"]==r["repaired_story_sha256"] and
                  rp["source_story_artifact_sha256"]==row["repair_product"]["sha256"] and
                  rp["status"]=="FROZEN" and rp["immutable"] is True and
                  rp["result_sha256"]==row["reaudit_result"]["sha256"] and
                  rp["embedded_reaudit_artifact_id"]==ra["artifact_id"],
                  "Reaudit exact source/artifact hash mismatch")
            _must(ra["decision"]==rp["decision"]=="LOCAL_REPAIR_REQUIRED" and
                  ra["next_stage"]==rp["next_stage"]=="STORY_LOCAL_REPAIR" and
                  ra["full_story_reaudited"] is True and
                  rr["state_commit_executed"] is False and
                  rh["status"]=="READY_NOT_AUTHORIZED" and
                  rh["paid_execution_authorized"] is False and
                  rh["repair_cycle_index"]==c+1 and
                  rh["source_reaudit_product_artifact_id"]==rp["artifact_id"] and
                  rh["source_reaudit_product_sha256"]==row["reaudit_product"]["sha256"] and
                  rh["source_reaudit_artifact_id"]==ra["artifact_id"] and
                  rh["source_story_artifact_id"]==p["artifact_id"] and
                  rh["source_story_sha256"]==r["repaired_story_sha256"],
                  "Reaudit decision or next-cycle lineage forged")
            event.update({"reaudit_run":row["reaudit_run"],
                          "reaudit_artifact_id":rp["artifact_id"],
                          "story_audit_decision":ra["decision"],
                          "reaudit_next_stage":ra["next_stage"]})
            previous={"story_id":p["artifact_id"],"story_sha":r["repaired_story_sha256"],
                      "reaudit_id":rp["artifact_id"],"reaudit_embedded":ra["artifact_id"]}
        else:
            _must(c==10 and not any(k.startswith("reaudit_") for k in row),
                  "Terminal cycle10 re-audit was invented")
            event.update({"reaudit_run":None,
                          "story_audit_decision":"NOT_REAUDITED",
                          "reaudit_next_stage":"PENDING"})
        events.append(event)
    return events


def qualify(*, repo_root, pinned_source_root, python_executable=sys.executable, inventory=None):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    local_manifest=load_json(secure_artifact(base,MANIFEST)) if inventory is None else inventory
    _verified_manifest(base,local_manifest)
    parent=qualify_writer(
        manifest=load_json(secure_artifact(base,"configs/story_harness_p1_frozen_import.json")),
        repo_root=base,pinned_source_root=source,python_executable=python_executable)
    _must(parent["same_story_spine_to_writer_confirmed"] is True and
          parent["state"]=="STOPPED_MISSING_SAME_STORY_Q25" and
          parent["provider_calls"]==0,
          "P3.0 real Writer evidence prerequisite failed")
    original={key:parent["identity"][key] for key in
              ("approval_id","spine_hash","context_pack_id","context_fingerprint")}
    audits=_check_original_audits(source,local_manifest,original)
    root=_check_cycle2_anchor(source,local_manifest,audits[1]["story_audit_artifact_id"])
    events=_check_cycles(source,local_manifest,root,original)
    failures=[]
    for record in local_manifest["failed_reaudit_attempts"]:
        c=record["cycle"]
        rid=record["run"]
        path=f"evidence/spineforge-v20-paid-writer/{rid}/age12-island-v20-story-quality-reaudit-c{c}-result.json"
        failed=_source_role(source,record["result"],path)
        _must(failed["status"]=="unhandled_story_quality_loop_runtime_failure"
              and failed["cycle_index"]==c and
              failed["state_commit_executed"] is False,
              "A failed historical reaudit attempt was promoted to a quality result")
        failures.append({"cycle":c,"run":rid,"status":failed["status"],
                         "excluded_from_successful_lineage":True})
    _must(len(events)==8 and len([e for e in events if e["story_audit_decision"]==
           "LOCAL_REPAIR_REQUIRED"])==7 and
          events[-1]["story_audit_decision"]=="NOT_REAUDITED",
          "Story quality unexpectedly accepted or stage dropped")
    return {
      "schema":SCHEMA,"source_commit":PINNED_SOURCE_COMMIT,
      "p30_real_spine_writer_receipt_sha256":digest(canonical_bytes(parent)),
      "cohort_manifest_sha256":MANIFEST_SHA,
      "mode":"FROZEN_HISTORICAL_QUALITY_LINEAGE_ONLY",
      "original_audit_records":audits,"cycle2_root_record":root,
      "repair_reaudit_cycles":events,"failed_reaudit_attempts":failures,
      "original_deterministic_spine_writer_validators_reexecuted":True,
      "historical_paid_audit_or_repair_models_reexecuted":False,
      "historical_reaudit_quality_gate_reexecuted":False,
      "full_cycle3_to_cycle10_lineage_ids_and_hashes_verified":True,
      "qualification_pass_is_story_accept":False,
      "original_story_quality_accepted":False,
      "last_generated_repair_cycle":10,
      "last_completed_reaudit_cycle":9,
      "last_verified_story_audit_decision":"LOCAL_REPAIR_REQUIRED",
      "unreviewed_cycle10_story_pending_reaudit":True,
      "same_story_q25_evidence_present":False,
      "stop_reason":"STORY_QUALITY_NOT_ACCEPTED",
      "state":"STOPPED_UNACCEPTED_STORY",
      "story_writer_execution_authorized":False,
      "repair_execution_authorized":False,
      "q25_execution_authorized":False,
      "downstream_execution_authorized":False,
      "english_master_seal_authorized":False,
      "state_commit_authorized":False,
      "production_write_performed":False,
      "provider_calls":0,"provider_cost_usd":"0"
    }


def verify_report(report,*,repo_root,pinned_source_root,python_executable=sys.executable):
    recalculated=qualify(repo_root=repo_root,pinned_source_root=pinned_source_root,
                         python_executable=python_executable)
    _must(recalculated==report,"P3.1 historical quality receipt was altered")
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    a=p.parse_args()
    base=Path(a.repo_root).resolve(strict=True)
    r=qualify(repo_root=base,pinned_source_root=a.pinned_source_root)
    if a.verify_report:
        _must(load_json(secure_artifact(base,a.verify_report))==r,
              "Stored P3.1 historical quality receipt changed")
    print(json.dumps(r,indent=2,sort_keys=True,ensure_ascii=False))


if __name__=="__main__":
    main()

