import os
import subprocess
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('PROJECT_HOME', root)
os.environ['MCFM_HOME'] = os.path.join(root, 'software', 'mcfm')

r = subprocess.run(['python3', 'dev/workflow.py'] + sys.argv[1:], cwd=root)
sys.exit(r.returncode)
