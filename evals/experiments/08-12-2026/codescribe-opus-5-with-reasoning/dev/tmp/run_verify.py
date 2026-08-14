"""Run `dev/workflow.py verify ...` with MCFM_HOME set.

The agent shell does not source software/mcfm/environment.sh, so workflow.py
refuses to run its verify subcommand. This wrapper sets MCFM_HOME and then
delegates to workflow.py with the exact arguments given.
"""
import os
import runpy
import sys

os.environ.setdefault("MCFM_HOME", os.path.abspath("software/mcfm"))
sys.argv = ["dev/workflow.py", "verify"] + sys.argv[1:]
runpy.run_path("dev/workflow.py", run_name="__main__")
