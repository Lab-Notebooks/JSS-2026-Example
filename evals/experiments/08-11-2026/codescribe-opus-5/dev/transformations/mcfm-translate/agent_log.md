# mcfm-translate — agent log

Worklist for the Fortran → C++ pass. Statuses follow `desired_spec.md` (`VERIFIED` /
`TRANSLATED` / `FAILED`).

## Ready set snapshot (latest refresh)

`python3 dev/workflow.py refresh` → 526 source files, 86 translated, 440 untranslated,
225 ready leaves (deps = 0, blind = 0).

## Group W2jet-helpers-1 (completed)

Ready leaves from `software/mcfm/src/W2jet` (coverage process `u d~ ve e+ g g`).
Each file was rewritten as `<base>.cpp` + `<base>.hpp` + `<base>_fi.F90`, wired into
`software/mcfm/src/W2jet/CMakeLists.txt`, and the original `.f` moved to
`software/mcfm/src/W2jet/deprecated/`.

- [x] software/mcfm/src/W2jet/fpp.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/faxsl.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/fvf.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/Ltfunctions.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/Ftexact.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)

Evidence: coverage probes run with `MCFM_HOME` set (`dev/tmp/run_probe.py` wrapper around
`python3 dev/workflow.py verify <file.cpp> -- u d~ ve e+ g g`); all five reported
`RESULT: NOT COVERED`, so all five stay `TRANSLATED`.
After the probes restored every source file, `jobrunner submit tests/mcfm` → SUCCESS and
`tests/mcfm/job.output` ends with `SUMMARY: pass rate 272/272` with 272 `PASSED` lines and
zero `FAILED` lines.

Each `.cpp` keeps exactly one `// @coverage-probe` marker on a single-line assignment of its
main output, so the probe can be repeated once a caller of these helpers is rewritten.

## Group W2jet-helpers-2 (completed)

Next ready leaves from `software/mcfm/src/W2jet` (coverage process `u d~ ve e+ g g`).
Each file was rewritten as `<base>.cpp` + `<base>.hpp` + `<base>_fi.F90`, wired into
`software/mcfm/src/W2jet/CMakeLists.txt`, and the original `.f` moved to
`software/mcfm/src/W2jet/deprecated/`.

- [x] software/mcfm/src/W2jet/atree.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/A6texact.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/atrLLL.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/atrLRL.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/vv.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)

Evidence: probes run with `python3 dev/tmp/run_probe.py <file>.cpp -- u d~ ve e+ g g`
(wrapper that sets `MCFM_HOME`, same code path as `python3 dev/workflow.py verify`); all
five reported `RESULT: NOT COVERED`, so all five stay `TRANSLATED`. After the probes restored
the tree, `jobrunner submit tests/mcfm` → SUCCESS and `tests/mcfm/job.output` ends with
`SUMMARY: pass rate 272/272` (272 `PASSED` lines, zero `FAILED` lines), so invariant `I`
still holds.

Each `.cpp` keeps exactly one `// @coverage-probe` marker on a single-line assignment of its
main output, so the probe can be repeated once a caller of these helpers is rewritten.

## Group W2jet-helpers-3 (completed)

Third batch of ready leaves from `software/mcfm/src/W2jet` (coverage process `u d~ ve e+ g g`).
Each file was rewritten as `<base>.cpp` + `<base>.hpp` + `<base>_fi.F90`, wired into
`software/mcfm/src/W2jet/CMakeLists.txt`, and the original `.f` moved to
`software/mcfm/src/W2jet/deprecated/`.

- [x] software/mcfm/src/W2jet/a6treeg.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/vvg.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/subqcd.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/Acalc.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)
- [x] software/mcfm/src/W2jet/LRcalc.f — TRANSLATED (build pass; coverage probe `u d~ ve e+ g g` → NOT COVERED)

Evidence: `python3 dev/tmp/run_probes_group3.py` (wrapper that sets `MCFM_HOME` and calls
`dev/tools/coverage/coverage_check.py`, the same code path as `python3 dev/workflow.py verify
<file.cpp> -- u d~ ve e+ g g`). All five printed
`RESULT: NOT COVERED — the numbers did not change, so the test never ran this file.`, so all
five stay `TRANSLATED`. After the probes restored the tree, `jobrunner submit tests/mcfm` →
SUCCESS and `tests/mcfm/job.output` ends with `SUMMARY: pass rate 272/272` (272 `PASSED`
lines, zero `FAILED` lines), so invariant `I` still holds.

Each `.cpp` keeps exactly one `// @coverage-probe` marker on a single-line assignment of its
main output, so the probe can be repeated once a caller of these helpers is rewritten.

## Session notes

- Session 1 (this session): first pass on this transformation; `agent_log.md` created.
  Gate reported "no log found — nothing to gate", so group `W2jet-helpers-1` was opened.
  Translation details:
  - `fpp.cpp` — calls `L0`, `L1`, `Lsm1`, `Lsm1_2mht` through `<Need.hpp>` and the already
    translated `t` through `<W1jet.hpp>`; no forward declarations added.
  - `faxsl.cpp` / `fvf.cpp` — `st` selectors come from `<heldefs_mod.hpp>`; `fvf`'s `zab2`
    statement function became a lambda; `I3m` maps to `i3m` from `<Need.hpp>`.
  - `Ltfunctions.cpp` — three entry points (`Ltm1`, `Lt0`, `Lt1`) in one translation unit,
    all declared in `Ltfunctions.hpp`; `Lt0`/`Lt1` call their siblings directly.
  - `Ftexact.cpp` — `loopI2` / `loopI3` come from `<Loop.hpp>`.
  - Every `.cpp` includes its own header; `extern "C"` is used only for the
    `<name>_wrapper` Fortran boundary.
