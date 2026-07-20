# C++ → Kokkos: what a Pepper kernel must look like

What a rewritten MCFM C++ amplitude (the output of step 1) must look like as a Kokkos kernel
that runs on GPUs inside Pepper, and how "correct" is defined. This file is only the desired
result and the correctness bar; how to run the step — the helper programs, the running-command
rules, which target to do next, the step-by-step, the authoring traps, and the splitting
procedure — lives in the Plan (`current_plan.md`).

```
Fortran (MCFM)  --step 1-->  C++ (FArray + std::complex)  --step 2-->  Kokkos kernel (Pepper)
```

The kernels become part of Pepper: Pepper does not link MCFM. A kernel is **verified** only
when Pepper's own tests (doctests) pass, comparing it against saved reference numbers — and
those reference doctests are added by a person, not a runner (see the correctness bar below),
so a runner's own output tops out at **translated**: matched against `libmcfm` and building
clean, but not yet covered by a frozen doctest. A header that only compiles is translated too.

Paths use `$MCFM_HOME`/`$PEPPER_HOME` (a normal-shell shortcut; the literal forms are
`software/mcfm` and `software/pepper`). The Pepper copy must be on the branch that has the
`mcfm_analytics` kernels.

---

## What a kernel looks like

- **Complex type and math.** `C = Kokkos::complex<double>` (from `../math.h`); imaginary unit
  `C(0,1)`. Event data is laid out as a structure of arrays (SoA), particles are 0-based with
  0 and 1 always incoming, and the
  result is `evt.me2(i)`. Put a skip-empty-event guard `if (evt.w(i)==0.0) return;` at the top
  of every kernel. Pass module globals in as a plain `<Name>_Params` struct by value.
- **Naming and files.** `<name>_kernel.h` plus a one-line `<name>_kernel.cpp` listed in
  `src/CMakeLists.txt`; entry point `double <name>_me2(double p[N][4], const <Name>_Params&)`;
  helpers are `KOKKOS_INLINE_FUNCTION` inside `namespace mcfm_<name>`. Reuse an already-checked
  helper by including it; never re-derive one.
- **Couplings.** Built on the host with MCFM's `couplz` convention at fixed Z-pole inputs
  (`xw=0.2312`, `alpha_s=0.118`, `m_Z=91.1876`, finite part `epinv=0`), so every reference
  number can be reproduced.

## Rewriting rules (MCFM C++ → Kokkos kernel)

| MCFM C++ | Pepper Kokkos kernel |
|---|---|
| free host function | `KOKKOS_INLINE_FUNCTION` helper; template only the dispatch entry |
| `std::complex<double>` | `C` (from `../math.h`); imaginary unit `C(0,1)` |
| `std::sqrt/log/pow/…` | `Kokkos::sqrt/log/pow/…` (never bare `std::` in device code) |
| `FArray` (1-based) | fixed-size local arrays, 0-based (`C za[N][N]`), no heap |
| module globals | fields of the plain-old-data (POD) `*_Params` struct |
| out-array + wrapper | scalar `*_me2(...)` return; the template kernel writes `evt.me2(i)` |
| QCDLoop (`loopI2/3/4`, `qli*`) | direct formulas (see "Loop integrals" below) — QCDLoop is not device code |

Two rules deserve their own line:

- **`Kokkos::complex` is not `std::complex`.** Its `/` divides using the 1-norm of the
  divisor, so complex divisions only agree to rounding. Prefer multiply-by-conjugate; set
  tolerances for division-heavy code at 1e-10; if a check gets stuck near 1e-12, suspect this
  before hunting for a math bug.
- **Keep the amplitude's structure** (for example, Born then K-factor) — same spirit as step
  1's "keep every call."

## Loop integrals: direct formulas on the GPU

QCDLoop can't run inside a kernel, so a correct kernel replaces each call with a direct
`KOKKOS_INLINE_FUNCTION` formula (Ellis–Zanderighi 0712.1851; QCDLoop 2.0 1605.03181), each
one checked on its own against the real QCDLoop through `libmcfm` (~1e-12) before use. Staying
accurate near thresholds is an open problem on the GPU (subtracting two nearly-equal dilogs
loses precision, and there is no cheap high-precision fallback per thread): the kernel must
carry a chosen plan per integral — a safe expanded formula, accept a few bad points, or flag
shaky inputs on the host — and say which one, in a comment. High-multiplicity boxes are the
hard case; bubbles and triangles have been fine.

## How split pieces are laid out

When a call tree is too big for one pass it is split into pieces (the Plan says how). The
desired layout is fixed: pieces live in `mcfm_analytics/<name>_parts/<piece>.h`, all inside
`namespace mcfm_<name>`; only the final `<name>_kernel.h` + `.cpp` go in CMake. Every header
has a `// MCFM sources: …` comment saying where it came from — that is what the closure tool
reads to work out reuse. A frozen piece is never edited by a later agent; if the full `|M|²`
then disagrees, the bug is in the join, not the pieces.

## The correctness bar: "matches MCFM", not physics

Pepper has no one-loop math of its own, so a kernel is checked by **matching MCFM
number-for-number**, not by redoing the physics: the tests' reference numbers are MCFM's
results for the same inputs, so the kernel must reproduce MCFM block by block and for the full
`|M|²`. The physics itself was already checked in step 1, when MCFM passed its tests to 1e-13.
While the kernel is written, `libmcfm` is the reference to match against, block by block
(loop functions → sub-amplitudes → full `|M|²`), aiming for **1e-10** relative — a helper for
the author, not part of Pepper or its tests.

The two outcomes:

- **VERIFIED** — a frozen Pepper doctest reproduces the saved reference numbers for this
  kernel. Those reference doctests are added by a **person**, not a runner: picking and
  freezing reference numbers needs human judgement. So a runner does not mark VERIFIED.
- **TRANSLATED** — the kernel matches `libmcfm` block by block, builds, and the existing tests
  still pass, but no frozen doctest covers it yet. This is the most a runner produces; it
  reports which layered doctests the developer should add (mirroring the existing
  `MCFM-analytics` cases). A person adds the doctest and, when it passes, marks it VERIFIED.

A kernel that a runner cannot get to match `libmcfm` is **FAILED**, handed to a person with the
symptom. Record each kernel's result in the run's checklist (`agent_checklist.md`, see the
Plan's recording note), not here.

## References

Pepper (arXiv:2311.06198); MadGraph4GPU/CUDACPP (arXiv:2312.02898, splitting
arXiv:2510.05392); scalar closed forms (arXiv:0712.1851); QCDLoop 2.0 (arXiv:1605.03181);
`Kokkos::complex` non-drop-in (kokkos/kokkos#7618).
