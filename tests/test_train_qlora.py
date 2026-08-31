from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.train_qlora import canonical_sha256, tokenize_row, verify_dataset


class FakeTokenizer:
    rendered = "<u>Do it\n\nBağlam:\nContext</u><a>Answer</a>"

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        if tokenize is not False:
            raise AssertionError("tokenize must be false")
        if len(messages) != 2 or add_generation_prompt:
            raise AssertionError("unexpected fake chat-template call")
        return self.rendered

    def __call__(self, text, *, add_special_tokens, return_offsets_mapping):
        if text != self.rendered:
            raise AssertionError("unexpected rendered text")
        if add_special_tokens is not False or return_offsets_mapping is not True:
            raise AssertionError("offset tokenization options required")
        start = text.index("Answer")
        return {
            "input_ids": [10, 11, 20, 21],
            "offset_mapping": [(0, 3), (3, start), (start, start + 3), (start + 3, start + 6)],
        }


class LongFakeTokenizer(FakeTokenizer):
    def __call__(self, text, *, add_special_tokens, return_offsets_mapping):
        start = text.index("Answer")
        return {
            "input_ids": [1, 2, 3, 4, 5, 6],
            "offset_mapping": [
                (0, 2),
                (2, 4),
                (4, start),
                (start, start + 2),
                (start + 2, start + 4),
                (start + 4, start + 6),
            ],
        }


class NoOffsetTokenizer(FakeTokenizer):
    def __call__(self, text, *, add_special_tokens, return_offsets_mapping):
        raise NotImplementedError("slow tokenizer")


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

    def test_assistant_only_labels_use_rendered_offsets(self) -> None:
        row = {"instruction": "Do it", "input": "Context", "output": "Answer"}
        result = tokenize_row(row, FakeTokenizer(), max_seq_length=10)
        self.assertEqual(result["input_ids"], [10, 11, 20, 21])
        self.assertEqual(result["labels"], [-100, -100, 20, 21])
        self.assertEqual(result["assistant_token_count"], 2)

    def test_training_aborts_instead_of_truncating(self) -> None:
        row = {"instruction": "Do it", "input": "Context", "output": "Answer"}
        with self.assertRaisesRegex(RuntimeError, "exceeds max_seq_length"):
            tokenize_row(row, LongFakeTokenizer(), max_seq_length=5)

    def test_training_requires_offset_mapping_for_safe_masking(self) -> None:
        row = {"instruction": "Do it", "input": "Context", "output": "Answer"}
        with self.assertRaisesRegex(RuntimeError, "offset_mapping"):
            tokenize_row(row, NoOffsetTokenizer(), max_seq_length=10)


if __name__ == "__main__":
    unittest.main()
