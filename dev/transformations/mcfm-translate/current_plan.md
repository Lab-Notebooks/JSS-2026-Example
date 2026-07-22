# Fortran → C++ plan

This file says how to run step 1. The rewrite rules and correctness bar are in
`desired_spec.md`.

## Log file

Keep the changing worklist in `agent_log.md` in this folder. Create it if missing and
keep it current. Use it for ready files, review groups, and per-file status. Keep durable prose
notes in the session log at the end of this file.

Record each finished file as:

- `- [x] <file> — VERIFIED (worst Δrel <value>)`
- `- [x] <file> — TRANSLATED (<reason>)`
- `- [ ] <file> — FAILED (<what went wrong>)`

Use paths like `software/mcfm/src/...`.

## Approval gate

Review groups live under headings starting with `Group` in `agent_log.md`. Humans do not edit
`agent_log.md`. Human approvals live in `approvals.toml` in this folder and should normally be
recorded with:

```
python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-translate --latest-blocking
```

or, to approve the oldest pending completed group,

```
python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-translate --latest
```

or, for an explicit group,

```
python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-translate "Group ..." --by <name>
```

Use the gate only when deciding whether to start a new group:

```
python3 dev/tools/approve/check_gate.py dev/transformations/mcfm-translate
```

Interpret it this way:

- If a group is still open, you may keep working inside that same group.
- A completed group containing `FAILED` requires approval before the next group starts.
- Otherwise, up to 3 completed groups may accumulate before approval is required.
- A gate failure blocks new-group creation, not builds, fixes, or verification inside the
  current open group.
- The gate checks only whether a group is approved; it does not interpret `approvals.toml`
  `note` text.
- After a group is approved, agents should read any matching approval record in
  `approvals.toml` before continuing work related to that group.
- Treat approval notes as binding human guidance for that group unless a later human
  instruction supersedes them.
- If an approval note changes scope or forbids an action, reflect that in the current work
  and logs rather than silently ignoring it.

Stop for human review only when the gate blocks the next group.

## Tools

Run these from the project root. Prefer the unified workflow interface:

- `python3 dev/workflow.py refresh`
  - refresh the readiness map and symbol index
- `python3 dev/workflow.py draft <file.f>`
  - make a rough draft and dependency hints
- `python3 dev/workflow.py verify <file.cpp> -- <process>`
  - decide VERIFIED vs TRANSLATED
- `python3 dev/workflow.py gate mcfm-translate`
  - enforce the human approval policy between completed groups
- `python3 dev/workflow.py approve mcfm-translate --latest-blocking`
  - approve the exact group currently blocking the gate
- `python3 dev/workflow.py approve mcfm-translate --latest`
  - approve the oldest pending completed group
- `python3 dev/workflow.py approve mcfm-translate --list-pending`
  - show pending completed groups waiting for approval
- `python3 dev/workflow.py approve mcfm-translate "Group ..." --by <name>`
  - record a human approval for a specific group in `approvals.toml`
- `jobrunner submit tests/mcfm`
  - full MCFM build + test run; run this before verification if MCFM is not yet built

The low-level scripts under `dev/tools/` remain available, but `dev/workflow.py` is the preferred interface.

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
   - Treat `<base>.hpp` + `<base>.cpp` as the default translated C++ layout: declarations in the header, definitions in the `.cpp`.
   - Ensure the translated `.cpp` includes its own `<base>.hpp` when such a header exists.
   - If the translated file calls another translated C++ unit and that callee has a header, include the header instead of adding a local forward declaration.
6. After a group is completed, check the gate before opening the next one.
7. After any required approval, refresh the roadmap again before picking more work.

The map exists so a file is only rewritten after its callees are already available in C++.

## Shell notes

CodeScribe bash is restricted. In practice:

- use plain relative paths like `software/mcfm/src/...`
- no `cd`, pipes, redirects, or `$VARIABLES`

## Verify

Mark the statement that writes the file's main output with `// @coverage-probe`, then run:

```
python3 dev/workflow.py verify <file.cpp> -- <process>
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
- For reusable translated C++ functions, put declarations in headers and include those headers before use from other `.cpp` files.
- A translated `.cpp` should normally include its own matching header when one exists.
- Prefer proper header inclusion over translation-era ad hoc forward declarations.
- If coverage shows no change, retry after a caller is rewritten.
- If numbers disagree, mark `FAILED` with the symptom instead of guessing.
- Add a dated note per session: what you changed, what remains, and any human decision needed.
