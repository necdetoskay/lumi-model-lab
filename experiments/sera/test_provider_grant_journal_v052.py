"""No-network P0 tests: safety and idempotency, NOT Mara real-model proof."""
import tempfile
import unittest
from pathlib import Path

from experiments.sera.provider_grant_journal_v052 import ProviderJournal, JournalBlocked


class TestGrantJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "receipts.sqlite3"
        self.journal = ProviderJournal(self.db)
        self.binding = dict(source_sha256="a"*64, world_sha256="b"*64,
                            scene_key="mara-s1-28", policy_sha256="c"*64,
                            model="approved/test")
        self.payload = {"messages": [{"role":"user","content":"source-only"}]}
        self.calls = []

    def invoke(self, **changes):
        args = dict(grant_id="sera-specific-001",binding=self.binding,
                    request_id="req-1",model="approved/test",
                    payload=self.payload,transport=self.transport)
        args.update(changes)
        return self.journal.execute_once(**args)

    def transport(self, **kwargs):
        self.calls.append(kwargs)
        return {"id":"gen-1","choices":[{"message":{"content":"{}"}}],
                "usage":{"prompt_tokens":7,"completion_tokens":3}}

    def grant(self):
        self.journal.register_grant(grant_id="sera-specific-001",
                                    binding=self.binding,authorized=True)

    def test_authorization_required(self):
        with self.assertRaises(JournalBlocked):
            self.journal.register_grant(grant_id="sera-specific-001",
                                        binding=self.binding)
        with self.assertRaises(JournalBlocked):
            self.invoke()
        self.assertEqual(self.calls, [])

    def test_receipt_replay_never_posts_twice(self):
        self.grant()
        a = self.invoke()
        b = ProviderJournal(self.db).execute_once(
            grant_id="sera-specific-001",binding=self.binding,
            request_id="req-1",model="approved/test",
            payload=self.payload,transport=self.transport)
        self.assertEqual(a,b)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.journal.status("sera-specific-001"),"RECEIPTED")

    def test_unknown_post_does_not_rebill(self):
        self.grant()
        def broken(**kwargs):
            raise TimeoutError("ambiguous")
        with self.assertRaises(TimeoutError):
            self.invoke(transport=broken)
        self.assertEqual(self.journal.status("sera-specific-001"),"STARTED")
        with self.assertRaisesRegex(JournalBlocked,"UNKNOWN_INFLIGHT"):
            ProviderJournal(self.db).execute_once(
                grant_id="sera-specific-001",binding=self.binding,
                request_id="req-1",model="approved/test",
                payload=self.payload,transport=self.transport)
        self.assertEqual(self.calls,[])

    def test_policy_and_source_drift_blocks(self):
        self.grant()
        for key in ("source_sha256","world_sha256","policy_sha256","model"):
            changed=dict(self.binding)
            changed[key]="different"
            with self.assertRaises(JournalBlocked):
                self.invoke(binding=changed,model=changed["model"])
        self.assertEqual(self.calls,[])

    def test_no_output_token_ceiling(self):
        self.grant()
        with self.assertRaises(Exception):
            self.invoke(payload={"max_tokens":16,"messages":[]})
        self.assertEqual(self.journal.status("sera-specific-001"),"NOT_STARTED")

    def test_request_rebind_blocked(self):
        self.grant()
        self.invoke()
        with self.assertRaises(JournalBlocked):
            self.invoke(request_id="req-2")
        with self.assertRaises(JournalBlocked):
            self.invoke(payload={"messages":[]})
        self.assertEqual(len(self.calls),1)

    def test_authorized_grant_cannot_rebind(self):
        self.grant()
        changed=dict(self.binding,scene_key="different")
        with self.assertRaises(JournalBlocked):
            self.journal.register_grant(grant_id="sera-specific-001",
                                        binding=changed,authorized=True)

    def test_no_real_provider_call_on_setup(self):
        self.assertEqual(self.journal.status("missing"),"NOT_STARTED")
        self.assertFalse(self.db.with_suffix(".api_key").exists())


if __name__ == "__main__":
    unittest.main()
