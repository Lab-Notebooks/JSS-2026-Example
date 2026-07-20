# C++ → Kokkos (step 2)

How to rewrite an MCFM C++ amplitude (the output of step 1) as a Kokkos kernel that runs on
GPUs, inside Pepper, and how to tell the result is correct. This is the source of truth for
the rules; the workflow and helper programs point here instead of repeating them.

```
Fortran (MCFM)  --step 1-->  C++ (FArray + std::complex)  --step 2-->  Kokkos kernel (Pepper)
```

The kernels become part of Pepper: Pepper does not link MCFM. A kernel is **verified** only
when Pepper's own tests (doctests) pass, comparing it against saved reference numbers. A
header that only compiles is **translated** (not yet verified). "Verified" here means it
matches MCFM number-for-number; it does not re-check the physics — the physics was already
checked in step 1, when MCFM passed its tests to 1e-13 (§6). While you write, `libmcfm` is a
handy reference to compare against, block by block (§4, §7); it is a helper for the author,
not part of Pepper or its tests.

Paths use `$MCFM_HOME`/`$PEPPER_HOME` (a normal-shell shortcut; the literal forms are
`software/mcfm` and `software/pepper`). The Pepper copy must be on the branch that has the
`mcfm_analytics` kernels.

---

## Helper programs (Tools)

The `port` and `validate` workflows run these small programs by name. Each explains how to
use it at the top of its own file under `dev/tools/`.

- **Closure.** `dev/tools/closure/calltree_closure.py <name>` lists everything an amplitude
  calls (its "closure") by reading what `libmcfm` links, and says how many pieces there are
  and whether they are all C++ (ready for step 2).
- **First draft (Kokkosify).** `dev/tools/kokkos/kokkosify.py` does the easy, mechanical
  parts of §3 and marks what it can't decide with `KOKKOSIFY-TODO` for the author to finish.
- **Compare-against-MCFM harness.** `dev/tools/kokkos/run_validation.sh <validator.cpp>`
  builds a small test that links `libmcfm` and includes your kernel, runs it, and prints
  each check (reference / got / relative error). It does not save a file itself; the
  `validate` loop reads what it prints and saves it to `dev/tmp/assets/validate-output.md`
  for the fix step.

## Running commands (works in both runners)

Two runners drive this step, and they have different shells. The Claude Code `port`/`validate`
workflows have a normal shell; the CodeScribe loop has a **limited** shell: it refuses the
characters `$ | & ; < > \``, refuses any command whose first word is not on its allow-list,
and does not fill in `$VARIABLES` when reading or writing files.

- **Use plain relative paths.** Write `software/mcfm/src/<...>` and
  `software/pepper/src/mcfm_analytics/<...>`, not `$MCFM_HOME/...` / `$PEPPER_HOME/...`. The
  `$…` shortcuts elsewhere only work in a normal shell. `run_validation.sh` reads
  `MCFM_HOME`/`PEPPER_HOME` from its own environment, so call it without `$`:
  `bash dev/tools/kokkos/run_validation.sh <validator.cpp>`.
- **No `cd`, pipes, or redirects.** Just read what a program prints.
- **Check with one command.** Run Pepper's tests with `jobrunner submit tests/pepper`; that
  one command sets up, builds, and runs the tests, and both shells allow it.

---

## §1 Before you start

1. `source "$PROJECT_HOME/environment.sh"` — sets `PEPPER_HOME`, `QCDLOOP_HOME`, `MCFM_HOME`
   (a one-time step in a normal shell; both runners inherit it).
2. The Pepper copy is on the `mcfm_analytics` branch. `jobrunner submit tests/pepper` builds
   Pepper on its own (Kokkos + QCDLoop, no MCFM) and runs the tests — that is the correctness
   check.
3. **You must build MCFM first — it is required, not optional.** Run
   `jobrunner submit tests/mcfm` before anything else: the Closure tool reads `libmcfm` to
   find the call tree, and the compare harness (§4 step 4) links `libmcfm`. On a fresh
   checkout, picking/sizing a target and validating both fail until MCFM is built.

## §2 Things that are easy to get wrong

