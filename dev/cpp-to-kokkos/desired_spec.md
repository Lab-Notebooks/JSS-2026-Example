# Spec — C++ → Kokkos kernel (stage 2)

The **Spec** for the stage-2 transformation: how to port an MCFM C++ amplitude
(the output of stage 1) into a device-portable Kokkos kernel inside Pepper, and
what makes the port **verified**. Orchestrator-agnostic; the Claude Code workflow
and the skills point here.

Pipeline position:

```
Fortran (MCFM)  --stage 1-->  C++ (FArray + std::complex)  --stage 2-->  Kokkos kernel (Pepper)
```

A kernel is **verified** only when its doctests pass (layered equivalence against
`libmcfm`); a header that merely compiles is **translated** (unverified). Stage-2
verification is *translation equivalence*, not physics — the physics was validated
when stage 1 passed the MCFM benchmark suite at 1e-13.

Paths use `$MCFM_HOME` and `$PEPPER_HOME` (set by `source environment.sh`). The
Pepper clone must be on the branch carrying the `mcfm_analytics` kernels
(see `software/README.md`).

---

## §1 Prerequisites

1. `source "$PROJECT_HOME/environment.sh"` (absolute path; the Bash tool persists
   cwd but resets env). Sets `MCFM_HOME` and `PEPPER_HOME`.
2. `$MCFM_HOME` is built and `libmcfm.*` exists — the validator links it.
3. The Pepper clone is on the `mcfm_analytics` branch.

## §2 Conventions you must not get wrong

### 2.1 Two 4-vector conventions

| | component order | incoming legs |
|---|---|---|
| Pepper `Vec4`, `evt.e/px/py/pz(i,part)`, fixtures | `{E, px, py, pz}` (E first) | stored with **negative energy** (all-outgoing crossing) |
| MCFM `p(mxpart,4)` and kernel `*_me2(double p[N][4], …)` | `{px, py, pz, E}` (E last) | **negative energy** as well |

Every translation reindexes E-first → E-last. Metric is mostly-minus `(+,-,-,-)`.

### 2.2 The incoming-leg sign flip — where it happens and where it must NOT

Both codes use incoming = negative energy internally, so:

- **Inside a device kernel** reading `evt.e/px/py/pz(i,part)`: **no sign flip** —
  the stored values already match the MCFM formulas.
- **In the standalone validator and the doctests**: the fixtures hand back
  *physical* (positive-energy) momenta, so when building the `p[N][4]` array for
  `*_me2` you **negate the whole 4-vector for particles 0 and 1**.
- **At the external `libmcfm` C++ API boundary**: that API takes positive-energy
  incoming momenta (`sign=-1.0` there). Do not copy that pattern into a kernel.

Stating "incoming particles negated" as one universal rule is a known error (G1);
it applies to the validator/doctest array-building step, not to in-kernel reads.
Validate **both** conventions explicitly (positive-energy all-outgoing evaluation
for translation-equivalence, and negative-energy incoming for production
correctness), as the worked ports did.

### 2.3 Pepper kernel infrastructure

- Complex type: `using C = Kokkos::complex<double>` (`../math.h`).
- Event data is SoA `Kokkos::View`s, event index first: `evt.e(i, part)`;
  particles 0-based, **0 and 1 are always incoming**; result is `evt.me2(i)`.
- Dispatch: free templated kernel
  `template <typename event_data> KOKKOS_INLINE_FUNCTION void k(const event_data& evt, int i, …)`
  launched via `RUN_KERNEL(...)`, one thread per event; always `Kokkos::fence(...)`
  after a `RUN_KERNEL`.
- Dead-event guard at the top of every kernel: `if (evt.w(i) == 0.0) return;`.
- Params delivery: a POD `<Name>_Params` struct passed **by value** (the convention
  the committed doctests fix).

### 2.4 Naming and signatures (fixed by the doctests)

- Files: `$PEPPER_HOME/src/mcfm_analytics/<name>_kernel.h` + a one-line TU
  `<name>_kernel.cpp`, registered in `src/CMakeLists.txt` under `PEPPER_LIB_SOURCES`.
- Entry point: `double <name>_me2(double p[N][4or5], const <Name>_Params&)` — a pure
  function; the templated dispatch kernel wraps it and writes `evt.me2(i)`.
- Params: `<Name>_Params` PascalCase-with-underscores. Virtual variants **nest the
  Born struct** as a `.born` member.
- Loop-function helpers live in a per-amplitude namespace (`namespace mcfm_<name>`).
  Reuse across kernels via include; never re-derive an already-validated helper.

### 2.5 Couplings — MCFM `couplz` convention

Built host-side (τ = 2·T3: −1 down-type & charged leptons, +1 up-type):

```
sin2w = 2*sqrt(xw*(1-xw))          # xw = sin^2(theta_W)
zl    = (tau - 2*Q*xw)/sin2w       # left Z coupling
zr    = (-2*Q*xw)/sin2w            # right Z coupling
esq   = 4*pi*alpha_em ;  gsq = 4*pi*alpha_s
```

