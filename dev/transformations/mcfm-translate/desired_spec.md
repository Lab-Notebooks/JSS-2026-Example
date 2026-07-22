# Fortran → C++: target output for one MCFM file

This file defines the rewrite target and correctness bar for step 1. The workflow lives in
`current_plan.md`.

Paths are written as `software/mcfm/src/...`.

---

## Output shape

One Fortran file becomes one C++ translation unit set, and the folder's `CMakeLists.txt` swaps
its `.f`/`.f90` entry for the new files:

- **`<base>.cpp`** — translated code plus `extern "C" <base>_wrapper(...)`; when a matching header exists, this file should include `<base>.hpp>`
- **`<base>.hpp`** — direct C++ declaration for the translated C++ entry points used outside the translation unit
- **`<base>_fi.F90`** — Fortran shim with the original entry name calling the wrapper

A Fortran module instead becomes a `.hpp`, a `.cpp`, and a `_fi.f90` that mirrors variables via
`c_f_pointer`. Follow existing rewritten modules in `src/Mods`.

## Rewrite rules

Rewrite line by line. Do not add a `main`, extra declarations, or invented names.

| Fortran | C++ |
|---|---|
| `subroutine`/`function` | free function + `<name>_wrapper` in `extern "C"`; declare the reusable C++ function in `<base>.hpp` when it is used outside its own `.cpp` |
| `use <mod>` | `#include <mod.hpp>` + `using namespace <mod>;` |
| `real(dp)` / `complex(dp)` | `double` / `std::complex<double>` |
| `dimension(nx,ny)` array | `FArray2D<double> a(nx, ny)` |
| `intent(in/inout)` scalar | pass by reference |
| statement function | C++ lambda |
| `x**n` | `pow(x, n)` |
| `return` | `return;` |

### Never invent a called symbol

Keep every call already present in the source.

- If the callee is already rewritten, include its `.hpp` and call the C++ function.
- If the callee is still Fortran, declare the plain Fortran symbol in `extern "C"` and call it
  with pointer arguments.
- If a needed module dependency has no usable C binding yet, stop and rewrite that dependency
  first.

The readiness map exists so a file is only rewritten when its callees are already available.
Use the Draft tool's hints and seed examples when needed.

## Header / source structure

Follow normal C++ structure for translated code.

1. If a translated unit has a `<base>.hpp`, the matching `<base>.cpp` should include it as the normal declaration point for that unit's C++ interface.
2. Treat the generated header/source pair as the default structure for translated C++: declarations live in the header, definitions live in the `.cpp`, and the `.cpp` includes its own header.
3. If one translated `.cpp` calls a C++ function defined in another translated `.cpp`, include the callee's header rather than adding a local forward declaration.
4. Use local forward declarations only when there is intentionally no reusable header yet and introducing one would not make the interface clearer.
5. Put declarations for reusable cross-translation-unit C++ functions in headers before they are used from other `.cpp` files.
6. Keep `extern "C"` declarations only for true Fortran or C interoperability boundaries, not as a substitute for ordinary C++ headers.

## Silent traps

Check these explicitly:

1. Dropped calls, especially near-duplicate paired calls.
2. Missing parentheses around denominators after translating chained `*` and `/`.
3. Wrong `FArray` sizes or bounds.
4. Accidental 0-based indexing for 1-based Fortran arrays.
5. Missing module or `Need.hpp` includes.
6. A translated `.cpp` failing to include its own matching header when one exists.
7. Calling a translated C++ sibling without including its header when one exists.
8. Keeping translation-era forward declarations even though a proper header interface exists.

If numbers still disagree after checking, mark the file `FAILED` with the symptom.

---

## Coverage map

A file is only verified if a test actually runs it.

| Directory | `./test -b` process |
|-----------|---------------------|
| W / W1jet / W2jet | `u d~ ve e+` (+ `g`, `g g`) |
| Z / Z1jet / Z2jet | `u u~ e- e+` (+ `g`, `g g`) |
| ThreeJets | `g g g g g` |
| ggH / gghgg_dep | `g g h` / `g g h g g` |
| Mods, Need, Inc, Procdep | infrastructure — mark `TRANSLATED` |

This mapping is also built into `dev/tools/index/build_roadmap.py`.

---

## Correctness bar

A passing MCFM test must match to **1e-13**. That alone is not enough: the test must also be
shown to exercise the rewritten file via `dev/tools/coverage/coverage_check.py`.

- **VERIFIED** — the coverage check shows the test exercised the file, and the restored build
  still matches.
- **TRANSLATED** — the file builds, but no test has been shown to exercise it.
- **FAILED** — the numbers disagree after checking.

Record results in `agent_log.md`, not here.
