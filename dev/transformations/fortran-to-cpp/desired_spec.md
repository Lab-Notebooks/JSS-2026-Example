# Fortran → C++ translation of MCFM

The rules for translating one MCFM Fortran file to C++, and what makes the result
**verified**. The workflow and tools point here rather than restating these rules.

A unit is **verified** only when a benchmark actually exercises it and the coverage probe
fires (§5); everything else is **translated**. Say which, plainly, and never claim
correctness for a merely-translated unit.

Paths use `$MCFM_HOME` (the MCFM clone, set by `source environment.sh`) and are relative to
`$MCFM_HOME/src`.

---

## Tools

The `translate` workflow runs these deterministic Tools by name; each documents its
interface in its own docstring under `dev/tools/`.

- **Discovery (Index).** `dev/tools/index/generate_doxygen.sh` builds the Doxygen call
  graph, then `dev/tools/index/build_roadmap.py` ranks units by readiness into
  `dev/tmp/assets/roadmap_metrics.tsv` (a ready leaf has `deps==0` and `blind==0`) and
  writes the symbol map `dev/tmp/assets/symbol_index.json`.
- **Authoring pre-pass (Draft).** `dev/tools/draft/scribe_draft.py <file.f>` writes a
  mechanical scaffold plus rule-9a external-symbol hints; pair it with the worked
  examples in `dev/tools/draft/seed_examples.toml`.

---

## §1 What each source file becomes

One Fortran file becomes one translation unit, replacing its `.f`/`.f90` entry in
the directory's `CMakeLists.txt`:

- **`<base>.cpp`** — the C++ implementation, plus an
  `extern "C" <base>_wrapper(...)` that exposes it to Fortran (raw pointers in,
  `FArray` views built inside the wrapper).
- **`<base>.hpp`** — the header (signature + include guard), so sibling C++ files
  can call it directly.
- **`<base>_fi.F90`** — a free-form `iso_c_binding` interface: a Fortran
  subroutine of the *original* name whose body declares the inner `bind(C)`
  interface and calls `<base>_wrapper`. This keeps every existing Fortran caller
  working unchanged during the incremental migration — the interface-layer approach
  that lets the codebase stay live instead of demanding a big-bang cutover.

A Fortran **module** instead becomes a `.hpp` (namespace of `extern` declarations),
a `.cpp` (definitions + `extern "C"` pointer accessors), and a `_fi.f90` that
mirrors each variable with `c_f_pointer`. Model a new module on a verified sibling
in `src/Mods`.

---

## §2 Translation rules

Translate the body line by line. Do not add a `main`, extra declarations, or any
symbol the source does not define.

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

**The one rule worth stating twice — never fabricate a called symbol (rule 9a).**
A file usually calls routines defined in *other* files whose signatures you are not
shown. Keep every `call` that exists; invent none. Resolve each by whether the
dependency is already translated:

- **Already C++** (`<dep>.cpp` sibling on disk) → call its C++ function directly:
  `#include "<dep>.hpp"` and match its signature.
- **Still Fortran** → call it through the free-subroutine ABI: declare
  `extern "C" void <name>_(/* every arg a pointer */);` and call
  `<name>_(&a, &b, …)`, arrays passed as the underlying pointer. Results come back
  through the pointers.

If a callee is an untranslated *module* function with no C binding, that is a real
blocker, not something to guess around — translate the dependency first. The
dependency graph (§the Index tool) exists precisely so the workflow only offers you
files whose callees are already done.

A full worked example (subroutine and module, all three output files) lives in the
few-shot seed the Draft step pairs with: `dev/tools/draft/seed_examples.toml`.

---

## §3 Common silent traps

Most translation bugs are *silent*: the code builds, links, and may even pass the
benchmark, yet is wrong. Each of these was seen on a real MCFM file — treat them as
a self-review checklist, and rely on the §5 coverage probe to catch what review
misses.

1. **A dropped `call`.** "Simplifying away" a call whose output you do not see used,
   or skipping one of a near-identical pair (a public routine often calls its
   `core` worker twice, once with the spinor arguments swapped). Leaves outputs
   uninitialized; builds clean.
2. **Operator precedence in rationals.** Fortran `)/za*za` divides by `za²`; C++
   left-to-right makes it `(…/za)*za`. Parenthesize every denominator.
3. **`FArray` layout.** Construct an existing array with *all* its dimensions and
   1-based bounds; passing too few sizes silently shifts the whole buffer. There is
   no `FArray5D` — flatten with an index lambda for D≥5.
4. **0-based vs 1-based.** Do not write index 0 of a 1-based Fortran array; keep
   fill loops 1-based so every subscript lands in `[1,N]`.
5. **Includes.** Include the module headers the `use` lines imply (not just a
   self-header), plus `<Need.hpp>` for the loop/spinor helpers (`lnrat`, `L0`,
   `spinoru`, `dot`, …). A missing cross-directory header is an integrator action:
   report the directory; do not edit shared CMake yourself.

When a numerical disagreement survives review, report it as FAILED with the symptom
rather than guessing a fix — a subtle mismatch is escalated to a human.

---

## §4 Directory → benchmark mapping

A translation is verified only if a benchmark exercises it. Map the file's
top-level `src/` directory to a `./test -b` process:

| Directory | `./test -b` process |
|-----------|---------------------|
| W / W1jet / W2jet | `u d~ ve e+` (+ `g`, `g g`) |
| Z / Z1jet / Z2jet | `u u~ e- e+` (+ `g`, `g g`) |
| ThreeJets | `g g g g g` |
| ggH / gghgg_dep | `g g h` / `g g h g g` |
| Mods, Need, Inc, Procdep | infrastructure — no benchmark; mark TRANSLATED |

A file in a directory with no benchmark is **translated but unverified**. This table
is also encoded in the Index tool (`dev/tools/index/build_roadmap.py`).

---

## §5 Verification and the coverage probe

Build and benchmark via the harness, or by hand for a single-process probe:

```bash
source "$PROJECT_HOME/environment.sh"
jobrunner submit tests/mcfm    # builds $MCFM_HOME/Bin and runs the full benchmark suite
# or, to build and probe one process by hand:
cd "$MCFM_HOME/Bin" && cmake . >/dev/null && make install 2>&1 | tail -40
./test -b <process>            # records four ratios: Finite / IR / IR2 / Born
```

A translation passes only when all four ratios match within **1e-13**. (Amplitudes
using complex powers show ~1e-15 deviations — normal, well within tolerance.)
Confirm linkage with `nm libmcfm.* | grep -i <name>`.

**The coverage probe is mandatory before calling anything VERIFIED.** A passing
benchmark is necessary but *not* sufficient: the frozen benchmark momenta may never
reach the routine, so it reports a match without ever being tested. So probe it:

1. Temporarily multiply the file's main output by 1.5.
2. Rebuild (single-file relink) and re-run the passing process.
3. If the ratios **break**, the file is exercised → revert the 1.5×, rebuild to
   confirm PASS, mark **VERIFIED**.
4. If the ratios are **unchanged**, the benchmark does not reach it → mark
   **TRANSLATED** (unverified). Re-probe after its caller becomes C++ — a leaf can
   read off-path only until the routine that uses it lands.

Always revert every probe edit and leave the tree building clean. This §5 *is* the
verification criteria: the workflow's serial Integrate phase applies it, and the
CodeScribe review phase would apply the same one. Record per-file outcomes
(verified / translated / failed) in the Plan (`current_plan.md`), not here.
