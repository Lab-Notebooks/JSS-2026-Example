import os, shutil, sys
src = "software/mcfm/src/W2jet"
dst = os.path.join(src, "deprecated")
os.makedirs(dst, exist_ok=True)
files = sys.argv[1:] or ["atree.f", "fvf.f", "a6treeg.f", "subqcd.f"]
for f in files:
    p = os.path.join(src, f)
    if os.path.isfile(p):
        shutil.move(p, os.path.join(dst, f))
        print("moved", f)
    else:
        print("missing", f)
print("MCFM_HOME=", os.environ.get("MCFM_HOME"))
