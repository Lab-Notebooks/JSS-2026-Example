# Spec — Fortran → C++ translation of MCFM

This is the **Spec** for the stage-1 transformation: the correctness
specification that defines the target code and what "done" means *before any
agent runs* (paper principle P1). It is orchestrator-agnostic — the Claude Code
workflow and the CodeScribe loop both read this same file. It is the single
source of truth for *how* to translate; skills and workflows point here rather
than restating it.

A translation is **verified** only when a benchmark actually exercises it and the
coverage probe fires (§6). Everything else is **translated** (unverified) — say
so explicitly; never claim correctness for it.

Paths use `$MCFM_HOME` (the MCFM clone; `source environment.sh` sets it). Files
are relative to `$MCFM_HOME/src`.

---

## §1 Conventions — output files per source file

### 1.1 General convention (most directories)

One new translation unit per Fortran file, replacing the `.f`/`.f90` in the
directory's `CMakeLists.txt`:

- **`<base>.cpp`** — the C++ implementation plus an `extern "C" <base>_wrapper(...)`
  that exposes it to Fortran (raw pointers in, `FArray` views built inside the
  wrapper).
- **`<base>.hpp`** — the C++ header (signature + include guard), so sibling C++
  files can call it directly.
- **`<base>_fi.F90`** — a free-form `iso_c_binding` interface: a Fortran
  subroutine of the original name whose body declares the inner `bind(C)`
  interface and calls `<base>_wrapper`. This keeps every Fortran caller working
  unchanged during the incremental migration.

### 1.2 `src/gghgg_dep` precision-split convention (different — read §4.I)

Every file in `src/gghgg_dep` is a Fortran module `<name>_generic` exposing a
generic interface over a DOUBLE-precision procedure `<name>` and a QUAD-precision
`<name>_qp`, both sharing one body `include 'Inc/<name>_inc.f'`. The benchmark
(`g g h g g`) uses only the double path, but the quad procedures are still
compiled into `libmcfm`, so they must stay:

- Translate the **dp path only** to `<base>.cpp` (impl + `extern "C" <base>_wrapper`,
  **no `.hpp`** — callers forward-declare it).
- Keep the **qp path as Fortran** in a fixed-form `<base>_fi.f` shim (note: `.f`,
  not `.F90`) that re-exposes the `<name>_generic` module: a dp forwarder calling
  the C++ wrapper, plus the unchanged qp procedure `include 'Inc/<name>_inc.f'`.
- The `Inc/*_inc.f` bodies are **not** independently translated; they stay on disk
  for the qp path.

Full recipe and structural variants are in §4.I.

---

## §2 Translation rules

Apply line-by-line; do not add function declarations, a `main`, or any symbol the
source does not define.

1. **Subroutine/function → C++ function.** Replace
   ```fortran
   use <module-name>
   subroutine <func-name>(xw)
      real(dp):: xw
      ...
   end subroutine
   ```
   with
   ```cpp
   #include <module-name.hpp>
   using namespace <module-name>;

   void <func-name>(double& xw) {
      ...
      return;
   }

   extern "C" {
      void <func-name>_wrapper(double* xw) { <func-name>(*xw); }
   }
   ```

2. **Module `use` lines → includes.** Each `use <module-name>` becomes
   `#include <module-name.hpp>` plus `using namespace <module-name>;`. Module-level
   data (constants, couplings, `nf`, `mxpart`, …) is available through those
   headers. This applies ONLY to module data — NOT to outputs of called
   subroutines, nor to routines defined in other files (see rule 9a). Ignore
   `use types` and other irrelevant modules.

3. **Types and arrays.**
   - `real(dp)` → `double`; `complex(dp)` → `std::complex<double>` (`#include <complex>`).
   - Fortran arrays → `FArray` templates with Fortran-like indexing:
     `real(dp), dimension(nx,ny) :: a` becomes `FArray2D<double> a(nx, ny);`.
     `#include <FArray.hpp>`; use `FArray1D`/`FArray2D`/`FArray3D`/`FArray4D` per
     dimensionality. There is **no `FArray5D`/`FArray6D`** — for D≥5 use a flat
     `std::complex<double>[N]` with an index lambda (see §4.D1, §4.I).

