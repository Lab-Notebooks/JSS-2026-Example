# Spec — C++ → Kokkos kernel (stage 2)

The **Spec** for the stage-2 transformation: how to port an MCFM C++ amplitude (the
output of stage 1) into a device-portable Kokkos kernel inside Pepper, and what
makes the port **verified**. Like the stage-1 Spec it is orchestrator-agnostic and
is the single source of truth; the workflow points here rather than restating it.

```
Fortran (MCFM)  --stage 1-->  C++ (FArray + std::complex)  --stage 2-->  Kokkos kernel (Pepper)
```

A kernel is **verified** only when its doctests pass (layered equivalence against
`libmcfm`); a header that merely compiles is **translated** (unverified). Stage-2
verification is *translation equivalence*, not physics — the physics was already
validated when stage 1 passed the MCFM benchmarks at 1e-13 (§6).

Paths use `$MCFM_HOME` and `$PEPPER_HOME` (set by `source environment.sh`). The
Pepper clone must be on the branch carrying the `mcfm_analytics` kernels.

---

## §1 Prerequisites

1. `source "$PROJECT_HOME/environment.sh"` — sets `MCFM_HOME`, `PEPPER_HOME`.
2. `$MCFM_HOME` is built and `libmcfm.*` exists — the validator links it.
3. The Pepper clone is on the `mcfm_analytics` branch.

## §2 Conventions you must not get wrong

- **Two 4-vector conventions.** Pepper's `evt.e/px/py/pz` and the fixtures store
  `{E,px,py,pz}` (E first); the MCFM kernel signature `*_me2(double p[N][4])` uses
  `{px,py,pz,E}` (E last). Every fixture conversion reindexes. Metric is mostly-minus.
- **The incoming-leg sign flip — where it happens and where it must not.** Both codes
  store incoming legs with negative energy internally, so *inside a kernel* reading
  `evt.*` there is **no flip**. It is the *validator and doctests* that hand back
  physical (positive-energy) momenta, so when building the `p[N][4]` array you negate
  the 4-vectors of particles 0 and 1. Stating "incoming particles negated" as one
  universal rule is a known error — it applies to array-building, not in-kernel reads.
- **Kernel infrastructure.** Complex type `C = Kokkos::complex<double>` (`../math.h`);
  event data SoA, particles 0-based with 0 and 1 always incoming, result `evt.me2(i)`;
  dead-event guard `if (evt.w(i)==0.0) return;` at the top of every kernel; module
  globals delivered as a POD `<Name>_Params` struct passed by value.
- **Naming.** `<name>_kernel.h` + a one-line `<name>_kernel.cpp` TU registered in
  `src/CMakeLists.txt`; entry point `double <name>_me2(double p[N][4], const <Name>_Params&)`;
  helpers `KOKKOS_INLINE_FUNCTION` inside `namespace mcfm_<name>`. Reuse an
  already-validated helper via include; never re-derive one.
- **Couplings.** Built host-side with MCFM's `couplz` convention at fixed Z-pole
  inputs (`xw=0.2312`, `alpha_s=0.118`, `m_Z=91.1876`, finite part `epinv=0`), so
  every reference value is reproducible.

## §3 Translation rules (MCFM C++ → Kokkos kernel)

| MCFM C++ | Pepper Kokkos kernel |
|---|---|
| free host function | `KOKKOS_INLINE_FUNCTION` helper; template only the dispatch entry |
| `std::complex<double>` | `C` (from `../math.h`); imaginary unit `C(0,1)` |
| `std::sqrt/log/pow/…` | `Kokkos::sqrt/log/pow/…` (never bare `std::` in device code) |
| `FArray` (1-based) | fixed-size local arrays, 0-based (`C za[N][N]`), no heap |
| module globals | fields of the POD `*_Params` struct |
| out-array + wrapper | scalar `*_me2(...)` return; the template kernel writes `evt.me2(i)` |
| QCDLoop (`loopI2/3/4`, `qli*`) | analytic closed forms (§5) — QCDLoop is not device code |

Two rules earn their own line:

- **`Kokkos::complex` is not `std::complex`.** Its `operator/` scales by the 1-norm
  of the divisor, so complex divisions agree only to rounding. Prefer
  multiply-by-conjugate; set division-heavy tolerances at 1e-10; if a check stalls
  near 1e-12 suspect this before hunting an algebra bug.
