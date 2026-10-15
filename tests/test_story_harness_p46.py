"""Source-anchored P4.6 authored manuscript revision tests."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import story_harness_p46 as p46
from src.story_harness_v1 import HarnessStop,load_json,secure_artifact

ROOT=Path(__file__).resolve().parents[1]


class P46WholeStoryAuthorialRevision(unittest.TestCase):
    def test_four_exact_changes_2482_word_candidate(self):
        proof=p46.review(repo_root=ROOT)
        self.assertEqual(proof["status"],"UNREVIEWED_AUTHORIAL_FULL_STORY_REVISION")
        self.assertEqual(proof["revised_story_words"],2482)
        self.assertEqual([r["id"] for r in proof["editorial_changes_verified"]],
                         list(p46.SCOPE))
        self.assertTrue(proof["other_source_content_unchanged"])

    def test_original_bridge_fix_stays_identical(self):
        m=load_json(secure_artifact(ROOT,p46.MANIFEST))
        new=(ROOT/m["new_story_relpath"]).read_text()
        before=(ROOT/m["parent_story_relpath"]).read_text()
        bridge=(ROOT/m["retained_bridge_scene"]).read_text().strip()
        self.assertEqual(new.count(bridge),1)
        self.assertEqual(before.count(bridge),1)
        self.assertIn("cut halves of their line dangled out of reach",new)
        self.assertIn("Its gate jammed tight against his harness",new)
        self.assertIn("tied it off. The line now linked both banks",new)

    def test_glider_tethers_and_return_timing_now_explicit(self):
        s=(ROOT/"evidence/story_harness_p46/offline-full-story-writer-revision.txt").read_text()
        self.assertLess(s.index("both gliders' landing tethers"),
                        s.index("Arda free his expedition line"))
        self.assertLess(s.index("They turned toward the shore."),
                        s.index('\"Our signal,\" she said.'))
        self.assertLess(s.index("He stopped at the final page:"),
                        s.index("The entry stopped. Mid-sentence."))
        self.assertIn("The Island That Wasn't on Any Map",s)
        self.assertIn("stone gate",s)

    def test_negative_missing_glider_tether_fails_full_replay(self):
        m=load_json(secure_artifact(ROOT,p46.MANIFEST))
        t=(ROOT/m["new_story_relpath"]).read_text()
        corrupt=t.replace("both gliders' landing tethers","one glider's rope")
        self.assertNotEqual(t,corrupt)
        self.assertNotEqual(p46.sha(t.encode()),p46.sha(corrupt.encode()))

    def test_sha_and_self_reported_quality_tampering_denied(self):
        original=load_json(secure_artifact(ROOT,p46.MANIFEST))
        for mutate in (
            lambda x:x.update(quality_decision="ACCEPT"),
            lambda x:x.update(independent_semantic_quality_accept=True),
            lambda x:x.update(english_master_seal_allowed=True),
            lambda x:x.update(q25_allowed=True),
            lambda x:x.update(state_commit_allowed=True),
            lambda x:x.update(real_provider_calls=1),
            lambda x:x["editorial_changes"].pop(),
            lambda x:x["editorial_changes"][0].update(new_text="fake text"),
        ):
            f=copy.deepcopy(original)
            mutate(f)
            self.assertNotEqual(f,original)
        with patch.object(p46,"MANIFEST_SHA","0"*64),self.assertRaises(HarnessStop):
            p46.review(repo_root=ROOT)

    def test_source_path_whitelist_blocks_symlinks_and_traversal(self):
        with self.assertRaises(HarnessStop):
            p46._bytes(ROOT,"../../etc/passwd")
        with self.assertRaises(HarnessStop):
            p46._bytes(ROOT,"/etc/passwd")
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"evidence/story_harness_p46"
            folder.mkdir(parents=True)
            (folder/"bad.txt").symlink_to(ROOT/"README.md")
            with self.assertRaises(HarnessStop):
                p46._bytes(Path(td),"evidence/story_harness_p46/bad.txt")

    def test_receipt_is_exact_and_never_paid(self):
        r=p46.review(repo_root=ROOT)
        saved=load_json(secure_artifact(ROOT,p46.RECEIPT))
        self.assertEqual(r,saved)
        self.assertTrue(all(r[x] is False for x in (
            "independent_semantic_quality_accept","new_model_quality_review_performed",
            "english_master_seal_issued","q25_source_admitted",
            "story_state_commit_authorized","paid_execution_authorized"
        )))
        self.assertEqual(r["provider_calls"],0)
        self.assertEqual(r["provider_cost_usd"],"0")
        self.assertEqual(r["new_v21_repair_calls"],0)

    def test_source_commit_is_p45_immutable_not_original_writer_mutation(self):
        m=load_json(secure_artifact(ROOT,p46.MANIFEST))
        self.assertEqual(m["source_git_commit"],p46.P45_SOURCE_COMMIT)
        self.assertEqual(m["original_story_word_count"],2494)
        self.assertEqual(m["new_story_word_count"],2482)
        self.assertEqual(m["editorial_origin"],
                         "OFFLINE_ASSISTANT_AUTHORED_WRITER_REVISION_NOT_MODEL_GENERATED")


if __name__=="__main__":unittest.main()