4. **Argument intent.** `intent(in)`/`intent(inout)` scalar args pass by reference:
   `real(dp), intent(in) :: a` → `double& a`.

5. **Statement functions** → C++ lambdas.

6. **Complex arithmetic** maps to `std::complex<double>`.

7. **Returns.** End the C++ function with `return;` to mirror the Fortran `return`.

8. **C wrappers.** In the `extern "C"` block, emit `<func-name>_wrapper` that
   converts C/Fortran data (especially arrays → FArray views) and calls the C++
   function. Always the `_wrapper` suffix.

9. **Fortran interface (`<base>_fi.F90`).** A subroutine of the original name with
   an inner `bind(C)` interface to `<func-name>_wrapper`, then
   `call <func-name>_wrapper(args)`. See §3 for the full shape. In the inner
   interface block, array args must be assumed-size `dimension(*)` (see §4.A1).

9a. **CROSS-FILE CALLS — never fabricate the called symbol.** The file often calls
   routines DEFINED IN OTHER FILES whose signature you are not shown. Do NOT invent
   accessors, helpers, or globals to stand in for a called routine or its outputs.
   Keep every `call` that exists; add none that do not. Resolve each call by whether
   the dependency is already translated:
   - **(A) dep has a `<dep>.cpp` sibling** → call its C++ function DIRECTLY. With a
     `.hpp`: `#include "<dep>.hpp"` (QUOTED) and call matching its signature. For
     `gghgg_dep` (no `.hpp`): forward-declare the child at the top of your `.cpp`.
     Do NOT call a translated sibling through its `_wrapper` or `_fi` symbol.
   - **(B) dep is still Fortran** (only `<dep>.f`, or a library routine) → a FREE
     Fortran subroutine has ABI `<name>_` (lowercase + single trailing underscore):
     `extern "C" void <name>_(/* every arg a pointer */);` and call
     `<name>_(&a1, &a2, …)`. Results are written back through those pointers. A
     function used in an expression: `extern "C" <return-type> <name>_(...);`
     (complex return → `std::complex<double>`). Pass scalars by pointer, arrays as
     the underlying pointer (`za.data()` or `&za(1,1)`). For a character/string arg
     use the Fortran hidden-length convention (§4.F1). Do NOT guess a
     module-mangled name (`__mod_MOD_name`) — if the dep is a module function with
     no C binding, it is a real blocker: translate the dep first.

10. **Module conversion.** If the input is a Fortran MODULE, produce three outputs
    (`.hpp`/`.cpp`/`_fi.f90`):
    - **Header:** include guard `<MODNAME>_MOD`; declarations inside
      `namespace <module-name>`; scalars become `extern`; arrays become
      `extern FArrayND<...>` (`#include <FArray.hpp>`).
    - **Source:** define the `extern` variables inside the namespace; construct
      FArray arrays with sizes and lower bounds from the Fortran declaration (e.g.
      `real(dp) :: mqq(0:2,-nf:nf,-nf:nf)` → `FArray3D<double> mqq(3, 2*nf+1, 2*nf+1, 0, -nf, -nf);`);
      provide `extern "C"` accessors returning pointers to each variable.
    - **Interface (`_fi.f90`):** same module name, `iso_c_binding`; an interface
      returning `type(c_ptr)` per accessor; Fortran `pointer` objects mirroring the
      C variables; `<modname>_init` binding them with `c_f_pointer`;
      `<modname>_finalize` nullifying them. See §3.2.

---

## §3 Worked examples

### 3.1 Subroutine

