# MCFM cleanup and consolidation: target output

This file defines the cleanup target and correctness bar for the post-translation pass. The
workflow lives in `current_plan.md`.

Paths are written as `software/mcfm/src/...`.

---

## Contract

This pass advances by *settling* cleanup targets one at a time: each target is edited, then
recorded in `agent_log.md` with a status `σ` once the oracle `V` confirms the invariants `I`
still hold. A target is ready when its dependencies are already settled.

Objective `f`. Minimize translation-era bloat (original sources, `_fi` shims, tiny wrappers,
ad hoc forward declarations) subject to `I`. Progress = the `move` / `shim-delete` / `merge`
counts from `python3 dev/workflow.py status`.

Invariants `I` (hold after every settled unit):

- `jobrunner submit tests/mcfm` passes.
- No called symbol is invented; no build reference is left dangling.
- On insufficient dependency-graph evidence, take the conservative `KEPT_*` action.

Oracle `V`. `jobrunner submit tests/mcfm`; for graph-sensitive edits, `python3 dev/workflow.py refresh`.

Status set `Σ`.

| σ            | class | reversible | runner sets | evidence in log        |
|--------------|-------|------------|-------------|------------------------|
| MOVED        | good  | yes        | yes         | build pass             |
| KEPT_SHIM    | good  | yes        | yes         | surviving caller cited |
| KEPT_SPLIT   | good  | yes        | yes         | reason                 |
| DELETED_SHIM | good  | no         | yes         | graph + build pass     |
| MERGED_CPP   | good  | no         | yes         | build pass             |
| FAILED       | bad   | —          | yes         | symptom                |

Risky `σ` (⇒ approval before the next group) = bad or irreversible: DELETED_SHIM, MERGED_CPP,
FAILED. The sections below elaborate this contract; on conflict the contract governs.

---

## Goal

Reduce translation-era bloat in the MCFM port while preserving behavior and buildability.

This pass works only on already-translated targets and focuses on three cleanup actions:

1. move obsolete original Fortran sources out of active source directories
2. remove `_fi` compatibility shims that are no longer required
3. merge and reorganize translated headers and sources into cleaner combined C++ interfaces and implementation units where that improves ownership and structure
4. replace translation-era local forward declarations with proper header-based C++ interfaces where appropriate

The desired direction is a cleaner and more organized C++ port with fewer tiny wrapper files,
less dead compatibility structure, and more standard C++ header/source organization. Prefer
coherent ownership and clearer interfaces, but do not invent new APIs or delete boundaries that
are still needed.

---

## Cleanup units

A typical cleanup target is a translated family with some subset of these files:

- `<base>.f` or `<base>.F`
- `<base>.cpp`
- `<base>.hpp`
- `<base>_fi.f90`, `<base>_fi.F90`, `<base>_fi.f`, or `<base>_fi.F`

Other translated layouts may exist, especially in library helpers. Apply the same principles.

---

## Action 1: move original Fortran sources

When a translated C++ implementation and any still-needed compatibility layer already exist, the
original `.f` or `.F` source should normally be moved into a sibling `deprecated/` directory.

### Move rule

Move the original Fortran file when:

- the translated implementation is present and wired into the build
- moving the original source does not break the current build wiring
- the original source is retained only for archival/reference purposes

### Output shape

- active directory keeps the translated C++ files and any still-needed compatibility files
- sibling `deprecated/` receives the obsolete original Fortran source

Do not delete the original source in this pass unless an existing project convention already does
so and the move is unnecessary.

---

## Action 2: delete `_fi` shims only when safe

The `_fi` files are compatibility shims for old Fortran-facing entry points. They should be kept
only while an active Fortran-side call path still needs them.

### Safe deletion rule

Delete a `_fi` shim only if all of the following are true:

1. The doxygen-based dependency graph, refreshed via `build_roadmap.py --doxygen`, shows no
   remaining active dependency that requires the shimmed interface.
2. Local inspection confirms there is no surviving Fortran caller or build entry that still
   expects the shim symbol.
