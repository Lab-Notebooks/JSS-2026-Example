#!/usr/bin/env python3
"""Fuse Doxygen's call graph with per-file complexity metrics to produce a
phased translation-order roadmap for the MCFM Fortran->C++ port.

Dependency edges: Doxygen XML references/compoundref (authoritative routine
call graph). On top we layer the signals that predict difficulty here:
size, statement functions (the Haiku backend's failure trigger), spinor
density, dependency depth (untranslated callees), and fan-in (hub-ness).

translated = a .cpp OR .hpp sibling exists (modules translate to .hpp).
graph-blind = file Doxygen could not parse (dense crashers) or include
fragments we excluded; their outgoing edges are unknown, so we do NOT trust
their ndeps==0 as "leaf".

This is the INDEX phase of the staged translation workflow. Indexing here is
Doxygen-based (a collaborator generated the call graph with Doxygen rather than a
regex symbol scan), so this one command produces both the dependency ranking and
the symbol -> file map the DRAFT phase needs.

Outputs:
  tools/assets/roadmap_metrics.tsv     full ranked table (leaf readiness: deps, blind)
  tools/assets/roadmap.md              phased roadmap (deliverable)
  tools/assets/symbol_index.json       symbol -> defining file (for tools/scribe_draft.py)

Paths resolve from $PROJECT_HOME (set by environment.sh), or from this script's
location (tools/build_roadmap.py -> project root) as a fallback. The MCFM clone is
expected at $PROJECT_HOME/software/mcfm with a Doxygen call graph under
software/mcfm/doxygen_dep/xml (see software/README.md).
"""
import os, re, glob, json, collections, xml.etree.ElementTree as ET

ROOT = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.environ.get("MCFM_HOME", ROOT + "/software/mcfm") + "/src"
XML  = ROOT + "/software/mcfm/doxygen_dep/xml"
ASSETS = ROOT + "/tools/assets"
os.makedirs(ASSETS, exist_ok=True)
EXCLUDE_DIRS = ("deprecated", "Store", "working", "gpt-4o-conversions")

BENCH = {
    "W": "u d~ ve e+", "W1jet": "u d~ ve e+ g",
    "W2jet": "u d~ ve e+ g g / u u~ e- e+ g g", "BDK": "u d~ ve e+ g g",
    "loop": "u d~ ve e+ g g", "Z": "u u~ e- e+", "Z1jet": "u u~ e- e+ g",
    "Z2jet": "u u~ e- e+ g g", "ThreeJets": "g g g g g", "ggH": "g g h",
    "gghgg_dep": "g g h g g",
}
INFRA = {"Mods", "Need", "Inc", "Procdep"}
DEFER = {"gghgg_dep"}   # g g h g g: 290 dense files, its own late phase

RE_USE  = re.compile(r"^\s*use\s+(\w+)", re.I)
RE_INCL = re.compile(r"""^\s*#?\s*include\s+['"<]?([\w./]+)""", re.I)
RE_DEF  = re.compile(r"^\s*(?:pure\s+|elemental\s+|recursive\s+|module\s+)*(?:subroutine|(?:[\w()*:,\s]*?\b)?function)\s+\w+", re.I)
RE_MOD  = re.compile(r"^\s*module\s+\w+\s*$", re.I)

def is_src(fn): return (fn.endswith(".f") or fn.endswith(".f90")) and "_fi." not in fn
def relsrc(p):
    p = p.replace("\\","/"); i = p.find("/src/")
    return p[i+5:] if i>=0 else os.path.relpath(p, SRC)

files = []
for root, dirs, fs in os.walk(SRC):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for fn in fs:
        if is_src(fn): files.append(os.path.join(root, fn))
files.sort()

