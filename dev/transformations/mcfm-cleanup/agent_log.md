# MCFM cleanup — agent log

## Session 1 (loop 1)

### Important discovery: pre-existing uncommitted submodule state

`software/mcfm` is a git submodule. Before this session made any edits, the submodule
working tree already contained a large set of **uncommitted** changes (visible via
`git -C software/mcfm status --porcelain`) that match this transformation's action
vocabulary almost exactly:

- BDK/: all `*_fi.F90` shims deleted, all original `*.f` sources renamed into
  `src/BDK/deprecated/`.
- ThreeJets/: several originals renamed into `src/ThreeJets/deprecated/`, several
  `*_fi.F90` shims deleted, and a few `.cpp`/`.hpp` files modified (looks like partial
  MERGED_CPP work: `A51mpmpp5g.hpp` and `A5gfill.hpp` deleted, `qqb_thrjet_v.{cpp,hpp}`
  modified).
- Need/: several `*_fi.F90` shims deleted, `CMakeLists.txt` and `cplx_fi.F90` modified.
- W2jet/: a very large number of original `.f` files show as deleted (`D`) rather than
  renamed, with a new untracked `src/W2jet/deprecated/` directory — needs confirmation
  this is a clean move and not a lossy delete before it is recorded as settled.

None of this was previously recorded in `agent_log.md` (the file did not exist at the
start of this session) and `dev/tmp/` contains leftover one-off scripts
(`delete_bdk_shims.py`, `find_bdk_callers.py`, `scan_all_moves.py`, `scan_mods.py`, ...)
that are consistent with an earlier, unlogged cleanup pass.

`jobrunner submit tests/mcfm` was run against this pre-existing dirty state (before this
session's own edit) and it **passed** (after one flaky-parallel-build retry — the first
attempt failed with a Fortran module ordering race, `mxpart_mod.mod` not found; the
second attempt succeeded from the same tree with no other changes). This is evidence
the BDK/Need/ThreeJets/W2jet state currently on disk is buildable, but it has not been
attributed to specific settled targets in this log yet, and the W2jet case in particular
needs verification before it is claimed as `MOVED` vs something riskier. Treating this
as **unfinished/unverified bookkeeping debt**, not as this session's own settled work.

### This session's own change

- [x] `software/mcfm/src/Inc/tri123x4x56coeffs.f` — MOVED (moved to
  `software/mcfm/src/Inc/deprecated/tri123x4x56coeffs.f`; the C++ implementation
  `software/mcfm/src/Inc/tri123x4x56coeffs.cpp` is already the active body-fragment
  used by `software/mcfm/src/W2jet/qqbggAxtri123x4x56.cpp`; the only remaining
  `include 'tri123x4x56coeffs.f'` reference is inside the already-deprecated
  `software/mcfm/src/W2jet/deprecated/qqbggAxtri123x4x56.f`; `Inc/` has no
  `CMakeLists.txt` so no build-wiring update was needed).

### Analysis performed but not yet finalized as log entries (Group "Mods interop shims")

The cleanup index / `dev/workflow.py cleanup report` flags ~57 `software/mcfm/src/Mods/*_mod`
families as `MOVE_F` because each has both a `.f90` and a `.cpp`/`.hpp` with the same base
name. Direct inspection shows this flag is a **false positive** for this family: the
`.f90` file is not a leftover pre-translation original — it is a `bind(C)` interop shim
(same base name, no `_fi` suffix) that establishes the Fortran-visible pointer/module data
backed by the C++ `.cpp` definition. A checker script
(`dev/tmp/check_mods_move.py`, kept for the next session) confirmed every one of these
`.f90` files has at least one active (non-`deprecated/`) Fortran caller — at minimum
`software/mcfm/src/Mods/Modules_Interface.f90`, and in most cases also
`software/mcfm/src/Procdep/chooser.f` or other still-untranslated `.f`/`.F` files or
`*_fi.F90` shims elsewhere in the tree (e.g. `b0_mod`, `Cabibbo_mod`, `blha_mod`,
`breit_mod`, `ckm1_mod`, `ckm_mod`, `couple_mod`, `docheck_mod`, `epinv2_mod`,
`epinv_mod`, `ewcharge_mod`, `ewcouple_mod`, `ewinput_mod`, `facscale_mod`, `first_mod`,
`flags_mod`, `ggZZ_mod`, `ggZZcomputemp_mod`, `ggZZintegrals_mod`, `hdecaymode_mod`, and
the rest of the `Mods/*_mod` family checked). Per the Spec's conservative fallback, these
should be recorded `KEPT_SHIM` (citing the caller), not `MOVE_F` — but that pass was not
finished/verified against a fresh `jobrunner submit tests/mcfm` this session, so it is
listed here as the next group rather than logged as settled `[x]` items yet.

### What remains (next session)

1. Reconcile the pre-existing uncommitted BDK/Need/ThreeJets/W2jet submodule changes:
   for each family, confirm (a) shim deletion was actually safe (no remaining Fortran
   caller) and (b) `.f` deletions in `W2jet/` are genuine moves into
   `src/W2jet/deprecated/` (content-diff each pair) rather than lossy deletes, then log
   each as `MOVED` / `DELETED_SHIM` / `FAILED` as appropriate. This group contains
   `DELETED_SHIM` results, so it will require human approval
   (`python3 dev/workflow.py approve mcfm-cleanup ...`) once logged and closed.
2. Finish and log the "Mods interop shims" `KEPT_SHIM` group (~57 targets) using
   `dev/tmp/check_mods_move.py` as the starting evidence, then rerun
   `jobrunner submit tests/mcfm` once after all edits (there should be no code edits
   needed for pure `KEPT_SHIM` calls, only log entries — verify no code changed).
3. Re-run `python3 dev/workflow.py refresh` and `python3 dev/workflow.py cleanup report`
   after the above to get a clean, current candidate list before opening new groups
   (BDK/ThreeJets/Need/W2jet dead entries should mostly drop out of the report once
   settled and logged, since `deprecated/` is excluded from the scan).
4. Continue with the remaining move/shim-delete/merge candidates
   (`W/`, `W1jet/`, `Z1jet`, `Z2jet`, `ggH`, `gpt-4o-conversions` subfolders, etc.) in
   ~20-target groups per the Plan, honoring the approval gate between risky groups.

### Verification this session

- `jobrunner submit tests/mcfm`: **1st attempt FAILED** (flaky parallel Fortran module
  build ordering: `mxpart_mod.mod` not found while compiling
  `W/ampqqbgll_fi.F90`), **2nd attempt (no changes in between) SUCCEEDED**. Ran against
  the pre-existing dirty submodule state, before this session's own
  `tri123x4x56coeffs.f` move.
- Did not get a chance this session to re-run `jobrunner submit tests/mcfm` *after* the
  `tri123x4x56coeffs.f` move (Inc/ has no CMakeLists.txt and nothing outside the already
  deprecated `W2jet/deprecated/qqbggAxtri123x4x56.f` includes it, so risk is low, but the
  invariant `jobrunner submit tests/mcfm passes` is not yet re-confirmed post-edit this
  session — do this first next session before further edits).
