# MCFM Translate Agent Log

## Group 1: Mods — module infrastructure translation queue

Queued before editing starts. Coverage map treats Mods as infrastructure (no coverage probe),
so each file's expected outcome is `TRANSLATED` rather than `VERIFIED`.

- [x] software/mcfm/src/Mods/types_mod.f — TRANSLATED (infrastructure: Mods — no coverage probe per Spec coverage map; build passes)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (infrastructure: Mods; build passes — Integrate wired ppwp2j_mod_init/_finalize into Modules_Interface.f90, without which pp was a null pointer and every Wjj process segfaulted)
- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (infrastructure: Mods; header-only, build passes)
- [ ] software/mcfm/src/Mods/Modules_Interface.f90 — verify: TRANSLATED (infrastructure: Mods)
- [x] software/mcfm/src/Mods/mod_qcdloop_c.f — TRANSLATED (infrastructure: Mods; build passes)

## Group 2: loop — generic loop-integral translation queue

Queued before editing starts. Coverage map maps `loop` to the `u d~ ve e+ g g` process
(W2jet / BDK / loop row), so these are expected `VERIFIED` if the probe lands, else `TRANSLATED`.

- [x] software/mcfm/src/loop/loopI4_generic.f — VERIFIED (worst Δrel 0, covered by u u~ e- e+ g g)
- [x] software/mcfm/src/loop/loopI2p_generic.f — TRANSLATED (build passes; NOT COVERED by any loop process in the Spec map (u d~ ve e+ g g, u u~ e- e+ g, u u~ e- e+ g g))
- [x] software/mcfm/src/loop/loopI1_generic.f — TRANSLATED (build passes; NOT COVERED by any loop process in the Spec map (u d~ ve e+ g g, u u~ e- e+ g, u u~ e- e+ g g))

## Group 3: Inc + Procdep — infrastructure translation queue

Queued before editing starts. Both folders fall under the coverage map's single
"Mods / Need / Inc / Procdep — infrastructure" row, so they share one topic/group even though
the folders differ.

- [ ] software/mcfm/src/Inc/tri123x4x56coeffs.f — verify: TRANSLATED (infrastructure: Inc)
- [x] software/mcfm/src/Inc/ppmax.f — TRANSLATED (infrastructure: Inc; INCLUDE fragment left in place, still textually included by pp_mod.f90 / ppwp2j_mod.f90; build passes)
- [x] software/mcfm/src/Procdep/chooser.f — TRANSLATED (infrastructure: Procdep; build passes)

## Group 4: Z2jet — two-jet amplitude translation queue

Queued before editing starts. Coverage map maps Z2jet to the `u u~ e- e+ g g` process.

