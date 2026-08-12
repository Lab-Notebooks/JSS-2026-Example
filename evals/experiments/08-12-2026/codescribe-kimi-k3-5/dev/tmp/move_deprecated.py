import os

base = "software/mcfm/src/W2jet"
dep = os.path.join(base, "deprecated")
os.makedirs(dep, exist_ok=True)
for f in ["vv.f", "fpm.f", "fpp.f", "fsl.f", "fvf.f"]:
    src = os.path.join(base, f)
    dst = os.path.join(dep, f)
    if os.path.exists(src):
        os.replace(src, dst)
        print("moved", src, "->", dst)
    else:
        print("missing", src)