- **Two ways to order a 4-vector.** Pepper's `evt.e/px/py/pz` and the fixtures store
  `{E,px,py,pz}` (energy first); the MCFM kernel signature `*_me2(double p[N][4])` uses
  `{px,py,pz,E}` (energy last). Every fixture conversion has to reorder. The metric is
  mostly-minus.
- **The incoming-leg sign flip — where it happens and where it must not.** Both codes store
  incoming legs with negative energy inside, so *inside a kernel* reading `evt.*` there is
  **no flip**. It is the *validator and the tests* that hand back real (positive-energy)
  momenta, so when you build the `p[N][4]` array you flip the sign of particles 0 and 1.
  Saying "flip all incoming particles" as one blanket rule is a known mistake — it is only
  for building the array, not for reads inside the kernel.
- **Kernel basics.** Complex type `C = Kokkos::complex<double>` (`../math.h`); event data is
  SoA, particles are 0-based with 0 and 1 always incoming, the result is `evt.me2(i)`; put a
  skip-empty-event guard `if (evt.w(i)==0.0) return;` at the top of every kernel; pass module
  globals in as a plain `<Name>_Params` struct by value.
- **Naming.** `<name>_kernel.h` plus a one-line `<name>_kernel.cpp` listed in
  `src/CMakeLists.txt`; entry point `double <name>_me2(double p[N][4], const <Name>_Params&)`;
  helpers are `KOKKOS_INLINE_FUNCTION` inside `namespace mcfm_<name>`. Reuse an
  already-checked helper by including it; never re-derive one.
- **Couplings.** Built on the host with MCFM's `couplz` convention at fixed Z-pole inputs
  (`xw=0.2312`, `alpha_s=0.118`, `m_Z=91.1876`, finite part `epinv=0`), so every reference
  number can be reproduced.

## §3 Rewriting rules (MCFM C++ → Kokkos kernel)

| MCFM C++ | Pepper Kokkos kernel |
|---|---|
| free host function | `KOKKOS_INLINE_FUNCTION` helper; template only the dispatch entry |
| `std::complex<double>` | `C` (from `../math.h`); imaginary unit `C(0,1)` |
| `std::sqrt/log/pow/…` | `Kokkos::sqrt/log/pow/…` (never bare `std::` in device code) |
| `FArray` (1-based) | fixed-size local arrays, 0-based (`C za[N][N]`), no heap |
| module globals | fields of the POD `*_Params` struct |
| out-array + wrapper | scalar `*_me2(...)` return; the template kernel writes `evt.me2(i)` |
| QCDLoop (`loopI2/3/4`, `qli*`) | direct formulas (§5) — QCDLoop is not device code |

Two rules deserve their own line:

- **`Kokkos::complex` is not `std::complex`.** Its `/` divides using the 1-norm of the
  divisor, so complex divisions only agree to rounding. Prefer multiply-by-conjugate; set
  tolerances for division-heavy code at 1e-10; if a check gets stuck near 1e-12, suspect this
  before hunting for a math bug.
- **Keep the amplitude's structure** (for example, Born then K-factor) — same spirit as step
  1's "keep every call."

## Which target to do next, and how big it is (Resolution)

A runner does not pick targets freely; the `port` workflow, the CodeScribe loop, and a person
all follow this, and this section (not the runner) is the source of truth.

- **First:** MCFM must be built (§1.3) before you can size any target.
- **Which one (in order).** Do a Born before its virtual, so earlier frozen pieces can be
  reused. A target is ready when the Closure tool says its whole call tree is C++ (step-1
  ready) *and* its step-1 files are tagged `VERIFIED` in the step-1 Plan
  (`dev/transformations/fortran-to-cpp/current_plan.md`). Auto-pick (`port … from:`) reads
  those tags; giving an explicit `target:` skips the search.
- **How big (direct vs split).** Size the call tree with the Closure tool. A small tree
  (about 30 pieces or fewer) is done in one pass; a bigger one uses the split plan (§7):
  break it into pieces, do them bottom-up, check each against its own reference, then join.
  The number is a guide, not a hard rule — split sooner if one agent can't hold the whole
  tree.

## §4 Steps for one amplitude