- [x] software/mcfm/src/Z2jet/Bdiff.f — TRANSLATED (build passes; NOT COVERED by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/fmt.f — TRANSLATED (build passes; NOT COVERED by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/fzip.f — TRANSLATED (build passes; NOT COVERED by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/ampqqb_qqb.f — TRANSLATED (build passes; NOT COVERED by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/storecsz.f — VERIFIED (worst Δrel 0, covered by u u~ e- e+ g g)
- [x] software/mcfm/src/Z2jet/msq_z2jetx.f — TRANSLATED (build passes; NOT COVERED by u u~ e- e+ g g)

## Group 5: ThreeJets (part 1) — five-gluon amplitude translation queue

Queued before editing starts. Coverage map maps ThreeJets to `g g g g g` (any variant works).
Split from the full ThreeJets batch (12 files) to keep group size near the Plan's ~5-file target.

- [x] software/mcfm/src/ThreeJets/A5qbmqpgpgpgm.f — VERIFIED (worst Δrel 7e-16, covered by d~ d g g g)
- [x] software/mcfm/src/ThreeJets/A51mpmpp5g.f — VERIFIED (worst Δrel 2e-15, covered by g g g g g)
- [x] software/mcfm/src/ThreeJets/A5qbmqpgpgmgp.f — VERIFIED (worst Δrel 7e-16, covered by d~ d g g g)
- [x] software/mcfm/src/ThreeJets/fillDij.f — VERIFIED (worst Δrel 4e-15, covered by d d~ u u~ g)
- [x] software/mcfm/src/ThreeJets/A5qbmqpgmgpgp.f — VERIFIED (worst Δrel 7e-16, covered by d~ d g g g)

## Group 6: ThreeJets (part 2) — five-gluon amplitude translation queue

Continuation of the ThreeJets batch, same folder and topic (`g g g g g`) as Group 5.

- [x] software/mcfm/src/ThreeJets/A5qbmgmqpgpgp.f — VERIFIED (worst Δrel 7e-16, covered by d~ d g g g)
- [x] software/mcfm/src/ThreeJets/fillEij.f — VERIFIED (worst Δrel 4e-15, covered by d d~ u u~ g)
- [x] software/mcfm/src/ThreeJets/A5qbmgpqpgmgp.f — VERIFIED (worst Δrel 7e-16, covered by d~ d g g g)
- [x] software/mcfm/src/ThreeJets/A5qbmgpqpgpgm.f — VERIFIED (worst Δrel 7e-16, covered by d~ d g g g)
- [x] software/mcfm/src/ThreeJets/A51mmppp5g.f — VERIFIED (worst Δrel 2e-15, covered by g g g g g)

## Group 7: ThreeJets (part 3) — five-gluon amplitude translation queue

Remainder of the ThreeJets batch, same folder and topic (`g g g g g`) as Groups 5-6.

- [x] software/mcfm/src/ThreeJets/qqb_thrjet_v.f — VERIFIED (worst Δrel 2e-15, covered by g g g g g)

## Group 8: BDK (part 1) — bootstrap amplitude translation queue

Queued before editing starts. BDK is not a coverage-map table row directly; nearest process
mapping (loop/W2jet/Z2jet/BDK all share `... g g`-style rows) is TBD per-file until checked
against the nearest process folder — mark `TRANSLATED` if it turns out uncovered. Split from
the full BDK batch (12 files) to keep group size near the Plan's ~5-file target.

- [x] software/mcfm/src/BDK/fvs.f — TRANSLATED (build passes; NOT COVERED by u d~ ve e+ g g or u u~ e- e+ g g)
- [x] software/mcfm/src/BDK/FPFMscT.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)
- [x] software/mcfm/src/BDK/FPMFsc.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)
- [x] software/mcfm/src/BDK/FFPPcc.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)

## Group 9: BDK (part 2) — bootstrap amplitude translation queue

Continuation of the BDK batch, same folder and topic (bench TBD) as Group 8.

- [x] software/mcfm/src/BDK/FFPPsc.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)
- [x] software/mcfm/src/BDK/M3abit1.f — TRANSLATED (build passes; NOT COVERED by u d~ ve e+ g g or u u~ e- e+ g g)
- [x] software/mcfm/src/BDK/FPFMccTtilde.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)
- [x] software/mcfm/src/BDK/FPFPsc.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)

## Group 10: BDK (part 3) — bootstrap amplitude translation queue

Remainder of the BDK batch, same folder and topic (bench TBD) as Groups 8-9.

- [x] software/mcfm/src/BDK/M2bit2.f — TRANSLATED (build passes; NOT COVERED by u d~ ve e+ g g or u u~ e- e+ g g)
- [x] software/mcfm/src/BDK/M2bit3.f — TRANSLATED (build passes; NOT COVERED by u d~ ve e+ g g or u u~ e- e+ g g)
- [x] software/mcfm/src/BDK/FPFPcc.f — VERIFIED (worst Δrel 0, covered by u d~ ve e+ g g)
- [x] software/mcfm/src/BDK/M1bit1.f — TRANSLATED (build passes; NOT COVERED by u d~ ve e+ g g or u u~ e- e+ g g)

## Notes / session log

- 2026-08-12: Recorded this round's 41-unit worklist across Groups 1-10 before any editing
  started, per the group-sizing/topic rule in `current_plan.md`'s Resolution section (same
  folder or test topic, ~5 files per group). Groups 1-4 are single-topic batches at or under
  the target size; Groups 5-7 split ThreeJets (12 files, topic `g g g g g`) and Groups 8-10
  split BDK (12 files, bench TBD) into ~5-file slices. No rewriting, building, or verification
  has happened yet — all lines are unchecked placeholders for the round about to start.

