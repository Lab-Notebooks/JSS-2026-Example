# mcfm-translate — agent log

Worklist for the Fortran → C++ pass. Statuses follow `desired_spec.md` (`VERIFIED`,
`TRANSLATED`, `FAILED`). Paths are relative to the repository root.

## Ready set snapshot (after `python3 dev/workflow.py refresh`)

- 531 source files, 86 translated, 445 untranslated
- 229 ready leaves (`deps == 0`, `blind == 0`, no generated `.cpp`)
- ready leaves by folder: gghgg_dep 140, W2jet 34, BDK 27, ThreeJets 11, Z2jet 6,
  Mods 5, loop 3, Inc 2, Procdep 1

## Group Z2jet-1 (small Z2jet leaves) — COMPLETED

Coverage process for `Z2jet`: `u u~ e- e+ g g`.

- [x] software/mcfm/src/Z2jet/fmt.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/fzip.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/storecsz.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/ampqqb_qqb.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/Bdiff.cpp — TRANSLATED (not covered by u u~ e- e+ g g)

Evidence: each file probed with `python3 dev/workflow.py verify <file>.cpp -- u u~ e- e+ g g`
→ `RESULT: NOT COVERED` (exit 1) for all five. Restored build re-checked with
`jobrunner submit tests/mcfm` → `SUCCESS`, `SUMMARY: pass rate 272/272`, 272 explicit
`PASSED` markers, 0 `FAILED`.

## Group Z2jet-loop-2 (remaining `u u~ e- e+ g g` leaves) — COMPLETED

Coverage process for `Z2jet` and `loop`: `u u~ e- e+ g g`.

- [x] software/mcfm/src/Z2jet/fmtfull.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/loop/loopI1_generic.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/loop/loopI2p_generic.cpp — TRANSLATED (not covered by u u~ e- e+ g g)
- [x] software/mcfm/src/loop/loopI4_generic.cpp — TRANSLATED (not covered by u u~ e- e+ g g)

Evidence: `jobrunner submit tests/mcfm` → `SUCCESS`, `SUMMARY: pass rate 272/272`, 272 explicit
`PASSED` markers, 0 `FAILED`, no `error` lines in `tests/mcfm/job.output`; each file then probed
with `python3 dev/workflow.py verify <file>.cpp -- u u~ e- e+ g g` → `RESULT: NOT COVERED`
(exit 1).

Still open in `Z2jet`: `msq_z2jetx.f` (ready leaf, two subroutines with `(2,2,2)` complex
amp arrays and `-nf:nf` indexed `Q`/`zL`/`zR` module arrays — deliberately deferred, not
started).

## Group W2jet-3 (small W2jet leaves) — COMPLETED

Coverage process for `W2jet`: `u d~ ve e+ g g`.

