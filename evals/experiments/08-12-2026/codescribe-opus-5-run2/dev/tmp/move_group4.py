import os
import shutil

src_dir = "software/mcfm/src/W2jet"
dst_dir = os.path.join(src_dir, "deprecated")
os.makedirs(dst_dir, exist_ok=True)

files = ["Acalc.f", "Ltfunctions.f", "LRcalc.f", "a6.f", "qqbggAxslCoeffs.f"]
for f in files:
    src = os.path.join(src_dir, f)
    dst = os.path.join(dst_dir, f)
    if os.path.exists(src):
        shutil.move(src, dst)
        print("moved", src, "->", dst)
    else:
        print("missing", src)
