import shutil, sys, os, glob
print("which(doxygen):", shutil.which("doxygen"))
cands = []
for pat in ["/usr/bin/doxygen*", "/usr/local/bin/doxygen*", "/opt/**/doxygen*"]:
    cands.extend(glob.glob(pat, recursive=True))
print("candidates:", cands)
