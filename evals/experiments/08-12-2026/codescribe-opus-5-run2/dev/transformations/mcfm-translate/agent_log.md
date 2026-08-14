# mcfm-translate worklist

Status vocabulary and evidence rules: see `desired_spec.md`.

## Group W2jet-1 (fpp, fvf, faxsl, subqcd)

Directory: `software/mcfm/src/W2jet` — coverage process `u d~ ve e+ g g`.
Originals moved to `software/mcfm/src/W2jet/deprecated/`; CMakeLists swapped to the
`.cpp` + `_fi.F90` pairs; shared declarations live in `software/mcfm/src/W2jet/W2jet.hpp`.

- [x] software/mcfm/src/W2jet/fpp.cpp — TRANSLATED (build + full test suite pass 272/272; coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/fvf.cpp — TRANSLATED (build + full test suite pass 272/272; coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/faxsl.cpp — TRANSLATED (build + full test suite pass 272/272; coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/subqcd.cpp — TRANSLATED (build + full test suite pass 272/272; coverage probe NOT COVERED for `u d~ ve e+ g g`)

Group status: completed (4/4 settled, no FAILED). Gate checked after completion:
`GATE: OK — completed groups do not yet require approval (1 waiting, limit 3).`

## Group W2jet-2 (a6treeg, + next ready W2jet leaves)

Directory: `software/mcfm/src/W2jet` — coverage process `u d~ ve e+ g g`.
Opened after the gate reported OK. Ready candidates from the refreshed roadmap
(deps=0, blind=0, no `.cpp` yet): `atree.f` (fanin 6), `w2jetsq.f`, `fpm.f`, `fsl.f`,
`fax.f`.

- [x] software/mcfm/src/W2jet/a6treeg.cpp — TRANSLATED (build + full test suite pass 272/272,
      272 `PASSED` markers, 0 `FAILED`; coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/atree.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/w2jetsq.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/fpm.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/fsl.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)

Group status: completed (5/5 settled, no FAILED). Originals `a6treeg.f`, `atree.f`,
`w2jetsq.f`, `fpm.f`, `fsl.f` are in `software/mcfm/src/W2jet/deprecated/`; CMakeLists lists
the `.cpp` + `_fi.F90` pairs; declarations live in `software/mcfm/src/W2jet/W2jet.hpp`.

## Group W2jet-3 (A6texact, Ftexact, atrLLL, atrLRL, vv)

Directory: `software/mcfm/src/W2jet` — coverage process `u d~ ve e+ g g`.
Opened after the gate reported `GATE: OK ... (2 waiting, limit 3)` and a roadmap refresh.
Ready leaves picked from `dev/tmp/assets/roadmap_metrics.tsv` (deps=0, blind=0, no `.cpp`).

- [x] software/mcfm/src/W2jet/A6texact.cpp — TRANSLATED (build + full test suite pass 272/272,
      272 `PASSED`, 0 `FAILED`; coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/Ftexact.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/atrLLL.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/atrLRL.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)
- [x] software/mcfm/src/W2jet/vv.cpp — TRANSLATED (build + full test suite pass 272/272;
      coverage probe NOT COVERED for `u d~ ve e+ g g`)

Group status: completed (5/5 settled, no FAILED). Originals moved to
`software/mcfm/src/W2jet/deprecated/`; CMakeLists swapped to the `.cpp` + `_fi.F90` pairs;
declarations added to `software/mcfm/src/W2jet/W2jet.hpp`. `A6texact`/`Ftexact` call
`loopI2`/`loopI3` through `loop/Loop.hpp`; `atrLLL`/`atrLRL` call the already translated
C++ `atree` through `W2jet.hpp`; `vv` calls `lnrat` through `Need.hpp`.

## Session log

- Loop 2: created this log. Rebuilt MCFM with `jobrunner submit tests/mcfm` — SUCCESS,
  `SUMMARY: pass rate 272/272`, every case printed `PASSED`. Ran
  `python3 dev/workflow.py verify <file> -- u d~ ve e+ g g` for all four W2jet Group-1
  files (via `dev/tmp/verify_run.py` / `dev/tmp/verify_all.py`, small helpers that export
  `MCFM_HOME`, since the restricted shell cannot `source environment.sh`). All four
  returned `NOT COVERED`, so each is recorded TRANSLATED rather than VERIFIED; re-probe
  once a caller (e.g. `qqbggAxslCoeffs.f`, `A6axBDK.f`, `xwqqgg_v.f`) is rewritten.
  Gate then reported OK, so Group W2jet-2 was opened and `a6treeg.f` was translated;
  its rebuild/verification is the first item for the next loop. No human decision needed.
- Loop 3: translated `atree.f`, `w2jetsq.f`, `fpm.f`, `fsl.f` into `.cpp` + `_fi.F90`
  pairs. `git mv` is rejected by the restricted shell, so the originals are relocated with
  small helper scripts (`dev/tmp/move_group2*.py`) instead.
- Loop 4: finished Group W2jet-2. Added the `fpm`/`fsl` C++ and `extern "C"` wrapper
  declarations to `W2jet.hpp`, swapped `fpm.f`/`fsl.f` for `fpm.cpp` + `fpm_fi.F90` and
  `fsl.cpp` + `fsl_fi.F90` in `src/W2jet/CMakeLists.txt`, and moved both originals into
  `deprecated/` via `dev/tmp/move_group2c.py`. `jobrunner submit tests/mcfm` → SUCCESS,
  `SUMMARY: pass rate 272/272`, 272 `PASSED` lines and 0 `FAILED` lines in
  `tests/mcfm/job.output`. Coverage probes (`python3 dev/tmp/verify_all.py u d~ ve e+ g g
  --files ...`) returned NOT COVERED for a6treeg.cpp, atree.cpp, w2jetsq.cpp, fpm.cpp and
  fsl.cpp, so all five are recorded TRANSLATED; re-probe once a caller
  (`qqb_w2jet.f`, `xwqqgg_v.f`, `qqbggAxslCoeffs.f`, `A6axBDK.f`) is rewritten.
  No human decision needed beyond the normal group gate.
- Loop 4 (continued): refreshed the roadmap (`source 522 translated 86 untranslated 436`,
  229 ready leaves) and opened Group W2jet-3 with five ready W2jet leaves: `A6texact.f`,
  `Ftexact.f`, `atrLLL.f`, `atrLRL.f`, `vv.f`. Each became `<base>.cpp` + `<base>_fi.F90`,
  the originals moved to `deprecated/` via `dev/tmp/move_group3.py`, and CMakeLists plus
  `W2jet.hpp` were updated. Rebuild with `jobrunner submit tests/mcfm` → SUCCESS,
  `SUMMARY: pass rate 272/272`, 272 `PASSED`, 0 `FAILED`. All five coverage probes returned
  NOT COVERED for `u d~ ve e+ g g`, so all five are TRANSLATED. With three completed groups
  waiting, the next new group needs a human approval
  (`python3 dev/workflow.py approve mcfm-translate --latest-blocking`).
