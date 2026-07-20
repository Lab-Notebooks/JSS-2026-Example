# Fortran → C++ plan

How to run this step: rewrite MCFM's Fortran files as C++, one file at a time, in the
order the map allows, and check each result. The **rules** for a single file and the
**correctness bar** live in the Spec (`desired_spec.md`); this Plan holds how to do the
work — the helper programs, the running-command rules, which files to do next, and the
running notes across sessions.

## Your checklist

The list of files in flight keeps changing, so it does not live in this Plan. Keep it in a
separate file you create, **`agent_checklist.md`** in this folder — create it if it isn't
there yet, and keep it current as you work. It holds the ready files grouped into
review-sized batches (see Resolution below), a checkbox per file, and each file's result.
This is the shared record across sessions; the durable prose notes go in the session log at
the bottom of this Plan.

**How to record a result** (write these in `agent_checklist.md`, not here). When a file is
done, tag its line so a program can read the result — step 2's `port … from:fortran-to-cpp`
only picks files tagged `VERIFIED`:

- `- [x] <file> — VERIFIED (worst Δrel <value>)` — the coverage check passed and the numbers match.
- `- [x] <file> — TRANSLATED (<reason>)` — builds, but not verified (not on a test's path,
  it's infrastructure, or the check was left for a normal-shell pass, see the Spec's
  correctness bar).
- `- [ ] <file> — FAILED (<what went wrong>)` — a bad rewrite handed to a person.

Only a runner with a normal shell (the `translate` combining step, or a person) may write
`VERIFIED`; a CodeScribe run writes `TRANSLATED` and leaves the upgrade to the check pass.
Paths are written as `software/mcfm/src/...` (the `$MCFM_HOME/src` form is only for a normal
shell — see "Running commands").

## Helper programs (Tools)

The workflow runs these small programs by name. They always do the same thing (no AI
guessing). Each one explains how to use it at the top of its own file under `dev/tools/`.

- **Find what's ready (Index).** `dev/tools/index/generate_doxygen.sh` maps out which file
  calls which, then `dev/tools/index/build_roadmap.py` ranks files by how ready they are to
  rewrite. It writes `dev/tmp/assets/roadmap_metrics.tsv` (a file is ready when `deps==0`
  and `blind==0`) and a name→file map `dev/tmp/assets/symbol_index.json`.
- **First draft (Draft).** `dev/tools/draft/scribe_draft.py <file.f>` writes a rough
  starting draft and flags which called names come from other files, so you don't invent
  them (see the Spec's rewrite rules — don't invent a called name). Use it with the worked
  examples in `dev/tools/draft/seed_examples.toml`.

Run `generate_doxygen.sh` once, ahead of time, in a normal shell. CodeScribe's limited
shell can't run it, so do it first; it leaves its output under `software/mcfm/doxygen_dep/xml`.

## Running commands (works in both runners)

Two runners drive this step, and they have different shells, so write commands that work in
both. The Claude Code `translate` workflow has a normal shell. The CodeScribe loop has a
**limited** shell: it refuses the characters `$ | & ; < > \``, refuses any command whose
first word is not on its allow-list, and does not fill in `$VARIABLES` when reading or
writing files.

- **Use plain relative paths.** Write `software/mcfm/src/<...>`, not `$MCFM_HOME/src/<...>`.
  The `$MCFM_HOME`/`$PEPPER_HOME` shortcuts elsewhere only work in a normal shell.
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
   Fortran-only routines; inventing those missing routines is exactly what the Spec's rewrite
   rules forbid.
2. **Optional focus.** You can limit a run to one top-level `src/` folder; otherwise take
   ready files from anywhere.
