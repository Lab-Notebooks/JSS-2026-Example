# MCFM Translate Agent Log

## Group 1: BDK — one-loop coefficient translation queue

Queued before editing starts. Coverage map maps BDK to the `u u~ e- e+ g g` process
(Z2jet / W2jet / BDK / loop row).

- [x] software/mcfm/src/BDK/FFMPcc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FFPMccT.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FFPMccTtilde.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FFPMscT.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FFPMscTtilde.f — VERIFIED (worst Δrel 0)

Group 1 is complete: all 5 units non-FAILED. Awaiting human approval before a new group
starts (approval is a human action; not recorded here).

## Session log

### 2026-08-12 — Group 1 serial integrate

Wiring (this step's responsibility; authors were forbidden to touch build files):

- `software/mcfm/src/BDK/CMakeLists.txt`: swapped each unit's `.f` entry for its generated
  `.cpp` + `_fi` shim (`FFMPcc.cpp`/`FFMPcc_fi.f90`, `FFPMccT.cpp`/`FFPMccT_fi.f90`,
  `FFPMccTtilde.cpp`/`FFPMccTtilde_fi.F90`, `FFPMscT.cpp`/`FFPMscT_fi.F90`,
  `FFPMscTtilde.cpp`/`FFPMscTtilde_fi.f90`).
- `software/mcfm/CMakeLists.txt`: added `src/BDK` to the include-directory list on the
  `objlib`, `libmcfm`, and `test` targets. This was the one shared wiring change the group
  needed — the units include their own headers as `<FFMPcc.hpp>` etc., and `src/BDK` had
  never been on the include path because BDK had no headers before this round.

Fixes applied during integration (build was broken as delivered):

- `FFPMscT.cpp` (3 sites) and `FFPMscTtilde.cpp` (2 sites): bare integer literals
  multiplying a `std::complex<double>` (`3*zab(...)`, `2*zab(...)`) — no matching
  `operator*`, hard compile error. Converted to `3.0`/`2.0`, matching the convention the
  sibling `FFPMccT.cpp` already used. The `2*s(...)`/`3*s(...)` factors were left alone:
  `s()` returns `double`, so those were always well-formed.
- `FFMPcc.cpp`: called `I3m(...)`, which does not exist in C++. The already-translated
  symbol is `i3m` (declared in `Need.hpp`, defined in `src/Need/i3m.cpp`); Fortran's
  case-insensitivity hid this. Retargeted to `i3m` — no symbol invented, the call is the
  same one the original `FFMPcc.f` made.

Coverage probes: all five markers arrived in a form `coverage_check.py` cannot use — its
rewrite requires a single-line `lhs = rhs;  // @coverage-probe`, but the markers sat on
their own line or on a continuation line of a multi-line expression. Moved each probe onto
the single-line assignment of the function result inside that unit's `extern "C"` wrapper.
Every caller of these five is still Fortran (`W2jet/fcc.f`, `BDK/FFPMcc.f`, `BDK/FFPMsc.f`),
so the wrapper is on the real call path and the probe scales the unit's actual output. This
left the translated arithmetic untouched rather than reflowing 2000-character expressions
onto one line.

Harness note for whoever runs Verify next — `python3 dev/workflow.py verify` cannot
currently report `COVERED` for any file. `workflow.py` `run()` launches `coverage_check.py`
with `cwd=ROOT`, and `coverage_check.run_test` invokes `Bin/test` without setting a cwd, so
the binary runs from the project root and answers `Process not available in MCFM.` for both
the baseline and the probed run. Identical output then reads as "not covered". All five
units first came back `NOT COVERED` this way; an `fprintf` trace in `FFPMccT_wrapper` showed
96 real calls during `u u~ e- e+ g g`, and hand-scaling that wrapper by 1.5 moved
`Finite: MCFM` from `3.1535139416645479e-09` to `3.1529674007308882e-09`, proving coverage.
Re-running `dev/tools/coverage/coverage_check.py` directly from `$MCFM_HOME/Bin` — the same
oracle, from the directory `tests/mcfm/test.sh` itself uses — reported `COVERED` for all
five. `workflow.py`/`coverage_check.py` are human-owned tooling, so neither was modified;
this is a real bug a person should fix (set `cwd` for the test subprocess).

Correctness bar: `jobrunner submit tests/mcfm` → SUCCESS, `SUMMARY: pass rate 272/272`,
272 explicit `PASSED` markers and 0 `FAILED` (the Spec's silent-segfault trap requires the
positive markers, not merely the absence of failures). Benchmark tolerance 1e-13. For the
BDK coverage process `u u~ e- e+ g g` all four reported ratios (Finite, IR, IR2, Born) are
exactly 1, so worst Δrel is 0. Covered + matching ⇒ all five VERIFIED.

Tree state: restored sources rebuilt and passing; no probe scaling left in the tree. The
five originals are in `software/mcfm/src/BDK/deprecated/`.

Remaining for a human: approve Group 1, and note that `FFPMscTtilde_fi.f90`,
`FFPMccT_fi.f90`, and `FFMPcc_fi.f90` use the lowercase `.f90` shim extension while the Spec
Output shape writes `_fi.F90`. Both build identically here (the root `CMakeLists.txt` puts
`-cpp` on all Fortran sources) and the existing repo precedent `W1jet/t_fi.f90` is lowercase,
so the mixed extensions were left as authored rather than renamed mid-integrate.

## Group 2: BDK — one-loop coefficient translation queue

Queued before editing starts. Same folder/topic as Group 1: BDK one-loop coefficients for
the `u u~ e- e+ g g` process (Z2jet / W2jet / BDK / loop row).

- [x] software/mcfm/src/BDK/FFPPcc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FFPPsc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FMPFsc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FPFMccTtilde.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FPFMscT.f — VERIFIED (worst Δrel 0)

Group 2 is complete: all 5 units non-FAILED. Awaiting human approval before a new group
starts (approval is a human action; not recorded here).

### 2026-08-12 — Group 2 serial integrate

Wiring (this step's responsibility; authors were forbidden to touch build files):

- `software/mcfm/src/BDK/CMakeLists.txt`: swapped each Group 2 unit's `.f` entry for its
  generated `.cpp` + `_fi` shim (`FFPPcc.cpp`/`FFPPcc_fi.F90`, `FFPPsc.cpp`/`FFPPsc_fi.F90`,
  `FMPFsc.cpp`/`FMPFsc_fi.f90`, `FPFMccTtilde.cpp`/`FPFMccTtilde_fi.F90`,
  `FPFMscT.cpp`/`FPFMscT_fi.F90`).
- **Group 1's wiring had been lost and was restored here.** Both `src/BDK/CMakeLists.txt` and
  the top-level `software/mcfm/CMakeLists.txt` were back at their pre-Group-1 HEAD state when
  this step started: all five Group 1 `.f` entries were listed again and `src/BDK` was missing
  from the include path, even though the Group 1 originals sit in `deprecated/`. This matches
  the `FMPFsc` author note — an author ran `verify`, which auto-edited both files, then
  reverted them with `git checkout --`, discarding Group 1's integrate edits along with its
  own. Re-applied: Group 1's five `.cpp`/`_fi` entries, and `src/BDK` on the
  `objlib`/`libmcfm`/`test` include-directory lists.

No other shared wiring change was needed; no source file was edited during integration (unlike
Group 1, this round's units compiled as delivered — the `int * complex<double>` trap was
already avoided by the authors).

Coverage probes: all five markers were already in the single-line
`lhs = rhs;  // @coverage-probe` form `coverage_check.py` requires, each on the function-result
assignment inside the unit's `extern "C"` wrapper. Every caller of these five is still Fortran,
so the wrapper is on the real call path. No probe repositioning was needed this round.

`FPFMscT` note: the unit's entry point is `FPFMccT`, not `FPFMscT` — an upstream MCFM
filename/symbol mismatch the author preserved rather than renaming. It probed `COVERED`
through that name, confirming the shim is on the live call path from `FPFMcc.f`.

Harness bug still open (unchanged from Group 1, still unfixed): `python3 dev/workflow.py verify`
reports `NOT COVERED` for every file. `workflow.py` `run()` uses `cwd=ROOT`, and
`coverage_check.run_test` invokes `Bin/test` without a cwd, so the binary runs from the project
root and answers `Process not available in MCFM.` for both the baseline and probed run;
identical output reads as "not covered". Reproduced directly this round: `Bin/test -b u u~ e-
e+ g g` prints `Process not available in MCFM.` from the root and the real ratios from `Bin`.
Ran the Spec's own coverage oracle `dev/tools/coverage/coverage_check.py` from `$MCFM_HOME/Bin`
— the same directory `tests/mcfm/test.sh` uses — and all five units reported `COVERED`.
`workflow.py`/`coverage_check.py` are human-owned tooling and were not modified; a person
should still fix this (set `cwd` for the test subprocess).

Correctness bar: `jobrunner submit tests/mcfm` → SUCCESS, `SUMMARY: pass rate 272/272`, with
272 explicit `PASSED` markers and 0 `FAILED` (the Spec's silent-segfault trap requires the
positive markers, not merely the absence of failures). Benchmark tolerance 1e-13. For the BDK
coverage process `u u~ e- e+ g g` all four reported ratios (Finite, IR, IR2, Born) are exactly
1, so worst Δrel is 0. Covered + matching ⇒ all five VERIFIED. The suite was re-run after the
coverage probing to confirm the restored tree still passes.

Tree state: builds clean, no probe scaling left in any `.cpp`, the five originals are in
`software/mcfm/src/BDK/deprecated/`. Group 1 and Group 2 are both wired in.

Remaining for a human: approve Group 2; fix the `coverage_check.py` cwd bug; and note the
mixed `_fi.f90` / `_fi.F90` shim extensions across both groups (the Spec's Output shape writes
`_fi.F90`, but the root `CMakeLists.txt` puts `-cpp` on all Fortran sources so both build
identically, and repo precedent `W1jet/t_fi.f90` is lowercase — left as authored).

## Group 3: BDK — one-loop coefficient translation queue

Queued before editing starts. Same folder/topic as Groups 1–2: BDK one-loop coefficients for
the `u u~ e- e+ g g` process (Z2jet / W2jet / BDK / loop row).

- [x] software/mcfm/src/BDK/FPFPcc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FPFPsc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FPMFcc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/FPMFsc.f — VERIFIED (worst Δrel 0)
- [x] software/mcfm/src/BDK/fvs.f — TRANSLATED (build passes 272/272; coverage_check reports NOT COVERED under both BDK processes — Fvs is called, but scaling its result changes no compared benchmark number)

Group 3 is complete: all 5 units non-FAILED. Awaiting human approval before a new group
starts (approval is a human action; not recorded here).

### 2026-08-12 — Group 3 serial integrate

Wiring (this step's responsibility; authors were forbidden to touch build files):

- `software/mcfm/src/BDK/CMakeLists.txt`: swapped each Group 3 unit's `.f` entry for its
  generated `.cpp` + `_fi` shim (`FPFPcc.cpp`/`FPFPcc_fi.F90`, `FPFPsc.cpp`/`FPFPsc_fi.f90`,
  `FPMFcc.cpp`/`FPMFcc_fi.f90`, `FPMFsc.cpp`/`FPMFsc_fi.f90`, `fvs.cpp`/`fvs_fi.f90`).
- No shared wiring change was needed this round. `src/BDK` was already on the
  `objlib`/`libmcfm`/`test` include-directory lists in `software/mcfm/CMakeLists.txt` from
  Group 2, and Groups 1–2 entries were still intact (unlike Group 2, nothing had been
  reverted). All five originals were already in `software/mcfm/src/BDK/deprecated/`.

Fix applied during integration (build was broken as delivered):

- `FPMFcc.cpp:49`: `2 * za(j1, j3)` — a bare `int` literal multiplying a
  `std::complex<double>`, no matching `operator*`, hard compile error. This is the same trap
  Group 1 hit in `FFPMscT.cpp`/`FFPMscTtilde.cpp`. Changed to `2.0`, matching the original
  `FPMFcc.f:55` factor (`-2*za(j1,j3)*zab2(j3,j1,j2,j6)`) and the convention the sibling
  `FFPMccT.cpp` already used. A scan of all five units found no other integer-literal ×
  complex sites in either operand order.

Coverage probes: all five markers arrived already in the single-line
`lhs = rhs;  // @coverage-probe` form `coverage_check.py` requires, each on the
function-result assignment inside the unit's `extern "C"` wrapper. No repositioning was
needed. `FPFPcc`, `FPFPsc`, `FPMFcc`, `FPMFsc` reported `COVERED` under the BDK process
`u u~ e- e+ g g`.

`fvs` is the exception and is the reason it is `TRANSLATED`, not `VERIFIED`. It reported
`NOT COVERED` under *both* processes the Spec's coverage map gives for BDK
(`u u~ e- e+ g g` and `u d~ ve e+ g g`). This was investigated rather than assumed: a
temporary `fprintf` counter in `Fvs_wrapper` showed the wrapper *is* reached during
`u u~ e- e+ g g` (and never during `u d~ ve e+ g g`), so the shim is correctly on the live
call path from the still-Fortran `W2jet/xzqqgg_v.f` via `Z2jet/qqb_z2jet_v.f`. But
hand-scaling `Fvs_out` by 1.5 and rebuilding left all four reported quantities bit-identical
(`Finite 3.1535139416645479e-09`, `IR -3.6253551175804121e-09`, `IR2 -2.4633208158173431e-09`,
`Born 1.5134453543168024e-08`), so `Fvs`'s result reaches no compared benchmark number at
this phase-space point. The Spec requires the test to be *shown* to exercise the file via
`coverage_check.py`; that cannot be shown here, so `TRANSLATED` is the honest status. Retry
after `xzqqgg_v.f` or another caller is rewritten, or under a benchmark that compares the
quantity `Fvs` feeds. Both the trace and the hand-scaling were reverted; `fvs.cpp` is back to
its authored content.

Harness bug still open (unchanged from Groups 1–2, still unfixed): `python3 dev/workflow.py
verify` reports `NOT COVERED` for every file. `workflow.py` `run()` uses `cwd=ROOT`, and
`coverage_check.run_test` invokes `Bin/test` without a cwd, so the binary runs from the
project root and answers `Process not available in MCFM.` for both the baseline and probed
run; identical output reads as "not covered". Reproduced again this round: `Bin/test -b u u~
e- e+ g g` prints `Process not available in MCFM.` from the root and the real ratios from
`Bin`. As in prior rounds the Spec's own oracle `dev/tools/coverage/coverage_check.py` was run
directly from `$MCFM_HOME/Bin` — the same directory `tests/mcfm/test.sh` uses.
`workflow.py`/`coverage_check.py` are human-owned tooling and were not modified; a person
should still fix this (set `cwd` for the test subprocess).

Correctness bar: `jobrunner submit tests/mcfm` → SUCCESS, `SUMMARY: pass rate 272/272`, with
272 explicit `PASSED` markers and 0 `FAILED` (the Spec's silent-segfault trap requires the
positive markers, not merely the absence of failures). Benchmark tolerance 1e-13. For both BDK
coverage processes all four reported ratios (Finite, IR, IR2, Born) are exactly 1, so worst
Δrel is 0. Covered + matching ⇒ four VERIFIED; `fvs` matches but is not covered ⇒ TRANSLATED.
The suite was re-run after all coverage probing to confirm the restored tree still passes.

Tree state: builds clean, no probe scaling or trace code left in any `.cpp`, all fifteen
Group 1–3 originals are in `software/mcfm/src/BDK/deprecated/`.

Remaining for a human: approve Group 3; fix the `coverage_check.py` cwd bug; decide whether
`fvs` warrants a benchmark that exercises the quantity it feeds (it is currently unverifiable
by the mapped processes); and note the still-mixed `_fi.f90` / `_fi.F90` shim extensions
across all three groups (the Spec's Output shape writes `_fi.F90`, but the root
`CMakeLists.txt` puts `-cpp` on all Fortran sources so both build identically, and repo
precedent `W1jet/t_fi.f90` is lowercase — left as authored).