Source:
```fortran
subroutine example(a,b,c,d)
   use types
   use constants_mod
   use nf_mod
   use zcouple_mod
   use ewcharge_mod
   implicit none
   real(dp) :: a
   real(dp), dimension(-nf:nf) :: b
   real(dp), intent(in), dimension(mxpart,4) :: c
   real(dp), intent(inout), dimension(mxpart,mxpart) :: d
   integer :: i,j
   real(dp), dimension(nf,4) :: temp
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
```

Header `example.hpp`:
```cpp
#ifndef EXAMPLE_H
#define EXAMPLE_H
#include <constants_mod.hpp>
#include <nf_mod.hpp>
#include <zcouple_mod.hpp>
#include <ewcharge_mod.hpp>
#include <FArray.hpp>
extern void example(double a, FArray1D<double>& b, FArray2D<double>& c, FArray2D<double>& d);
#endif
```

Source `example.cpp` (include the DIRECT module headers, per §4.B1 — not a bare
`<example.hpp>`):
```cpp
#include <constants_mod.hpp>
#include <nf_mod.hpp>
#include <zcouple_mod.hpp>
#include <ewcharge_mod.hpp>
#include <FArray.hpp>
void example(double a, FArray1D<double>& b, FArray2D<double>& c, FArray2D<double>& d) {
   using namespace constants_mod;
   using namespace nf_mod;
   using namespace zcouple_mod;
   using namespace ewcharge_mod;
   FArray2D<double> temp(nf,4);
   for(int i=-nf; i<=nf; i++) {
      b(i) = 0.0;
   }
   for(int i=2; i<=10; i++) {
      for(int j=1; j<i; j++) {
         c(j,2) = d(i,j);
      }
   }
   return;
}
extern "C" {
   void example_wrapper(double a, double* fb, double* fc, double* fd) {
      using namespace mxpart_mod;
      FArray1D<double> b(fb, 2*nf+1, -nf);
      FArray2D<double> c(fc, mxpart, 4);
      FArray2D<double> d(fd, mxpart, mxpart);
      example(a, b, c, d);
   }
}
```

Interface `example_fi.F90`:
```fortran
subroutine example(a,b,c,d)
   use, intrinsic :: iso_c_binding
   use constants_mod
   use nf_mod
   use zcouple_mod
   use ewcharge_mod
   implicit none
   real(c_double), intent(inout) :: a
   real(c_double), dimension(-nf:nf), intent(inout) :: b
   real(c_double), dimension(mxpart,4), intent(in) :: c
   real(c_double), dimension(mxpart,mxpart), intent(inout) :: d
   interface
      subroutine example_wrapper(a,b,c,d) bind(C, name="example_wrapper")
         import :: c_double
         real(c_double), value :: a
         real(c_double), dimension(*), intent(inout) :: b   ! §4.A1: assumed-size
         real(c_double), dimension(*), intent(in) :: c
         real(c_double), dimension(*), intent(inout) :: d
      end subroutine example_wrapper
   end interface
   call example_wrapper(a,b,c,d)
end subroutine example
```

### 3.2 Module

Source:
```fortran
module qcdcouple_mod
   use types
   implicit none
   public
   real(dp):: gsq,as,ason2pi,ason4pi
   save
end module
```

Follow the rule-10 pattern: `namespace qcdcouple_mod { extern double gsq, as, ason2pi, ason4pi; }`
in the `.hpp`; the matching definitions plus `extern "C"` pointer accessors
(`double* qcdcouple_mod_gsq() { return &qcdcouple_mod::gsq; }`) in the `.cpp`; and
a `_fi.f90` module declaring one `type(c_ptr)` interface per accessor, mirroring
each variable as a `real(c_double), pointer`, binding them in `qcdcouple_mod_init`
with `c_f_pointer` (nullify in `qcdcouple_mod_finalize`). Match a verified sibling
module in `src/Mods`.

---

## §4 Fixups and gotchas checklist

Apply as a self-review on **every** file. A defect is **silent** (builds, may even
pass the benchmark, yet is wrong) unless marked otherwise — silent ones are
exactly why the §6 coverage probe is mandatory before marking anything verified.
Each was seen on a real file.

