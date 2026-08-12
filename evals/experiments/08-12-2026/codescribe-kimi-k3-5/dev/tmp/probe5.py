import re

# Who calls msq_qq / msq_qqb / their wrappers outside msq_z2jetx itself?
for path in [
    "software/mcfm/src/Z2jet/z2jetsq.f",
    "software/mcfm/src/Z2jet/qqb_z2jetx_new.f",
    "software/mcfm/src/Z2jet/msq_z2jetx.f",
    "software/mcfm/src/Z2jet/msq_z2jetx_fi.f90",
    "software/mcfm/src/Z2jet/qqb_z2jet_v.f",
]:
    try:
        txt = open(path).read()
    except FileNotFoundError:
        print(path, "NOT FOUND")
        continue
    hits = [l for l in txt.splitlines() if re.search(r"msq_qq", l, re.I)]
    print("==", path, "->", len(hits), "msq_qq refs")
    for h in hits[:12]:
        print("   ", h.strip()[:110])
