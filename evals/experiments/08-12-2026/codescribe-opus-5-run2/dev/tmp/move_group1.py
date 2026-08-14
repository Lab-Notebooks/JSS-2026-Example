import os, shutil

src = "software/mcfm/src/W2jet"
dst = os.path.join(src, "deprecated")
os.makedirs(dst, exist_ok=True)
for f in ["fpp.f", "fvf.f", "faxsl.f", "subqcd.f"]:
    p = os.path.join(src, f)
    if os.path.exists(p):
        shutil.move(p, os.path.join(dst, f))
print(sorted(os.listdir(dst)))