Canonical fixed inputs for every reference value (Z pole, GeV): `xw=0.2312`,
`alpha_em=1/128.802223295`, `alpha_s=0.118`, `m_Z=91.1876`, `Gamma_Z=2.4952`,
`m_t=173.21`, `musq=m_Z^2`, `epinv=epinv2=0` (finite part), scheme `dred`.

## §3 Translation rules (MCFM C++ → Kokkos kernel)

| MCFM C++ | Pepper Kokkos kernel |
|---|---|
| free host function | `KOKKOS_INLINE_FUNCTION` helper; template only on the dispatch entry |
| `#include "x.h"` | `#include "../x.h"` (relative; keeps `src/` off the angle path) |
| `std::complex<double>` | `C` (from `../math.h`) |
| imaginary unit | `C(0,1)` |
| `std::sqrt/abs/log/atan/pow` | `Kokkos::sqrt/fabs/log/atan/pow` (never bare `std::` in device code) |
| `pow(std::abs(z),2)` | explicit `z.real()*z.real() + z.imag()*z.imag()` |
| `FArray2D<double> p` (1-based) | `double p[N][4]` 0-based, comps `{0:px,1:py,2:pz,3:E}` |
| dynamic `FArray` scratch | fixed-size local arrays (`C za[N][N]`), no heap |
| `std::vector/map/string/cout`, `throw`, virtual dispatch | forbidden in device code (`Kokkos::abort()` if a hard stop is unavoidable) |
| module globals (`epinv`, `musq`, couplings, masses, `nflav`, …) | fields of the POD `*_Params` struct passed by value |
| out-array `msq(j,k)` / wrapper | scalar `*_me2(...)` return; the template kernel writes `evt.me2(i)` |
| Fortran/FArray 1-based indices | 0-based everywhere |
| QCDLoop (`loopI2/3/4`, `qli*`) | analytic closed forms, §5 — QCDLoop is NOT device code |

Additional rules:

- **`Kokkos::complex` is not numerically identical to `std::complex`.** Its
  `operator/` scales by the 1-norm of the divisor, so complex divisions agree only
  to rounding. Consequences: prefer multiply-by-conjugate over division; set
  validation tolerances at 1e-10 relative for division-heavy paths; if a check
  stalls around 1e-12 suspect this before hunting algebra bugs.
- Never `reinterpret_cast` a `Kokkos::complex` to `double[2]` (UB). Use `.real()/.imag()`.
- Keep `epinv`/`epinv2` as Params fields (0 for the finite part) so the kernel can
  also emit poles.
- No `KOKKOS_LAMBDA` nested inside another lambda/`KOKKOS_FUNCTION`; capture by value.
- Preserve the amplitude's internal structure (e.g. Born-then-K-factor); same
  spirit as stage 1's "keep every call."

## §4 Procedure per amplitude

1. **Map the dependency tree and audit portability.** Read
   `$MCFM_HOME/src/.../<name>.cpp`, follow every call, and list: the call tree;
   module globals read (→ Params fields); portability blockers (QCDLoop → §5, STL,
   heap, I/O); already-ported helpers (reuse via include). Cross-check completeness
   with `python3 tools/calltree_closure.py <name>` — it derives the closure from
   libmcfm's linked objects (symbols do not lie), flags any plain-Fortran object (a
   stage-1 gap), and reports stage-2 reuse from headers' `// MCFM sources:`
   provenance lines (§7). The Doxygen roadmap is NOT a completeness authority here.
2. **Author the kernel header** (the Author/Direct phase of `kokkos-translate`):
   device-safe helpers
   bottom-up, then the pure `<name>_me2(p, params)`, then the templated dispatch
   kernel reading `evt.*` directly (no sign flip, §2.2) and writing `evt.me2(i)`.
   Add the one-line `.cpp` TU. For large call trees, split at function boundaries
   (§7).
3. **Closed forms for scalar integrals** — only if the amplitude calls QCDLoop (§5).
4. **Standalone host validation against libmcfm** (the Validate phase /
   `kokkos-validate-loop`): the kernel compiles host-side through a Kokkos shim
   (`C = std::complex`); compare
   layered — loop functions → sub-amplitudes → full `msq`/`msqv`, target ≤1e-10
   relative, same fixed inputs and same momenta both sides.
