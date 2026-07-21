# Fortran → C++ plan

How to run this step: rewrite MCFM's Fortran files as C++, one file at a time, in the order
the map allows, and check each result. The **rules** for a single file and the **correctness
bar** live in the Spec (`desired_spec.md`); this Plan holds how to do the work. The runner is
the CodeScribe loop (`loop.toml`), which reads both files and does the work end to end —
there is nothing to set up by hand first.

## Your checklist

The list of files in flight keeps changing, so it does not live in this Plan. Keep it in a
separate file you create, **`agent_checklist.md`** in this folder — create it if it isn't
there yet, and keep it current as you work. It holds the ready files grouped into
review-sized batches (see Resolution below), a checkbox per file, and each file's result.
This is the shared record across sessions; the durable prose notes go in the session log at
the bottom of this Plan.

**How to record a result.** When a file is done, tag its line so a program can read the
result — the cpp-to-kokkos step only picks files tagged `VERIFIED`:

- `- [x] <file> — VERIFIED (worst Δrel <value>)` — the coverage check passed and the numbers
  match.
- `- [x] <file> — TRANSLATED (<reason>)` — builds, but not verified (not on a test's path, or
  it's infrastructure; see the Spec's correctness bar).
- `- [ ] <file> — FAILED (<what went wrong>)` — a bad rewrite handed to a person.

Paths are written as `software/mcfm/src/...`.

**The approval gate (how a person signs off a group).** A person reviews one group's results
and, when happy, writes a line right under that group's heading in `agent_checklist.md`:

```
APPROVED 2026-07-21 by <name>
```

A runner must **not start a new group while an earlier, completed group is unapproved** — that
is the "a human approves each step before the next one starts" rule made mechanical. Check it
with the gate tool before picking the next group:

```
python3 dev/tools/approve/check_gate.py dev/transformations/fortran-to-cpp/agent_checklist.md
```

It exits non-zero and names any completed-but-unapproved group; stop and get sign-off first.

## Tools

Every tool is a plain `python3 <path> ...` call — none need a special shell, since each one
shells out to whatever it needs (doxygen, cmake, make) itself. Each explains its own flags at
the top of its file; this is only what each is for.

- `dev/tools/index/build_roadmap.py` — **Index.** `--doxygen` (re)generates the call-graph
  XML; with no flag, ranks files by translation readiness into
  `dev/tmp/assets/roadmap_metrics.tsv` and writes the name→file map
  `dev/tmp/assets/symbol_index.json`. Run both, in order, at the start of every round — cheap,
  and it's how newly-rewritten files unblock the ones that called them.
- `dev/tools/draft/scribe_draft.py <file.f>` — **Draft.** A rough starting draft plus flags for
  which called names come from other files, so you don't invent them. `--seed` prints the
  worked examples (one subroutine, one module) to translate from.
- `dev/tools/coverage/coverage_check.py <file.cpp> -- <process>` — **Coverage.** Proves a test
  actually ran a rewritten file — the *verified* vs *translated* decision (see "Verify"
  below).
- `dev/tools/approve/check_gate.py <agent_checklist.md>` — **Gate.** Fails if a completed
  review group has no `APPROVED` line (see above).

The one non-python3 command is `jobrunner submit tests/mcfm`, which builds MCFM and runs its
full benchmark suite in one shot — use it to get an initial build before the first round, and
any time you want to check a run beyond a single file's coverage check.

## Which files to do next (Resolution)

The unit of work is one file, and the order is set by which file needs which — a runner does
not pick freely.

1. **Only "ready" files.** In `dev/tmp/assets/roadmap_metrics.tsv` (from the Index tool), a
   file is **ready** when `deps == 0` and `blind == 0` — every routine it calls is already in
   C++ — and it has no `.cpp` version yet. Don't rewrite a file that still calls Fortran-only
   routines; inventing those missing routines is exactly what the Spec's rewrite rules forbid.
2. **Optional focus.** You can limit a run to one top-level `src/` folder; otherwise take
   ready files from anywhere.
3. **Group for review.** Put the ready files into review-sized groups a person can check
   without being overwhelmed: keep each group on one topic (same folder, same test from the
   Spec's test-coverage table) and small (about 5 files). Write the groups in
   `agent_checklist.md` under a heading whose text starts with `Group` (so the gate tool can
   find it), one group per heading. A person approves one group at a time (see "The approval
   gate" above); do not start a new group until the previous completed one is signed off.
4. **Rewrite the group, then build it.** Draft and rewrite each ready file (it only touches
   its own output), wire the new files into the folder's `CMakeLists.txt`, build, and run the
   coverage check per file (see "Verify" below). Give a big or deeply nested file (about 400+
   lines) a stronger model or extra care — those go wrong most often.
5. **Look again after building.** Once a group is built its files are now C++, so a file that
   was `blind` (it called a not-yet-rewritten routine) becomes ready. Check the approval gate
   so the just-finished group is signed off, then re-run the Index to refresh the map and pick
   the next group.

This ordering is the whole point of the map: a writer is only ever handed a file whose called
routines are already in C++.

## Shell notes

CodeScribe's bash tool is limited: it refuses the characters `$ | & ; < > \``, refuses any
command whose first word is not on `loop.toml`'s allow-list, and does not expand
`$VARIABLES` when reading or writing files. In practice this means:

- **Use plain relative paths** — `software/mcfm/src/<...>`, not `$MCFM_HOME/src/<...>`.
- **No `cd`, no pipes, no redirects** — every tool above takes plain arguments and prints
  what it did; there's nothing to pipe into `grep` or `tail`.

## Verify (the coverage check)

The Spec's "correctness bar" defines what VERIFIED/TRANSLATED/FAILED mean; this is how to
produce that result. Mark the one statement that writes the file's main output with
`// @coverage-probe`, e.g. `msq(i, j) = ampsq;   // @coverage-probe`, then run:

```
python3 dev/tools/coverage/coverage_check.py <file.cpp> -- <process>
```

using the process the Spec's test-coverage table maps to the file's folder (e.g.
`-- u u~ e- e+` for `Z`). It builds, records the numbers, scales the marked output, rebuilds,
compares, then always restores the file and rebuilds clean — a forgotten undo can never
poison the tree. It exits reporting **COVERED** (mark VERIFIED, once the restored build's
match is confirmed) or **NOT COVERED** (mark TRANSLATED; check again once a file that calls it
is rewritten).

## Notes / session log

- Files in `Mods/Need/Inc/Procdep` have no test that runs them — mark them *translated*,
  never *verified* (see the Spec's test-coverage table).
- If a coverage check shows no change, the file just isn't on a test's path yet; check it
  again after a file that calls it is rewritten.
- If you suspect a bad rewrite, mark it FAILED with the symptom instead of guessing; hand a
  small number mismatch to a person and note it here.
- _(Add a dated line per session: what you did, what's left, anything a person must decide.)_
