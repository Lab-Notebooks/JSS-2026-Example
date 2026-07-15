#!/usr/bin/env python3
"""Transitive call-tree closure of an MCFM routine, from linked-object symbols.

Deterministic completeness cross-check for the stage-2 (Kokkos) Split phase:
an agent maps the call tree by reading sources, THIS tool derives it from the
build itself -- every linked object's undefined symbols are its real callees,
resolved against the objects actually listed in libmcfm's link line. Symbols
do not lie; a closure file missing from a split plan is either a missed
callee or must be explicitly justified as dead/off-path.

Why not the Doxygen graph (tools/build_roadmap.py): that graph is built from
the FORTRAN sources and 288/476 of its per-file XMLs are empty stubs (silent
parse failures, no call edges), so it cannot certify completeness. It remains
fine for what stage 1 uses it for (ranking candidate leaves; the integrate
build catches its false leaves), but not as an authority.

Granularity is object == source file. Language tags show stage-1 state:
  cpp     translated C++
  fi      iso_c_binding shim (fine; check it holds no retained Fortran)
  FORTRAN a plain .f/.f90 object in the closure = a stage-1 gap for stage 2

The 'kokkos' column shows stage-2 progress: which closure files are already
ported into Pepper kernels/fragments, read from the machine-readable
provenance line every mcfm_analytics header carries:
  // MCFM sources: src/Z1jet/qqb_z1jet_v.cpp, src/Need/lfunctions.cpp (partial)
'partial' means the header ports only some functions of that file -- reuse
still requires checking that the functions you need are among them.

Usage:
  python3 tools/calltree_closure.py qqb_z2jet_v
  python3 tools/calltree_closure.py Z2jet/qqb_z2jet_v      # disambiguate
Requires a built tree ($MCFM_HOME/Bin/CMakeFiles/libmcfm.dir/link.txt) and, for
the stage-2 reuse column, the Pepper clone ($PEPPER_HOME). Both are set by
environment.sh; see software/README.md.
"""
import collections
import glob as globmod
import os
import subprocess
import sys

_ROOT = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCFM = os.environ.get("MCFM_HOME", _ROOT + "/software/mcfm")
BINDIR = MCFM + "/Bin"
LINKTXT = BINDIR + "/CMakeFiles/libmcfm.dir/link.txt"
PEPPER = os.environ.get("PEPPER_HOME", _ROOT + "/software/pepper")
KERNELS = PEPPER + "/src/mcfm_analytics"


def base_key(path):
    """Extension-independent key: src/Z/qqb_z.cpp == src/Z/qqb_z.f"""
    p = path.strip().rstrip(",")
    for ext in (".cpp", ".cxx", ".f90", ".F90", ".f", ".F", ".hpp", ".h"):
        if p.endswith(ext):
            p = p[: -len(ext)]
            break
    return p


def kokkos_provenance():
    """base_key -> list of (pepper header, partial?) claiming to port it."""
    ported = collections.defaultdict(list)
    for h in sorted(globmod.glob(KERNELS + "/**/*.h", recursive=True)):
        try:
            with open(h) as fh:
                text = fh.read()
        except OSError:
            continue
        for ln in text.splitlines():
            if "MCFM sources:" not in ln:
                continue
            for ent in ln.split("MCFM sources:", 1)[1].split(","):
                ent = ent.strip()
                if not ent:
                    continue
                partial = "(partial)" in ent
                key = base_key(ent.replace("(partial)", "").strip())
                ported[key].append((os.path.relpath(h, KERNELS), partial))
    return ported


def linked_objects():
    with open(LINKTXT) as fh:
        txt = fh.read()
    objs = [t for t in txt.split() if t.endswith(".o")]
    return [o if os.path.isabs(o) else os.path.join(BINDIR, o) for o in objs]


def nm_symbols(objs):
    """defined: symbol -> object; undefined: object -> set(symbols)."""
    defined, undef = {}, collections.defaultdict(set)
    out = subprocess.run(["nm", "-g"] + objs, capture_output=True, text=True).stdout
    cur = None
    for ln in out.splitlines():
        if ln.endswith(":") and (".o" in ln):
            cur = ln[:-1]
        elif cur and ln.strip():
            parts = ln.split()
            if len(parts) >= 2 and parts[-2] == "U":
                undef[cur].add(parts[-1])
            elif len(parts) >= 3 and parts[-2] in ("T", "D", "S"):
                defined.setdefault(parts[-1], cur)
    return defined, undef


def rel(obj):
    i = obj.find("objlib.dir/")
    return obj[i + len("objlib.dir/"):-2] if i >= 0 else os.path.basename(obj)[:-2]


def lang(obj):
    r = rel(obj)
    if r.endswith(".cpp") or r.endswith(".cxx"):
        return "cpp"
    if "_fi.F90" in r or "_fi.f" in r:
        return "fi"
    return "FORTRAN"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    entry = sys.argv[1]
    objs = linked_objects()
    defined, undef = nm_symbols(objs)

    base = os.path.basename(entry)
    starts = [o for o in objs
              if os.path.basename(o).split(".")[0] in (base, base + "_fi")
              and (entry in rel(o) or "/" not in entry)]
    if not starts:
        starts = [o for o in objs if os.path.basename(o).startswith(base)]
    if not starts:
        sys.exit(f"no linked object matches '{entry}'")

    depth = {o: 0 for o in starts}
    queue = list(starts)
    while queue:
        o = queue.pop(0)
        for sym in sorted(undef.get(o, ())):
            d = defined.get(sym)
            if d and d not in depth:
                depth[d] = depth[o] + 1
                queue.append(d)

    ported = kokkos_provenance()
    print(f"# symbol closure of {entry}: {len(depth)} linked object(s)")
    print("# depth\tlang\tkokkos\tsource")
    gaps = 0
    nported = npartial = 0
    for o in sorted(depth, key=lambda k: (depth[k], rel(k))):
        lg = lang(o)
        gaps += lg == "FORTRAN"
        claims = ported.get(base_key(rel(o)), [])
        if claims:
            partial = all(p for _, p in claims)
            npartial += partial
            nported += not partial
            kk = ("partial: " if partial else "ported: ") + claims[0][0]
        else:
            kk = "-"
        print(f"{depth[o]}\t{lg}\t{kk}\t{rel(o)}")
    if gaps:
        print(f"# WARNING: {gaps} plain-Fortran object(s) in the closure -> "
              f"stage-1 gaps for a Kokkos port.")
    print(f"# stage-1 readiness: {len(depth) - gaps}/{len(depth)} objects are "
          f"C++ -> {'READY' if gaps == 0 else 'BLOCKED'} for stage 2")
    print(f"# stage-2 reuse: {nported} file(s) fully ported, {npartial} "
          f"partially ported in mcfm_analytics (from '// MCFM sources:' lines)")
    print("# NOTE: 'fi' shims are expected; grep each for retained Fortran "
          "bodies (functions beyond the bind(C) interface).")


if __name__ == "__main__":
    main()