def metrics(path):
    fixed = path.endswith(".f")
    with open(path, errors="replace") as fh: raw = fh.readlines()
    code=stmtfn=spinor=contin=nincl=0; uses=set(); defines=False; ismod=False
    for ln in raw:
        s=ln.rstrip("\n"); low=ln.lower()
        if s.strip() and not (fixed and s[:1] in "cC*!") and not (not fixed and s.lstrip().startswith("!")):
            code+=1
        if "statement function" in low: stmtfn+=1
        m=RE_USE.match(ln)
        if m: uses.add(m.group(1).lower())
        if RE_INCL.match(ln): nincl+=1
        if RE_DEF.match(ln) and not low.lstrip().startswith("end"): defines=True
        if RE_MOD.match(ln): ismod=True
        spinor+=low.count("za(")+low.count("zb(")
        if fixed:
            if len(ln)>5 and ln[5] not in (" ","0","\t") and s[:1] not in "cC*!": contin+=1
        elif s.endswith("&"): contin+=1
    return dict(code=code,stmtfn=stmtfn,spinor=spinor,contin=contin,nincl=nincl,
                nuse=len(uses),defines=defines,ismod=ismod)

info={}; translated=set()
for p in files:
    r=relsrc(p)
    base=p.rsplit(".",1)[0]
    info[r]=dict(rel=r, top=r.split("/")[0], ext=("f90" if p.endswith(".f90") else "f"), **metrics(p))
    if os.path.exists(base+".cpp") or os.path.exists(base+".hpp"):
        translated.add(r)

# ---- doxygen call graph -> file edges + symbol -> file index ----
# The INDEX phase is Doxygen-based (a collaborator generated the call graph with
# Doxygen rather than a regex symbol scan). Alongside the file-level edges that
# drive leaf ranking, we emit a symbol -> file map (module/subroutine/function
# name -> defining source file) that the DRAFT phase (tools/scribe_draft.py)
# consumes to flag which called constructs are external functions.
cref2file={}
symbols={}   # symbol name (lower) -> src-relative defining file
xmls=[x for x in glob.glob(XML+"/*.xml") if not x.endswith("index.xml")]
for x in xmls:
    try: root=ET.parse(x).getroot()
    except ET.ParseError: continue
    for cd in root.findall("compounddef"):
        kind=cd.get("kind")
        if kind=="file":
            loc=cd.find("location")
            if loc is not None and loc.get("file"): cref2file[cd.get("id")]=relsrc(loc.get("file"))
        elif kind=="module":
            cn=cd.find("compoundname"); loc=cd.find("location")
            if cn is not None and cn.text and loc is not None and loc.get("file"):
                symbols.setdefault(cn.text.strip().lower(), relsrc(loc.get("file")))
edges=collections.defaultdict(set)
for x in xmls:
    try: root=ET.parse(x).getroot()
    except ET.ParseError: continue
    for md in root.iter("memberdef"):
        loc=md.find("location")
        cf=relsrc(loc.get("file")) if (loc is not None and loc.get("file")) else None
        if not cf: continue
        if md.get("kind") in ("function","subroutine"):
            nm=md.find("name")
            if nm is not None and nm.text: symbols.setdefault(nm.text.strip().lower(), cf)
        for ref in md.findall("references"):
            g=cref2file.get(ref.get("compoundref"))
            if g and g!=cf: edges[cf].add(g)
known=set(info)
for f in list(edges): edges[f]={g for g in edges[f] if g in known}

# graph-blind: doxygen crashers + include fragments (no reliable outgoing edges)
exf=ROOT+"/software/mcfm/doxygen_dep/excluded.txt"
blind=set(open(exf).read().split()) if os.path.exists(exf) else set()
def is_blind(r): return r in blind or r.endswith("_inc.f") or r.startswith("gghgg_dep/Inc/")

untouched=[r for r in info if r not in translated]
uset=set(untouched)
fanin=collections.Counter()
for r in info:
    deps=edges.get(r,set()); ud={g for g in deps if g in uset and g!=r}
    info[r]["udeps"]=ud; info[r]["ndeps"]=len(ud)
    for g in ud: fanin[g]+=1
for r in info: info[r]["fanin"]=fanin.get(r,0); info[r]["blind"]=is_blind(r)

