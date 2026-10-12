"""Record a verified frozen-start/final-state comparison without model calls."""
import argparse
import json
from pathlib import Path
from src.spineforge_seeded_design import compare_story_states


def main():
    parser=argparse.ArgumentParser()
    for name in ("seed","freeze","fixture","records","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    # Reserve output first so failed comparisons cannot overwrite past evidence.
    with args.output.open("xb") as stream:
        try:
            proof=compare_story_states(args.seed,args.freeze,args.fixture,args.records)
        except (ValueError,RuntimeError,KeyError,TypeError) as exc:
            proof=dict(status="REJECTED_STATE_COMPARISON",failure_type=type(exc).__name__,message=str(exc))
        stream.write((json.dumps(proof,ensure_ascii=False,indent=2)+"\n").encode())
    print(json.dumps({k:v for k,v in proof.items() if k!="changes"},ensure_ascii=False))
    return 0 if proof["status"]=="VERIFIED_STATE_COMPARISON" else 2


if __name__=="__main__":raise SystemExit(main())
