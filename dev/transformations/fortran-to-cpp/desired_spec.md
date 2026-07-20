# Fortran → C++: how to rewrite one MCFM file

The rules for rewriting one MCFM Fortran file as C++, and how to tell the result is
correct. The workflow and the helper programs point here instead of repeating the rules.

A file is **verified** only when a test actually runs it and the coverage check passes
(§5). Otherwise it is only **translated** (rewritten, but not yet shown to be correct).
Always say which one it is, and never call a merely-translated file correct.

Paths are written as `software/mcfm/src/...` (relative to the MCFM code). The `$MCFM_HOME/src`
form used in a few places below means the same thing; it is a shortcut for a normal shell.

---

## Helper programs (Tools)

The workflow runs these small programs by name. They always do the same thing (no AI
guessing). Each one explains how to use it at the top of its own file under `dev/tools/`.

- **Find what's ready (Index).** `dev/tools/index/generate_doxygen.sh` maps out which file
  calls which, then `dev/tools/index/build_roadmap.py` ranks files by how ready they are to
  rewrite. It writes `dev/tmp/assets/roadmap_metrics.tsv` (a file is ready when `deps==0`
  and `blind==0`) and a name→file map `dev/tmp/assets/symbol_index.json`.
- **First draft (Draft).** `dev/tools/draft/scribe_draft.py <file.f>` writes a rough
  starting draft and flags which called names come from other files, so you don't invent
  them (see rule 9a). Use it with the worked examples in `dev/tools/draft/seed_examples.toml`.

Run `generate_doxygen.sh` once, ahead of time, in a normal shell. CodeScribe's limited
shell can't run it, so do it first; it leaves its output under `software/mcfm/doxygen_dep/xml`.

## Running commands (works in both runners)

Two runners drive this step, and they have different shells, so write commands that work in
both. The Claude Code `translate` workflow has a normal shell. The CodeScribe loop has a
**limited** shell: it refuses the characters `$ | & ; < > \``, refuses any command whose
first word is not on its allow-list, and does not fill in `$VARIABLES` when reading or
writing files.

- **Use plain relative paths.** Write `software/mcfm/src/<...>`, not `$MCFM_HOME/src/<...>`.
  The `$MCFM_HOME`/`$PEPPER_HOME` shortcuts elsewhere here only work in a normal shell.
- **No `cd`, no pipes, no redirects.** Use `cmake -S software/mcfm -B software/mcfm/Bin`
  and `make -C software/mcfm/Bin install` instead of `cd … && cmake …`. Don't use `| tail`,
  `2>&1`, or `>/dev/null`; just read what the program prints.
- **Check with one command.** Build and run all the tests with `jobrunner submit tests/mcfm`
  instead of running `cmake`/`make`/`./test` yourself. That one command sets up the
  environment, builds, and runs the tests, and both shells allow it.

## Which files to do next (Resolution)

The unit of work is one file, and the order is set by which file needs which. So a runner
does not pick freely — the `translate` workflow, the CodeScribe loop, and a person all
follow the rule below. This section is the source of truth; a runner just does these steps.

1. **Only "ready" files.** In `dev/tmp/assets/roadmap_metrics.tsv` (from the Index program),
   a file is **ready** when `deps == 0` and `blind == 0` — every routine it calls is already
   in C++ — and it has no `.cpp` version yet. Don't rewrite a file that still calls
   Fortran-only routines; inventing those missing routines is exactly what rule 9a (§2)
   forbids.
2. **Optional focus.** You can limit a run to one top-level `src/` folder; otherwise take
   ready files from anywhere.
3. **Group for review.** Put the ready files into review-sized groups a person can check
   without being overwhelmed: keep each group on one topic (same folder, same test from §4)
   and small (about 5 files). Write the groups in the Plan's "Review bundles" section; a
   person approves one group at a time.
4. **Write in parallel, combine one at a time.** Rewrite each file on its own (it only
   touches its own output). Then one step combines them: it owns the build, wires the new
   files in, and runs the check in §5. Give a big or deeply nested file (about 400+ lines) a
   stronger model or extra care — those go wrong most often.
5. **Look again after combining.** Once a group is combined its files are now C++, so a file
   that was `blind` (it called a not-yet-rewritten routine) becomes ready. Re-run the Index
   to refresh the map, then pick the next group.

This ordering is the whole point of the map: a writer is only ever handed a file whose
called routines are already in C++.

---

## §1 What each file turns into

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

## §2 Rules for rewriting

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