# ---- category + phase ----
def category(d):
    if d["ismod"] or (d["ext"]=="f90" and d["top"] in INFRA): return "module"
    if d["rel"].endswith("_inc.f"): return "insert"
    if not d["defines"] and d["code"]<=6: return "decl"      # array/common declaration fragment
    if not d["defines"]: return "insert"
    return "routine"

def phase(d):
    c=d["cat"]
    if d["top"] in DEFER: return 4                      # gghgg_dep family, deferred
    if c in ("module","decl"): return 0                 # headers/declarations, foundational
    dense = d["stmtfn"]>0 or d["spinor"]>120 or d["code"]>200
    if dense or d["ndeps"]>=3: return 3                 # Sonnet-class
    if c=="routine" and not d["blind"] and d["ndeps"]==0 and d["code"]<=70 and d["spinor"]<=60: return 1
    if d["ndeps"]<=2 and d["code"]<=160: return 2
    return 3

for r in untouched: info[r]["cat"]=category(info[r])
for r in untouched:
    d=info[r]; d["phase"]=phase(d)
    d["score"]=round(d["code"]+8*d["stmtfn"]+0.25*d["spinor"]+14*d["ndeps"]+6*d["nincl"]+1.5*d["nuse"],1)

# ---- symbol index (Doxygen-derived; consumed by the DRAFT phase) ----
with open(ASSETS+"/symbol_index.json","w") as fh:
    json.dump({"root":SRC,"symbols":symbols}, fh, indent=1, sort_keys=True)

# ---- TSV ----
cols=["rel","top","ext","cat","phase","code","nuse","ndeps","fanin","stmtfn","spinor","nincl","blind","score","deps","bench"]
with open(ASSETS+"/roadmap_metrics.tsv","w") as fh:
    fh.write("\t".join(cols)+"\n")
    for r in sorted(untouched,key=lambda x:(info[x]["phase"],info[x]["score"])):
        d=info[r]
        fh.write("\t".join(str(v) for v in [d["rel"],d["top"],d["ext"],d["cat"],d["phase"],d["code"],
            d["nuse"],d["ndeps"],d["fanin"],d["stmtfn"],d["spinor"],d["nincl"],int(d["blind"]),
            d["score"],";".join(sorted(d["udeps"])),BENCH.get(d["top"],"")])+"\n")

# ---- markdown deliverable ----
def rows_for(pred, key=None, lim=None):
    rs=[r for r in untouched if pred(info[r])]
    rs.sort(key=key or (lambda x:(info[x]["phase"],info[x]["score"])))
    return rs[:lim] if lim else rs

def mdtable(rs, extra_cols=()):
    head="| file | cat | code | deps | fanin | sf | spinor | score |"
    sep ="|------|-----|-----:|-----:|------:|---:|-------:|------:|"
    out=[head,sep]
    for r in rs:
        d=info[r]
        out.append(f"| `{d['rel']}` | {d['cat']} | {d['code']} | {d['ndeps']} | {d['fanin']} | {d['stmtfn']} | {d['spinor']} | {d['score']} |")
    return "\n".join(out)

ph=collections.Counter(info[r]["phase"] for r in untouched)
bydir=collections.Counter(info[r]["top"] for r in untouched)
hubs=rows_for(lambda d: d["fanin"]>=2 and d["phase"]!=0, key=lambda x:-info[x]["fanin"], lim=20)

md=[]
md.append("# MCFM Translation Roadmap (dependency-ordered)\n")
md.append("Auto-generated by `tools/build_roadmap.py` from a Doxygen call graph "
          "(`software/mcfm/doxygen_dep`) fused with static complexity metrics. "
          "Full per-file data: `tools/assets/roadmap_metrics.tsv`.\n")
md.append("## How files are ranked\n")
md.append("- **Dependency depth (`deps`)** — number of *still-untranslated* source files this file calls "
          "(from Doxygen `references`). 0 = leaf, translate-ready.\n"
          "- **Fan-in** — how many untranslated files call *this* one. High fan-in = translate early to unblock others.\n"
          "- **`sf` (statement functions)** — Fortran statement-function blocks. Empirically the trigger that makes the "
          "Haiku backend silently drop amplitude algebra; `sf > 0` routes a file to the stronger-model phase.\n"
          "- **`spinor`** — count of `za(`/`zb(` spinor products; proxy for dense amplitude algebra.\n"
          "- **`code`** — non-comment source lines.\n")