### A. Interface file (`_fi.F90` / `_fi.f`)

- **A1. `dimension(mxpart,mxpart)` inside the inner `bind(C)` interface block**
  *(compile error `Variable 'mxpart' cannot appear in the expression`)*. An
  `interface` block has its own scope; `mxpart` is not visible there. **Fix:**
  declare array args assumed-size in the inner interface —
  `complex(c_double_complex), dimension(*), intent(in) :: za, zb`. The OUTER
  subroutine keeps `dimension(mxpart,mxpart)`.

### B. Includes / headers (`.cpp`)

- **B1. Include the DIRECT module headers, not just a self-header** *(else compile
  error `'<base>.hpp' file not found` or undefined module symbols)*. The `src/`
  process subdirs are not on the compiler include path, so a bare
  `#include <base.hpp>` does not resolve and does not pull in what the routine
  needs. In the `.cpp`, include the module headers derived from the Fortran `use`
  lines, plus `<cmath>`, `<complex>`, `<FArray.hpp>` as needed. Compare a verified
  sibling.
- **B2. Missing `#include <Need.hpp>`** *(undefined loop/log helper)*. Add it if
  the routine calls any of: `lnrat, L0, L1, L2, L0old, L1old, Ls0, Ls1, Ls2, Ls3,
  Lsm1*, i3m, cplx1, cplx2, spinoru, dot, dotpr, dotvec, massvec`.
- **B3. Cross-directory sibling header not on the include path** *(compile error
  `'<dep>.hpp' file not found` when calling an already-translated sibling in
  another `src/` subdir)*. **Fix:** add the dependency's directory to
  `target_include_directories(objlib …)` in the top-level `CMakeLists.txt`,
  rebuild, re-verify. *(Integrator action — authors report the missing dir, they do
  not edit shared CMake.)*
- **B4. Header signature disagrees with its own `.cpp`** *(link error at the FIRST
  cross-file caller; latent for months)*. Make the header match the `.cpp`. When you
  translate the first caller of a dep, sanity-check the dep's `.hpp` vs its `.cpp`.

### C. Keep every `call` (SILENT if you drop one)

Rule 9a as a self-check: do not "simplify away" a `call` whose outputs you do not
otherwise see used, and do not skip one of a pair of near-identical calls. A
dropped call leaves outputs uninitialized or drifts the benchmark, and it builds
clean.

- **The public/core split is the easy one to get wrong.** A public routine over a
  `<name>core` worker keeps a helicity-reflection loop and must call BOTH
  `<name>core(za,zb)` AND the reflected `<name>core(zb,za)` (note the za/zb swap).
  Dropping either leaves the output zero/partial.

### D. `FArray` usage

- **D1. There is no `FArray5D`/`FArray6D`.** The template only goes to 4D. For a
  ≥5-D Fortran array use a flat `std::complex<double>[N]` with an index lambda.
- **D2. Construct an existing-array `FArray4D` with all four dims, 1-based:**
  `FArray4D<...> A(ptr, d1, d2, d3, d4);`. Passing only three sizes binds the 4th to
  `start_i` and shifts the whole buffer by one slot — a silent, layout-corrupting
  bug (see E2 cause A).
- **D3. Only the public routine needs a `_wrapper` + `_fi` subroutine.** A `core`
  worker called only internally is plain C++ with no wrapper/interface.
- **D4. `FArray::fill()` on a negative-offset array can be a SILENT no-op.** An old
  `fill()` looped `for (size_t i = start_i; i < ni + start_i; …)`; with
  `start_i = -nf` the `size_t` counter wraps and the body never runs, so
  `msqv.fill(0.0)` on an `-nf:nf` array zeroed nothing. It bit routines that (a)
  have a negative lower bound AND (b) rely on `fill()` to zero a buffer the caller
  reuses. Fill flat over the contiguous `data`. If a routine is correct on its
  first call but drifts when a benchmark calls it repeatedly, suspect a
  stale-buffer zeroing bug like this.