- **Preserve the amplitude's internal structure** (e.g. Born-then-K-factor) — the
  same spirit as stage 1's "keep every call."

## §4 Procedure per amplitude

1. **Map the call tree and audit portability.** Follow every call from the entry
   `.cpp`; list the tree, the module globals read (→ Params fields), the portability
   blockers (QCDLoop → §5, STL, heap, I/O), and the already-ported helpers to reuse.
   Cross-check completeness with `python3 dev/tools/closure/calltree_closure.py <name>`
   — it derives the closure from `libmcfm`'s linked objects (symbols do not lie) and
   flags any plain-Fortran object as a stage-1 gap.
2. **Author the kernel header** bottom-up: device-safe helpers, then the pure
   `<name>_me2(p, params)`, then the templated dispatch kernel reading `evt.*`
   directly and writing `evt.me2(i)`. Add the one-line `.cpp` TU. Large call trees
   split at function boundaries (§7).
3. **Closed forms for scalar integrals** — only if the amplitude calls QCDLoop (§5).
4. **Validate against `libmcfm`** host-side through the Kokkos shim: compare layered —
   loop functions → sub-amplitudes → full `|M|²`, target ≤1e-10 relative, same fixed
   inputs and momenta on both sides. This is the `kokkos-validate-loop` workflow.
5. **Doctests and build wiring**: add layered `DOCTEST_TEST_CASE`s mirroring the
   existing `MCFM-analytics` cases; register the header + TU; run
   `pepper_test --dt-test-case="*<name>*"`.
6. **Report** files written, worst relative error per layer, and blockers.
   Verified ⇔ doctests pass; else translated.

## §5 Scalar integrals: closed forms on device

QCDLoop cannot run in a kernel. Replace each call with an analytic
`KOKKOS_INLINE_FUNCTION` closed form (Ellis–Zanderighi 0712.1851; QCDLoop 2.0
1605.03181) and validate it **in isolation** against the real QCDLoop through
`libmcfm` (~1e-12) before using it. Numerical stability near thresholds is an open
problem on device (catastrophic dilog cancellations, no affordable quad fallback per
thread): choose a strategy per integral — safe expanded branch, accept rare bad
points, or flag unstable kinematics host-side — and record which one. Boxes at high
multiplicity are the hard case; bubbles and triangles have been fine.

## §6 Why validation is equivalence, not physics

Pepper has no internal one-loop recursion, so virtual kernels are validated purely
by **translation equivalence** against `libmcfm`, block by block and then the
assembled `|M|²`. This checks the faithfulness of the port; the physics was validated
at stage 1.

## §7 Splitting large call trees across agents

A kernel absorbs its entire call tree (no external calls from device code), so the
unit of work is the flattened tree, not the file. Because each MCFM C++ function has
a bit-identical reference symbol in `libmcfm`, **every piece has its own oracle** —
which is what makes a split safe:

1. Split at function boundaries, never at line counts.
2. Build the piece DAG and author bottom-up: leaves first (in parallel), then
   sub-amplitudes, then the assembly. One agent per piece; each reports the globals
   it needs (these become Params fields).
3. Validate each piece against its `libmcfm` twin before joining (≤1e-12 → frozen).
4. Join: the assembly agent includes the frozen fragments, writes the `*_Params`
   struct and the dispatch kernel, then runs the full-ME validation. If the full ME
   disagrees while every piece passes, the bug is in the assembly layer — a small
   search space.

**Convention:** fragments live in `mcfm_analytics/<name>_parts/<piece>.h`, all inside
`namespace mcfm_<name>`; only the final `<name>_kernel.h` + TU are registered in
CMake. Every header carries a `// MCFM sources: …` provenance line — that is what the
closure tool reads to compute reuse. A frozen fragment is never edited by a later
agent; if the full ME then disagrees, fix the assembly, not the fragments.

## §8 References

Pepper (arXiv:2311.06198); MadGraph4GPU/CUDACPP (arXiv:2312.02898, splitting
arXiv:2510.05392); scalar closed forms (arXiv:0712.1851); QCDLoop 2.0
(arXiv:1605.03181); `Kokkos::complex` non-drop-in (kokkos/kokkos#7618).
