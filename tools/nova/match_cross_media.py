#!/usr/bin/env python3
"""Transparent textual matcher for research ideas only, not narrative quality."""
import json
import re
import sys
import unicodedata
from validate_cross_media import read_jsonl

STOP = {
    "bir","ve","ile","olan","icin","gibi","daha","sonra","olur","gore",
    "olan","son","bu","da","de","ki","hakkinda","olarak","anlati","hikaye"
}

def norm(value):
    text = value.lower().replace("ı","i")
    text = unicodedata.normalize("NFKD",text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]+"," ",text)).strip()

def search(query,limit=5):
    qtext=norm(query)
    words={x for x in qtext.split() if len(x)>2 and x not in STOP}
    out=[]
    for m in read_jsonl("mechanisms"):
        name=norm(m["label"])
        tokens={x for x in name.split() if len(x)>2 and x not in STOP}
        abstract=norm(m["abstraction"])
        value=80 if name in qtext else 0
        value+=10*len(words & tokens)
        value+=len(words & set(abstract.split()))
        if value>0:
            out.append({"mechanic_id":m["mechanic_id"],"work_id":m["work_id"],
                        "label":m["label"],"lexical_score":value,
                        "provenance":m["source_ids"],"status":"candidate_not_story_quality_proof",
                        "application_guardrail":m["guardrail"]})
    return sorted(out,key=lambda a:(-a["lexical_score"],a["mechanic_id"]))[:limit]

if __name__=="__main__":
    print(json.dumps({"query":" ".join(sys.argv[1:]),"matches":search(" ".join(sys.argv[1:]))},
                     ensure_ascii=False,indent=2))
