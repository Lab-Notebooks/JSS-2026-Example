# C++ → Kokkos plan

How to run this step: rewrite MCFM's C++ amplitudes (the output of step 1) as Pepper Kokkos
kernels, in order of need, and check each one. The **rules** for a kernel and the
**correctness bar** live in the Spec (`desired_spec.md`); this Plan holds how to do the work
— the helper programs, the running-command rules, which target to do next, and the running
notes across sessions.

## Your checklist

The list of amplitudes in flight keeps changing, so it does not live in this Plan. Keep it in
a separate file you create, **`agent_checklist.md`** in this folder — create it if it isn't
there yet, and keep it current as you work. It holds the amplitudes to do (in order of need),
a checkbox each, and each one's result. This is the shared record across sessions; the durable
prose notes go in the session log at the bottom of this Plan.

**How to record a result** (write these in `agent_checklist.md`, not here). When an amplitude
is done, add a tag: `- [x] <name> — VERIFIED (maxRelErr <value>)`,
`- [x] <name> — TRANSLATED (<reason>)`, or `- [ ] <name> — FAILED (<what went wrong>)`. A
runner tops out at `TRANSLATED` (the compare-against-`libmcfm` match holds and the build and
existing tests are clean); a person adds the reference doctest and, when it passes, marks it
`VERIFIED` (see the Spec's correctness bar). Paths are written as
`software/pepper/src/mcfm_analytics/…` (the `$PEPPER_HOME` form is only for a normal shell —
see "Running commands").

## Helper programs (Tools)

The `port` workflow (including its built-in check-and-fix loop) runs these small programs by
name. Each explains how to use it at the top of its own file under `dev/tools/`.

- **Closure.** `dev/tools/closure/calltree_closure.py <name>` lists everything an amplitude
  calls (its "closure") by reading what `libmcfm` links, and says how many pieces there are
  and whether they are all C++ (ready for step 2).
- **First draft (Kokkosify).** `dev/tools/kokkos/kokkosify.py` does the easy, mechanical
  parts of the Spec's rewriting rules and marks what it can't decide with `KOKKOSIFY-TODO`
  for the author to finish.
- **Compare-against-MCFM harness.** `dev/tools/kokkos/run_validation.sh <validator.cpp>`
  builds a small test that links `libmcfm` and includes your kernel, runs it, and prints
  each check (reference / got / relative error). It does not save a file itself; port's
  check-and-fix loop reads what it prints and saves it to `dev/tmp/assets/validate-output.md`
  for the fix step.

## Running commands (works in both runners)

Two runners drive this step, and they have different shells. The Claude Code `port` workflow
has a normal shell; the CodeScribe loop has a **limited** shell: it refuses the
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

## Which target to do next, and how big it is (Resolution)

A runner does not pick targets freely; the `port` workflow, the CodeScribe loop, and a person
all follow this, and this section (not the runner) is the source of truth.

- **First:** MCFM must be built (see "Before you start" below) before you can size any target.
- **Which one (in order).** Do a Born before its virtual, so earlier frozen pieces can be
  reused. A target is ready when the Closure tool says its whole call tree is C++ (step-1
  ready) *and* its step-1 files are tagged `VERIFIED` in the step-1 checklist
  (`dev/transformations/fortran-to-cpp/agent_checklist.md`). Auto-pick (`port … from:`) reads
  those tags; giving an explicit `target:` skips the search.
- **How big (direct vs split).** Size the call tree with the Closure tool. A small tree
  (about 30 pieces or fewer) is done in one pass; a bigger one uses the splitting procedure
  below: break it into pieces, do them bottom-up, check each against its own reference, then
  join. The number is a guide, not a hard rule — split sooner if one agent can't hold the
  whole tree.

## Before you start

1. `source "$PROJECT_HOME/environment.sh"` — sets `PEPPER_HOME`, `QCDLOOP_HOME`, `MCFM_HOME`
   (a one-time step in a normal shell; both runners inherit it).
2. The Pepper copy is on the `mcfm_analytics` branch. `jobrunner submit tests/pepper` builds
   Pepper on its own (Kokkos + QCDLoop, no MCFM) and runs the tests.
3. **You must build MCFM first — it is required, not optional.** Run
   `jobrunner submit tests/mcfm` before anything else: the Closure tool reads `libmcfm` to
   find the call tree, and the compare harness links `libmcfm`. On a fresh checkout, picking
   or sizing a target and matching against `libmcfm` both fail until MCFM is built.

## How to do the work

1. **Check reuse and step-1 readiness**:
   `python3 dev/tools/closure/calltree_closure.py <name>` lists everything the amplitude
   calls, read from the linked pieces. A still-Fortran piece in that list is a step-1 gap;
   finish it in `dev/transformations/fortran-to-cpp/` before rewriting.
2. **Rewrite** with the `port` workflow: `args:{projectRoot, transformation:"cpp-to-kokkos",
   target:"<name>"}` for one (or `targets:[...]` in order). Auto-pick (`from:"fortran-to-cpp"`,
   no target) rewrites the files the step-1 checklist tags `VERIFIED` whose call tree is fully
   C++; it only finds work once step 1 has verified the target's dependencies, so for the
   list below (whose C++ dependencies already ship) pass an explicit `target:`. It sizes the
   tree, writes the kernel (one pass or split, per "Authoring a kernel" below), compares
   against `libmcfm` while writing, then wires up and runs the existing tests.
3. **Check**: `jobrunner submit tests/pepper` builds Pepper on its own and runs the tests.
   Run it to root out compile/link errors and runtime crashes and to confirm the pre-existing
   cases still pass; a runner does **not** author new reference doctests — that is the
   developer's job (see the Spec's correctness bar).