3. The corresponding `.cpp` implementation is the direct interface now used by remaining call
   paths.
4. Any build-system references to the `_fi` file are removed or updated.
5. `jobrunner submit tests/mcfm` passes afterward.

### Conservative fallback

If the graph is incomplete, ambiguous, or only proves C++ usage but not absence of all Fortran
callers, keep the shim and record `KEPT_SHIM` with the reason.

---

## Action 3: merge and reorganize translated `.hpp` and `.cpp` files

The cleanup pass may merge several translation-era headers into a combined header and may also
merge several implementation files into one or more coherent `.cpp` files when that produces a
cleaner C++ structure. The goal is not simply to collapse every `.hpp` into its `.cpp`, but to
organize related code around reusable interfaces, ownership, and cohesive implementation units.

A combined header may legitimately be included by multiple `.cpp` files when it represents the
right shared interface. Likewise, several former per-file translated implementations may be
merged into one `.cpp` if they belong to the same logical implementation unit.

### Good merge candidates

- several tiny translated headers that collectively define one coherent reusable interface
- several small translated `.cpp` files that implement one logical facility or tightly related set of methods/functions
- file-local helper declarations that do not deserve a standalone reusable header
- translated units where the per-file split exists only because the rewrite process emitted it by default
- families of files that become easier to navigate when grouped by ownership or responsibility rather than original Fortran file boundaries

### Do not merge when

- the existing header split is already the clearest reusable interface boundary
- merging would blur distinct ownership or create a less coherent API surface
- the header forms a needed interop boundary
- different implementation files should remain separate for clarity, dependency control, or build structure
- merging would create circular include, initialization-order, or build-structure problems
- the merge makes the implementation materially harder to navigate

### Merge rule

Merge or reorganize translated headers/sources only when:

1. repository inspection shows the new combined layout is a clearer representation of the reusable interfaces and implementation ownership
2. any declarations needed across translation units remain available in one or more proper headers
3. local-only declarations can be kept inside implementation files without harming clarity
4. local build wiring remains correct
5. the reorganization reduces translation-era bloat without removing a genuinely useful interface boundary
6. any combined header still serves as the proper declaration point for all active `.cpp` users that should share that interface
7. `jobrunner submit tests/mcfm` passes afterward

If unsure, keep the existing split and record `KEPT_SPLIT`.

## Action 4: replace local forward declarations with headers where appropriate

A common translation artifact is a `.cpp` file that calls a translated C++ sibling via a local
forward declaration even though a corresponding header exists or should clearly serve as the
interface.

### Preferred cleanup

Prefer standard C++ structure:

- reusable functions are declared in headers
- `.cpp` files include the headers for the translated C++ functions they use
- local forward declarations are reserved for narrow cases where no reusable header is warranted

### Cleanup rule

Replace a local forward declaration with a header include when:

1. the callee already has a header, or clearly should have one as a reusable interface
2. the function is used across translation units
3. the change reduces duplication or declaration drift risk
4. local include/build structure stays clear and correct
5. `jobrunner submit tests/mcfm` passes afterward

If the function is truly local in spirit or introducing/keeping a header would add needless
surface area, keep the declaration local and record the reason in the log notes.

---

## Dependency analysis requirement

The key safety signal for this transformation is the doxygen-based dependency graph already used
by existing transformation mechanics.

Before making deletion decisions, refresh:

```bash
python3 dev/tools/index/build_roadmap.py --doxygen
python3 dev/tools/index/build_roadmap.py
```

Use the resulting dependency/caller information together with direct repository inspection.
Graph evidence is necessary but not, by itself, sufficient for deleting a shim.

---

## Correctness bar

A cleanup is correct only if it preserves buildability and benchmark behavior.

Required verification:

```bash
jobrunner submit tests/mcfm
```

For graph-sensitive edits, also rerun the roadmap refresh and ensure the resulting dependency
state is consistent with the cleanup decision.

### Status meanings

The status set `Σ`, its classes, reversibility, and required evidence are defined once in the
`## Contract` above; the Action sections define when each applies. Record results in
`agent_log.md`, not here.