1. **Map the call tree and check it can move to the GPU.** Follow every call from the entry
   `.cpp`; list the tree, the module globals it reads (→ Params fields), the things that
   can't go on the GPU as-is (QCDLoop → §5, STL, heap, I/O), and the already-ported helpers
   you can reuse. Double-check you have everything with
   `python3 dev/tools/closure/calltree_closure.py <name>` — it reads `libmcfm`'s linked
   pieces (symbols don't lie) and flags any still-Fortran piece as a step-1 gap.
2. **Write the kernel header** bottom-up: GPU-safe helpers first, then the plain
   `<name>_me2(p, params)`, then the templated kernel that reads `evt.*` and writes
   `evt.me2(i)`. Add the one-line `.cpp`. Split big trees at function boundaries (§7).
3. **Direct formulas for the loop integrals** — only if the amplitude calls QCDLoop (§5).
4. **Compare against `libmcfm`** on the host through the Kokkos shim, layer by layer: loop
   functions → sub-amplitudes → full `|M|²`, aiming for 1e-10 relative, with the same fixed
   inputs and momenta on both sides. This is the `validate` workflow.
5. **Tests and build wiring**: add layered `DOCTEST_TEST_CASE`s like the existing
   `MCFM-analytics` ones (they check against saved reference numbers, not a live `libmcfm`);
   list the header + `.cpp` in `src/CMakeLists.txt`. Build and run the check with
   `jobrunner submit tests/pepper`, or faster with `pepper_test --dt-test-case="*<name>*"`.
6. **Report** the files written, the worst relative error per layer, and any blockers.
   Verified = the tests pass; otherwise translated.

## §5 Loop integrals: direct formulas on the GPU

QCDLoop can't run inside a kernel. Replace each call with a direct `KOKKOS_INLINE_FUNCTION`
formula (Ellis–Zanderighi 0712.1851; QCDLoop 2.0 1605.03181) and check it **on its own**
against the real QCDLoop through `libmcfm` (~1e-12) before using it. Staying accurate near
thresholds is an open problem on the GPU (subtracting two nearly-equal dilogs loses
precision, and there is no cheap high-precision fallback per thread): pick a plan per
integral — a safe expanded formula, accept a few bad points, or flag shaky inputs on the host
— and write down which one you chose. High-multiplicity boxes are the hard case; bubbles and
triangles have been fine.

## §6 Why the check is "matches MCFM", not physics

Pepper has no one-loop math of its own, so virtual kernels are checked by **matching MCFM
number-for-number**, not by redoing the physics: the tests' reference numbers are MCFM's
results for the same inputs, so a passing test means the kernel reproduces MCFM block by
block and for the full `|M|²`. The `libmcfm` comparison (§4 step 4) is the same check, run on
the side while you write. The physics itself was checked in step 1.

## §7 Splitting a big call tree across agents

A kernel pulls in its whole call tree (no calls out of the GPU code), so the unit of work is
the flattened tree, not the file. Because each MCFM C++ function has an exact reference in
`libmcfm`, **every piece has its own reference** — which is what makes splitting safe:

1. Split at function boundaries, never by line count.
2. Lay out the pieces and do them bottom-up: leaves first (in parallel), then sub-amplitudes,
   then the join. One agent per piece; each one reports the globals it needs (these become
   Params fields).
3. Check each piece against its `libmcfm` twin before joining (≤1e-12 → frozen).
4. Join: the joining agent includes the frozen pieces, writes the `*_Params` struct and the
   kernel, then runs the full check. If the full `|M|²` disagrees while every piece passes,
   the bug is in the join — a small place to look.

**Convention:** pieces live in `mcfm_analytics/<name>_parts/<piece>.h`, all inside
`namespace mcfm_<name>`; only the final `<name>_kernel.h` + `.cpp` go in CMake. Every header
has a `// MCFM sources: …` comment saying where it came from — that is what the closure tool
reads to work out reuse. A frozen piece is never edited by a later agent; if the full `|M|²`
then disagrees, fix the join, not the pieces.

## §8 References

Pepper (arXiv:2311.06198); MadGraph4GPU/CUDACPP (arXiv:2312.02898, splitting
arXiv:2510.05392); scalar closed forms (arXiv:0712.1851); QCDLoop 2.0 (arXiv:1605.03181);
`Kokkos::complex` non-drop-in (kokkos/kokkos#7618).
