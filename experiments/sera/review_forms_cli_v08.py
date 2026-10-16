"""SERA v0.8: export blind Mara S1 review forms; compare completed forms.

Only structural checks. This CLI cannot authenticate a reviewer or grant
gold truth, live model rights, or canonical state approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.sentence_review_packet_v07 import (
    generate_mara_packet, validate_review_packet,
)
from experiments.sera.mara_s1_v04_audit import PATH
from experiments.sera.review_adjudication_v08 import (
    blank_annotation, validate_annotation, compare_annotations,
)

INSTRUCTIONS = """
# Mara S1 — Blind double human review

This is a human-review worksheet, NOT an authenticated gold dataset.
Two reviewers must independently examine all 28 source sentences without
sharing answers. Their forms deliberately hide the earlier nine analyst
candidate events.

For every sentence:
1. Replace disposition UNREVIEWED with STATE_EVENT, KNOWLEDGE_EVENT,
   CLAIM_ONLY, NO_TRACKED_CHANGE, TEXTURE or AMBIGUOUS.
2. For every lexical entity hint, choose PHYSICALLY_PRESENT,
   MENTIONED_ONLY, REPORTED_ONLY, NOT_ENTITY or AMBIGUOUS.
   Enter an explanatory nonempty reason; a noun inside a document
   does not prove the physical object was present.
3. Enter all detected events with event_id, event_type, start, end, exact
   quote, epistemic, effect, entity_refs and reason. More than one event
   per sentence is allowed; an event may span multiple sentences using
   the same event_id and a matching semantic signature.
4. Do not confuse 02:07 on a watch with the time someone looked at it.
   Do not canonize a report that a train arrived.
5. Note unknown noun candidates in notes for a second independent
   evidence check. Do not invent offsets or create physical entities.
6. Do not change gold_status or canonical_commit_authorized; this
   standalone offline tool has no identity authentication.

To build a comparison after completing both JSON files:

python -m experiments.sera.review_forms_cli_v08 compare --review-a \
  reviewer_A_unverified.json --review-b reviewer_B_unverified.json \
  --output adjudication-queue.json

The comparison is non-authorizing even if reviewers agree perfectly.
Trusted reviewer authentication and real adjudication are separate steps.
"""


def emit_forms(output_dir: Path) -> dict:
    packet = generate_mara_packet()
    prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
    validate_review_packet(prose=prose, packet=packet)
    output_dir.mkdir(parents=True, exist_ok=True)
    info = []
    for alias in ("reviewer_A_unverified", "reviewer_B_unverified"):
        form = blank_annotation(packet, reviewer_alias=alias)
        status = validate_annotation(packet=packet, annotation=form)
        if status["reviewed_sentence_count"] != 0:
            raise RuntimeError("BLIND_REVIEW_FORM_MUST_BE_UNREVIEWED")
        file = output_dir / (alias + ".json")
        file.write_text(
            json.dumps(form, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        info.append(file.name)
    instructions = output_dir / "REVIEW_INSTRUCTIONS.md"
    instructions.write_text(INSTRUCTIONS.strip() + "\n", encoding="utf-8")
    return {
        "protocol": "sera.blind-review-export.v0.8",
        "source_prose_sha256": packet["prose_sha256"],
        "source_packet_sha256": packet["packet_sha256"],
        "sentence_count": len(packet["sentences"]),
        "exported": info + [instructions.name],
        "prior_analyst_annotations_shown_to_reviewers": False,
        "gold_qualified": False,
        "model_calls": 0,
        "canonical_commit_authorized": False,
    }


def compare_files(*, review_a: Path, review_b: Path,
                  output: Path | None = None) -> dict:
    packet = generate_mara_packet()
    prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
    validate_review_packet(prose=prose, packet=packet)
    a = json.loads(review_a.read_text(encoding="utf-8"))
    b = json.loads(review_b.read_text(encoding="utf-8"))
    result = compare_annotations(packet=packet, reviewer_a=a, reviewer_b=b)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result



def validate_file(*, review: Path, require_complete: bool = False) -> dict:
    """Validate a locally saved reviewer form before human comparison.

    The result cannot authenticate a reviewer or declare gold. Incomplete
    forms are allowed during editing; --require-complete rejects blanks.
    """
    packet = generate_mara_packet()
    prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
    validate_review_packet(prose=prose, packet=packet)
    form = json.loads(review.read_text(encoding="utf-8"))
    return validate_annotation(
        packet=packet, annotation=form,
        require_complete=require_complete,
    )


def main():
    p = argparse.ArgumentParser()
    cmd = p.add_subparsers(dest="command", required=True)
    init = cmd.add_parser("export")
    init.add_argument("--output-dir", required=True, type=Path)
    compare = cmd.add_parser("compare")
    compare.add_argument("--review-a", required=True, type=Path)
    compare.add_argument("--review-b", required=True, type=Path)
    compare.add_argument("--output", type=Path)
    validate = cmd.add_parser("validate")
    validate.add_argument("--review", required=True, type=Path)
    validate.add_argument("--require-complete", action="store_true")
    args = p.parse_args()
    if args.command == "export":
        result = emit_forms(args.output_dir)
    elif args.command == "validate":
        result = validate_file(
            review=args.review, require_complete=args.require_complete,
        )
    else:
        result = compare_files(
            review_a=args.review_a, review_b=args.review_b,
            output=args.output,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
