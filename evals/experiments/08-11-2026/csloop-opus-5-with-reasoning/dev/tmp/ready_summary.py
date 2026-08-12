import collections, os, sys
rows = [l.split("\t") for l in open("dev/tmp/assets/roadmap_metrics.tsv").read().splitlines()[1:]]
ready = [r for r in rows if r[2] == "0" and r[3] == "0"]
c = collections.Counter(r[1] for r in ready)
print(len(ready))
print(c.most_common())
for top in sys.argv[1:]:
    print("==", top)
    for r in ready:
        if r[1] == top:
            p = os.path.join("software/mcfm/src", r[0])
            n = sum(1 for _ in open(p, errors="ignore")) if os.path.exists(p) else -1
            print(r[0], "lines=", n, "fanin=", r[4], "bench=", r[5] if len(r) > 5 else "")
