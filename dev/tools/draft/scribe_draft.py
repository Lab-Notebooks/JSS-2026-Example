"""Draft tool — a mechanical first cut of one Fortran file, with hints.

  python3 scribe_draft.py <file.f> [--index PATH] [-o OUT] [--force] [--stdout]
  python3 scribe_draft.py --seed          print the few-shot seed examples

Given a Fortran source and the symbol index (from build_roadmap.py), it writes a
`<base>.scribe` draft: a block of `scribe-prompt:` hints plus a rough mechanical
conversion (use -> using namespace, real -> double, dimension -> FArray, x**n -> pow).
The hints flag which called names are defined in other files, so the Author agent does
not fabricate them. The draft is scaffolding; the agent reads it with the seed examples
(--seed) and the Spec, then writes the real translation.

Default output: dev/tmp/drafts/<path-below-src>.scribe (git-ignored scratch).
"""
import argparse, json, os, re, sys

RE_USE  = re.compile(r"^\s*use\s+(\w+)", re.I)
RE_CALL = re.compile(r"^\s*call\s+(\w+)", re.I)
RE_NAME = re.compile(r"\b(\w+)\s*\(")

# Few-shot seed for Fortran -> C++. The translation *rules* live in the Spec; this only
# shows the output shape: one subroutine and one module, each -> a C++ header
# (<cheader>), C++ source (<csource>), Fortran interface (<fsource>).
SEED = """
[[chat.user]]
content = '''
You convert one Fortran file to C++ following the rules in the Spec. Keep every call,
invent no symbol, and emit the code between <cheader>/<csource>/<fsource> tags. The
input arrives under <source> tags, with an optional machine draft under <draft>.
When you understand, reply: I am ready.
'''

[[chat.assistant]]
content = '''
I am ready.
'''

[[chat.user]]
content = '''
<source>
subroutine example(a,b,c,d)
   use constants_mod
   use nf_mod
   implicit none
   real(dp) :: a
   real(dp), dimension(-nf:nf) :: b
   real(dp), intent(in), dimension(mxpart,4) :: c
   real(dp), intent(inout), dimension(mxpart,mxpart) :: d
   integer :: i,j
   do i=-nf,nf
      b(i) = 0.
   end do
   do i=2,10
   do j=1,i-1
      c(j,2) = d(i,j)
   end do
   end do
   return
end subroutine example
</source>
'''

[[chat.assistant]]
content = '''
<cheader>
#ifndef EXAMPLE_H
#define EXAMPLE_H
#include <constants_mod.hpp>
#include <nf_mod.hpp>
#include <FArray.hpp>
extern void example(double a, FArray1D<double>& b, FArray2D<double>& c, FArray2D<double>& d);
#endif
</cheader>

<csource>
#include <constants_mod.hpp>
#include <nf_mod.hpp>
#include <FArray.hpp>
void example(double a, FArray1D<double>& b, FArray2D<double>& c, FArray2D<double>& d) {
   using namespace nf_mod;
   for(int i=-nf; i<=nf; i++) b(i) = 0.0;
   for(int i=2; i<=10; i++)
      for(int j=1; j<i; j++) c(j,2) = d(i,j);
   return;
}
extern "C" {
   void example_wrapper(double a, double* fb, double* fc, double* fd) {
      using namespace nf_mod; using namespace mxpart_mod;
      FArray1D<double> b(fb, 2*nf+1, -nf);
      FArray2D<double> c(fc, mxpart, 4);
      FArray2D<double> d(fd, mxpart, mxpart);
      example(a, b, c, d);
   }
}
</csource>

<fsource>
subroutine example(a,b,c,d)
   use, intrinsic :: iso_c_binding
   use nf_mod
   implicit none
   real(c_double), intent(inout) :: a
   real(c_double), dimension(-nf:nf), intent(inout) :: b
   real(c_double), dimension(mxpart,4), intent(in) :: c
   real(c_double), dimension(mxpart,mxpart), intent(inout) :: d
   interface
      subroutine example_wrapper(a,b,c,d) bind(C, name="example_wrapper")
         import :: c_double
         real(c_double), value :: a
         real(c_double), dimension(*), intent(inout) :: b   ! assumed-size in the inner interface
         real(c_double), dimension(*), intent(in) :: c
         real(c_double), dimension(*), intent(inout) :: d
      end subroutine example_wrapper
   end interface
   call example_wrapper(a,b,c,d)
end subroutine example
</fsource>
'''

[[chat.user]]
content = '''
Correct. Now the module case:

<source>
module qcdcouple_mod
   use types
   implicit none
   public
   real(dp):: gsq,as
   save
end module
</source>
'''

[[chat.assistant]]
content = '''
<cheader>
#ifndef QCDCOUPLE_MOD
#define QCDCOUPLE_MOD
namespace qcdcouple_mod { extern double gsq, as; }
#endif
</cheader>

<csource>
#include <qcdcouple_mod.hpp>
namespace qcdcouple_mod { double gsq, as; }
extern "C" {
   double* qcdcouple_mod_gsq() { return &qcdcouple_mod::gsq; }
   double* qcdcouple_mod_as()  { return &qcdcouple_mod::as; }
}
</csource>

<fsource>
module qcdcouple_mod
   use, intrinsic :: iso_c_binding
   implicit none
   private
   interface
      function get_gsq() bind(C, name="qcdcouple_mod_gsq")
         import :: c_ptr ; type(c_ptr) :: get_gsq
      end function
      function get_as() bind(C, name="qcdcouple_mod_as")
         import :: c_ptr ; type(c_ptr) :: get_as
      end function
   end interface
   public :: gsq, as, qcdcouple_mod_init, qcdcouple_mod_finalize
   real(c_double), pointer :: gsq, as
contains
   subroutine qcdcouple_mod_init()
      call c_f_pointer(get_gsq(), gsq)
      call c_f_pointer(get_as(), as)
   end subroutine
   subroutine qcdcouple_mod_finalize()
      nullify(gsq, as)
   end subroutine
end module qcdcouple_mod
</fsource>
'''

[[chat.user]]
content = '''
Correct. Now convert the following similarly:
'''
""".lstrip()


