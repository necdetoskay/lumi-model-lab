"""P4.22 offline real-source independent audit contract, no synthetic ACCEPT promotion."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from copy import deepcopy

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case,sha
from src.story_harness_p422_independent_audit import (
    audit_wire, verify_auditor_reply, audit_once, load_source, SCHEMA,
)
from src.story_harness_v1 import HarnessStop
from src.story_harness_p417_live_pilot import MODEL


def fake_source():
    pack=compile_case(load_plan(".")["cases"][0])
    scene=pack["canonical_state"]["locations"][0]
    beats=[]
    for i in range(4):
        beats.append({
            "id":f"BEAT_{i+1:02d}",
            "location":scene if i in (0,3) else pack["canonical_state"]["locations"][1],
            "goal":f"A story goal for Mira is explained at moment {i}.",
            "choice":f"Mira decides what to do at moment {i}.",
            "consequence":f"Something happens because of Mira's choice {i}.",
            "obligation_reference":pack["open_obligations"][0] if i==3 else None,
        })
    spine={"source_pack_sha256":pack["pack_sha256"],
           "spine_summary":"A warm and courageous story of a missing light.",
           "beats":beats}
    text="Mira chose to help the missing star. "+("She walked carefully through the meadow. "*55)
    return {
        "pack":pack,
        "spine":{"spine":spine,"spine_sha256":sha(spine),
                 "provider_generation_id":"gen-REAL123456789"},
        "story":{"story_text":text,"story_sha256":hashlib.sha256(text.encode()).hexdigest()},
    }


def fake_reply(source,*,verdict="ACCEPT",score=4,blockers=None,cost=0.009):
    blocks=[] if blockers is None else blockers
    return {"model":MODEL,"id":"gen-AUDIT123456789",
            "usage":{"prompt_tokens":2100,"completion_tokens":1200,"cost":cost},
            "choices":[{"finish_reason":"stop","message":{"content":json.dumps({
                "story_sha256":source["story"]["story_sha256"],
                "spine_sha256":source["spine"]["spine_sha256"],
                "verdict":verdict,"reader_score":score,
                "blocking_findings_json":json.dumps(blocks),
                "advisories_json":"[]",
                "rationale":"This is a complete independent critical review.",
            })}}]}


class P422Tests(unittest.TestCase):
    def setUp(self):
        self.source=fake_source()

    def test_full_source_and_spine_in_prompt_not_only_hash(self):
        body=audit_wire(self.source)
        p=json.loads(body["messages"][1]["content"])
        self.assertEqual(p["complete_story_text"],self.source["story"]["story_text"])
        self.assertEqual(p["approved_spine_beats"],self.source["spine"]["spine"]["beats"])
        self.assertEqual(p["story_sha256"],self.source["story"]["story_sha256"])
        self.assertEqual(p["reader_age"],4)
        self.assertEqual(body["max_tokens"],3200)
        self.assertEqual(body["provider"]["only"],["Anthropic"])
        self.assertFalse(body["provider"]["allow_fallbacks"])
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        schema=body["response_format"]["json_schema"]["schema"]
        self.assertNotIn("beats",schema["properties"])
        self.assertIn("blocking_findings_json",schema["properties"])

    def test_clean_fake_provider_only_proves_parser_not_real_quality(self):
        r=verify_auditor_reply(self.source,fake_reply(self.source))
        self.assertTrue(r["quality_initial_audit_accepted"])
        self.assertFalse(r["full_original_v21_final_audit_completed"])
        self.assertFalse(r["english_master_authorized"])
        self.assertFalse(r["q25_authorized"])
        self.assertFalse(r["state_write_authorized"])
        self.assertEqual(r["auditor_reported_cost_usd"],"0.009")

    def test_severe_spatial_issue_rejected_with_story_anchored_quote(self):
        issue={"family":"spatial","quote":"Mira chose to help",
               "reason":"Her position later conflicts with her previous location."}
        r=verify_auditor_reply(self.source,fake_reply(
            self.source,verdict="REJECT",score=3,blockers=[issue]))
        self.assertEqual(len(r["blocking_findings"]),1)
        self.assertFalse(r["quality_initial_audit_accepted"])

    def test_fake_accept_with_real_blocker_is_fail_closed(self):
        issue={"family":"canon","quote":"Mira chose to help",
               "reason":"Canon obligation not fulfilled and not marked open."}
        with self.assertRaises(HarnessStop):
            verify_auditor_reply(self.source,fake_reply(
                self.source,verdict="ACCEPT",score=5,blockers=[issue]))

    def test_hallucinated_quotes_and_unknown_families_not_admitted(self):
        for change in ({"family":"invented","quote":"Mira chose to help",
                        "reason":"Some problem with the story."},
                       {"family":"canon","quote":"EXCERPT NOT IN ORIGINAL",
                        "reason":"Some problem with the story."}):
            with self.subTest(change=change),self.assertRaises(HarnessStop):
                verify_auditor_reply(self.source,fake_reply(
                    self.source,verdict="REJECT",score=3,blockers=[change]))

    def test_story_spine_sha_swap_or_weak_score_rejected(self):
        for key in ("story_sha256","spine_sha256"):
            row=fake_reply(self.source)
            obj=json.loads(row["choices"][0]["message"]["content"])
            obj[key]="0"*64
            row["choices"][0]["message"]["content"]=json.dumps(obj)
            with self.assertRaises(HarnessStop):
                verify_auditor_reply(self.source,row)
        with self.assertRaises(HarnessStop):
            verify_auditor_reply(self.source,fake_reply(
                self.source,verdict="ACCEPT",score=2))

    def test_unknown_charge_wrong_model_or_output_truncation_denied(self):
        for case in ("missing_cost","high_cost","wrong_model","length"):
            row=fake_reply(self.source)
            if case=="missing_cost":
                del row["usage"]["cost"]
            elif case=="high_cost":
                row["usage"]["cost"]=0.041
            elif case=="wrong_model":
                row["model"]="wrong"
            else:
                row["choices"][0]["finish_reason"]="length"
            with self.subTest(case=case), self.assertRaises(HarnessStop):
                verify_auditor_reply(self.source,row)

    def test_audit_once_immutable_no_retry_even_on_unknown_cost(self):
        with TemporaryDirectory() as td:
            calls=[]
            def fake(body):
                calls.append(1)
                return fake_reply(self.source)
            r=audit_once(self.source,td,transport=fake)
            self.assertTrue(r["quality_initial_audit_accepted"])
            self.assertEqual(len(calls),1)
            with self.assertRaises(FileExistsError):
                audit_once(self.source,td,transport=fake)
            self.assertEqual(len(calls),1)
        with TemporaryDirectory() as td:
            with self.assertRaises(HarnessStop):
                audit_once(self.source,td,transport=lambda b:{"model":MODEL})
            p=list(Path(td).glob("*/01-audit-outcome.json"))[0]
            report=json.loads(p.read_text())
            self.assertEqual(report["quality_initial_verdict"],
                             "STOP_UNKNOWN_OR_INVALID")

    def test_real_source_requires_two_settled_provider_receipts(self):
        from src.story_harness_p410 import canonical_json
        with TemporaryDirectory() as td:
            parent=Path(td)
            pack=self.source["pack"]
            root=parent/("b01-"+pack["pack_sha256"][:16]+"-r06")
            root.mkdir()
            spine={
                "schema":"lumi.story-harness-p421-real-spine-artifact.v1",
                "source_pack_sha256":pack["pack_sha256"],
                "spine_sha256":self.source["spine"]["spine_sha256"],
                "spine":self.source["spine"]["spine"],
                "provider_generation_id":"gen-REAL123456789",
            }
            story={
                "schema":"lumi.story-harness-p417-real-provider-pilot.v1",
                "source_pack_sha256":pack["pack_sha256"],
                "spine_sha256":spine["spine_sha256"],
                "spine_artifact_path":"spine-plan.json",
                "story_text":self.source["story"]["story_text"],
                "story_sha256":self.source["story"]["story_sha256"],
                "word_count":len(self.source["story"]["story_text"].split()),
                "model_generated":True,
                "quality_accepted":False,"english_master_authorized":False,
                "q25_authorized":False,"story_state_write_authorized":False,
                "total_reported_usd":"0.018",
            }
            original={
                "stage":"SPINEFORGE","outcome":"SETTLED",
                "retry_authorized":False,
                "provider_usage":{"prompt_tokens":150,"completion_tokens":500},
                "provider_generation_id":"gen-REAL123456789",
                "provider_reported_cost_usd":"0.009"}
            writer=deepcopy(original)
            writer["stage"]="WRITER"
            writer["provider_generation_id"]="gen-WRITER123456789"
            for name,document in [
                ("spine-plan.json",spine),("story-draft.json",story),
                ("01-spineforge-receipt.json",original),
                ("02-writer-receipt.json",writer)]:
                (root/name).write_bytes(canonical_json(document))
            verified=load_source(".",parent)
            self.assertEqual(verified["generation_cost_usd"],"0.018")
            writer["outcome"]="STOP_UNKNOWN"
            (root/"02-writer-receipt.json").write_bytes(canonical_json(writer))
            with self.assertRaises(HarnessStop):
                load_source(".",parent)


if __name__=="__main__":
    unittest.main()