md.append("> Caveat: files marked *graph-blind* (Doxygen could not parse them — 6 dense crashers — or include "
          "fragments) have unknown outgoing edges, so a `deps=0` on them is not a real leaf signal. They are kept "
          "out of Phase 1.\n")
md.append("## Status\n")
md.append(f"- Source files (filtered): **{len(info)}**  |  translated (`.cpp` or `.hpp`): **{len(translated)}**  |  untouched: **{len(untouched)}**")
md.append(f"- Call-graph edges: **{sum(len(v) for v in edges.values())}**  |  untouched leaves (`deps=0`, non-blind): "
          f"**{sum(1 for r in untouched if info[r]['ndeps']==0 and not info[r]['blind'])}**\n")
md.append("Untouched by phase: " + ", ".join(f"P{k}={ph[k]}" for k in sorted(ph)) + "\n")

md.append("## Phase 0 — foundation: modules & declaration headers\n")
md.append("Constants, types, label tables, array/common declarations. Trivial to translate (most become a `.hpp`), "
          "zero dependencies, high fan-in. Do these first so everything downstream has its headers. "
          "(Several `Mods/` already have `.hpp` and are counted translated.)\n")
md.append(mdtable(rows_for(lambda d: d["phase"]==0, key=lambda x:(-info[x]["fanin"], info[x]["score"]))))
md.append("\n## Phase 1 — leaf routines in benchmark-reachable families (translate first)\n")
md.append("Real routines with **no untranslated callees**, no statement functions, small and low spinor density, "
          "in directories a benchmark can verify (excludes `gghgg_dep`). These are the safe, high-confidence wins "
          "for the current Haiku backend.\n")
md.append(mdtable(rows_for(lambda d: d["phase"]==1)))
md.append("\n## Phase 2 — shallow-dependency routines\n")
md.append("Routines with 1–2 untranslated callees (translate after their Phase-1 leaves) or modestly larger bodies. "
          "Still Haiku-appropriate.\n")
md.append(mdtable(rows_for(lambda d: d["phase"]==2)))
md.append("\n## Phase 3 — dense / statement-function routines (stronger model)\n")
md.append("Statement-function-heavy or high-spinor-density or deep-dependency routines. This is the class that the "
          "Haiku backend silently mistranslates (e.g. the `qqbggAx*` box/tri family); route these to "
          "`claudecode-claude-sonnet` and translate their dependencies first.\n")
md.append(mdtable(rows_for(lambda d: d["phase"]==3)))
md.append("\n## Phase 4 — `gghgg_dep` (g g h g g) family, deferred\n")
md.append(f"The Higgs+2-jet family: **{bydir.get('gghgg_dep',0)}** untouched files, overwhelmingly dense amplitude "
          "code and include fragments. Its own benchmark (`g g h g g`) and largely self-contained. Defer as a block "
          "until the W/Z/3-jet families are done; order it internally by the same metrics (see TSV).\n")
md.append("\n## Hubs to prioritize within their phase (high fan-in)\n")
md.append("Translating these unblocks the most downstream files:\n")
md.append(mdtable(hubs))
md.append("")

with open(ASSETS+"/roadmap.md","w") as fh:
    fh.write("\n".join(md))

# ---- console ----
print(f"source {len(info)}  translated {len(translated)}  untouched {len(untouched)}")
print("untouched by phase:", dict(sorted(ph.items())))
print("untouched by dir:", dict(sorted(bydir.items(), key=lambda kv:-kv[1])))
print(f"\nPhase 1 leaf routines: {sum(1 for r in untouched if info[r]['phase']==1)}")
print(f"symbol index: {len(symbols)} symbol(s) -> tools/assets/symbol_index.json")
print("wrote tools/assets/roadmap.md, tools/assets/roadmap_metrics.tsv, tools/assets/symbol_index.json")