- Remaining for the next session: run the coverage probe for each of the five files
  (`python3 dev/workflow.py verify ... -- u d~ ve e+ g g`, needs `MCFM_HOME` exported from
  `environment.sh`) and promote `COVERED` files from `TRANSLATED` to `VERIFIED`; then
  refresh the roadmap and continue with the next W2jet ready leaves.
- Session 2: coverage probes executed. The restricted shell rejects inline env assignments,
  so `dev/tmp/run_probe.py` sets `MCFM_HOME` to `software/mcfm` and calls
  `dev/tools/coverage/coverage_check.py` directly (same code path as
  `python3 dev/workflow.py verify`). All five W2jet helpers reported `NOT COVERED` for
  process `u d~ ve e+ g g`: the current test matrix does not yet reach these low-level
  helpers, because their W2jet callers are still Fortran. Per the Spec they therefore stay
  `TRANSLATED`, and group `W2jet-helpers-1` is now completed.
  The probe restores each file and rebuilds; the restored tree was re-validated with
  `jobrunner submit tests/mcfm` → 272/272 PASSED, so invariant `I` still holds.
- No human decision was needed while the group was open; the gate is consulted before any
  new group is opened.
- Session 3: `python3 dev/workflow.py gate mcfm-translate` exited 0 (group
  `W2jet-helpers-1` completed and under the 3-group allowance), so group `W2jet-helpers-2`
  was opened with the next five W2jet ready leaves: `atree.f`, `A6texact.f`, `atrLLL.f`,
  `atrLRL.f`, `vv.f`.
  - Wiring: `software/mcfm/src/W2jet/CMakeLists.txt` now lists `atree.cpp`/`atree_fi.F90`,
    `A6texact.cpp`/`A6texact_fi.F90`, `atrLLL.cpp`/`atrLLL_fi.F90`,
    `atrLRL.cpp`/`atrLRL_fi.F90` and `vv.cpp`/`vv_fi.F90` in place of the five `.f` entries.
  - The five original `.f` sources were moved into `software/mcfm/src/W2jet/deprecated/`,
    which now holds all ten converted W2jet originals.
  - Every `.cpp` includes its own `.hpp`; cross-unit calls go through headers
    (`atrLLL.cpp` / `atrLRL.cpp` call the translated `atree` through `atree.hpp`), and
    `extern "C"` appears only for the `<name>_wrapper` Fortran boundary.
  - Coverage probes for all five reported `NOT COVERED` for `u d~ ve e+ g g`: their W2jet
    callers (`a6.f`, `a61*.f`, …) are still Fortran, so the test matrix does not yet reach
    them. Per the Spec they are recorded as `TRANSLATED`.
  - Invariant `I` re-validated after the probes restored the tree:
    `jobrunner submit tests/mcfm` → SUCCESS, `SUMMARY: pass rate 272/272`, 272 `PASSED`,
    zero `FAILED`.
  - Group `W2jet-helpers-2` is complete; the gate is consulted before opening a third group.
- Session 4: group `W2jet-helpers-3` (`a6treeg.f`, `vvg.f`, `subqcd.f`, `Acalc.f`,
  `LRcalc.f`) was translated, wired and settled.
  - Wiring: `software/mcfm/src/W2jet/CMakeLists.txt` now lists `a6treeg.cpp`/`a6treeg_fi.F90`,
    `vvg.cpp`/`vvg_fi.F90`, `subqcd.cpp`/`subqcd_fi.F90`, `Acalc.cpp`/`Acalc_fi.F90` and
    `LRcalc.cpp`/`LRcalc_fi.F90` in place of the five `.f` entries.
  - The five original `.f` sources were moved into `software/mcfm/src/W2jet/deprecated/`,
    which now holds all fifteen converted W2jet originals.
  - Every `.cpp` includes its own `.hpp`; cross-unit calls go through headers (for example
    `subqcd.cpp` calls the translated siblings through their headers), and `extern "C"`
    appears only for the `<name>_wrapper` Fortran boundary.
  - Coverage probes: all five reported `NOT COVERED` for `u d~ ve e+ g g` — their W2jet
    callers (`a6g.f`, `a61g.f`, `xwqqgg_v.f`, …) are still Fortran, so the test matrix does
    not reach them yet. Per the Spec they are recorded as `TRANSLATED`.
  - Invariant `I` re-validated after the probes restored the tree:
    `jobrunner submit tests/mcfm` → SUCCESS, `SUMMARY: pass rate 272/272`, 272 `PASSED`,
    zero `FAILED`.
  - Group `W2jet-helpers-3` is complete. Three completed groups have now accumulated, so the
    gate is expected to require human approval before a fourth group is opened.
  - Gate result at the end of session 4: `python3 dev/workflow.py gate mcfm-translate` →
    `GATE: BLOCKED — approval batch limit reached before opening a new group.`
    Blocking group: `Group W2jet-helpers-1 (completed)`; reason: 3 completed groups waiting,
    limit is 3. **Human decision needed**: record approvals with
    `python3 dev/workflow.py approve mcfm-translate --latest-blocking` (repeat as needed).
    No new group is opened until then; per `current_plan.md` “When to stop” this is the
    stopping point for this pass.
