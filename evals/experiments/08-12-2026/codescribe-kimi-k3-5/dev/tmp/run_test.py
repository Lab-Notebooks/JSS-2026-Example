import os
import subprocess
import sys

os.environ.setdefault("MCFM_HOME", "/home/user/JSS-2026-Example/software/mcfm")
os.environ.setdefault("PEPPER_HOME", "/home/user/JSS-2026-Example/software/pepper")
os.environ.setdefault("QCDLOOP_HOME", "/home/user/JSS-2026-Example/software/qcdloop")

mcfm = os.environ["MCFM_HOME"]
args = sys.argv[1:] or ["u", "d~", "ve", "e+", "g", "g"]
p = subprocess.run([mcfm + "/Bin/test", "-b", *args], cwd=mcfm + "/Bin",
                   capture_output=True, text=True)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
print(f"EXIT_CODE={p.returncode}")
sys.exit(p.returncode)