- [x] software/mcfm/src/W2jet/A6texact.cpp — TRANSLATED (not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/Ftexact.cpp — TRANSLATED (not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/Ltfunctions.cpp — TRANSLATED (not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/atree.cpp — TRANSLATED (not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/fvf.cpp — TRANSLATED (not covered by u d~ ve e+ g g)

Evidence: `jobrunner submit tests/mcfm` after the rewrite → `SUCCESS`, `SUMMARY: pass rate 272/272`,
272 explicit `PASSED` markers, 0 `FAILED`; each file then probed with
`python3 dev/workflow.py verify <file>.cpp -- u d~ ve e+ g g` (run through
`dev/tmp/verify_group_w2jet.py`, which exports `MCFM_HOME`) →
`RESULT: NOT COVERED — the numbers did not change, so the test never ran this file.` (exit 1)
for all five.

## Notes / session log

- 2024 session (loop 1): opened `Group Z2jet-1` and translated the five small ready leaves
  of `software/mcfm/src/Z2jet`: `fmt`, `fzip`, `storecsz`, `ampqqb_qqb`, `Bdiff`.
  Each became `<base>.cpp` + `<base>.hpp` + `<base>_fi.F90`; each `.cpp` includes its own
  header. Originals moved to `software/mcfm/src/Z2jet/deprecated/`, and
  `software/mcfm/src/Z2jet/CMakeLists.txt` now lists the `.cpp` / `_fi.F90` pairs.
- Callee handling: `fzip` calls the already-translated `i3m`, `lnrat`, `cplx2` through
  `Need.hpp`; `Bdiff` calls `loopI2` through `Loop.hpp`; `ampqqb_qqb` calls the still-Fortran
  `aqqb_zbb_new` through an `extern "C"` declaration with pointer arguments. No symbol invented.
- One `// @coverage-probe` marker per translated `.cpp`.
- Whole-suite check after the rewrite: 272/272 cases `PASSED`.
- 2024 session (loop 2): ran the coverage probe for all five Group Z2jet-1 files with process
  `u u~ e- e+ g g`. `fzip.cpp` first failed the probe mechanically (`could not scale the marked
  line`) because the marked assignment spanned four physical lines; the expression was joined
  onto one line (no numeric change) and the probe then ran. All five report `NOT COVERED`, so
  all five are recorded `TRANSLATED`. Group Z2jet-1 is now COMPLETED; re-check coverage later,
  once a Z2jet caller of these leaves is rewritten.
- 2024 session (loop 2, cont.): gate was `OK` (1 completed group waiting, limit 3), so opened
  `Group Z2jet-loop-2` and translated `Z2jet/fmtfull`, `loop/loopI1_generic`,
  `loop/loopI2p_generic`, `loop/loopI4_generic`.
  - `fmtfull` → `fmtfull.cpp` + `fmtfull.hpp` + `fmtfull_fi.F90`; it calls the translated
    `Bdiff` through `"Bdiff.hpp"`, `loopI3` through `<Loop.hpp>`, `cplx2` through `<Need.hpp>`.
  - The three `loop` modules follow the folder's existing module pattern
    (`loopI2_generic` / `loopI3_generic`): `<base>.cpp` with overloaded real/complex C++
    entry points plus `extern "C"` wrappers, `<base>_fi.f90` re-creating the Fortran module
    (generic interface preserved), and declarations added to the shared `loop/Loop.hpp`
    (`loopI1`, `loopI2p`, `loopI4` overloads and the `qli1/qli1c/qli2p/qli2pc/qli4/qli4c`
    Fortran-boundary `extern "C"` declarations). No symbol invented.
  - Originals plus their `_inc.f` include bodies moved to the respective `deprecated/`
    folders; both `CMakeLists.txt` files now list the `.cpp` / `_fi` pairs.
  - Whole-suite check after the rewrite: 272/272 cases `PASSED`; all four probes
    `NOT COVERED`, so all four are `TRANSLATED`.
  - Next: `Z2jet/msq_z2jetx.f` is the remaining ready `Z2jet` leaf; then W2jet / BDK /
    ThreeJets / gghgg_dep leaves. Gate must be checked again before opening group 3.
- 2024 session (loop 3): gate was `OK` (2 completed groups waiting, limit 3), so opened
  `Group W2jet-3` and translated five small ready leaves of `software/mcfm/src/W2jet`:
  `A6texact`, `Ftexact`, `Ltfunctions`, `atree`, `fvf`. Each became `<base>.cpp` +
  `<base>.hpp` + `<base>_fi.F90`, and each `.cpp` includes its own header.
  - Callee wiring: `loopI2` / `loopI3` come from `<Loop.hpp>`; `lnrat`, `cplx2` and the other
    small helpers come from `<Need.hpp>`; kinematic invariants and helicity conventions come
    from the `sprods` / `heldefs` modules via their generated headers. Where a callee is still
    Fortran it is declared in `extern "C"` and called with pointer arguments. No symbol
    invented.
  - The five original `.f` files were moved to `software/mcfm/src/W2jet/deprecated/`, and
    `software/mcfm/src/W2jet/CMakeLists.txt` now lists the `.cpp` / `_fi.F90` pairs instead.
  - One `// @coverage-probe` marker per translated `.cpp`.
  - Whole-suite check after the rewrite: 272/272 cases `PASSED`, 0 `FAILED`.
- 2024 session (loop 4): recorded the `Group W2jet-3` results above. Re-ran all five coverage
  probes; every one reports `NOT COVERED`, so all five are `TRANSLATED` (no `u d~ ve e+ g g`
  caller of these leaves is rewritten yet — re-check once one is).
  - Environment note: `python3 dev/workflow.py verify <file>.cpp -- u d~ ve e+ g g` exits 2 when
    `MCFM_HOME` is unset in the shell environment; the probe needs `MCFM_HOME` pointing at
    `software/mcfm`. `dev/tmp/verify_group_w2jet.py` sets it before delegating to
    `dev/workflow.py verify`, which is why the wrapper succeeds where the direct call fails.
    Later loops should either export `MCFM_HOME` or use the wrapper.
  - `python3 dev/workflow.py refresh` after the rewrite: 511 source files, 86 translated,
    425 untranslated, 223 ready leaves.
  - Restored-build check re-run at the end of this loop: `jobrunner submit tests/mcfm` →
    `SUCCESS`, `SUMMARY: pass rate 272/272`, 272 `PASSED` markers, 0 `FAILED`.
  - Three completed groups (`Z2jet-1`, `Z2jet-loop-2`, `W2jet-3`) are now waiting for human
    approval; per the Approval gate this blocks opening a fourth group, so the pass stops here
    for human review.
