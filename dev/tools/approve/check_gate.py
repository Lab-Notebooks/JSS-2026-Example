"""Approval gate — block new work until finished review groups are signed off.

  python3 check_gate.py <path/to/agent_checklist.md>

A group is a heading containing `group`. A group blocks if it has a completed item
(`- [x] ...`) but no `APPROVED YYYY-MM-DD by ...` line before the next heading.

Exit codes: 0 ok, 1 blocked, 2 usage or missing file.
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
