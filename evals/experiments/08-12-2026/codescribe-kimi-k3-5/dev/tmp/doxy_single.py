import os
import shutil
import subprocess
import sys

# usage: python3 dev/tmp/doxy_single.py <input-file-or-dir> [--filter <filter-script>]
inp = sys.argv[1]
filt = None
if len(sys.argv) > 3 and sys.argv[2] == "--filter":
    filt = sys.argv[3]

out = "dev/tmp/doxy_single_out"
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out, exist_ok=True)

cfg = """
PROJECT_NAME = Single
OPTIMIZE_FOR_FORTRAN = YES
RECURSIVE = YES
EXCLUDE_PATTERNS = */deprecated/* */Store/* */working/*
EXTENSION_MAPPING = f=FortranFixed F=FortranFixed f90=FortranFree F90=FortranFree
FILE_PATTERNS = *.f *.F *.f90 *.F90
EXTRACT_ALL = YES
REFERENCED_BY_RELATION = YES
REFERENCES_RELATION = YES
GENERATE_HTML = NO
GENERATE_LATEX = NO
GENERATE_XML = YES
XML_OUTPUT = xml
QUIET = NO
INPUT = %s
OUTPUT_DIRECTORY = %s
""" % (os.path.abspath(inp), os.path.abspath(out))
if filt:
    cfg += 'INPUT_FILTER = "python3 %s"\n' % os.path.abspath(filt)

with open("dev/tmp/Doxyfile.single", "w") as fh:
    fh.write(cfg)

r = subprocess.run(["doxygen", "dev/tmp/Doxyfile.single"], capture_output=True, text=True)
print("doxygen exit:", r.returncode)
print("STDOUT tail:")
print((r.stdout or "")[-800:])
print("STDERR tail:")
print((r.stderr or "")[-4000:])
n = 0
xmldir = os.path.join(out, "xml")
if os.path.isdir(xmldir):
    n = len([x for x in os.listdir(xmldir) if x.endswith(".xml")])
print("xml files:", n)
