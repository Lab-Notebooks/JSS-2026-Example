# C++ → Kokkos plan

This file says how to run step 2. The kernel contract and correctness bar are in
`desired_spec.md`.

## Checklist file

Keep the changing worklist in `agent_checklist.md` in this folder. Create it if missing and
keep it current. Use it for active amplitudes, review groups, and per-amplitude status. Keep
session prose in the log at the end of this file.

Record each finished amplitude as:

- `- [x] <name> — TRANSLATED (maxRelErr <value>)`
- `- [ ] <name> — FAILED (<what went wrong>)`
- `- [x] <name> — VERIFIED (<doctest>)` only by a person after a doctest lands

Use paths like `software/pepper/src/mcfm_analytics/...`.

## Approval gate

Review groups live under headings starting with `Group` in `agent_checklist.md`. A person signs
off a finished group by adding:

```
APPROVED 2026-07-21 by <name>
```

Do not start a new completed group while an earlier completed group is unapproved. Check with:

```
python3 dev/tools/approve/check_gate.py dev/transformations/cpp-to-kokkos/agent_checklist.md
```

If it fails, stop.

## Tools

Run these from the project root:

- `python3 dev/tools/closure/calltree_closure.py <name>`
  - transitive linked closure, stage-1 readiness, and existing reuse
- `python3 dev/tools/kokkos/kokkosify.py <input.cpp> [-o draft.h] [-r report.md]`
  - mechanical first draft plus blockers
- `python3 dev/tools/kokkos/kokkosify.py validate <validator.cpp>`
  - compare the ported kernel against `libmcfm`
- `python3 dev/tools/approve/check_gate.py <agent_checklist.md>`
  - enforce human sign-off between groups
- `jobrunner submit tests/mcfm`
- `jobrunner submit tests/pepper`
  - build and test both codebases

Build both codebases once before the first round if needed.

## Resolution: which target to do next

- Do Born before virtual when both exist.
- A target is ready only when:
  1. Closure shows its full call tree is in C++.
  2. The needed step-1 files are marked `VERIFIED` in
     `dev/transformations/fortran-to-cpp/agent_checklist.md`.
- Size the closure before starting:
  - about 30 linked pieces or fewer: do it directly
  - larger trees: split by function boundary and work bottom-up

## Authoring steps

1. Map the full call tree, globals, blockers, and reusable ported helpers.
2. Use Kokkosify for the mechanical draft.
3. Write the real kernel from the Spec:
   - helpers first
   - then `<name>_me2(p, params)`
   - then the event kernel
   - then the one-line `.cpp`
4. Replace QCDLoop calls with direct formulas where needed.
5. Validate against `libmcfm` layer by layer until the kernel matches.
6. Add the header and `.cpp` to `src/CMakeLists.txt`, then run `jobrunner submit tests/pepper`.
7. Do not add new doctests. Report which doctests a developer should add.

## Splitting a large tree

If the closure is too large for one pass:

1. Split only at function boundaries.
2. Do leaves first, then sub-amplitudes, then the join.
3. Check each piece against its `libmcfm` twin before freezing it.
4. Join frozen pieces into the final kernel. If pieces pass but the final `|M|²` does not, fix
   the join, not the frozen pieces.

The desired split layout is defined in the Spec.

## Shell notes

CodeScribe bash is restricted. In practice:

- use plain relative paths under `software/mcfm/...` and `software/pepper/...`
- no `cd`, pipes, redirects, or `$VARIABLES`

## Notes / session log

- Existing reference kernels live in `software/pepper/src/mcfm_analytics/`: `qqb_z`,
  `qqb_z_v`, `qqb_z1jet`, `qqb_z1jet_v`.
- `qqb_z2jet` is the main split-demo target. `qqb_z2jet_v` is the hard case because of box
  integrals near threshold.
- The stage-2 correctness target is “matches MCFM”, not independent physics validation.
- `Kokkos::complex` division typically limits agreement to about `1e-10` in division-heavy code.
- Add a dated note per session: what you changed, what remains, and any human decision needed.
