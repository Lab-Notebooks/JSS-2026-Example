import os
import subprocess
import sys

os.environ["MCFM_HOME"] = os.path.abspath("software/mcfm")
rc = subprocess.call(["python3", "dev/workflow.py", "verify"] + sys.argv[1:])
sys.exit(rc)
