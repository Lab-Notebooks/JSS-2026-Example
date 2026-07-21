# C++ → Kokkos plan

How to run this step: rewrite MCFM's C++ amplitudes (the output of step 1) as Pepper Kokkos
kernels, in order of need, and check each one. The **rules** for a kernel and the
**correctness bar** live in the Spec (`desired_spec.md`); this Plan holds how to do the work.
The runner is the CodeScribe loop (`loop.toml`), which reads both files and does the work end
to end, beyond the one-time machine setup in the README.

## Your checklist

The list of amplitudes in flight keeps changing, so it does not live in this Plan. Keep it in
a separate file you create, **`agent_checklist.md`** in this folder — create it if it isn't
there yet, and keep it current as you work. It holds the amplitudes to do (in order of need),
a checkbox each, and each one's result. This is the shared record across sessions; the durable
prose notes go in the session log at the bottom of this Plan.

**How to record a result.** When an amplitude is done, tag its line:

- `- [x] <name> — TRANSLATED (maxRelErr <value>)` — matches `libmcfm`, builds, and the
  existing tests still pass. This is as far as a runner goes (see the Spec's correctness bar).
- `- [ ] <name> — FAILED (<what went wrong>)` — cannot be made to match; hand it to a person.
- `- [x] <name> — VERIFIED (<doctest>)` — written by a **person**, after they add a frozen
  reference doctest that passes. A runner never writes this tag.

Paths are written as `software/pepper/src/mcfm_analytics/…`.

**The approval gate (how a person signs off).** Group the amplitudes in flight under headings
whose text starts with `Group` in `agent_checklist.md`. When a person has reviewed a group's
results they write a line under that group's heading:

```
APPROVED 2026-07-21 by <name>
```

A runner must **not start a new group while an earlier, completed group is unapproved** — the
"a human approves each step before the next one starts" rule, made mechanical. Check it before
picking the next group:

```
python3 dev/tools/approve/check_gate.py dev/transformations/cpp-to-kokkos/agent_checklist.md
```

It exits non-zero and names any completed-but-unapproved group; stop and get sign-off first.

## Tools

Every tool is a plain `python3 <path> ...` call — each shells out to whatever it needs (`nm`,
a C++ compiler) itself. Each explains its own flags at the top of its file; this is only what
each is for.

- `dev/tools/closure/calltree_closure.py <name>` — **Closure.** Lists everything an amplitude
  calls (its transitive closure), read from what `libmcfm` actually links — not from source —
  so it tells you how many pieces there are, whether they're all C++ yet (step-1 ready), and
  which are already reused via a ported header's `// MCFM sources:` line.
- `dev/tools/kokkos/kokkosify.py <input.cpp> [-o draft.h] [-r report.md]` — **Kokkosify.** Does
  the mechanical parts of the Spec's rewriting rules and marks what it can't decide with
  `KOKKOSIFY-TODO` for you to finish.
- `dev/tools/kokkos/kokkosify.py validate <validator.cpp>` — **Compare-against-MCFM harness.**
  Builds a small host-side test that links `libmcfm` and includes your kernel, runs it, and
  prints each check (reference / got / relative error). Reads `MCFM_DIR`/`KERNELS_DIR` from
  its own environment (or falls back to `MCFM_HOME`/`PEPPER_HOME`), so call it plainly, no
  `$` needed.
- `dev/tools/approve/check_gate.py <agent_checklist.md>` — **Gate.** Same as step 1.

The two non-python3 commands are `jobrunner submit tests/mcfm` and `jobrunner submit
tests/pepper`, which build each codebase and run its tests in one shot. Run both once before
the first round if they haven't been built yet — Closure and the compare harness both need a
built `libmcfm`.

## Which target to do next, and how big it is (Resolution)

A runner does not pick targets freely — this section is the source of truth.

- **Which one (in order).** Do a Born before its virtual, so earlier frozen pieces can be
  reused. A target is ready when the Closure tool says its whole call tree is C++ (step-1
  ready) *and* its step-1 files are tagged `VERIFIED` in the step-1 checklist
  (`dev/transformations/fortran-to-cpp/agent_checklist.md`).
- **How big (direct vs split).** Size the call tree with the Closure tool. A small tree
  (about 30 pieces or fewer) is done in one pass; a bigger one uses the splitting procedure
  below: break it into pieces, do them bottom-up, check each against its own reference, then
  join. The number is a guide, not a hard rule — split sooner if one agent can't hold the
  whole tree.

## Shell notes

CodeScribe's bash tool is limited: it refuses the characters `$ | & ; < > \``, refuses any
command whose first word is not on `loop.toml`'s allow-list, and does not expand
`$VARIABLES` when reading or writing files. In practice this means:

- **Use plain relative paths** — `software/mcfm/src/<...>` and
  `software/pepper/src/mcfm_analytics/<...>`, not `$MCFM_HOME/...` / `$PEPPER_HOME/...`.
- **No `cd`, no pipes, no redirects** — every tool above takes plain arguments and prints
  what it did.

## Authoring a kernel (the steps)

1. **Map the call tree and check it can move to the GPU.** Follow every call from the entry
   `.cpp`; list the tree, the module globals it reads (→ `*_Params` fields), the things that
   can't go on the GPU as-is (QCDLoop → the Spec's loop-integral rule, the C++ standard library
   (STL), heap, I/O), and the already-ported helpers you can reuse. Double-check with the
   Closure tool — it reads `libmcfm`'s linked pieces (symbols don't lie).
2. **Write the kernel header** bottom-up, following the Spec's "what a kernel looks like" and
   its rewriting rules: GPU-safe helpers first, then the plain `<name>_me2(p, params)`, then
   the templated kernel that reads `evt.*` and writes `evt.me2(i)`. Add the one-line `.cpp`.
   Split big trees at function boundaries (see "Splitting" below). Use Kokkosify for the
   mechanical parts first.
3. **Direct formulas for the loop integrals** — only if the amplitude calls QCDLoop (the
   Spec's loop-integral rule).
4. **Compare against `libmcfm`** with the compare-against-MCFM harness, on the host through
   the Kokkos shim, layer by layer: loop functions → sub-amplitudes → full `|M|²`, aiming for
   1e-10 relative, with the same fixed inputs and momenta on both sides. Fix and re-run until
   it holds.
5. **Build wiring, then run the tests.** List the header + `.cpp` in `src/CMakeLists.txt`,
   then build and run the existing suite with `jobrunner submit tests/pepper` (or faster,
   `pepper_test --dt-test-case="*<name>*"`). Do **not** author new reference
   `DOCTEST_TEST_CASE`s (the Spec's bar leaves that to the developer); instead report which
   layered cases the developer should add, mirroring the existing `MCFM-analytics` ones.
6. **Report** the files written, the worst relative error per layer, the tests the developer
   should add, and any blockers.

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
