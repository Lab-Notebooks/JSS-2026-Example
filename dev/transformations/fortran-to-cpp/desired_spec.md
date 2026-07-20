# Fortran → C++: what a rewritten MCFM file must look like

The rules for what one rewritten MCFM file must look like, and how "correct" is defined.
This file is only the desired result and the correctness bar; how to run the step — the
helper programs, the running-command rules, which files to do next, the self-check list, and
the coverage-check procedure — lives in the Plan (`current_plan.md`).

A file is **verified** only when a test actually runs it and the coverage check passes.
Otherwise it is only **translated** (rewritten, but not yet shown to be correct). Always say
which one it is, and never call a merely-translated file correct.

Paths are written as `software/mcfm/src/...` (relative to the MCFM code). The `$MCFM_HOME/src`
form used in a few places means the same thing; it is a shortcut for a normal shell.

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
Index program the Plan names) exists so the workflow only hands you files whose called
routines are already done.

A full worked example (a subroutine and a module, all three output files) is in the examples
the Draft step uses: `dev/tools/draft/seed_examples.toml`.

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
routine, so a test can report a match without ever running your code. So the meaning of the
two outcomes is:

- **VERIFIED** — a test actually exercised the file *and* the numbers match. Proving a test
  exercised it is what the Plan's coverage check does; a rewrite is verified only once that
  check fires.
- **TRANSLATED** — it builds and links, but no test has been shown to run it (it's off every
  test's path, or it's in an infrastructure folder with no test). Rewritten, not yet correct.

Only a runner with a normal shell can run the coverage check, so only it may mark **VERIFIED**;
the CodeScribe loop (limited shell) marks **TRANSLATED** and leaves the upgrade to a
normal-shell pass. The verified-vs-translated meaning does not change, only who can mark
which. If a number still disagrees after checking, mark it **FAILED** with the symptom instead
of guessing a fix — a small mismatch goes to a person. Record each file's result in the run's
checklist (`agent_checklist.md`, see the Plan's recording note), not here.
