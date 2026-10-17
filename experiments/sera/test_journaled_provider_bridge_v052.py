"""SERA v0.52 journaled provider bridge offline adversarial tests."""
import tempfile
import unittest
from pathlib import Path

from experiments.sera.provider_grant_journal_v052 import ProviderJournal, JournalBlocked
from experiments.sera.journaled_provider_bridge_v052 import (
    create_journaled_provider, fingerprint_for_request)

MODELS = dict(extraction="real/one",semantic="real/two",typed="real/three",writer="real/four")
SHA = dict(source_sha256="a"*64,world_sha256="b"*64,
           scene_key="mara-s1",policy_sha256="c"*64)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = ProviderJournal(Path(self.tmp.name)/"grants.db")
        self.requests = []
        self.request = {"messages":[{"role":"user","content":"source"}]}
        self.fingerprint = fingerprint_for_request(
            stage="extraction",model=MODELS["extraction"],
            request=self.request,**SHA)
        self.binding = dict(**SHA,model=MODELS["extraction"],
                            stage="extraction",request_fingerprint=self.fingerprint)

    def transport(self, **kwargs):
        self.requests.append(kwargs)
        return {"raw":{"id":"g1","choices":[],"usage":{}},"error":None}

    def bridge(self, **overrides):
        args=dict(journal=self.journal,approved_models=MODELS,
                  grants={self.fingerprint:dict(grant_id="sera-grant-01",
                                                 request_id="req-01")},
                  transport=self.transport,authorization_verified=True,**SHA)
        args.update(overrides)
        return create_journaled_provider(**args)

    def test_missing_verified_authorization(self):
        with self.assertRaises(JournalBlocked):
            self.bridge(authorization_verified=False)

    def test_unregistered_grant_never_posts(self):
        with self.assertRaisesRegex(JournalBlocked,"GRANT_MISSING"):
            self.bridge()(key="placeholder",model=MODELS["extraction"],
                          prepared={"request":self.request})
        self.assertEqual(len(self.requests),0)

    def test_request_specific_receipt_reused(self):
        self.journal.register_grant(grant_id="sera-grant-01",binding=self.binding,
                                    authorized=True)
        callback=self.bridge()
        a=callback(key="unused",model=MODELS["extraction"],
                   prepared={"request":self.request})
        b=self.bridge()(key="unused",model=MODELS["extraction"],
                        prepared={"request":self.request})
        self.assertEqual(a,b)
        self.assertEqual(len(self.requests),1)

    def test_different_payload_blocks(self):
        self.journal.register_grant(grant_id="sera-grant-01",binding=self.binding,
                                    authorized=True)
        with self.assertRaisesRegex(JournalBlocked,"REQUEST_SPECIFIC_GRANT_MISSING"):
            self.bridge()(key="unused",model=MODELS["extraction"],
                          prepared={"request":{"messages":[]}})
        self.assertEqual(self.requests,[])

    def test_wrong_model_blocks(self):
        with self.assertRaisesRegex(JournalBlocked,"MODEL_NOT_ALLOWLISTED"):
            self.bridge()(key="unused",model="unapproved/model",
                          prepared={"request":self.request})

    def test_source_drift_blocks(self):
        with self.assertRaises(JournalBlocked):
            self.bridge(source_sha256="d"*64)(
                key="unused",model=MODELS["extraction"],
                prepared={"request":self.request})
        self.assertEqual(self.requests,[])

    def test_missing_output_token_ceiling(self):
        with self.assertRaises(Exception):
            self.bridge()(key="unused",model=MODELS["extraction"],
                          prepared={"request":{"max_tokens":1}})

    def test_no_duplicate_model_for_roles(self):
        with self.assertRaisesRegex(JournalBlocked,"MODEL_ROLE_ALLOWLIST_INVALID"):
            self.bridge(approved_models={**MODELS,"writer":MODELS["typed"]})

if __name__=="__main__":
    unittest.main()
