"""List ready leaves (deps=0, blind=0, no generated .cpp) from the roadmap metrics."""
import csv
import sys
from pathlib import Path

tsv = Path("dev/tmp/assets/roadmap_metrics.tsv")
rows = list(csv.DictReader(tsv.open(), delimiter="\t"))
if not rows:
    sys.exit("no rows")
print("columns:", list(rows[0].keys()))

folder = sys.argv[1] if len(sys.argv) > 1 else ""


def get(row, *names):
    for n in names:
        if n in row:
            return row[n]
    return ""


cands = []
for r in rows:
    path = get(r, "rel", "path", "file", "source")
    deps = get(r, "deps", "ndeps")
    blind = get(r, "blind", "blind_calls")
    if deps == "0" and blind == "0" and folder in path:
        cands.append(r)

print("ready candidates:", len(cands))
for r in cands[:40]:
    print(" | ".join(f"{k}={v}" for k, v in r.items()))