def external_hints(path, symbols):
    """Names this file calls that are defined in *other* files (rule 9a)."""
    used, self_base = set(), os.path.basename(path)
    with open(path, errors="replace") as fh:
        for line in fh:
            for m in (RE_USE.match(line), RE_CALL.match(line)):
                if m: used.add(m.group(1).lower())
            for name in RE_NAME.findall(line):
                used.add(name.lower())
    return {n: rel for n, rel in symbols.items()
            if n in used and os.path.basename(rel) != self_base}


def annotate(path, symbols):
    hints = [
        'scribe-prompt: Add an extern "C" <name>_wrapper; see the seed examples for FArray/scalar handling.',
        "scribe-prompt: A variable used as a function is an external or statement function.",
    ]
    for name, rel in sorted(external_hints(path, symbols).items()):
        hints.append(f"scribe-prompt: {name} is an external function (defined in {rel})")

    includes, body = {"#include <cmath>", "#include <complex>"}, []
    with open(path, errors="replace") as fh:
        for raw in fh:
            s = raw.strip(); low = s.lower()
            if low.startswith(("c ", "!")) and not low.startswith(("complex", "call")):
                continue
            u = RE_USE.match(s)
            if u:
                includes.add(f"#include <{u.group(1)}.hpp>")
                body.append(f"using namespace {u.group(1)};")
                continue
            line = re.sub(r"implicit none", "", raw)
            line = re.sub(r"\binteger\b", "int", line, flags=re.I)
            line = re.sub(r"\breal\s*(\([^)]*\))?", "double", line, flags=re.I)
            line = re.sub(r"\bcomplex\s*\(\s*dp\s*\)", "complex<double>", line, flags=re.I)
            line = re.sub(r"(?<!std)::", "", line)
            line = re.sub(r"\b(double|int|complex<[^>]+>)\s*,?\s*dimension\s*\((.*?)\)\s*(\w+)",
                          r"FArray<\1> \3(\2)", line, flags=re.I)
            line = re.sub(r"(\w+)\s*\*\*\s*(\d+)", r"pow(\1,\2)", line)
            body.append(line.rstrip())
    return "\n".join(hints) + "\n\n" + "\n".join(sorted(includes)) + "\n\n" + "\n".join(body) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fortran_file", nargs="?")
    ap.add_argument("--seed", action="store_true", help="print the few-shot seed and exit")
    ap.add_argument("--index", default=None)
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    if args.seed:
        sys.stdout.write(SEED); return
    if not args.fortran_file:
        ap.error("fortran_file is required (or use --seed)")

    src = os.path.abspath(args.fortran_file)
    if not os.path.isfile(src):
        sys.exit(f"error: file not found: {src}")

    project = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    index = args.index or os.path.join(project, "dev/tmp/assets/symbol_index.json")
    symbols = {}
    if os.path.isfile(index):
        with open(index) as fh:
            symbols = (json.load(fh) or {}).get("symbols", {})
    else:
        print(f"warning: no symbol index at {index} — run build_roadmap.py first; hints omitted", file=sys.stderr)

    draft = annotate(src, symbols)
    if args.stdout:
        sys.stdout.write(draft); return
    rel = src.split("/src/", 1)[1] if "/src/" in src else os.path.basename(src)
    out = args.output or os.path.join(project, "dev/tmp/drafts", os.path.splitext(rel)[0] + ".scribe")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and not args.force:
        print(f"skipping (exists): {out}  (use --force)"); return
    with open(out, "w") as fh:
        fh.write(draft)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
