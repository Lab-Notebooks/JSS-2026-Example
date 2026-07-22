# C++ → Kokkos: target output for one Pepper kernel

This file defines the kernel contract and correctness bar for step 2. The workflow lives in
`current_plan.md`.

```
Fortran (MCFM) -> C++ (step 1) -> Kokkos kernel in Pepper (step 2)
```

Pepper does not link MCFM. During authoring, `libmcfm` is only the reference used to compare
against. A runner can produce `TRANSLATED`, not `VERIFIED`; doctest-based verification is a
human step.

---

## Kernel shape

- Use `C = Kokkos::complex<double>` from `../math.h`; imaginary unit `C(0,1)`.
- Event data is SoA, particles are 0-based, and the result is written to `evt.me2(i)`.
- Start every kernel with `if (evt.w(i)==0.0) return;`.
- Pass module globals through a plain `<Name>_Params` struct by value.
- Files are `<name>_kernel.h` plus a one-line `<name>_kernel.cpp` listed in `src/CMakeLists.txt`.
- Entry point is `double <name>_me2(double p[N][4], const <Name>_Params&)`.
- Helpers are `KOKKOS_INLINE_FUNCTION` inside `namespace mcfm_<name>`.
- Reuse already-checked helpers by including them; do not re-derive them.

Use fixed Z-pole inputs matching MCFM's `couplz` convention so reference numbers reproduce.

## Rewrite rules

| MCFM C++ | Pepper Kokkos |
|---|---|
| free host function | `KOKKOS_INLINE_FUNCTION` helper |
| `std::complex<double>` | `C` |
| `std::sqrt/log/pow/...` | `Kokkos::sqrt/log/pow/...` |
| `FArray` (1-based) | fixed-size local arrays, 0-based |
| module globals | fields of `*_Params` |
| out-array + wrapper | scalar `*_me2(...)` + event kernel writes `evt.me2(i)` |
| QCDLoop calls | direct formulas |

### Important traps

- `Kokkos::complex` division is not `std::complex` division. Division-heavy code often settles
  near `1e-10`, not `1e-13`.
- Preserve the amplitude structure; do not collapse away meaningful stages.
- Reorder four-vectors correctly: fixtures use `{E,px,py,pz}` while `*_me2(double p[N][4])`
  uses `{px,py,pz,E}`.
- Flip incoming legs only when building the validator/test `p[N][4]` array, not inside kernel
  reads from `evt.*`.

## Loop integrals

QCDLoop does not run in device code. Replace each loop-integral call with a direct
`KOKKOS_INLINE_FUNCTION` formula and check that formula against QCDLoop before relying on it.
For threshold-sensitive cases, choose and document the handling strategy per integral.

## Split layout

If a tree is split, pieces live in `mcfm_analytics/<name>_parts/<piece>.h` inside
`namespace mcfm_<name>`. Only the final `<name>_kernel.h` and `.cpp` go in CMake. Every split
header needs a `// MCFM sources: ...` line. Frozen pieces are not edited later; fix the join if
joined output disagrees.

## Correctness bar

Correctness for step 2 means **matches MCFM**, not independent physics revalidation.

While authoring, compare block by block against `libmcfm` and target **1e-10** relative error
for the final kernel.

- **TRANSLATED** — matches `libmcfm`, builds, and existing Pepper tests pass.
- **VERIFIED** — a human-added Pepper doctest reproduces frozen reference numbers.
- **FAILED** — cannot be made to match `libmcfm`.

A runner never marks `VERIFIED`. Record results in `agent_log.md`, not here.

## References

Pepper (arXiv:2311.06198), MadGraph4GPU/CUDACPP (arXiv:2312.02898, arXiv:2510.05392),
Ellis–Zanderighi scalar integrals (arXiv:0712.1851), QCDLoop 2.0 (arXiv:1605.03181), and the
`Kokkos::complex` behavior note in kokkos/kokkos#7618.
