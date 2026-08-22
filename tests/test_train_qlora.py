from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.train_qlora import canonical_sha256, tokenize_row, verify_dataset


class FakeTokenizer:
    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        self._check(tokenize)
        if len(messages) == 1 and add_generation_prompt:
            return [10, 11, 12]
        if len(messages) == 2 and not add_generation_prompt:
            return [10, 11, 12, 20, 21]
        raise AssertionError("unexpected fake chat-template call")

    @staticmethod
    def _check(tokenize):
        if tokenize is not True:
            raise AssertionError("tokenize must be true")


class LongFakeTokenizer(FakeTokenizer):
    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        self._check(tokenize)
        if len(messages) == 1 and add_generation_prompt:
            return [1, 2]
        if len(messages) == 2 and not add_generation_prompt:
            return [1, 2, 3, 4, 5, 6]
        raise AssertionError("unexpected fake chat-template call")


class TrainQloraTests(unittest.TestCase):
    def test_canonical_sha_normalizes_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "train.jsonl"
            path.write_bytes(b'{"a":1}\r\n{"b":2}\r\n')
            expected = hashlib.sha256(b'{"a":1}\n{"b":2}\n').hexdigest()
            self.assertEqual(canonical_sha256(path), expected)

    def test_verify_dataset_accepts_cross_platform_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "train.jsonl"
            manifest = root / "manifest.json"
            dataset.write_bytes(b'{"a":1}\r\n')
            expected = hashlib.sha256(b'{"a":1}\n').hexdigest()
            manifest.write_text(json.dumps({"sha256": expected}), encoding="utf-8")
            self.assertEqual(verify_dataset(dataset, manifest), expected)

    def test_assistant_only_labels_mask_prompt_tokens(self) -> None:
        row = {"instruction": "Do it", "input": "Context", "output": "Answer"}
        result = tokenize_row(row, FakeTokenizer(), max_seq_length=10)
        self.assertEqual(result["input_ids"], [10, 11, 12, 20, 21])
        self.assertEqual(result["labels"], [-100, -100, -100, 20, 21])
        self.assertEqual(result["assistant_token_count"], 2)

    def test_training_aborts_instead_of_truncating(self) -> None:
        row = {"instruction": "Do it", "input": "Context", "output": "Answer"}
        with self.assertRaisesRegex(RuntimeError, "exceeds max_seq_length"):
            tokenize_row(row, LongFakeTokenizer(), max_seq_length=5)


if __name__ == "__main__":
    unittest.main()
