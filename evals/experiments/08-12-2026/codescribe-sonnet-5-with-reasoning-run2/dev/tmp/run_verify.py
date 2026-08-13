import os
import subprocess
import sys

os.environ["MCFM_HOME"] = "/home/user/JSS-2026-Example/software/mcfm"
os.environ["PROJECT_HOME"] = "/home/user/JSS-2026-Example"
os.environ["PEPPER_HOME"] = "/home/user/JSS-2026-Example/software/pepper"
os.environ["QCDLOOP_HOME"] = "/home/user/JSS-2026-Example/software/qcdloop"

args = sys.argv[1:]
r = subprocess.run([sys.executable, "dev/workflow.py"] + args)
sys.exit(r.returncode)