### E. Algebraic mistranslations (SILENT — caught only by the benchmark)

- **E1. Missing parentheses in a rational term.** Fortran `)/za(j1,j2)*za(j1,j2)`
  means divide by `za²`, but C++ left-to-right makes it `(…/za)*za`. **Fix:**
  parenthesize the denominator: `)/(za(j1,j2)*za(j1,j2))`. Review every
  division/`pow` for precedence.
- **E2. "Outputs match yet the benchmark regresses."** Two causes:
  - **Cause A — output-buffer LAYOUT** (e.g. the 3-dim `FArray4D` shift in D2):
    correct values written to the wrong physical slots. Dump the array **as the
    caller reads it** (raw column-major), not via the producer's accessor.
  - **Cause B — a missing/extra shared-state write** (module/common data written as
    a side effect). Only after the physical buffer is proven identical, compare every
    module/common variable the Fortran touches against the C++.
  The §6 coverage probe catches either.

### F. Strings and bounds

- **F1. C string length / null terminator** on a `character*N` arg. Build the C++
  side to the Fortran length with no null: `string st(st_in, 9)` for `character*9`.
- **F2. Out-of-bounds write (0-based vs 1-based).** Do not write index 0 of a
  Fortran 1-based array.
- **F2b. 0-based fill loop over a 1-based `FArray2D` (SILENT underflow).** Make loops
  1-based (`for(i=1;i<=2;++i)`); ensure every `FArray` subscript lands in `[1,N]`.
  Leave genuine 0-based plain-C scratch arrays alone.

### G. Helper subroutines defined INSIDE the translated file (build break for siblings)

One MCFM `.f` often defines the public subroutine **plus several free helper
subroutines** that *other* files call via `extern "C" <name>_`. Translating the
public routine removes those Fortran symbols and breaks the sibling's link.
**Fix:** before translating, `grep` the file for every `subroutine`/`function` it
defines and check `grep -rl <name> $MCFM_HOME/src` for outside callers. Keep
still-needed helpers as Fortran by moving their verbatim definitions into
`<base>_fi.F90` (convert fixed-form to free-form).

### H. Coverage-probe FALSE NEGATIVE — an extracted inline sub-expression reads off-path until its caller lands

A small leaf builds/links/passes but its coverage probe (scale return by 1.5×)
leaves every ratio UNCHANGED, so you mark it TRANSLATED. Later, after translating
the routine that *uses* it, the SAME leaf probes BROKEN → VERIFIED. **Cause:** in
MCFM a "function" is often an inline sub-expression of a still-Fortran caller, not
a call — while the caller is Fortran it computes the term inline and never calls
your C++ leaf. **Rule:** a leaf that probes UNCHANGED is only provisionally
off-path; re-probe it after its caller becomes C++ before trusting the TRANSLATED
verdict. Do not conclude a whole chain is off-benchmark from leaf probes alone.

### I. `src/gghgg_dep` generic dp/qp module pattern (translate dp → C++, KEEP qp Fortran)

- **`<base>.cpp`** — translate ONLY the dp body. Signature mirrors the Fortran
  function's args plus threaded module data:
  `std::complex<double> <name>(int p1.., FArray2D<std::complex<double>>& za, zb, FArray2D<double>& s)`,
  plus `extern "C" void <name>_wrapper(...raw ptrs..., res_ptr)`. Includes:
  `<cmath>`, `<complex>`, `<FArray.hpp>`, and `"gghgg_consts.hpp"` (QUOTED). In-closure
  deps are called case-A (direct C++, pass `za,zb,s` down); QCDLoop via `extern "C"`.
  **No `.hpp`** — callers forward-declare the child and call it passing `(p1..p4,za,zb,s)`.
