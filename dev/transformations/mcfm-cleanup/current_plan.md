# MCFM cleanup and consolidation plan

This file says how to run the cleanup pass after Fortran-to-C++ translation work. The cleanup
rules and correctness bar are in `desired_spec.md`.

## Log file

Keep the changing worklist in `agent_log.md` in this folder. Create it if missing and
keep it current. Use it for ready cleanup targets, review groups, and per-target status. Keep
session prose notes in the log at the end of this file.

Record finished cleanup items as:

- `- [x] <path> — MOVED (<where the original .f went>)`
- `- [x] <path> — DELETED_SHIM (<why _fi is no longer needed>)`
- `- [x] <path> — KEPT_SHIM (<remaining caller or boundary>)`
- `- [x] <path> — MERGED_CPP (<what was merged>)`
- `- [x] <path> — KEPT_SPLIT (<why the header/source split stays>)`
- `- [ ] <path> — FAILED (<what blocked safe cleanup>)`

Use paths like `software/mcfm/src/...`.

## Approval gate

Review groups live under headings starting with `Group` in `agent_log.md`. Humans do not edit
`agent_log.md`. Human approvals live in `approvals.toml` in this folder and should normally be
recorded with:

```
python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest-blocking
```

or, to approve the oldest pending completed group,

```
python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest
```

or, for an explicit group,

```
python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup "Group ..." --by <name>
```

Use the gate only when deciding whether to start a new group:

```
python3 dev/tools/approve/check_gate.py dev/transformations/mcfm-cleanup
```

Interpret it this way:

- If a group is still open, you may keep working inside that same group.
- A completed group containing `DELETED_SHIM`, `MERGED_CPP`, or `FAILED` requires approval before the next group starts.
- Otherwise, up to 2 completed groups may accumulate before approval is required.
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
  - refresh the doxygen-based dependency graph and derived readiness/index data
- `python3 dev/workflow.py cleanup report`
  - report cleanup candidates from the current index data
- `python3 dev/workflow.py gate mcfm-cleanup`
  - enforce the human approval policy between completed groups
- `python3 dev/workflow.py approve mcfm-cleanup --latest-blocking`
  - approve the exact group currently blocking the gate
- `python3 dev/workflow.py approve mcfm-cleanup --latest`
  - approve the oldest pending completed group
- `python3 dev/workflow.py approve mcfm-cleanup --list-pending`
  - show pending completed groups waiting for approval
- `python3 dev/workflow.py approve mcfm-cleanup "Group ..." --by <name>`
  - record a human approval for a specific group in `approvals.toml`
- `jobrunner submit tests/mcfm`
  - full MCFM build + benchmark run after cleanup edits

The low-level scripts under `dev/tools/` remain available, but `dev/workflow.py` is the preferred interface.
Use ordinary repository inspection as needed to confirm whether a header is reused or a shim is
still part of an active Fortran call path.

## Resolution: which cleanup targets to do next

1. Only pick files that are already translated to C++ and have corresponding cleanup artifacts,
   typically some subset of:
   - original `.f` or `.F`
   - translated `.cpp`
   - translated `.hpp`
   - compatibility shim `_fi.f90`, `_fi.F90`, `_fi.f`, or `_fi.F`
2. Favor targets where all of the following are likely true:
   - the original Fortran source has not yet been moved into `deprecated/`
   - the shim appears to have no remaining required callers
   - the header/source split looks local and mergeable
3. Group review items by folder and call-path topic, about 20 cleanup targets per group.
4. If there is already an open group, keep filling and fixing that group before opening another.
5. For each target, perform cleanup in this order:
   - move deprecated original Fortran source into sibling `deprecated/` when a translated path
     already exists
   - decide whether the `_fi` shim must stay or can be deleted safely
   - decide whether translated headers and implementation files should stay as-is or be reorganized into one or more combined `.hpp` and `.cpp` files
   - when merging, group files by coherent reusable interface and implementation ownership rather than forcing a 1:1 header/source collapse
   - replace translation-era local forward declarations with proper header includes when a reusable interface exists
   - update local `CMakeLists.txt` or includes as needed
6. After a group is completed, check the gate before opening the next one.
7. After any required approval, refresh the roadmap again before picking more work.

## Decision rules

### Moving original Fortran sources

After a translated implementation exists, prefer moving the obsolete original `.f`/`.F` into a
sibling `deprecated/` directory rather than leaving it next to active C++ sources.

### Deleting `_fi` shims

Delete a `_fi` shim only when all of the following are true:

1. The doxygen-based dependency/caller graph and local source inspection show no remaining active
   Fortran caller depends on the shimmed symbol.
2. The C++ implementation is already the effective interface for all remaining call paths.
3. Build wiring is updated so the deleted shim is not still compiled or referenced.
4. `jobrunner submit tests/mcfm` passes after the deletion.

If any point is uncertain, keep the shim and record why.

### Merging translated headers and sources

Prefer fewer, more coherent C++ files when safe, but be conservative.

Merging in this pass means reorganizing translation-era per-file outputs into cleaner combined
interfaces and implementation units when that better matches ownership and reuse. This may mean:

- merging several `.hpp` files into one combined reusable header
- merging several `.cpp` files into one implementation file
- keeping one combined `.hpp` shared by multiple `.cpp` files
- keeping some headers separate while merging only implementations

Reorganize headers/sources only when all of the following are true:

1. The new layout is a clearer representation of the actual reusable interfaces or logical implementation ownership.
2. Cross-translation-unit declarations remain available in appropriate headers.
3. Local-only helpers can move into implementation files without harming clarity.
4. The header is not needed to preserve a distinct stable interop boundary that would be obscured by the merge.
5. The reorganization reduces obvious bloat without obscuring ownership or call structure.
6. Using a combined header for multiple `.cpp` files makes interface sense and does not just create an arbitrary umbrella file.
7. `jobrunner submit tests/mcfm` passes after the merge.

Otherwise keep the split and record why.

### Replacing local forward declarations

Prefer header-based interfaces over translation-era local forward declarations.

Replace a local forward declaration with a proper header include when all of the following are true:

1. the callee already has a header, or clearly should have one as the reusable interface
2. the declaration is used across translation units rather than only inside one implementation file
3. using the header reduces duplication or risk of signature drift
4. include/build structure stays clean
5. `jobrunner submit tests/mcfm` passes after the change

Otherwise keep the local declaration and record why.

## Verify

After cleanup edits, run:

```
jobrunner submit tests/mcfm
```

If the cleanup may affect call structure, rerun:

```
python3 dev/workflow.py refresh
```

Interpret results as:

- test/build passes and graph stays consistent → keep the cleanup
- build/test fails or the graph shows a still-needed boundary was removed → revert/fix and mark
  `FAILED` or `KEPT_*` as appropriate

## When to stop

Stop only when one of these is true:

- a completed group needs human approval before the next group can start
- there is no safe cleanup to apply
- a real blocker requires a person

Otherwise continue editing, building, testing, and verifying.

## Notes / session log

- The purpose of this pass is cleanup, not new translation.
- Bias toward fewer tiny wrapper files and a cleaner C++ structure, but never guess about active
  callers.
- Prefer normal C++ declaration-before-use structure: reusable functions declared in headers, included before use in other `.cpp` files.
- When merging, group code by coherent interface and ownership; several former `.hpp` files may become one reusable header referenced by multiple `.cpp` files.
- A merged C++ layout is preferred only when it preserves current behavior and verification.
- Add a dated note per session: what you changed, what remains, and any human decision needed.
