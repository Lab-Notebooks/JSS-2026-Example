import os
import subprocess
import sys

os.environ.setdefault("MCFM_HOME", "/home/adubey/JSS-2026-Example/software/mcfm")
os.environ.setdefault("PEPPER_HOME", "/home/adubey/JSS-2026-Example/software/pepper")
os.environ.setdefault("QCDLOOP_HOME", "/home/adubey/JSS-2026-Example/software/qcdloop")

rc = subprocess.run(
    [sys.executable, "dev/tools/coverage/coverage_check.py", *sys.argv[1:]]
).returncode
print(f"EXIT_CODE={rc}")
sys.exit(rc)
