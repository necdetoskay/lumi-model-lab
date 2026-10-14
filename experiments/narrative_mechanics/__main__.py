"""Offline research CLI; does not invoke any writer or model."""
import argparse
import sys
from pathlib import Path

from .core import Invalid, build_manifest, canonical, freeze, load_release, read_json, select


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    manifest = sub.add_parser("freeze-archive")
    manifest.add_argument("--directory", type=Path, required=True)
    selection = sub.add_parser("select")
    selection.add_argument("--request", type=Path, required=True)
    selection.add_argument("--audit-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "verify":
            artifacts = load_release()
            print(canonical({"status": "PASS", "scope": "LAB_ONLY", "episodes": len(artifacts["archive"]["episodes"]),
                             "cards": len(artifacts["cards"]), "provider_calls": 0}).decode())
        elif args.command == "freeze-archive":
            print(freeze(args.directory, "archive", build_manifest()))
        else:
            writer, audit = select(read_json(args.request))
            if args.audit_dir:
                freeze(args.audit_dir, "selection", audit)
            sys.stdout.buffer.write(canonical(writer) + b"\n")
    except (Invalid, OSError, ValueError, KeyError):
        # Raw file paths, source fragments and parser text never cross this boundary.
        print("NML_INPUT_OR_INTEGRITY_FAILURE", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
