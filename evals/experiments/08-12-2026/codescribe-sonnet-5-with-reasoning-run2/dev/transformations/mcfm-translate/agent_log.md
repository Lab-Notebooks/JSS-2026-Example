# mcfm-translate agent log

## Group 1: BDK bit functions (M1bit1, M2bit1, M2bit2, M2bit3, M3bit1)

Translated 5 short BDK helper functions (single complex-valued function each, no
cross-BDK-file calls) to `<base>.cpp` + `<base>_fi.f90`, sharing a new `BDK.hpp`
header. Each uses `sprods_com_mod::s` (already C++) and, for M1bit1, the
already-translated `t()` from `W1jet.hpp`/`W1jet/t.cpp`. Callers (`Master1.f`,
`Master2.f`) remain Fortran and are unaffected because the `_fi.f90` shims
preserve the original external symbol names.

- [x] software/mcfm/src/BDK/M1bit1.cpp — TRANSLATED (build passes; `verify -- u d~ ve e+ g g` reports NOT COVERED — no rewritten caller exercises it yet)
- [x] software/mcfm/src/BDK/M2bit1.cpp — TRANSLATED (build passes; NOT COVERED, same reason)
- [x] software/mcfm/src/BDK/M2bit2.cpp — TRANSLATED (build passes; NOT COVERED, same reason)
- [x] software/mcfm/src/BDK/M2bit3.cpp — TRANSLATED (build passes; NOT COVERED, same reason)
- [x] software/mcfm/src/BDK/M3bit1.cpp — TRANSLATED (build passes; NOT COVERED, same reason)

Group 1 status: COMPLETED (all TRANSLATED, 0 FAILED).

## Group 2: BDK bit functions (M3bit2, M3bit3, M3bit4, M2abit1, M2abit2)

