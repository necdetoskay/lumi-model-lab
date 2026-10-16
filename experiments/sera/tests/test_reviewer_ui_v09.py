"""Offline SERA v0.9 review workspace source and security acceptance tests."""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.reviewer_ui_v09 import (
    export_mara_browser_forms, render_html,
)
from experiments.sera.sentence_review_packet_v07 import generate_mara_packet
from experiments.sera.review_adjudication_v08 import validate_annotation


class EmbeddedJsonReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.data = {}
        self.external_scripts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            if "src" in attrs:
                self.external_scripts.append(attrs["src"])
            if attrs.get("id") in ("reviewForm", "reviewCues"):
                self.current = attrs["id"]
                self.data[self.current] = ""
    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None
    def handle_data(self, value):
        if self.current is not None:
            self.data[self.current] += value


class OfflineReviewerUIV09Tests(unittest.TestCase):
    def test_two_generated_offline_forms_have_distinct_reviewers_and_source(self):
        packet = generate_mara_packet()
        with TemporaryDirectory() as td:
            result = export_mara_browser_forms(Path(td))
            self.assertEqual(result["sentence_count"], 28)
            self.assertEqual(len(result["files"]), 2)
            self.assertFalse(result["prior_analyst_labels_exposed"])
            self.assertFalse(result["gold_qualified"])
            self.assertFalse(result["canonical_commit_authorized"])
            self.assertEqual(result["llm_calls"], 0)
            aliases = set()
            for filename in result["files"]:
                text = (Path(td)/filename).read_text(encoding="utf-8")
                dom = EmbeddedJsonReader()
                dom.feed(text)
                self.assertEqual(dom.external_scripts, [])
                self.assertIn("connect-src 'none'", text)
                self.assertIn("default-src 'none'", text)
                self.assertNotIn("ANALYST_CANDIDATE_NOT_ADJUDICATED", text)
                self.assertNotIn('"suggested_event_ids"', text)
                self.assertNotIn('"event_suggestions"', text)
                self.assertIn("JSON değerlendirmeyi indir", text)
                self.assertIn("Önceki JSON'u içe aktar", text)
                self.assertIn("Array.from", text)
                self.assertIn("URL.createObjectURL", text)
                review = json.loads(dom.data["reviewForm"])
                cues = json.loads(dom.data["reviewCues"])
                validation = validate_annotation(packet=packet,
                                                 annotation=review)
                self.assertEqual(validation["reviewed_sentence_count"], 0)
                self.assertEqual(len(review["rows"]), 28)
                self.assertEqual(len(cues), 28)
                self.assertEqual(review["source_packet_sha256"],
                                 packet["packet_sha256"])
                self.assertFalse(review["canonical_commit_authorized"])
                aliases.add(review["reviewer_alias"])
            self.assertEqual(aliases, {
                "reviewer_A_unverified", "reviewer_B_unverified",
            })

    def test_html_escapes_source_script_breakouts_in_form_json(self):
        packet = generate_mara_packet()
        packet["sentences"][0]["quote"] = (
            'A fake </script><script src="https://evil.example"> tag'
        )
        html = render_html(packet=packet, reviewer_alias="test")
        self.assertNotIn("</script><script src=", html)
        dom = EmbeddedJsonReader()
        dom.feed(html)
        actual = json.loads(dom.data["reviewForm"])
        self.assertEqual(actual["rows"][0]["quote"],
                         packet["sentences"][0]["quote"])
        self.assertEqual(dom.external_scripts, [])

    def test_generated_browser_does_not_claim_authentication_or_gold(self):
        html = render_html(packet=generate_mara_packet(),
                           reviewer_alias="reviewer_X")
        self.assertIn('"gold_status": "NOT_GOLD"', html)
        self.assertIn('"review_source": "CLAIMED_HUMAN_UNATTESTED"', html)
        self.assertIn('"canonical_commit_authorized": false', html)
        self.assertNotIn("fetch(", html)
        self.assertNotIn("XMLHttpRequest", html)
        self.assertNotIn("localStorage", html)
        self.assertIn("eventId", html)
        self.assertIn("eventQuote", html)

if __name__ == "__main__":
    unittest.main()
