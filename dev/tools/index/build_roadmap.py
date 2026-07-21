"""Index tool — build the step-1 readiness map and additive cleanup metadata.

  python3 build_roadmap.py --doxygen
  python3 build_roadmap.py

Outputs:
- `dev/tmp/assets/roadmap_metrics.tsv`
- `dev/tmp/assets/symbol_index.json`
- `dev/tmp/assets/cleanup_candidates.tsv`
- `dev/tmp/assets/cleanup_index.json`

`deps == 0` and `blind == 0` means a file is ready to rewrite. A file is treated as
translated when a sibling `.cpp` or `.hpp` exists.
"""
import os, glob, sys, json, shutil, collections, subprocess, re, xml.etree.ElementTree as ET

ROOT   = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MCFM   = os.environ.get("MCFM_HOME", ROOT + "/software/mcfm")
SRC    = MCFM + "/src"
XML    = MCFM + "/doxygen_dep/xml"
ASSETS = ROOT + "/dev/tmp/assets"
HEADER_RE = re.compile(r'^\s*#\s*include\s+["<]([^">]+)[">]')
TARGET_RE = re.compile(r'^\s*target_sources\s*\(')

# top-level src/ directory -> the ./test -b benchmark that exercises it.
BENCH = {
    "W": "u d~ ve e+", "W1jet": "u d~ ve e+ g", "W2jet": "u d~ ve e+ g g",
    "Z": "u u~ e- e+", "Z1jet": "u u~ e- e+ g", "Z2jet": "u u~ e- e+ g g",
    "ThreeJets": "g g g g g", "ggH": "g g h", "gghgg_dep": "g g h g g",
}

# Minimal Doxygen config for the XML the roadmap reads: XML only, Fortran, with the
# cross-reference relations that make <references> edges appear. INPUT/OUTPUT are
# appended at run time from $MCFM_HOME so this stays machine-independent.
DOXYFILE = """
PROJECT_NAME           = MCFM
RECURSIVE              = YES
FILE_PATTERNS          = *.f *.F *.f90 *.F90
OPTIMIZE_FOR_FORTRAN   = YES
EXTENSION_MAPPING      = f=FortranFixed F=FortranFixed f90=FortranFree F90=FortranFree
EXTRACT_ALL            = YES
EXTRACT_PRIVATE        = YES
EXTRACT_STATIC         = YES
EXCLUDE_PATTERNS       = */deprecated/* */Store/* */working/*
SOURCE_BROWSER         = YES
REFERENCED_BY_RELATION = YES
REFERENCES_RELATION    = YES
GENERATE_HTML          = NO
GENERATE_LATEX         = NO
GENERATE_XML           = YES
XML_OUTPUT             = xml
XML_PROGRAMLISTING     = NO
HAVE_DOT               = NO
QUIET                  = YES
WARNINGS               = NO
WARN_IF_UNDOCUMENTED   = NO
"""


def relsrc(p):
    p = p.replace("\\", "/"); i = p.find("/src/")
    return p[i + 5:] if i >= 0 else os.path.relpath(p, SRC)


def is_src(fn):
    return (fn.endswith(".f") or fn.endswith(".f90")) and "_fi." not in fn


def run_doxygen():
    """Generate $MCFM_HOME/doxygen_dep/xml from the embedded config."""
    if not shutil.which("doxygen"):
        sys.exit("error: doxygen not found on PATH (Ubuntu: sudo apt-get install -y doxygen)")
    out = os.path.dirname(XML)
    os.makedirs(out, exist_ok=True)
    print(f"Generating Doxygen XML for {SRC} -> {XML}")
    config = DOXYFILE + f"\nINPUT = {SRC}\nOUTPUT_DIRECTORY = {out}\n"
    r = subprocess.run(["doxygen", "-"], input=config, text=True,
                       stdout=subprocess.DEVNULL)
    n = len([x for x in glob.glob(XML + "/*.xml") if not x.endswith("index.xml")])
    if r.returncode or n == 0:
        sys.exit("error: no XML produced — check doxygen output")
    print(f"wrote {n} XML file(s) to {XML}")


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def collect_cmake_sources(root):
    cmake_sources = collections.defaultdict(set)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
        if "CMakeLists.txt" not in files:
            continue
        cmake_path = os.path.join(dirpath, "CMakeLists.txt")
        text = read_text(cmake_path)
        if not text or not TARGET_RE.search(text):
            continue
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("target_sources(") or line == ")":
                continue
            if any(line.endswith(ext) for ext in (".f", ".F", ".f90", ".F90", ".cpp", ".hpp", ".h")):
                cmake_sources[os.path.relpath(dirpath, root)].add(line)
    return cmake_sources


def collect_header_usage(root):
    usage = collections.Counter()
    users = collections.defaultdict(set)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
        for fn in files:
            if not fn.endswith((".cpp", ".hpp", ".h", ".cc", ".cxx")):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace("\\", "/")
            text = read_text(path)
            for line in text.splitlines():
                m = HEADER_RE.match(line)
                if not m:
                    continue
                inc = m.group(1).replace("\\", "/")
                usage[inc] += 1
                users[inc].add(rel)
                base = os.path.basename(inc)
                if base != inc:
                    usage[base] += 1
                    users[base].add(rel)
    return usage, users


