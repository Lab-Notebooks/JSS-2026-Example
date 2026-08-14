import os
import subprocess
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('PROJECT_HOME', root)
os.environ['MCFM_HOME'] = os.path.join(root, 'software', 'mcfm')

target = sys.argv[1]
proc = sys.argv[2] if len(sys.argv) > 2 else 'none'
cmd = ['python3', 'dev/workflow.py', 'verify', target, '--', proc]
r = subprocess.run(cmd, cwd=root)
sys.exit(r.returncode)