3. **Group for review.** Put the ready files into review-sized groups a person can check
   without being overwhelmed: keep each group on one topic (same folder, same test from
   the Spec's test-coverage table) and small (about 5 files). Write the groups in
   `agent_checklist.md`; a person approves one group at a time.
4. **Write in parallel, combine one at a time.** Rewrite each file on its own (it only
   touches its own output). Then one step combines them: it owns the build, wires the new
   files in, and runs the coverage check (see "How to verify" below). Give a big or deeply nested file (about 400+
   lines) a stronger model or extra care — those go wrong most often.
5. **Look again after combining.** Once a group is combined its files are now C++, so a file
   that was `blind` (it called a not-yet-rewritten routine) becomes ready. Re-run the Index
   to refresh the map, then pick the next group.

This ordering is the whole point of the map: a writer is only ever handed a file whose
called routines are already in C++.

## How to do the work

1. **Index first** — build the call map once in a normal shell, then rank the files:
   ```
   source environment.sh
   dev/tools/index/generate_doxygen.sh          # one-time, normal shell; writes the call map
   python3 dev/tools/index/build_roadmap.py     # -> dev/tmp/assets/roadmap_metrics.tsv
   ```
   Which files to take, how to group them, and the order all follow the Resolution section
   above (ready files are the rows with `deps==0` and `blind==0`). The Doxygen step can't run
   in CodeScribe's limited shell, so do it before starting a run.
2. **Draft, then rewrite** each ready file: `dev/tools/draft/scribe_draft.py <file.f>` for
   the rough draft and its don't-invent-a-called-name hints, then the real rewrite following `desired_spec.md` and
   `dev/tools/draft/seed_examples.toml`. The `translate` workflow does this for you
   (index → resolve → bundle → author → integrate) and refreshes the checklist.
3. **Check and cover** (see "How to verify" below): `jobrunner submit tests/mcfm` builds MCFM
   and runs the test suite; the coverage check then tells *verified* from *translated*.
4. **Record** the result in `agent_checklist.md` — flip the box, add the tag and a one-line
   note — and, before you stop, add a dated line to the session log below so the next round
   knows what happened.

## Silent traps to self-check

Most rewriting bugs are *silent*: the code builds, links, and may even pass the test, but is
still wrong. Each one below happened on a real MCFM file. Use them as a self-check, and rely
on the coverage check to catch what you miss.

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

## How to verify (the coverage check)

The Spec's "correctness bar" defines *verified* vs *translated*; this is how you run it. Build
and run the tests through the harness — one command both runners can use, which sets up the
environment, builds, and runs the tests:

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

It passes only when all four numbers match to within **1e-13**. To confirm the code is linked
in, run `nm software/mcfm/Bin/libmcfm.*` and read its output for `<name>` (don't pipe to
`grep`; the limited shell won't allow it).

**Always run the coverage check before calling anything VERIFIED.** A passing test can report
a match without ever reaching your routine, so prove it ran:

1. Multiply the file's main output by 1.5 for a moment.
2. Rebuild (just relink the one file) and re-run the test that passed.
3. If the numbers **change**, your code ran → undo the 1.5×, rebuild to confirm it PASSES,
   and mark **VERIFIED**.
4. If the numbers **don't change**, the test never reached your code → mark **TRANSLATED**
   (not verified). Check again later, after a routine that calls it is rewritten.

Always undo every check edit and leave the build clean. This check needs a normal shell (a
single-file relink and re-run), which the limited shell can't do — so a CodeScribe run marks
files **TRANSLATED** and leaves the check, and the VERIFIED upgrade, to a normal-shell pass
(the `translate` combining step, or a person).

## Notes / session log

- Files in `Mods/Need/Inc/Procdep` have no test that runs them — mark them *translated*,
  never *verified* (see the Spec's test-coverage table).
- If a coverage check shows no change, the file just isn't on a test's path yet; check it
  again after a file that calls it is rewritten.
- If you suspect a bad rewrite, mark it FAILED with the symptom instead of guessing; hand a
  small number mismatch to a person and note it here.
- _(Add a dated line per session: what you did, what's left, anything a person must decide.)_
