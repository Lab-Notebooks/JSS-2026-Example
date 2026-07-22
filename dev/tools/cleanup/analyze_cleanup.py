"""Cleanup analysis tool — inspect translated MCFM families for conservative cleanup actions.

  python3 dev/tools/cleanup/analyze_cleanup.py
  python3 dev/tools/cleanup/analyze_cleanup.py --json

Reads `dev/tmp/assets/cleanup_index.json` when available, otherwise performs the same repository
scan directly. Prints a human-readable report and can emit JSON to stdout.
"""
import os
import sys
import json
from pathlib import Path

ROOT = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MCFM = os.environ.get("MCFM_HOME", ROOT + "/software/mcfm")
SRC = MCFM + "/src"
ASSETS = ROOT + "/dev/tmp/assets"
CLEANUP_JSON = ASSETS + "/cleanup_index.json"
COMMON = Path(__file__).resolve().parent.parent / "common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))
from cleanup_index import build_cleanup_index


def scan_cleanup(root):
    return build_cleanup_index(root)


def load_candidates():
    if os.path.isfile(CLEANUP_JSON):
        try:
            with open(CLEANUP_JSON, encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("candidates", [])
        except (OSError, json.JSONDecodeError):
            pass
    return scan_cleanup(SRC)


def classify(row):
    actions = []
    reasons = []
    if row.get("move_candidate"):
        actions.append("MOVE_F")
    if row.get("delete_shim_candidate"):
        actions.append("DELETE_SHIM?")
    elif row.get("fi"):
        reasons.append("keep shim: original Fortran still appears in build or evidence is incomplete")
    if row.get("merge_candidate"):
        actions.append("MERGE_HPP_CPP?")
    elif row.get("header"):
        reasons.append(f"keep split: header include count {row.get('header_include_count', 0)}")
    if not actions:
        actions.append("NO_ACTION")
    return actions, reasons


def print_report(rows):
    print(f"# cleanup candidates under {SRC}")
    print("# base\tactions\tfortran\tcpp\tfi\theader\theader_uses")
    for row in rows:
        actions, _ = classify(row)
        print(
            f"{row.get('base','')}\t{','.join(actions)}\t{int(bool(row.get('fortran')))}\t"
            f"{int(bool(row.get('cpp')))}\t{int(bool(row.get('fi')))}\t{int(bool(row.get('header')))}\t"
            f"{row.get('header_include_count', 0)}"
        )
    print()
    for row in rows:
        actions, reasons = classify(row)
        if actions == ["NO_ACTION"] and not reasons:
            continue
        print(f"## {row.get('base','')}")
        print(f"- actions: {', '.join(actions)}")
        if row.get("header_users"):
            print(f"- header users: {', '.join(row['header_users'])}")
        for reason in reasons:
            print(f"- note: {reason}")


def main(argv):
    rows = load_candidates()
    if "--json" in argv:
        json.dump(rows, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    print_report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