4. **Record** the result in `agent_checklist.md` (flip the box, add the tag and the worst
   relative error) and, before you stop, add a dated line to the session log below.

## Authoring a kernel (the steps)

This is the ladder the `port` workflow follows for one amplitude; a person doing it by hand
follows the same order.

1. **Map the call tree and check it can move to the GPU.** Follow every call from the entry
   `.cpp`; list the tree, the module globals it reads (→ `*_Params` fields), the things that
   can't go on the GPU as-is (QCDLoop → the Spec's loop-integral rule, STL, heap, I/O), and
   the already-ported helpers you can reuse. Double-check with
   `python3 dev/tools/closure/calltree_closure.py <name>` — it reads `libmcfm`'s linked pieces
   (symbols don't lie) and flags any still-Fortran piece as a step-1 gap.
2. **Write the kernel header** bottom-up, following the Spec's "what a kernel looks like" and
   its rewriting rules: GPU-safe helpers first, then the plain `<name>_me2(p, params)`, then
   the templated kernel that reads `evt.*` and writes `evt.me2(i)`. Add the one-line `.cpp`.
   Split big trees at function boundaries (see "Splitting" below).
3. **Direct formulas for the loop integrals** — only if the amplitude calls QCDLoop (the
   Spec's loop-integral rule).
4. **Compare against `libmcfm`** on the host through the Kokkos shim, layer by layer: loop
   functions → sub-amplitudes → full `|M|²`, aiming for 1e-10 relative, with the same fixed
   inputs and momenta on both sides. This is port's built-in check-and-fix loop.
5. **Build wiring, then run the tests.** List the header + `.cpp` in `src/CMakeLists.txt`,
   then build and run the existing suite with `jobrunner submit tests/pepper` (or faster,
   `pepper_test --dt-test-case="*<name>*"`). Do **not** author new reference
   `DOCTEST_TEST_CASE`s (the Spec's bar leaves that to the developer); instead report which
   layered cases the developer should add, mirroring the existing `MCFM-analytics` ones.
6. **Report** the files written, the worst relative error per layer, the tests the developer
   should add, and any blockers.

## Traps to self-check

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

## Splitting a big call tree across agents

A kernel pulls in its whole call tree (no calls out of the GPU code), so the unit of work is
the flattened tree, not the file. Because each MCFM C++ function has an exact reference in
`libmcfm`, **every piece has its own reference** — which is what makes splitting safe. The
desired file layout is fixed by the Spec ("how split pieces are laid out"); the procedure is:

1. Split at function boundaries, never by line count.
2. Lay out the pieces and do them bottom-up: leaves first (in parallel), then sub-amplitudes,
   then the join. One agent per piece; each one reports the globals it needs (→ Params fields).
3. Check each piece against its `libmcfm` twin before joining (≤1e-12 → frozen).
4. Join: the joining agent includes the frozen pieces, writes the `*_Params` struct and the
   kernel, then runs the full check. If the full `|M|²` disagrees while every piece passes,
   the bug is in the join — a small place to look. Fix the join, not the frozen pieces.

## Notes / session log

- **Where things stand.** The Z Born and single-jet cases already ship as ready reference
  kernels in `software/pepper/src/mcfm_analytics/` (use them as test references and to reuse
  pieces): `qqb_z` (Born, direct K-factor, no QCDLoop), `qqb_z_v` (first virtual, smallest
  real loop functions), `qqb_z1jet` (Born), and `qqb_z1jet_v` (loop functions + heavy-quark
  axial anomaly). `qqb_z2jet` is the open demo target (bigger call tree → uses the splitting
  procedure above); `qqb_z2jet_v` (virtual, boxes) is the hard case and needs a
  loop-integral accuracy-near-threshold decision.
- The step-2 check is "matches MCFM", not physics (the Spec's correctness bar): a kernel is
  correct once it reproduces MCFM's reference numbers block by block. Pepper does not link
  MCFM; `libmcfm` is only the compare-while-writing helper.
- Watch the `Kokkos::complex` division catch (the Spec's rewriting rules): division-heavy code
  only agrees to ~1e-10, not 1e-13.
- High-multiplicity box integrals are the open hard case (the Spec's loop-integral rule): pick
  the accuracy-near-threshold plan on purpose and write down which one, per integral.
- If a rewrite needs a person to compare runs by hand, hand it to a person and note it here.
- _(Add a dated line per session: what you did, what's left, anything a person must decide.)_