- **`<base>_fi.f`** — MUST be fixed-form `.f`, NOT `.F90`. The module redeclares the
  generic interface; the dp procedure forwards to the C++ wrapper passing module
  array `s` by reference; the qp procedure is the unchanged original
  (`include 'Inc/<name>_inc.f'`). Inner `bind(C)` interface: `za,zb,s` are
  `dimension(*)` assumed-size, `res` scalar.
- **No module-storage bridge.** The dp forwarder `use sprod_dp` already sees `s` and
  threads it down as a pointer. `gghgg_consts.hpp` supplies named constants — if one
  is missing, report it (the integrator adds it once); do NOT edit it yourself.
- **`Inc/*_inc.f` are NOT independently translated.**
- **Structural variants** (match a verified sibling of the same family): clean leaf
  `(p1..p4,za,zb)`; D-simple leaf `(p1..p4,mtsq,za,zb)`; helicity amps filling
  `Dcoeff/Ccoeff/Bcoeff`; roots returning squared ME `msq`; QCDLoop leaves calling
  `qli2/qli3/qli4` via `#include <Loop.hpp>`.

### Real blockers (NOT fixups — translate the dependency first)

When the build fails because a *called* routine is itself an untranslated **module**
function with no C binding (only `__mod_MOD_name` exists), do not guess the ABI.
Translate the dependency first. The dependency graph (§5 / the workflow's resolve
phase) prevents this by only offering files whose callees are already translated
(`deps==0`).

---

## §5 Directory → benchmark mapping

A translation is **verified** only if a benchmark exercises it. Map the file's
top-level `src/` directory to a `./test -b` process:

| Directory | `./test -b` process |
|-----------|---------------------|
| W | `u d~ ve e+` |
| W1jet | `u d~ ve e+ g` |
| W2jet, BDK, loop | `u d~ ve e+ g g` (also `u u~ e- e+ g g`) |
| Z | `u u~ e- e+` |
| Z1jet | `u u~ e- e+ g` |
| Z2jet | `u u~ e- e+ g g` |
| ThreeJets | `g g g g g` |
| ggH | `g g h` |
| gghgg_dep | `g g h g g` |
| Mods, Need, Inc, Procdep | (infrastructure — no direct benchmark; mark TRANSLATED, not VERIFIED) |

A file in a directory with no benchmark is **translated but unverified**. This
table is also encoded in `dev/tools/index/build_roadmap.py` (the `BENCH` dict).

---

## §6 Verification and the coverage probe

Build and benchmark in `$MCFM_HOME/Bin`:

```bash
source "$PROJECT_HOME/environment.sh"
cd "$MCFM_HOME/Bin" && cmake . >/dev/null && make install 2>&1 | tail -40
./test -b <process>        # records four ratios: Finite / IR / IR2 / Born
```

A translation passes only when all four ratios match within **1e-13**. Confirm
linkage with `nm libmcfm.* | grep -i <name>` (look for `_<name>_wrapper`).

**Coverage probe — MANDATORY before calling any file VERIFIED.** A passing
benchmark is necessary but NOT sufficient: the frozen benchmark momenta may never
reach the routine. Probe it:

1. Temporarily multiply the file's main amplitude output by 1.5.
2. Rebuild (single-file relink) and re-run the passing process(es).
3. If ratios BREAK far beyond 1e-13, the file is exercised → revert the 1.5×,
   rebuild to confirm PASS, mark **VERIFIED**.
4. If ratios are UNCHANGED, the benchmark does not reach it → mark **TRANSLATED**
   (unverified). See §4.H: re-probe after the caller lands.

Always revert every probe edit and leave the tree building clean and passing.
Probe files individually; batch only if you can still attribute which file moved
which ratio.

**Expected precision:** amplitudes using complex powers show ~1e-15 ratio
deviations (C++ `std::pow` vs Fortran `**`); this is normal and well within
tolerance.

This §6 is the **verification bar**: the workflow's serial Integrate phase applies
it, and the CodeScribe reference loop's review phase would apply the same bar. Record
per-file outcomes (verified / translated / failed) in the Plan
(`current_plan.md`), not in this Spec.
