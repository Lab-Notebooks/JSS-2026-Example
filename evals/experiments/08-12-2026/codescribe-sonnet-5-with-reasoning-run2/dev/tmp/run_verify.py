import os
import subprocess
import sys

os.environ["MCFM_HOME"] = "/home/akash/Desktop/Akash/Projects/JSS-Paper-Example/software/mcfm"
os.environ["PROJECT_HOME"] = "/home/akash/Desktop/Akash/Projects/JSS-Paper-Example"
os.environ["PEPPER_HOME"] = "/home/akash/Desktop/Akash/Projects/JSS-Paper-Example/software/pepper"
os.environ["QCDLOOP_HOME"] = "/home/akash/Desktop/Akash/Projects/JSS-Paper-Example/software/qcdloop"

args = sys.argv[1:]
r = subprocess.run([sys.executable, "dev/workflow.py"] + args)
sys.exit(r.returncode)
