import os, shutil, sys

d = sys.argv[1]
dep = os.path.join(d, "deprecated")
os.makedirs(dep, exist_ok=True)
for f in sys.argv[2:]:
    src = os.path.join(d, f)
    dst = os.path.join(dep, f)
    shutil.move(src, dst)
    print("moved", src, "->", dst)