**The rule worth repeating — don't invent a called name (rule 9a).** A file usually calls
routines defined in *other* files whose signatures you can't see. Keep every `call` that is
there; invent none. Handle each one based on whether it has been rewritten yet:

- **Already C++** (a `<dep>.cpp` file exists) → call the C++ function directly:
  `#include "<dep>.hpp"` and match its signature.
- **Still Fortran** → call it the plain Fortran way: declare
  `extern "C" void <name>_(/* every arg a pointer */);` and call `<name>_(&a, &b, …)`,
  passing arrays as the underlying pointer. Results come back through the pointers.

If a called routine is in a module that isn't rewritten yet and has no C binding, that is a
real blocker — rewrite that dependency first, don't guess around it. The readiness map (the
Index program) exists so the workflow only hands you files whose called routines are already
done.

A full worked example (a subroutine and a module, all three output files) is in the examples
the Draft step uses: `dev/tools/draft/seed_examples.toml`.

---

## §3 Mistakes that don't show up as errors

Most rewriting bugs are *silent*: the code builds, links, and may even pass the test, but is
still wrong. Each one below happened on a real MCFM file. Use them as a self-check, and rely
on the §5 coverage check to catch what you miss.

1. **A dropped `call`.** Leaving out a call whose output you don't see used, or skipping one
   of a near-identical pair (a public routine often calls its `core` worker twice, once with
   the spinor arguments swapped). This leaves outputs unset, and it builds fine.
2. **Order of × and ÷.** Fortran `)/za*za` divides by `za²`; C++ goes left to right and
   makes it `(…/za)*za`. Put parentheses around every denominator.
3. **`FArray` sizes.** Build an existing array with *all* its sizes and 1-based bounds;
   giving too few sizes silently shifts the whole buffer. There is no `FArray5D` — for 5+
   dimensions, flatten it with an index lambda.
4. **0-based vs 1-based.** Don't write index 0 of a 1-based Fortran array; keep fill loops
   1-based so every index stays in `[1,N]`.
5. **Includes.** Include the module headers the `use` lines imply (not just the file's own
   header), plus `<Need.hpp>` for the loop/spinor helpers (`lnrat`, `L0`, `spinoru`, `dot`,
   …). A missing header from another folder is the combining step's job: report the folder;
   don't edit shared CMake yourself.

If a number still disagrees after you've checked, mark it FAILED with the symptom instead of
guessing a fix — a small mismatch goes to a person.

---

## §4 Which test covers which folder

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

## §5 Checking the result, and the coverage check

Build and run the tests through the harness — one command both runners can use, which sets
up the environment, builds, and runs the tests:

```bash
jobrunner submit tests/mcfm    # builds software/mcfm/Bin and runs the full benchmark suite
```

In a normal shell you can build and run one test by hand. Write it without `cd`, pipes, or
redirects so it also works in the limited shell:

```bash
cmake -S software/mcfm -B software/mcfm/Bin
make -C software/mcfm/Bin install
software/mcfm/Bin/test -b <process>   # four numbers: Finite / IR / IR2 / Born
```

It passes only when all four numbers match to within **1e-13**. (Code that uses complex
powers can be off by about 1e-15 — that is normal and well inside the limit.) To confirm the
code is linked in, run `nm software/mcfm/Bin/libmcfm.*` and read its output for `<name>`
(don't pipe to `grep`; the limited shell won't allow it).

**Always run the coverage check before calling anything VERIFIED.** A passing test is
necessary but not enough: the fixed test inputs might never reach your routine, so it reports
a match without ever running your code. So check it:

1. Multiply the file's main output by 1.5 for a moment.
2. Rebuild (just relink the one file) and re-run the test that passed.
3. If the numbers **change**, your code ran → undo the 1.5×, rebuild to confirm it PASSES,
   and mark **VERIFIED**.
4. If the numbers **don't change**, the test never reached your code → mark **TRANSLATED**
   (not verified). Check again later, after a routine that calls it is rewritten.

Always undo every check edit and leave the build clean.

**The coverage check needs a normal shell.** Steps 1–3 need a single-file relink and re-run,
which the limited shell can't do (no `cd`, no single-file rebuild, no `./test`). So the check
— and marking something **VERIFIED** — is done by whichever runner has a normal shell: the
Claude Code `translate` workflow does it in its combining step. A CodeScribe run marks the
file **TRANSLATED** and leaves it for a normal-shell pass (the combining step, or a person)
to run the check and mark it VERIFIED. The verified-vs-translated meaning does not change,
only who can mark VERIFIED. Write each file's result in the Plan (`current_plan.md`, see its
recording note), not here.
