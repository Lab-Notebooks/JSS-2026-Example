#!/usr/bin/env python3
"""Closure tool — the transitive call tree of an MCFM routine, from linked objects.

The completeness cross-check for the stage-2 Split phase. An agent maps a call tree
by reading source; this tool derives it from the *build itself*: every linked
object's undefined symbols are its real callees, resolved against the objects
actually in libmcfm's link line. Symbols do not lie — a closure file missing from a
split plan is either a missed callee or must be justified as off-path.

(The Doxygen roadmap from the Index tool is not used here: many of its per-file XMLs
are empty stubs, so it cannot certify completeness. It is fine for ranking stage-1
leaves; it is not an authority for stage-2 coverage.)

Language tags show stage-1 state: cpp (translated), fi (iso_c_binding shim), FORTRAN
(a plain object still in the closure = a stage-1 gap). The 'kokkos' column reads the
`// MCFM sources:` provenance line every ported header carries, to show reuse.

Usage: calltree_closure.py qqb_z2jet_v   (needs a built tree; $MCFM_HOME, $PEPPER_HOME)
"""
import collections, glob, os, subprocess, sys

ROOT    = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MCFM    = os.environ.get("MCFM_HOME", ROOT + "/software/mcfm")
BINDIR  = MCFM + "/Bin"
LINKTXT = BINDIR + "/CMakeFiles/libmcfm.dir/link.txt"
KERNELS = os.environ.get("PEPPER_HOME", ROOT + "/software/pepper") + "/src/mcfm_analytics"


def base_key(path):
    p = path.strip().rstrip(",")
    for ext in (".cpp", ".cxx", ".f90", ".F90", ".f", ".F", ".hpp", ".h"):
        if p.endswith(ext):
            return p[:-len(ext)]
    return p


def rel(obj):
    i = obj.find("objlib.dir/")
    return obj[i + len("objlib.dir/"):-2] if i >= 0 else os.path.basename(obj)[:-2]


def lang(obj):
    r = rel(obj)
    if r.endswith((".cpp", ".cxx")): return "cpp"
    if "_fi.F90" in r or "_fi.f" in r: return "fi"
    return "FORTRAN"


def ported_sources():
    """base_key -> (header, partial?) for every already-ported kernel/fragment."""
    out = collections.defaultdict(list)
    for h in sorted(glob.glob(KERNELS + "/**/*.h", recursive=True)):
        try: text = open(h).read()
        except OSError: continue
        for ln in text.splitlines():
            if "MCFM sources:" not in ln: continue
            for ent in ln.split("MCFM sources:", 1)[1].split(","):
                ent = ent.strip()
                if ent:
                    out[base_key(ent.replace("(partial)", "").strip())].append(
                        (os.path.relpath(h, KERNELS), "(partial)" in ent))
    return out


def nm_symbols(objs):
    """defined: symbol -> object ; undef: object -> {symbols}."""
    defined, undef = {}, collections.defaultdict(set)
    out = subprocess.run(["nm", "-g"] + objs, capture_output=True, text=True).stdout
    cur = None
    for ln in out.splitlines():
        if ln.endswith(":") and ".o" in ln:
            cur = ln[:-1]
        elif cur and ln.strip():
            parts = ln.split()
            if len(parts) >= 2 and parts[-2] == "U":
                undef[cur].add(parts[-1])
            elif len(parts) >= 3 and parts[-2] in ("T", "D", "S"):
                defined.setdefault(parts[-1], cur)
    return defined, undef


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    entry = sys.argv[1]
    objs = [o if os.path.isabs(o) else os.path.join(BINDIR, o)
            for o in open(LINKTXT).read().split() if o.endswith(".o")]
    defined, undef = nm_symbols(objs)

    base = os.path.basename(entry)
    starts = [o for o in objs if os.path.basename(o).split(".")[0] in (base, base + "_fi")]
    if not starts:
        sys.exit(f"no linked object matches '{entry}'")

    # BFS over undefined-symbol edges: object -> the objects that define its callees.
    depth = {o: 0 for o in starts}
    queue = list(starts)
    while queue:
        o = queue.pop(0)
        for sym in undef.get(o, ()):
            d = defined.get(sym)
            if d and d not in depth:
                depth[d] = depth[o] + 1
                queue.append(d)

    ported, gaps = ported_sources(), 0
    print(f"# symbol closure of {entry}: {len(depth)} linked object(s)")
    print("# depth\tlang\tkokkos\tsource")
    for o in sorted(depth, key=lambda k: (depth[k], rel(k))):
        lg = lang(o); gaps += lg == "FORTRAN"
        claims = ported.get(base_key(rel(o)), [])
        kk = "-" if not claims else ("partial: " if all(p for _, p in claims) else "ported: ") + claims[0][0]
        print(f"{depth[o]}\t{lg}\t{kk}\t{rel(o)}")
    if gaps:
        print(f"# WARNING: {gaps} plain-Fortran object(s) in the closure -> stage-1 gaps.")
    print(f"# stage-1 readiness: {len(depth) - gaps}/{len(depth)} objects are C++ -> "
          f"{'READY' if gaps == 0 else 'BLOCKED'} for stage 2")


if __name__ == "__main__":
    main()
