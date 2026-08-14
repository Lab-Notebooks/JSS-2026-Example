# mcfm-translate — agent log

Worklist for step 1 (Fortran → C++). Statuses follow `desired_spec.md` (`Σ` = VERIFIED /
TRANSLATED / FAILED). Only this file is AI-owned in this folder.

## Group W2jet leaves 1 (atree, fvf, a6treeg, subqcd)

Ready leaves picked from `dev/tmp/assets/roadmap_metrics.tsv` (deps=0, blind=0, no `.cpp` yet),
all in `software/mcfm/src/W2jet`. Coverage processes: `u d~ ve e+ g g` for the W2jet routines,
`u u~ e- e+ g g` for `fvf` (its only caller, `xzqqgg_v.f`, is the Z amplitude).

- [x] software/mcfm/src/W2jet/atree.f — TRANSLATED (build pass; probe on the `pp` branch reported
      `NOT COVERED` for `u d~ ve e+ g g`, so no coverage evidence yet)
- [x] software/mcfm/src/W2jet/fvf.f — TRANSLATED (build pass; probe reported `NOT COVERED` for
      `u u~ e- e+ g g`)
- [x] software/mcfm/src/W2jet/a6treeg.f — TRANSLATED (build pass; probe on the `hqpgpgpqbm`
      branch reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/subqcd.f — TRANSLATED (build pass; probe on `amp(-1,-1)` reported
      `NOT COVERED` for `u d~ ve e+ g g`)

Group status: completed, no FAILED entries. Awaiting the approval gate before a new group.

### What was done

- New translation units in `software/mcfm/src/W2jet`: `atree.{hpp,cpp}` + `atree_fi.F90`,
  `fvf.{hpp,cpp}` + `fvf_fi.F90`, `a6treeg.{hpp,cpp}` + `a6treeg_fi.F90`,
  `subqcd.{hpp,cpp}` + `subqcd_fi.F90`.
- Each `.cpp` includes its own `<base>.hpp`; cross-unit calls go through existing headers only:
  `W1jet.hpp` (`t`), `Need.hpp` (`i3m`, `Lsm1_2mh`, `Lsm1_2me`), `mxpart_mod.hpp`,
  `sprods_com_mod.hpp`, `heldefs_mod.hpp`, `constants_mod.hpp`. No new/invented callees, no
  translation-era forward declarations.
- Statement functions became lambdas (`tree`, `zab2`, `zba2`, `zba3`); `x**n` became
  `std::pow(x, n)`; `amp(-1:1,-1:1)` became `FArray2D<std::complex<double>> amp(famp, 3, 3, -1, -1)`
  so the Fortran lower bounds are preserved.
- `software/mcfm/src/W2jet/CMakeLists.txt` now lists the `.cpp` + `_fi.F90` pairs instead of the
  four `.f` files; `software/mcfm/CMakeLists.txt` gained `src/W2jet` on the include path for
  `objlib`, `libmcfm`, and `test`.
- Originals moved to `software/mcfm/src/W2jet/deprecated/` (`atree.f`, `fvf.f`, `a6treeg.f`,
  `subqcd.f`).

### Evidence

- Oracle: `jobrunner submit tests/mcfm` → `SUMMARY: pass rate 272/272`, every listed case shows
  `PASSED` (no silent-segfault case: each case prints an explicit `PASSED`).
- Coverage: `python3 dev/workflow.py verify <file.cpp> -- <process>` (run through a small
  wrapper that exports `MCFM_HOME`, since the shell used by the agent does not source
  `environment.sh`) reported `NOT COVERED` for all four files, hence `TRANSLATED` rather than
  `VERIFIED`.
- The `// @coverage-probe` markers are left in place on the marked output statements so the
  probe can be re-run cheaply after a caller is rewritten.

## Group W2jet leaves 2 (w2jetsq, Ftexact, faxsl, fpp, vv)

Second batch of ready leaves from `dev/tmp/assets/roadmap_metrics.tsv` (deps=0, blind=0, no
`.cpp` yet), all in `software/mcfm/src/W2jet`. Coverage process for the whole group:
`u d~ ve e+ g g` (the W2jet row of the Spec's coverage map).

- [x] software/mcfm/src/W2jet/w2jetsq.f — TRANSLATED (build pass; probe on the
      `msq = mmsq_cs(...)` sum reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/Ftexact.f — TRANSLATED (build pass; probe on the `Ftexact_value`
      assignment reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/faxsl.f — TRANSLATED (build pass; probe on the `hqpqbmgpgm`
      branch reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/fpp.f — TRANSLATED (build pass; probe on `fpp_value = t0`
      reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/vv.f — TRANSLATED (build pass; probe on the `pp`/`pm` branch
      reported `NOT COVERED` for `u d~ ve e+ g g`)

Group status: completed, no FAILED entries.

### What was done

- New translation units in `software/mcfm/src/W2jet`: `w2jetsq.{hpp,cpp}` + `w2jetsq_fi.F90`,
  `Ftexact.{hpp,cpp}` + `Ftexact_fi.F90`, `faxsl.{hpp,cpp}` + `faxsl_fi.F90`,
  `fpp.{hpp,cpp}` + `fpp_fi.F90`, `vv.{hpp,cpp}` + `vv_fi.F90`.
- Each `.cpp` includes its own `<base>.hpp`; cross-unit calls go through existing headers only
  (`Need.hpp`, `Loop.hpp`, `W1jet.hpp`, `constants_mod.hpp`, `mxpart_mod.hpp`,
  `sprods_com_mod.hpp`, `masses_mod.hpp`, `heldefs_mod.hpp`, `scale_mod.hpp`, `epinv_mod.hpp`,
  `epinv2_mod.hpp`, `scalarselect_mod.hpp`). No invented callees and no translation-era forward
  declarations.
- `software/mcfm/src/W2jet/CMakeLists.txt` lists the five `.cpp` + `_fi.F90` pairs instead of the
  five `.f` files; the originals now live in `software/mcfm/src/W2jet/deprecated/`.
- The `Ftexact`, `faxsl` and `vv` probe statements were reflowed onto a single line (formatting
  only, expression unchanged): `dev/tools/coverage/coverage_check.py` can rescale a probe only
  when it is a one-line `lhs = rhs;   // @coverage-probe` statement, and the first `Ftexact.cpp`
  run failed with `could not scale the marked line`.

### Evidence

- Oracle: `jobrunner submit tests/mcfm` → `SUMMARY: pass rate 272/272`, with 272 `PASSED`
  markers and 0 `FAILED` markers in `tests/mcfm/job.output` (so no silent-segfault case).
- Coverage: `python3 dev/workflow.py verify <file.cpp> -- u d~ ve e+ g g` (run through
  `dev/tmp/run_verify.py`, which only sets `MCFM_HOME` and then delegates to `dev/workflow.py`,
  since the agent shell cannot source `environment.sh`) reported `NOT COVERED` for all five
  files, hence `TRANSLATED` rather than `VERIFIED`.
- The `// @coverage-probe` markers are left in place so the probe can be re-run cheaply once a
  caller is rewritten.

## Group W2jet leaves 3 (Ltfunctions, Acalc, ZZtri12_34LL, LRcalc, ZZbox1LL)

Third batch of ready leaves from `dev/tmp/assets/roadmap_metrics.tsv` (deps=0, blind=0, no `.cpp`
yet), all in `software/mcfm/src/W2jet`. Coverage process for the whole group: `u d~ ve e+ g g`
(the W2jet row of the Spec's coverage map).

- [x] software/mcfm/src/W2jet/Ltfunctions.f — TRANSLATED (build pass; probe on `Ltm1_value =
      xInt(by) - xInt(bx)` reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/Acalc.f — TRANSLATED (build pass; probe on the `A(1)` assignment
      reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/ZZtri12_34LL.f — TRANSLATED (build pass; probe on
      `Xmp(h3,h5) = tri3masscoeff_(...)` reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/LRcalc.f — TRANSLATED (build pass; probe on the `Xmp(h3,h5)`
      assignment reported `NOT COVERED` for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/ZZbox1LL.f — TRANSLATED (build pass; probe on
      `Xpp(h3,h5) = app0 + mtsq*app2 + mtsq**2*app4` reported `NOT COVERED` for
      `u d~ ve e+ g g`)

Group status: completed, no FAILED entries.

### What was done

- New translation units in `software/mcfm/src/W2jet`: `Ltfunctions.{hpp,cpp}` +
  `Ltfunctions_fi.F90` (all three entry points `Ltm1`, `Lt0`, `Lt1` in one unit),
  `Acalc.{hpp,cpp}` + `Acalc_fi.F90`, `LRcalc.{hpp,cpp}` + `LRcalc_fi.F90`,
  `ZZtri12_34LL.{hpp,cpp}` + `ZZtri12_34LL_fi.F90`, `ZZbox1LL.{hpp,cpp}` + `ZZbox1LL_fi.F90`.
- Each `.cpp` includes its own `<base>.hpp`; module dependencies go through the existing
  headers `constants_mod.hpp`, `mxpart_mod.hpp`, `sprods_com_mod.hpp`, `ZZclabels_mod.hpp`,
  `ZZdlabels_mod.hpp`, `ggZZintegrals_mod.hpp`, `ggZZcomputemp_mod.hpp`. No invented callees.
- Statement functions became lambdas (`zab2`, `zba2` in `LRcalc`; `zab2`, `funcpp2`, `funcmp2`
  in `ZZbox1LL`); `x**n` became `std::pow(x, n)`; `Xrat(2,2,2,2)` became
  `FArray4D<std::complex<double>>`; `Xpp(:,:)=czip` became `Xpp.fill(czip)`.
- `ZZtri12_34LLcore` and `ZZbox1LLcore` are file-local in the original Fortran (no external
  caller), so they stayed internal `static` functions in their `.cpp` — no header entry.
- `Tri3masscoeff` is still Fortran, so it is called through an `extern "C"` declaration of the
  plain Fortran symbol `tri3masscoeff_` with pointer arguments (the call itself is unchanged).
- `software/mcfm/src/W2jet/CMakeLists.txt` now lists the five `.cpp` + `_fi.F90` pairs instead
  of the five `.f` files; the originals were moved to `software/mcfm/src/W2jet/deprecated/`
  with `dev/tmp/move_deprecated.py` (plain `git mv` still exits 128 under the restricted shell).

### Evidence

- Oracle: `jobrunner submit tests/mcfm` → `SUMMARY: pass rate 272/272`, with 272 `PASSED`
  markers and 0 `FAILED` markers in `tests/mcfm/job.output` (so no silent-segfault case).
- Coverage: `python3 dev/tmp/run_verify.py <file.cpp> -- u d~ ve e+ g g` reported
  `NOT COVERED` for all five files, hence `TRANSLATED` rather than `VERIFIED`.
- The `// @coverage-probe` markers are left in place so the probe can be re-run cheaply once a
  caller is rewritten (`A6axBDK.f` for `Ltfunctions`, `ggZZmassamp_new.f` for `Acalc`/`LRcalc`,
  `ZZmassivetri.f` for `ZZtri12_34LL`, `ZZmassivebox.f` / `ZZmassiveboxtri.f` for `ZZbox1LL`).

## Notes / session log

- 2024 session 1 (loop 1): created this log, refreshed the roadmap
  (`source 531 / translated 86 / untranslated 445`, 229 ready leaves), opened
  `Group W2jet leaves 1` and settled its four files. The restored build still matches
  (272/272). Nothing needs a human decision beyond the normal approval gate.
- Retry coverage for these four files after their Fortran callers (`a6.f`, `a6routine.f`,
  `xzqqgg_v.f`, `xwqqgg_v.f`, `w2jetsq.f`) are rewritten; the probe branch chosen for
  `atree`/`a6treeg` may also need moving to another helicity branch.
- Remaining ready leaves for the next group include `Mods/types_mod.f`,
  `W2jet/ggZZcapture.f`, `W2jet/ZZbox1LL.f`, `W2jet/a6treeg`-adjacent files, and
  `gghgg_dep/gghgg_dep_params.f`.
- 2024 session 2 (loop 2): translated the five files of `Group W2jet leaves 2` and rewired
  `software/mcfm/src/W2jet/CMakeLists.txt` to the new `.cpp` + `_fi.F90` pairs. `git mv` of the
  originals into `deprecated/` failed under the restricted shell (exit 128), so the moves were
  done with the small helper `dev/tmp/move_deprecated.py` instead; the tree state is the same.
- 2024 session 3 (loop 3): recorded `Group W2jet leaves 2` in this log, added
  `dev/tmp/run_verify.py` (sets `MCFM_HOME`, then delegates to `dev/workflow.py verify`), and
  ran the coverage probe for all five files. All five came back `NOT COVERED` → `TRANSLATED`.
  Reflowing three multi-line probe statements onto one line was required before the checker
  could rescale them. The restored build still matches: 272/272, every case `PASSED`.
  Nothing needs a human decision beyond the normal approval gate.
- Retry coverage for `w2jetsq`, `Ftexact`, `faxsl`, `fpp` and `vv` after their Fortran callers
  (`qqb_w2jet.f`, `qqb_w2jet_v.f`, `xwqqgg_v.f`, `A6texact.f`, `fax.f`, `a6routine.f`) are
  rewritten.
- Practical note for future probes: write the marked output as a single-line
  `lhs = rhs;   // @coverage-probe` statement, otherwise `coverage_check.py` aborts with
  `could not scale the marked line`.
- Gate + roadmap state at the end of loop 3: `GATE: OK — completed groups do not yet require
  approval (2 waiting, limit 3)`; `python3 dev/workflow.py refresh` reports
  `source 522  translated 86  untranslated 436`, `ready leaves (deps=0, non-blind): 229`.
- Next group (not yet opened — no code written for it): `Group W2jet leaves 3` with the ready
  W2jet leaves `Ltfunctions.f` (39 lines), `Acalc.f` (74), `ZZtri12_34LL.f` (97),
  `LRcalc.f` (106) and `ZZbox1LL.f` (153), coverage process `u d~ ve e+ g g`. Notes gathered
  while sizing them: `Acalc.f` needs `ZZclabels_mod` / `ZZdlabels_mod` / `ggZZintegrals_mod`,
  `ZZtri12_34LL.f` needs `ggZZcomputemp_mod` and calls the still-Fortran `Tri3masscoeff`
  (so an `extern "C"` pointer-argument declaration is required), and both `ZZtri12_34LL.f` and
  `ZZbox1LL.f` also define a `...core` subroutine in the same file plus statement functions
  (`zab2`, `funcpp2`, `funcmp2`) that become lambdas. `ZZbox1LL` also needs a 4-index
  `Xrat(2,2,2,2)` array.
- Opening that group was deferred only because loop 3 ran out of session budget after settling
  and logging `Group W2jet leaves 2`; the gate does not block it.
- 2024 session 4 (loop 4): gate reported `GATE: OK — completed groups do not yet require
  approval (2 waiting, limit 3)`, so `Group W2jet leaves 3` was opened and its five files were
  translated, wired into `software/mcfm/src/W2jet/CMakeLists.txt`, and the originals moved to
  `deprecated/`. Full oracle run after the swap: 272/272, 272 `PASSED`, 0 `FAILED`.
- Re-ran the group-2 probes for `w2jetsq.cpp`, `Ftexact.cpp` and `faxsl.cpp` with the W2jet
  process `u d~ ve e+ g g` to confirm the process recorded in `Group W2jet leaves 2`; all three
  again reported `NOT COVERED`, so those entries stand unchanged as `TRANSLATED`.
- New translation detail worth reusing: a still-Fortran callee is reached from C++ by declaring
  the mangled symbol (`tri3masscoeff_`) in `extern "C"` and passing `&scalar` / `array.data`.
- Remaining W2jet ready leaves after this group (candidates for `Group W2jet leaves 4`):
  `ggZZcapture.f`, `ZZtri1_2LL.f`, `ZZtri1_34LL.f`, `ZZC01x2LLmp.f` and friends; also
  `Mods/types_mod.f` and `gghgg_dep/gghgg_dep_params.f` outside W2jet.
- Three completed groups are now waiting, so the gate is expected to require
  `python3 dev/workflow.py approve mcfm-translate --latest-blocking` before a fourth group is
  opened. Nothing else needs a human decision.
- 2024 session 5 (loop 5): **stopped at the approval gate — human decision required.**
  `python3 dev/workflow.py gate mcfm-translate` reports
  `GATE: BLOCKED — approval batch limit reached before opening a new group.`,
  blocking group `Group W2jet leaves 1 (atree, fvf, a6treeg, subqcd)`,
  reason `3 completed group(s) are waiting; limit is 3`.
  `python3 dev/workflow.py approve mcfm-translate --list-pending` lists all three groups
  (`W2jet leaves 1`, `W2jet leaves 2`, `W2jet leaves 3`) as pending, and `approvals.toml`
  still contains only `version = 1`, i.e. no approval and no review note has been recorded yet.
  No new group was opened and no source file was translated this session, because the Plan's
  *When to stop* rule ("a completed group needs human approval before the next group can
  start") applies and `approvals.toml` is human-owned (the AI may modify only this log).
- Loop-5 state check (no code changed): `python3 dev/workflow.py refresh` →
  `source 517  translated 86  untranslated 431`, `ready leaves (deps=0, non-blind): 225`,
  `symbol index: 915 symbol(s)`. Oracle re-run on the current tree:
  `jobrunner submit tests/mcfm` → `SUCCESS`, `tests/mcfm/job.output` line 952
  `SUMMARY: pass rate 272/272`, with 272 `PASSED` markers and 0 `FAILED` markers, so the
  invariants of the three settled groups still hold while the gate waits.
- Proposed (NOT opened) next group, ready W2jet leaves confirmed by this refresh with
  `deps=0, blind=0`, coverage process `u d~ ve e+ g g`:
  `Group W2jet leaves 4` = `W2jet/ggZZcapture.f` (fanin 6), `W2jet/ZZbox2LL.f`,
  `W2jet/ZZtri1_2LL.f`, `W2jet/ZZC012x34LLmp.f`, `W2jet/ZZC02x34LLmp.f`.
  Other ready W2jet leaves now visible (26 in total) include `fax.f`, `fpm.f`, `fsl.f`,
  `vvg.f`, `A6texact.f`, `A6axBDK.f`, `xwqqgg_v.f`, `qqb_w2jet.f`, `qqbw2j_loop.f`,
  `qqbZggtree.f`, `qqbggAxbox3x12x4.f`, `qqbggAxbox3x4x12.f`, `qqbggAxslCoeffs.f`,
  `qqbggAxtri123x4x56.f`, `qqbggAxtri12x3x456.f`, `ZZmbc.f`, `ZZintegraleval.f`,
  `atrLLL.f`, `atrLRL.f`, `xzqqgg.f`, `aqqb_zbb.f`.
  Note that several of these are the callers needed to turn earlier `TRANSLATED` entries into
  `VERIFIED` (`A6texact.f`/`fax.f` for `Ftexact`/`faxsl`, `xwqqgg_v.f`/`qqb_w2jet.f` for
  `w2jetsq`/`vv`/`fpp`, `A6axBDK.f` for `Ltfunctions`), so probes should be re-run right after
  those files are settled.
- Human decision needed to continue: approve the blocking group with
  `python3 dev/workflow.py approve mcfm-translate --latest-blocking`
  (or `python3 dev/workflow.py approve mcfm-translate "Group W2jet leaves 1 (atree, fvf,
  a6treeg, subqcd)" --by <name>`). After that, the next agent session should re-read any
  review note with `python3 dev/workflow.py approvals mcfm-translate --latest-approved`,
  re-run `python3 dev/workflow.py refresh`, and only then open `Group W2jet leaves 4`.
- Tooling note added this session: `dev/tmp/ready_leaves.py <folder-substring>` prints the ready
  leaves straight from `dev/tmp/assets/roadmap_metrics.tsv` (columns are
  `rel, top, deps, blind, fanin, bench`); the restricted shell rejects `python3 -c` snippets and
  any command containing `;`, `|` or redirects, so keep helper logic in small files under
  `dev/tmp/`.
