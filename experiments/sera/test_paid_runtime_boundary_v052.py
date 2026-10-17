"""SERA v0.52 protected local paid runtime boundary: zero network tests."""
import json
import multiprocessing
import os
import shutil
import sqlite3
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from experiments.sera.paid_runtime_boundary_v052 import (
    SCHEMA,provision_local_journal,read_protected_runtime_config,
    verify_shared_local_journal,assert_paid_approval_active,
    open_bound_paid_journal,bind_revocation_checked_transport)
from experiments.sera.provider_grant_journal_v052 import JournalBlocked,ProviderJournal


def _concurrent_paid_worker(path, identity, ready, results):
    """Separate Linux process, shared pre-provisioned SQLite, fake one-POST."""
    try:
        journal=ProviderJournal(path,expected_file_identity=identity)
        binding=dict(source_sha256="a"*64,world_sha256="b"*64,
                     scene_key="mara-no-network",policy_sha256="c"*64,
                     model="test/isolated")
        journal.register_grant(
            grant_id="shared-grant-01",binding=binding,authorized=True)
        ready.wait(5)
        def fake_post(**kwargs):
            results.put("POST")
            return {"raw":{"id":"fake-receipt","usage":{"cost":0}},
                    "error":None}
        journal.execute_once(
            grant_id="shared-grant-01",binding=binding,
            request_id="shared-request-01",model="test/isolated",
            payload={"messages":[{"role":"user","content":"offline"}]},
            transport=fake_post)
        results.put("RECEIPT")
    except JournalBlocked:
        results.put("BLOCKED")
    except BaseException as exc:
        results.put("ERROR:"+type(exc).__name__)


class PaidRuntimeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.ledger=self.root/"one-authoritative-ledger.sqlite3"
        identity=provision_local_journal(path=self.ledger)
        self.config=self.root/"issuer-trust.json"
        self.value=dict(
            schema=SCHEMA,trusted_raw_key_sha256=sha256(b"fake issuer").hexdigest(),
            journal_path=identity["journal_path"],journal_id=identity["journal_id"],
            host_id_sha256=identity["host_id_sha256"],
            revoked_approval_ids=[])
        self.write_config()

    def write_config(self):
        self.config.write_text(json.dumps(self.value),encoding="utf-8")
        self.config.chmod(0o600)

    def checked(self):
        return verify_shared_local_journal(
            read_protected_runtime_config(self.config))

    def test_existing_single_local_journal_passes_no_post(self):
        self.assertEqual(self.checked(),str(self.ledger))
        with sqlite3.connect(self.ledger) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM calls").fetchone()[0],0)

    def test_new_empty_journal_cannot_bootstrap_silently(self):
        self.ledger.unlink()
        with self.assertRaisesRegex(JournalBlocked,"JOURNAL_MISSING"):
            self.checked()
        self.assertFalse(self.ledger.exists())

    def test_copy_in_same_path_is_detected_by_inode(self):
        duplicate=self.root/"duplicate.db"
        shutil.copy2(self.ledger,duplicate)
        self.ledger.unlink()
        os.replace(duplicate,self.ledger)
        with self.assertRaisesRegex(JournalBlocked,"IDENTITY_OR_COPY_DRIFT"):
            self.checked()

    def test_copy_in_alternate_path_rejected_even_with_modified_config(self):
        duplicate=self.root/"copy.db"
        shutil.copy2(self.ledger,duplicate)
        self.value["journal_path"]=str(duplicate)
        self.write_config()
        with self.assertRaisesRegex(JournalBlocked,"IDENTITY_OR_COPY_DRIFT"):
            self.checked()

    def test_forged_other_machine_identity_refused(self):
        self.value["host_id_sha256"]="0"*64
        self.write_config()
        with self.assertRaisesRegex(JournalBlocked,"HOST_MISMATCH"):
            self.checked()

    def test_group_writable_config_denied(self):
        self.config.chmod(0o660)
        with self.assertRaisesRegex(JournalBlocked,"TRUST_FILE_INSECURE"):
            self.checked()

    def test_group_writable_config_directory_denied(self):
        self.root.chmod(0o770)
        with self.assertRaisesRegex(JournalBlocked,"TRUST_PARENT_INSECURE"):
            self.checked()

    def test_symlinked_config_denied(self):
        link=self.root/"link.json"
        link.symlink_to(self.config)
        with self.assertRaises(JournalBlocked):
            read_protected_runtime_config(link)

    def test_symlinked_journal_denied(self):
        alternate=self.root/"alias.db"
        alternate.symlink_to(self.ledger)
        altered=dict(self.value,journal_path=str(alternate))
        with self.assertRaisesRegex(JournalBlocked,"SYMLINKED_PATH"):
            verify_shared_local_journal(altered)

    def test_unmarked_sqlite_database_denied(self):
        blank=self.root/"blank.sqlite3"
        with sqlite3.connect(blank) as db:
            db.execute("CREATE TABLE ordinary (n INTEGER)")
        self.value["journal_path"]=str(blank)
        self.write_config()
        with self.assertRaisesRegex(JournalBlocked,"NOT_PROVISIONED"):
            self.checked()

    def test_live_revocation_update_stops_next_request(self):
        original=read_protected_runtime_config(self.config)
        self.assertTrue(assert_paid_approval_active(
            config_path=self.config,original_config=original,approval_id="alpha"))
        self.value["revoked_approval_ids"]=["alpha"]
        self.write_config()
        with self.assertRaisesRegex(JournalBlocked,"APPROVAL_REVOKED"):
            assert_paid_approval_active(
                config_path=self.config,original_config=original,approval_id="alpha")

    def test_live_trust_change_blocks_existing_run(self):
        original=read_protected_runtime_config(self.config)
        self.value["trusted_raw_key_sha256"]="f"*64
        self.write_config()
        with self.assertRaisesRegex(JournalBlocked,"RUNTIME_TRUST_CHANGED"):
            assert_paid_approval_active(
                config_path=self.config,original_config=original,approval_id="alpha")

    def test_journal_replacement_after_open_stops_all_new_connections(self):
        bound=open_bound_paid_journal(self.value)
        with bound._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM calls").fetchone()[0],0)
        replacement=self.root/"replacement.db"
        shutil.copy2(self.ledger,replacement)
        os.replace(replacement,self.ledger)
        with self.assertRaisesRegex(JournalBlocked,"FILE_IDENTITY_CHANGED"):
            bound._connect()

    def test_pinned_journal_missing_billing_schema_fails_closed(self):
        with sqlite3.connect(self.ledger) as db:
            db.execute("DROP TABLE calls")
        with self.assertRaisesRegex(JournalBlocked,"SCHEMA_OR_HISTORY_MISSING"):
            open_bound_paid_journal(self.value)

    def test_transport_rechecks_revocation_after_stage_admission(self):
        posted=[]
        original=read_protected_runtime_config(self.config)
        send=bind_revocation_checked_transport(
            transport=lambda **kwargs:posted.append(kwargs) or {"raw":{}},
            config_path=self.config,original_config=original,
            approval_id="mara-approval-offline")
        self.value["revoked_approval_ids"]=["mara-approval-offline"]
        self.write_config()
        with self.assertRaisesRegex(JournalBlocked,"APPROVAL_REVOKED"):
            send(model="test/model",payload={"messages":[]},request_id="first")
        self.assertEqual(posted,[])

    def test_transport_detects_journal_replacement_before_http(self):
        posted=[]
        original=read_protected_runtime_config(self.config)
        send=bind_revocation_checked_transport(
            transport=lambda **kwargs:posted.append(kwargs) or {"raw":{}},
            config_path=self.config,original_config=original,
            approval_id="mara-approval-offline")
        replacement=self.root/"replacement.db"
        shutil.copy2(self.ledger,replacement)
        os.replace(replacement,self.ledger)
        with self.assertRaisesRegex(JournalBlocked,"IDENTITY_OR_COPY_DRIFT"):
            send(model="test/model",payload={"messages":[]},request_id="first")
        self.assertEqual(posted,[])

    def test_transport_allowed_when_still_authorized(self):
        posted=[]
        original=read_protected_runtime_config(self.config)
        send=bind_revocation_checked_transport(
            transport=lambda **kwargs:posted.append(kwargs) or {"raw":{}},
            config_path=self.config,original_config=original,
            approval_id="mara-approval-offline")
        self.assertEqual(send(model="test/model",payload={"messages":[]},
                              request_id="first"),{"raw":{}})
        self.assertEqual(len(posted),1)

    def test_real_separate_workers_share_one_post_journal(self):
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("requires Linux fork worker isolation")
        info=os.stat(self.ledger)
        identity=(info.st_dev,info.st_ino)
        context=multiprocessing.get_context("fork")
        start=context.Event()
        results=context.Queue()
        workers=[context.Process(
            target=_concurrent_paid_worker,
            args=(str(self.ledger),identity,start,results))
            for _ in range(4)]
        for w in workers:
            w.start()
        start.set()
        for w in workers:
            w.join(7)
            if w.is_alive():
                w.terminate()
                w.join(2)
                self.fail("isolated worker stalled")
            self.assertEqual(w.exitcode,0)
        from queue import Empty
        received=[]
        while True:
            try:
                received.append(results.get(timeout=0.25))
            except Empty:
                break
        self.assertEqual(received.count("POST"),1,received)
        self.assertEqual(received.count("RECEIPT")+
                         received.count("BLOCKED"),4,received)
        self.assertFalse(any(x.startswith("ERROR:") for x in received),received)
        journal=open_bound_paid_journal(self.value)
        self.assertEqual(journal.status("shared-grant-01"),"RECEIPTED")

    def test_bootstrap_cannot_replace_existing_ledger(self):
        with self.assertRaisesRegex(JournalBlocked,"REQUIRES_NEW_ABSOLUTE_PATH"):
            provision_local_journal(path=self.ledger)
        self.assertEqual(self.checked(),str(self.ledger))


if __name__ == "__main__":
    unittest.main()
