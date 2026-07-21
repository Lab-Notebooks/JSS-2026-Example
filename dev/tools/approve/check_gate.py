"""Approval gate — make the human sign-off between review groups mechanical.

  python3 check_gate.py <path/to/agent_checklist.md>

Reads a step's checklist and fails if a group that already has finished work has not
been signed off, so a runner can *check* the sign-off instead of *trust* it. Format:

    ### Group 1 — W, ./test -b u d~ ve e+
    - [x] software/mcfm/src/W/qqb_w.cpp — TRANSLATED (off-path)
    APPROVED 2026-07-21 by AK

A group starts at a heading (`##`..`####`) whose text contains "group"; it is "done"
if it has a `- [x]` item, and approved if an `APPROVED <YYYY-MM-DD> ...` line follows
before the next heading. A done, unapproved group blocks; open-only groups do not.

Exit codes: 0 = all done groups approved; 1 = a done group is unapproved; 2 = bad usage/missing file.
"""
import re
import sys

HEADING = re.compile(r"^#{2,4}\s+(.*)$")
DONE_ITEM = re.compile(r"^\s*-\s*\[[xX]\]")
APPROVED = re.compile(r"^\s*APPROVED\s+\d{4}-\d{2}-\d{2}\b")


def main(argv):
    if len(argv) != 2:
        print("usage: check_gate.py <path/to/agent_checklist.md>", file=sys.stderr)
        return 2
    path = argv[1]
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        print(f"error: checklist not found: {path}", file=sys.stderr)
        print("  (a fresh checkout has only the Plan and Spec; nothing to gate yet)", file=sys.stderr)
        return 2

    # Split the file into group blocks keyed by their heading text.
    groups = []  # (title, [body lines])
    current = None
    for line in lines:
        m = HEADING.match(line)
        if m and "group" in m.group(1).lower():
            current = (m.group(1).strip(), [])
            groups.append(current)
        elif current is not None:
            current[1].append(line)

    if not groups:
        print(f"no review groups found in {path} — nothing to gate.")
        return 0

    blocked = []
    for title, body in groups:
        done = any(DONE_ITEM.match(b) for b in body)
        approved = any(APPROVED.match(b) for b in body)
        if done and not approved:
            blocked.append(title)

    if blocked:
        print("GATE: BLOCKED — these completed groups have no APPROVED line:")
        for title in blocked:
            print(f"  - {title}")
        print("\nAsk a person to review, then add a line like")
        print("    APPROVED 2026-07-21 by <name>")
        print("under the group in the checklist before starting the next group.")
        return 1

    print(f"GATE: OK — every completed group in {path} is approved.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
