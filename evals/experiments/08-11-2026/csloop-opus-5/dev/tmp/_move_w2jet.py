import os, shutil, sys

d = "software/mcfm/src/W2jet"
dep = os.path.join(d, "deprecated")
os.makedirs(dep, exist_ok=True)
for f in sys.argv[1:]:
    src = os.path.join(d, f)
    if os.path.isfile(src):
        shutil.move(src, os.path.join(dep, f))
print(sorted(os.listdir(dep)))
