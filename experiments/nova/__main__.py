"""No network adapter exists. Real generation is deliberately unavailable."""
import argparse
import json
import sys

from experiments.narrative_mechanics import core as nml
from . import evaluate, trial, vault
from .match import match


def main(argv=None):
    parser = argparse.ArgumentParser(description="NOVA independent offline LAB")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    run = sub.add_parser("dry-run")
    run.add_argument("--output", required=True)
    index = sub.add_parser("index")
    index.add_argument("--output", required=True)
    sub.add_parser("generate")
    prep = sub.add_parser("prepare-trial")
    prep.add_argument("--output", required=True)
    prep.add_argument("--seed", type=int, default=314159)
    prep.add_argument("--repeats", type=int, default=3)
    imp = sub.add_parser("import-stories")
    imp.add_argument("--trial", required=True)
    imp.add_argument("--bundle", required=True)
    scoring = sub.add_parser("score-trial")
    scoring.add_argument("--trial", required=True)
    scoring.add_argument("--ballots", required=True)
    selection = sub.add_parser("match")
    selection.add_argument("--brief-id", required=True)
    selection.add_argument("--history")
    selection.add_argument("--audit-dir", required=True)
    analysis = sub.add_parser("analyze")
    analysis.add_argument("--mechanic-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            raise nml.Invalid("PAID_DISPATCH_BLOCKED_NO_BUDGET_OR_AUTHORIZATION")
        if args.command == "prepare-trial":
            result = trial.prepare_trial(args.output, args.seed, args.repeats)
        elif args.command == "import-stories":
            result = trial.import_stories(args.trial, nml.read_json(args.bundle))
        elif args.command == "score-trial":
            result = trial.score_trial(args.trial, nml.read_json(args.ballots))
        elif args.command == "analyze":
            rows, _, _ = vault.load()
            found = [r for r in rows if r["id"] == args.mechanic_id]
            if not found:
                raise nml.Invalid("UNKNOWN_MECHANIC")
            result = found[0]  # Researcher-only evidence; never a generator input.
        elif args.command == "match":
            rows, state, briefs, _ = evaluate.load_inputs()
            found = [b for b in briefs if b["id"] == args.brief_id]
            if not found:
                raise nml.Invalid("UNKNOWN_BRIEF")
            history = vault.load_usage(args.history) if args.history else []
            result, audit = match(found[0], state, rows, history)
            nml.freeze(args.audit_dir, "selection", audit)
            vault.record_usage(args.audit_dir, audit, found[0])
        elif args.command == "dry-run":
            result = evaluate.dry_run(args.output)
        elif args.command == "index":
            rows, _, release = vault.load()
            vault.build_index(args.output, rows, release)
            result = {"status": "PASS", "records": len(rows)}
        else:
            rows, _, briefs, _ = evaluate.load_inputs()
            result = {"status": "PASS", "mechanics": len(rows), "briefs": len(briefs),
                      "provider_calls": 0, "integration_authorized": False}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (nml.Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc) if isinstance(exc, nml.Invalid) else "INVALID_IO_OR_DATA"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