5. **Doctests and build wiring**: add layered `DOCTEST_TEST_CASE`s mirroring the
   existing `MCFM-analytics …` cases (tol 1e-10 for 4-particle, 1e-9 for
   5-particle finals; Born-without-fixed-reference uses the constant-ratio check vs
   Pepper's recursion over ≥6 random points, tol 1e-6). Register header + TU in
   `src/CMakeLists.txt`. Build and run `pepper_test --dt-test-case="*<name>*"`.
6. **Report**: files written, worst relative error per layer, `pepper_test` result,
   blockers/approximations. Verified ⇔ doctests pass; else translated.

## §5 Scalar integrals: closed forms on device

QCDLoop cannot run in a kernel. Replace each call with an analytic
`KOKKOS_INLINE_FUNCTION` closed form and validate it **in isolation before** the
full ME:

1. Formula sources: Ellis & Zanderighi (arXiv:0712.1851); QCDLoop 2.0 code paper
   (arXiv:1605.03181) for the exact MCFM variant incl. complex masses; Denner
   (arXiv:0709.1075) for complex-mass/finite-width forms.
2. Generate references through the real QCDLoop in `libmcfm` (`scalarselect=1`,
   `qlinit()`) over a grid spanning thresholds and the spacelike region; require
   ~1e-12 agreement.
3. Each closed form takes its scales as arguments (`s`, `m2`, `musq`, `epinv`) — no
   globals.

**Numerical stability near thresholds is an open problem on device** (catastrophic
dilog cancellations; QCDLoop's CPU fallback is quad precision, unaffordable
per-thread). Choose explicitly per integral: (a) always evaluate a
safe/expanded-near-threshold branch, (b) accept divergence for rare bad points, or
(c) flag unstable kinematics host-side and shunt to a slow path. Boxes at higher
multiplicity are the hard case; bubbles/triangles have been fine in practice.
Budget sub-amplitude tolerances by their absolute contribution to the ME, not a
uniform relative figure.

## §6 Why validation is equivalence, not physics

Pepper has no internal one-loop recursion, so virtual kernels are validated purely
by **translation equivalence** against MCFM (`libmcfm`), block by block and then
the assembled |M|². This checks the faithfulness of the port; the physics was
validated at stage 1.

## §7 Splitting large call trees across agents

A Kokkos kernel absorbs its entire call tree (no external calls from device code),
so the unit of work is the flattened tree, not the file. Protocol:

1. **Split at MCFM function boundaries, never at line counts.** Each C++ function
   maps 1:1 onto a `KOKKOS_INLINE_FUNCTION` helper and has a bit-identical
   reference symbol in `libmcfm` — so every piece has its own oracle.
2. **Build the piece DAG**, author bottom-up: leaves (pure loop functions, closed
   forms) in parallel first, then sub-amplitudes, then the assembly. One agent per
   piece; each reports which globals it needs (these become Params fields).
3. **Validate each piece against its libmcfm twin before joining** (≤1e-12 → frozen).
4. **Join**: the assembly agent includes the frozen fragments, writes the
   `*_Params` struct (union of reported globals) and the dispatch kernel, then runs
   the full-ME validation. If the full ME disagrees while all pieces pass, the bug
   is in the assembly layer — a small search space.

**Fragment file convention:** fragments live in
`$PEPPER_HOME/src/mcfm_analytics/<name>_parts/<piece>.h`, all inside
`namespace mcfm_<name>`, first include `#include "../../math.h"`; only the final
`<name>_kernel.h` + one-line `.cpp` TU are registered in CMake. **Provenance line
(mandatory):** every mcfm_analytics header carries, in its top comment,
`// MCFM sources: src/<dir>/<file>.cpp, …` with ` (partial)` on any file it ports
only part of — this is what `tools/calltree_closure.py` reads to compute reuse. A
frozen fragment is never edited by a later agent; if the full ME then disagrees,
fix the assembly layer, not the fragments.

## §8 Gotcha catalog

- **G1** — sign flip only in the validator/doctest arrays, not in-kernel `evt.*` reads.
- **G2** — E-first (`Vec4`) vs E-last (`p[N][4]`); every fixture conversion reindexes.
- **G3** — `Kokkos::complex` division ≠ `std::complex`; budget tolerance or avoid division.
- **G4** — some Pepper members are stale (`evt.host` → `.h`/`.device`); don't imitate.
- **G5** — use `Kokkos::` math namespace in device code, not bare `std::`.
- **G6** — `Kokkos::fence(...)` after every `RUN_KERNEL`.
- **G7** — no View allocation inside kernels; build tables host-side, pass by const ref.
- **G8** — dead-event guard `if (evt.w(i) == 0.0) return;`.
- **G9** — the host shim is math-only; keep the pure `*_me2` free of event-data types.

## §9 References

- Pepper: arXiv:2311.06198 (SciPost Phys. 17, 081, 2024).
- MadGraph4GPU/CUDACPP: arXiv:2312.02898; kernel splitting arXiv:2510.05392.
- Scalar one-loop closed forms: Ellis & Zanderighi, arXiv:0712.1851.
- QCDLoop 2.0: Carrazza, Ellis, Zanderighi, arXiv:1605.03181.
- Complex-mass one-loop forms: Denner, arXiv:0709.1075.
- Kokkos: kokkos.org guide; `Kokkos::complex` non-drop-in kokkos/kokkos#7618.
