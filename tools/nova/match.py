#!/usr/bin/env python3
"""A transparent lexical candidate matcher, NOT narrative quality prediction."""
import json
import re
import sys
import unicodedata
from validate import read_jsonl

def norm(value):
    text = value.lower().replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text)).strip()

def rank(query, limit=5):
    q = " " + norm(query) + " "
    matches = []
    for mechanic in read_jsonl("mechanics.jsonl"):
        matched_phrases = []
        for phrase in mechanic["retrieval_phrases_tr"]:
            p = norm(phrase)
            if p and (" " + p + " ") in q:
                matched_phrases.append(phrase)
        if matched_phrases:
            matches.append({
                "mechanic_id": mechanic["mechanic_id"],
                "label_tr": mechanic["label_tr"],
                "score": sum(1 + len(norm(p).split()) for p in matched_phrases),
                "matched_phrases": matched_phrases,
                "status": "candidate_only_not_story_validated",
            })
    matches.sort(key=lambda x: (-x["score"], x["mechanic_id"]))
    return matches[:limit]

if __name__ == "__main__":
    print(json.dumps({"query": " ".join(sys.argv[1:]), "candidates": rank(" ".join(sys.argv[1:]))},
                     ensure_ascii=False, indent=2))