def build_cleanup_index(root, cmake_sources, header_usage, header_users):
    cleanup = []
    families = collections.defaultdict(dict)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
        rel_dir = os.path.relpath(dirpath, root)
        for fn in files:
            full = os.path.join(dirpath, fn)
            base, ext = os.path.splitext(fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            fi_base = None
            if base.endswith("_fi") and ext in (".f", ".F", ".f90", ".F90"):
                fi_base = base[:-3]
                families[(rel_dir, fi_base)]["fi"] = rel
                continue
            if ext in (".f", ".F", ".f90", ".F90"):
                families[(rel_dir, base)]["fortran"] = rel
            elif ext == ".cpp":
                families[(rel_dir, base)]["cpp"] = rel
            elif ext in (".hpp", ".h"):
                families[(rel_dir, base)]["header"] = rel

    for (rel_dir, base), parts in sorted(families.items()):
        rel_prefix = "" if rel_dir == "." else rel_dir + "/"
        original = parts.get("fortran", "")
        cpp = parts.get("cpp", "")
        header = parts.get("header", "")
        fi = parts.get("fi", "")
        original_name = os.path.basename(original) if original else ""
        deprecated_original = bool(original and "/deprecated/" in original)
        local_cmake_entries = cmake_sources.get(rel_dir, set())
        cmake_original = int(original_name in local_cmake_entries) if original_name else 0
        cmake_cpp = int(os.path.basename(cpp) in local_cmake_entries) if cpp else 0
        cmake_header = int(os.path.basename(header) in local_cmake_entries) if header else 0
        cmake_fi = int(os.path.basename(fi) in local_cmake_entries) if fi else 0
        header_key = os.path.basename(header) if header else ""
        include_count = header_usage.get(header_key, 0) if header_key else 0
        users = sorted(header_users.get(header_key, set())) if header_key else []
        merge_candidate = int(bool(cpp and header) and include_count <= 1)
        move_candidate = int(bool(original and cpp and not deprecated_original))
        delete_shim_candidate = int(bool(fi and cpp and not cmake_original))
        cleanup.append({
            "base": rel_prefix + base,
            "dir": "." if rel_dir == "." else rel_dir,
            "fortran": original,
            "cpp": cpp,
            "header": header,
            "fi": fi,
            "deprecated_original": int(deprecated_original),
            "cmake_original": cmake_original,
            "cmake_cpp": cmake_cpp,
            "cmake_header": cmake_header,
            "cmake_fi": cmake_fi,
            "header_include_count": include_count,
            "header_users": users,
            "move_candidate": move_candidate,
            "delete_shim_candidate": delete_shim_candidate,
            "merge_candidate": merge_candidate,
        })
    return cleanup


def build_roadmap():
    os.makedirs(ASSETS, exist_ok=True)

    # ---- source files and their translated state ----
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

    # ---- additive cleanup metadata ----
    cmake_sources = collect_cmake_sources(SRC)
    header_usage, header_users = collect_header_usage(SRC)
    cleanup = build_cleanup_index(SRC, cmake_sources, header_usage, header_users)

    # ---- outputs ----
    with open(ASSETS + "/symbol_index.json", "w") as fh:
        json.dump({"root": SRC, "symbols": symbols}, fh, indent=1, sort_keys=True)

    cols = ["rel", "top", "deps", "blind", "fanin", "bench"]
    with open(ASSETS + "/roadmap_metrics.tsv", "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in sorted(untranslated, key=lambda x: (info[x]["deps"], -info[x]["fanin"])):
            fh.write("\t".join(str(info[r][c]) for c in cols) + "\n")

    cleanup_cols = [
        "base", "dir", "fortran", "cpp", "header", "fi", "deprecated_original",
        "cmake_original", "cmake_cpp", "cmake_header", "cmake_fi",
        "header_include_count", "move_candidate", "delete_shim_candidate", "merge_candidate",
    ]
    with open(ASSETS + "/cleanup_candidates.tsv", "w") as fh:
        fh.write("\t".join(cleanup_cols) + "\n")
        for row in cleanup:
            fh.write("\t".join(str(row[c]) for c in cleanup_cols) + "\n")

    with open(ASSETS + "/cleanup_index.json", "w") as fh:
        json.dump({"root": SRC, "candidates": cleanup}, fh, indent=1, sort_keys=True)

    leaves = sum(1 for r in untranslated if info[r]["deps"] == 0 and not info[r]["blind"])
    cleanup_moves = sum(row["move_candidate"] for row in cleanup)
    cleanup_shims = sum(row["delete_shim_candidate"] for row in cleanup)
    cleanup_merges = sum(row["merge_candidate"] for row in cleanup)
    print(f"source {len(info)}  translated {len(translated)}  untranslated {len(untranslated)}")
    print(f"ready leaves (deps=0, non-blind): {leaves}")
    print(f"symbol index: {len(symbols)} symbol(s)")
    print(f"cleanup candidates: move {cleanup_moves}  shim-delete {cleanup_shims}  merge {cleanup_merges}")
    print("wrote roadmap_metrics.tsv, symbol_index.json, cleanup_candidates.tsv, cleanup_index.json")


if __name__ == "__main__":
    if "--doxygen" in sys.argv[1:]:
        run_doxygen()
    else:
        build_roadmap()