- 2026-08-12 (Integrate): Wired all 38 authored units of this round into the build and ran the
  Spec's oracle. Build wiring: swapped each unit's `.f`/`.f90` entry for its `.cpp` + shim in
  `src/{Mods,loop,Procdep,Z2jet,ThreeJets,BDK}/CMakeLists.txt`; added `src/Z2jet`,
  `src/ThreeJets`, `src/BDK`, `src/Procdep` to the three `target_include_directories` lines in
  `software/mcfm/CMakeLists.txt` (the new units use `#include <Own.hpp>`, which GCC does not
  resolve from the including file's own directory); moved the leftover
  `src/ThreeJets/A5qbmqpgmgpgp.f` into `ThreeJets/deprecated/` so it stops colliding with the
  new `.cpp` + `.f90` shim. `src/Inc` has no `CMakeLists.txt` and `Inc/ppmax.f` was
  deliberately left in place, so nothing to wire there.
- 2026-08-12 (Integrate): Three defects had to be fixed here before the tree would build or run.
  (1) `Mods/ppwp2j_mod.f90`'s `c_f_pointer` shim is only valid after `ppwp2j_mod_init()` runs,
  and nothing called it — `Mods/Modules_Interface.f90` (this round's one deferred Mods unit) had
  no entry for it, so `pp` stayed null and every W+jj / W-jj process segfaulted. The first bench
  run showed `pass rate 198/272` with **zero** `FAILED` markers — exactly Spec silent trap #9 —
  and gdb put the fault at `W2jet/qqb_wp2jetx_new.f:871` on `pp(j,k,-n1,0)`. Added the
  `ppwp2j_mod_init`/`ppwp2j_mod_finalize` use+call pairs to `Modules_Interface.f90`.
  (2) 75 sites across `BDK/FFPPsc.cpp`, `BDK/FPFMccTtilde.cpp` and `ThreeJets/fillDij.cpp`
  multiplied an integer literal by a `std::complex<double>`, which C++ (unlike Fortran) will not
  do; promoted just those literals to double (`2` -> `2.0`), value-preserving.
  (3) `Inc/FArray.hpp`'s `FArray1D<T>::fill` wrote `*this(i) = value` (parses as `*(this(i))`);
  latent until `ThreeJets/fillEij.cpp` became its first instantiation. Fixed to `(*this)(i)`.
- 2026-08-12 (Integrate): Coverage probes. 19 of the 32 non-infrastructure units shipped a probe
  that `dev/tools/coverage/coverage_check.py` cannot rewrite — its scaler needs the whole
  `lhs = rhs;  // @coverage-probe` on one line — plus `loopI2p_generic.cpp` had two markers,
  `fillEij.cpp` three, and `loopI1_generic.cpp`/`fillDij.cpp` none. Normalized every one to a
  single well-formed marker (pure reformatting; for `fvs`, `FPFPcc`, `FPMFsc` and `M2bit3`,
  whose output statement was a bare `return <expr>;`, the expression was bound to a local
  `<name>_value` first, matching the sibling convention already used by `FPFPsc`, `M2bit2`,
  `M3abit1` and `FPFMccTtilde`).
- 2026-08-12 (Integrate) — **for a human**: `python3 dev/workflow.py verify` can never report
  `COVERED`. `dev/workflow.py`'s `run()` forces `cwd=ROOT`, so `coverage_check.py` launches
  `Bin/test` from the project root, where MCFM answers `Process not available in MCFM.`
  identically for the baseline and probed builds. This round's coverage results therefore come
  from invoking the Spec's named oracle directly with the correct working directory:
  `cd $MCFM_HOME/Bin && python3 $PROJECT_HOME/dev/tools/coverage/coverage_check.py <abs .cpp> -- <process>`.
  `dev/workflow.py` is not AI-owned, so the cwd bug was left unfixed — please repair it (or
  document the required cwd) before the next round relies on the wrapper.
- 2026-08-12 (Integrate): Oracle result — `jobrunner submit tests/mcfm` finishes at
  `SUMMARY: pass rate 272/272`, matching the pre-round baseline, with every individual case
  printing `PASSED` (checked explicitly against silent trap #9; tolerance 1e-13). 21 units are
  `VERIFIED`, 17 `TRANSLATED`; none `FAILED`. ThreeJets probes used the Spec's
  "any variant works" allowance: the six `A5qbm*` amplitudes need a quark variant
  (`d~ d g g g`) and `fillDij`/`fillEij` a four-quark variant (`d d~ u u~ g`); `g g g g g`
  alone leaves them unexercised.
- 2026-08-12 (Integrate) — **needs a human decision**: two Group 1/3 units are still unchecked
  because their authors produced no artifact and deferred by design.
  `software/mcfm/src/Mods/Modules_Interface.f90` is an aggregator over ~60 module-internal
  `X_mod_init` procedures with no portable `bind(C)` symbols, so translating it would mean
  either guessing mangled names or editing 60 sibling units.
  `software/mcfm/src/Inc/tri123x4x56coeffs.f` is a bare INCLUDE fragment with no signature; it
  should be inlined when `W2jet/qqbggAxtri123x4x56.f` is translated, not settled on its own.
  Both need the Plan owner to re-scope or drop them; Groups 1 and 3 cannot close until then.
- 2026-08-12 (Integrate): New C++/shim files are on disk and wired but left uncommitted in the
  `software/mcfm` submodule, matching how this round's authors left them.
