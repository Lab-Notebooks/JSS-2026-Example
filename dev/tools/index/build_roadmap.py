#!/usr/bin/env python3
"""Index tool — rank MCFM's Fortran files by translation readiness.

The deterministic first phase of the stage-1 workflow. It fuses Doxygen's call
graph with a translated/not-translated check to answer one question the Resolve
phase needs: which files are *leaves* — every routine they call is already C++, so
they can be translated now without a missing dependency.

A collaborator generated the call graph with Doxygen (not a regex scan), so this one
command also emits the symbol → file map the Draft tool consumes. Two outputs:

  dev/tmp/assets/roadmap_metrics.tsv   per-file: deps, blind, fanin, bench
  dev/tmp/assets/symbol_index.json     symbol → defining file (for scribe_draft.py)

All generated output goes under dev/tmp/ (the scratch root, git-ignored).

deps = untranslated callees (0 = ready). blind = a file Doxygen could not parse, so
its edges are unknown and deps==0 cannot be trusted. translated = a .cpp or .hpp
sibling exists. Paths resolve from $PROJECT_HOME (set by environment.sh).
"""
import os, re, glob, json, collections, xml.etree.ElementTree as ET

ROOT   = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SRC    = os.environ.get("MCFM_HOME", ROOT + "/software/mcfm") + "/src"
XML    = ROOT + "/software/mcfm/doxygen_dep/xml"
ASSETS = ROOT + "/dev/tmp/assets"
os.makedirs(ASSETS, exist_ok=True)

# top-level src/ directory -> the ./test -b benchmark that exercises it (Spec's test-coverage table).
BENCH = {
    "W": "u d~ ve e+", "W1jet": "u d~ ve e+ g", "W2jet": "u d~ ve e+ g g",
    "Z": "u u~ e- e+", "Z1jet": "u u~ e- e+ g", "Z2jet": "u u~ e- e+ g g",
    "ThreeJets": "g g g g g", "ggH": "g g h", "gghgg_dep": "g g h g g",
}

def relsrc(p):
    p = p.replace("\\", "/"); i = p.find("/src/")
    return p[i + 5:] if i >= 0 else os.path.relpath(p, SRC)

def is_src(fn):
    return (fn.endswith(".f") or fn.endswith(".f90")) and "_fi." not in fn

# ---- collect source files and their translated state ----
files = []
for root, dirs, fs in os.walk(SRC):
    dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
    files += [os.path.join(root, fn) for fn in fs if is_src(fn)]

info, translated = {}, set()
for p in sorted(files):
    r = relsrc(p)
    info[r] = {"rel": r, "top": r.split("/")[0]}
    if os.path.exists(p.rsplit(".", 1)[0] + ".cpp") or os.path.exists(p.rsplit(".", 1)[0] + ".hpp"):
        translated.add(r)

# ---- Doxygen call graph -> file edges + symbol -> file index ----
cref2file, symbols, edges = {}, {}, collections.defaultdict(set)
xmls = [x for x in glob.glob(XML + "/*.xml") if not x.endswith("index.xml")]
for x in xmls:
    try: root = ET.parse(x).getroot()
    except ET.ParseError: continue
    for cd in root.findall("compounddef"):
        loc = cd.find("location")
        if cd.get("kind") == "file" and loc is not None and loc.get("file"):
            cref2file[cd.get("id")] = relsrc(loc.get("file"))
        elif cd.get("kind") == "module":
            cn = cd.find("compoundname")
            if cn is not None and cn.text and loc is not None and loc.get("file"):
                symbols.setdefault(cn.text.strip().lower(), relsrc(loc.get("file")))
for x in xmls:
    try: root = ET.parse(x).getroot()
    except ET.ParseError: continue
    for md in root.iter("memberdef"):
        loc = md.find("location")
        cf = relsrc(loc.get("file")) if (loc is not None and loc.get("file")) else None
        if not cf: continue
        if md.get("kind") in ("function", "subroutine"):
            nm = md.find("name")
            if nm is not None and nm.text: symbols.setdefault(nm.text.strip().lower(), cf)
        for ref in md.findall("references"):
            g = cref2file.get(ref.get("compoundref"))
            if g and g in info and g != cf: edges[cf].add(g)

# ---- readiness: untranslated callees (deps), fan-in, blindness ----
def is_blind(r):
    return r.endswith("_inc.f") or r.startswith("gghgg_dep/Inc/")

untranslated = {r for r in info if r not in translated}
fanin = collections.Counter()
for r in info:
    udeps = {g for g in edges.get(r, set()) if g in untranslated and g != r}
    info[r]["deps"] = len(udeps)
    for g in udeps: fanin[g] += 1
for r in info:
    info[r]["fanin"] = fanin.get(r, 0)
    info[r]["blind"] = int(is_blind(r))
    info[r]["bench"] = BENCH.get(info[r]["top"], "")

# ---- outputs ----
with open(ASSETS + "/symbol_index.json", "w") as fh:
    json.dump({"root": SRC, "symbols": symbols}, fh, indent=1, sort_keys=True)

cols = ["rel", "top", "deps", "blind", "fanin", "bench"]
with open(ASSETS + "/roadmap_metrics.tsv", "w") as fh:
    fh.write("\t".join(cols) + "\n")
    for r in sorted(untranslated, key=lambda x: (info[x]["deps"], -info[x]["fanin"])):
        fh.write("\t".join(str(info[r][c]) for c in cols) + "\n")

leaves = sum(1 for r in untranslated if info[r]["deps"] == 0 and not info[r]["blind"])
print(f"source {len(info)}  translated {len(translated)}  untranslated {len(untranslated)}")
print(f"ready leaves (deps=0, non-blind): {leaves}")
print(f"symbol index: {len(symbols)} symbol(s)")
print("wrote roadmap_metrics.tsv, symbol_index.json")
