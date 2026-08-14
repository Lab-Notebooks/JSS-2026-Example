"""Move converted Fortran originals into deprecated/ (restricted shell has no mv)."""
import os
import shutil

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(root, "software", "mcfm", "src", "W2jet")
dst_dir = os.path.join(src_dir, "deprecated")
os.makedirs(dst_dir, exist_ok=True)

for name in ["a6treeg.f"]:
    src = os.path.join(src_dir, name)
    if os.path.isfile(src):
        shutil.move(src, os.path.join(dst_dir, name))
        print("moved", name)
    else:
        print("already moved", name)
