# Fortran → C++: what a rewritten MCFM file must look like

The rules for what one rewritten MCFM file must look like, and how "correct" is defined.
This file is only the desired result and the correctness bar; how to run the step — the
helper programs, the running-command rules, which files to do next, and the notes across
sessions — lives in the Plan (`current_plan.md`).

Paths are written as `software/mcfm/src/...` (relative to the MCFM code).

---

## What each file turns into

One Fortran file becomes one C++ output, and its `.f`/`.f90` entry in the folder's
`CMakeLists.txt` is swapped for it:

- **`<base>.cpp`** — the C++ code, plus an `extern "C" <base>_wrapper(...)` so Fortran can
  still call it (raw pointers come in; `FArray` views are built inside the wrapper).
- **`<base>.hpp`** — the header, so other C++ files can call it directly.
- **`<base>_fi.F90`** — a small Fortran shim (an `iso_c_binding` interface): a Fortran
  subroutine with the *original* name that calls `<base>_wrapper`. This lets every existing
  Fortran caller keep working while you rewrite the code a bit at a time, instead of
  switching everything at once.

A Fortran **module** instead becomes a `.hpp` (a namespace of `extern` declarations), a
`.cpp` (the definitions plus `extern "C"` pointer accessors), and a `_fi.f90` that mirrors
each variable with `c_f_pointer`. Copy the shape of an already-done module in `src/Mods`.

---

## Rules for rewriting

Rewrite the body line by line. Don't add a `main`, extra declarations, or any name the
source doesn't already use.

| Fortran | C++ |
|---|---|
| `subroutine`/`function` | free function; add `<name>_wrapper` in an `extern "C"` block |
| `use <mod>` | `#include <mod.hpp>` + `using namespace <mod>;` (module *data* only) |
| `real(dp)` / `complex(dp)` | `double` / `std::complex<double>` |
| `dimension(nx,ny)` array | `FArray2D<double> a(nx, ny)` (1-based; `FArray1D…4D` only) |
| `intent(in/inout)` scalar | pass by reference (`double& a`) |
| statement function | C++ lambda |
| `x**n` | `pow(x, n)` |
| `return` | `return;` |

**The rule worth repeating — don't invent a called name.** A file usually calls routines
defined in *other* files whose signatures you can't see. Keep every `call` that is there;
invent none. Handle each one based on whether it has been rewritten yet:

- **Already C++** (a `<dep>.cpp` file exists) → call the C++ function directly:
  `#include "<dep>.hpp"` and match its signature.
- **Still Fortran** → call it the plain Fortran way: declare
  `extern "C" void <name>_(/* every arg a pointer */);` and call `<name>_(&a, &b, …)`,
  passing arrays as the underlying pointer. Results come back through the pointers.

If a called routine is in a module that isn't rewritten yet and has no C binding, that is a
real blocker — rewrite that dependency first, don't guess around it. The readiness map (the
Index program the Plan names) exists so a rewrite is only ever handed a file whose called
routines are already done.

A full worked example (a subroutine and a module, all three output files) is in the examples
the Draft tool prints: `dev/tools/draft/scribe_draft.py --seed`.

### Silent traps to self-check

Most rewriting bugs are *silent*: the code builds, links, and may even pass the test, but is
still wrong. Each one below happened on a real MCFM file. Use them as a self-check, and rely
on the coverage check (below) to catch what you miss.

1. **A dropped `call`.** Leaving out a call whose output you don't see used, or skipping one
   of a near-identical pair (a public routine often calls its `core` worker twice, once with
   the spinor arguments swapped). This leaves outputs unset, and it builds fine.
2. **Order of × and ÷.** Fortran `)/za*za` divides by `za²`; C++ goes left to right and
   makes it `(…/za)*za`. Put parentheses around every denominator.
3. **`FArray` sizes.** Build an existing array with *all* its sizes and 1-based bounds;
   giving too few sizes silently shifts the whole buffer. There is no `FArray5D` — for 5+
   dimensions, flatten it with an index lambda.
4. **0-based vs 1-based.** Don't write index 0 of a 1-based Fortran array; keep fill loops
   1-based so every index stays in `[1,N]`.
5. **Includes.** Include the module headers the `use` lines imply (not just the file's own
   header), plus `<Need.hpp>` for the loop/spinor helpers (`lnrat`, `L0`, `spinoru`, `dot`,
   …). A missing header from another folder means that folder needs a rewritten dependency
   first — don't edit shared CMake yourself.

If a number still disagrees after you've checked, mark it FAILED with the symptom instead of
guessing a fix — a small mismatch goes to a person.

---

## Which test covers which folder

A rewrite counts as verified only if a test actually runs it. Match the file's top-level
`src/` folder to a `./test -b` run:

| Directory | `./test -b` process |
|-----------|---------------------|
| W / W1jet / W2jet | `u d~ ve e+` (+ `g`, `g g`) |
| Z / Z1jet / Z2jet | `u u~ e- e+` (+ `g`, `g g`) |
| ThreeJets | `g g g g g` |
| ggH / gghgg_dep | `g g h` / `g g h g g` |
| Mods, Need, Inc, Procdep | infrastructure — no test; mark TRANSLATED |

A file in a folder with no test is **translated but not verified**. This table is also built
into the Index program (`dev/tools/index/build_roadmap.py`).

---

## The correctness bar

A rewrite passes only when the MCFM test that runs it matches to within **1e-13** (code that
uses complex powers can be off by about 1e-15 — that is normal and well inside the limit).
But a passing test is necessary, not sufficient: the fixed test inputs might never reach your
routine, so a test can report a match without ever running your code — which is what
`dev/tools/coverage/coverage_check.py` (the Plan's "Verify" step) exists to prove.

- **VERIFIED** — the coverage check confirms a test actually exercised the file, and the
  restored build's numbers match.
- **TRANSLATED** — it builds and links, but no test has been shown to run it (it's off every
  test's path, or it's in an infrastructure folder with no test). Rewritten, not yet correct.
- **FAILED** — the numbers disagree after checking. Record the symptom instead of guessing a
  fix; a small mismatch goes to a person.

Record each file's result in the run's checklist (`agent_checklist.md`, see the Plan's
recording note), not here.
