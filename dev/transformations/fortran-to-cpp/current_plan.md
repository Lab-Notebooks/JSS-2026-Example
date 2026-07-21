# Fortran → C++ plan

This file says how to run step 1. The rewrite rules and correctness bar are in
`desired_spec.md`.

## Checklist file

Keep the changing worklist in `agent_checklist.md` in this folder. Create it if missing and
keep it current. Use it for ready files, review groups, and per-file status. Keep durable prose
notes in the session log at the end of this file.

Record each finished file as:

- `- [x] <file> — VERIFIED (worst Δrel <value>)`
- `- [x] <file> — TRANSLATED (<reason>)`
- `- [ ] <file> — FAILED (<what went wrong>)`

Use paths like `software/mcfm/src/...`.

## Approval gate

Review groups live under headings starting with `Group` in `agent_checklist.md`. A person signs
off a finished group by adding:

```
APPROVED 2026-07-21 by <name>
```

Use the gate only when deciding whether to start a new group:

```
python3 dev/tools/approve/check_gate.py dev/transformations/fortran-to-cpp/agent_checklist.md
```

Interpret it this way:

- If a group is still open, you may keep working inside that same group.
- If an earlier group is completed but unapproved, do not start a new group.
- A gate failure blocks new-group creation, not builds, fixes, or verification inside the
  current open group.

Stop for human review only when a completed group blocks the next group.

## Tools

Run these from the project root:

- `python3 dev/tools/index/build_roadmap.py --doxygen` then
  `python3 dev/tools/index/build_roadmap.py`
  - refresh the readiness map and symbol index
- `python3 dev/tools/draft/scribe_draft.py <file.f>`
  - make a rough draft and dependency hints
- `python3 dev/tools/coverage/coverage_check.py <file.cpp> -- <process>`
  - decide VERIFIED vs TRANSLATED
- `python3 dev/tools/approve/check_gate.py <agent_checklist.md>`
  - enforce human sign-off between completed groups
- `jobrunner submit tests/mcfm`
  - full MCFM build + test run; run this before verification if MCFM is not yet built

## Resolution: which files to do next

1. Only rewrite **ready** files from `dev/tmp/assets/roadmap_metrics.tsv`:
   - `deps == 0`
   - `blind == 0`
   - no generated `.cpp` yet
2. Optional: limit one run to one top-level `src/` folder.
3. Group ready files for review:
   - same folder or test topic
   - about 5 files per group
   - headings must start with `Group`
4. If there is already an open group, keep filling and fixing that group before opening another.
5. Rewrite the group, wire it into the folder's `CMakeLists.txt`, build, and verify each file.
   - After converting a Fortran source into `<base>.cpp`, `<base>_fi.F90`, and `<base>.hpp`, move the deprecated original Fortran source file into `deprecated/` under the same directory.
6. After a group is completed, check the gate before opening the next one.
7. After approval, refresh the roadmap again before picking more work.

The map exists so a file is only rewritten after its callees are already available in C++.

## Shell notes

CodeScribe bash is restricted. In practice:

- use plain relative paths like `software/mcfm/src/...`
- no `cd`, pipes, redirects, or `$VARIABLES`

## Verify

Mark the statement that writes the file's main output with `// @coverage-probe`, then run:

```
python3 dev/tools/coverage/coverage_check.py <file.cpp> -- <process>
```

Use the process mapped from the file's top-level folder in the Spec. If verification work is
needed and MCFM is not built yet, run `jobrunner submit tests/mcfm` first.

Interpret results as:

- `COVERED` → mark `VERIFIED` once the restored build still matches
- `NOT COVERED` → mark `TRANSLATED`

If build or verification fails, keep fixing the current group unless the gate is blocking the
start of a later group.

## When to stop

Stop only when one of these is true:

- a completed group needs human approval before the next group can start
- there is no ready file to work on
- a real blocker requires a person

Otherwise continue editing, building, testing, and verifying.

## Notes / session log

- Files under `Mods/Need/Inc/Procdep` have no coverage test; mark them `TRANSLATED`.
- If coverage shows no change, retry after a caller is rewritten.
- If numbers disagree, mark `FAILED` with the symptom instead of guessing.
- Add a dated note per session: what you changed, what remains, and any human decision needed.
