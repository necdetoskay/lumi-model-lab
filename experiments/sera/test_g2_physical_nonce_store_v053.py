"""SERA v0.53 local durable physical nonce claims: all OFFLINE."""
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.g2_physical_nonce_store_v053 import (
    LocalPhysicalNonceStore,provision_nonce_store,
)

NONCE="unique-g2-physical-nonce-0000000000001"


def claim_in_process(path,ready,results):
    try:
        ledger=LocalPhysicalNonceStore(path)
        ready.wait(5)
        results.put(bool(ledger.consume(NONCE)))
    except BaseException as exc:
        results.put(type(exc).__name__+":"+str(exc))


class PhysicalNonceStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"physical-challenges.db"
        provision_nonce_store(self.path)

    def test_durable_replay_is_blocked_after_worker_restart(self):
        first=LocalPhysicalNonceStore(self.path)
        self.assertTrue(first.consume(NONCE))
        second=LocalPhysicalNonceStore(self.path)
        self.assertFalse(second.consume(NONCE))
        self.assertTrue(second.consume("new-physical-nonce-00000000000000002"))
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM physical_nonce_claim").fetchone()[0],2)

    def test_missing_or_replaced_database_fails_not_recreated(self):
        store=LocalPhysicalNonceStore(self.path)
        copy=Path(self.tmp.name)/"copy.db"
        shutil.copy2(self.path,copy)
        os.replace(copy,self.path)
        with self.assertRaisesRegex(CoverageError,"NONCE_STORE_REPLACED"):
            store.consume(NONCE)
        self.path.unlink()
        with self.assertRaisesRegex(CoverageError,"NONCE_STORE_MISSING"):
            LocalPhysicalNonceStore(self.path)
        self.assertFalse(self.path.exists())

    def test_database_cannot_be_bootstrapped_twice(self):
        with self.assertRaisesRegex(
                CoverageError,"NONCE_BOOTSTRAP_REQUIRES_NEW_PATH"):
            provision_nonce_store(self.path)

    def test_unsafe_file_permission_rejected(self):
        self.path.chmod(0o666)
        with self.assertRaisesRegex(CoverageError,"NONCE_FILE_INSECURE"):
            LocalPhysicalNonceStore(self.path)

    def test_four_separate_processes_one_atomic_winner(self):
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("Linux fork required")
        ctx=multiprocessing.get_context("fork")
        gate=ctx.Event()
        queue=ctx.Queue()
        workers=[ctx.Process(target=claim_in_process,
                             args=(str(self.path),gate,queue)) for _ in range(4)]
        for worker in workers:worker.start()
        gate.set()
        for worker in workers:
            worker.join(timeout=7)
            if worker.is_alive():
                worker.terminate()
                worker.join(2)
                self.fail("physical nonce worker never finished")
            self.assertEqual(worker.exitcode,0)
        outcomes=[queue.get(timeout=3) for _ in workers]
        self.assertEqual(outcomes.count(True),1,outcomes)
        self.assertEqual(outcomes.count(False),3,outcomes)
        self.assertFalse(LocalPhysicalNonceStore(self.path).consume(NONCE))


if __name__=="__main__":
    unittest.main()