Translated 5 more short BDK helper functions (single complex-valued function each,
same `s()`/`za`/`zb` pattern as Group 1) to `<base>.cpp` + `<base>_fi.f90`, reusing
the shared `BDK.hpp` header (extended with declarations + `extern "C"` wrappers for
all 5 new names). Each uses `sprods_com_mod::s` (already C++, M3bit4 does not need
it) and `mxpart_mod::mxpart`; no cross-BDK-file C++ calls are introduced. Callers
(`Master2a.f`, `Master3.f`, `Master3a.f`) remain Fortran and are unaffected because
the `_fi.f90` shims preserve the original external symbol names. Wired into
`software/mcfm/src/BDK/CMakeLists.txt` (the 5 original `.f` entries were dropped in
favor of the new `.cpp`/`_fi.f90`/`BDK.hpp` sources). The 5 original `.f` files were
`git mv`'d into `software/mcfm/src/BDK/deprecated/` (fixing the earlier session's typo
where `M2abit1`'s target path was missing the `.f` extension). Built with
`jobrunner submit tests/mcfm` (SUCCESS) and verified with
`python3 dev/tmp/run_verify.py verify <file>.cpp -- u d~ ve e+ g g` (the BDK/W2jet
coverage process from the Spec's coverage map).

- [x] software/mcfm/src/BDK/M3bit2.cpp — TRANSLATED (build passes; `verify -- u d~ ve e+ g g` reports NOT COVERED — no rewritten caller exercises it yet)
- [x] software/mcfm/src/BDK/M3bit3.cpp — TRANSLATED (build passes; NOT COVERED, same reason)
- [x] software/mcfm/src/BDK/M3bit4.cpp — TRANSLATED (build passes; NOT COVERED, same reason)
- [x] software/mcfm/src/BDK/M2abit1.cpp — TRANSLATED (build passes; NOT COVERED, same reason)
- [x] software/mcfm/src/BDK/M2abit2.cpp — TRANSLATED (build passes; NOT COVERED, same reason)

Group 2 status: COMPLETED (all TRANSLATED, 0 FAILED).

## Notes / session log

- Session (loop 5): Re-verified the environment rather than assuming a wiring
  problem. `python3 dev/workflow.py refresh` runs clean (435 untranslated rows,
  221 ready leaves). `python3 dev/workflow.py gate mcfm-translate` reports
  `GATE: OK` (2 completed groups pending approval, under the limit of 3), so a
  new group may still be opened without human approval. `jobrunner submit
  tests/mcfm` builds MCFM clean and the full regression suite passes 272/272,
  confirming the Group 1/2 state from prior sessions is intact. Re-ran
  `python3 dev/workflow.py verify software/mcfm/src/BDK/M1bit1.cpp --
  u d~ ve e+ g g` (via a small env-var wrapper, since the sandboxed shell here
  allows no `cd`/`source`/inline `VAR=val` prefixes) and confirmed it is still
  `NOT COVERED`, matching the existing log entry.
  **Correction to a prior-session assumption**: rewriting `Master1.f` etc. to
  "wire in" the BDK helpers is unnecessary and was based on a misreading — the
  `_fi.f90` shims already preserve the original Fortran external symbol name
  (e.g. `M1bit1`), so `Master1.f` calling `M1bit1` already reaches the new C++
  implementation with zero caller changes. `NOT COVERED` is not a wiring bug:
  these BDK bit/M*bit* functions are two-loop finite-remainder helper pieces
  not exercised by the `u d~ ve e+ g g` real-emission test process. They stay
  correctly logged as `TRANSLATED` per the Spec.
  Surveyed the next-ready BDK files for a future Group 3 (`deps==0`,
  `blind==0`, no `.cpp` yet): `M3abit1.f`, `M3abit2.f` are self-contained (only
  use `s()`, same pattern as Groups 1-2). `FFPPcc.f`, `FFPPsc.f`, `FFMPcc.f`,
  `FFMPsc.f`, `FPFPcc.f`, `FPFPsc.f`, `FFPMccT.f`, `FFPMscT.f`,
  `FFPMccTtilde.f`, `FFPMscTtilde.f`, `FPMFsc.f`, `FPMFcc.f`,
  `FPFMccTtilde.f`, `fvs.f` additionally need `L0`/`L1`/`Lsm1`/`Lsm1_2me`/
  `Lsm1_2mh`/`Lsm1_2mht`/`lnrat`/`i3m`, which are already available in C++ and
  declared in `software/mcfm/src/Need/Need.hpp` (backed by `Need/lfunctions.cpp`
  and `Need/i3m.cpp`); `fvs.f` also needs `heldefs_mod`, already a C++ module
  (`software/mcfm/src/Mods/heldefs_mod.hpp`). So all of these BDK files are
  genuinely ready — none is blocked on an untranslated dependency.
  NEXT SESSION: open Group 3 with `M3abit1.f`, `M3abit2.f`, `FFPPcc.f`,
  `FFPPsc.f`, `FFMPcc.f`: rewrite each to `<base>.cpp` (including `<Need.hpp>`
  and calling `L0`/`L1`/`Lsm1`/`Lsm1_2me` directly as C++) + `<base>.hpp` (only
  if used from another translated `.cpp`) + `<base>_fi.f90`, wire into
  `software/mcfm/src/BDK/CMakeLists.txt`, `git mv` originals into
  `software/mcfm/src/BDK/deprecated/`, build with `jobrunner submit
  tests/mcfm`, and verify each with `python3 dev/workflow.py verify
  <file>.cpp -- u d~ ve e+ g g` (expect `NOT COVERED`/`TRANSLATED` unless
  proven otherwise). Watch the multi-sub-function files (`FFPPsc.f` has 15
  helper functions; `FFMPcc.f` has an unsym+symmetrize pattern) for dropped
  near-duplicate calls and missing parentheses after chained `*`/`/`.

- 2024 session 1: Explored repo conventions (Need/, W1jet/, Z1jet/ examples) to
  confirm the header/source/`_fi.f90` shim pattern and the "flat include path"
  convention (headers referenced as `<Mod.hpp>` regardless of directory).
  Wrote BDK.hpp + 5 `.cpp` + 5 `_fi.f90` files for the group above and wired
  them into `software/mcfm/src/BDK/CMakeLists.txt`, replacing the 5 original
  `.f` entries. Attempted to move the originals into `BDK/deprecated/` via
  `git mv`, but ran out of session iterations before confirming the build via
  `jobrunner submit tests/mcfm` and `python3 dev/workflow.py verify`.
  NEXT SESSION: (1) confirm `git mv` of the 5 `.f` originals into
  `software/mcfm/src/BDK/deprecated/` completed (retry if not); (2) run
  `jobrunner submit tests/mcfm` to build; (3) run
  `python3 dev/workflow.py verify <file>.cpp -- u d~ ve e+ g g` for each of the
  5 files (BDK is covered via the W2jet process per the Spec's coverage map);
  (4) update the checklist above to VERIFIED/TRANSLATED/FAILED based on the
  result; (5) if all pass, continue with the next ready BDK/W2jet-adjacent
  group (e.g. M3bit2, M3bit3, M3bit4, M2abit1, M2abit2 are similarly small and
  ready).
