# Agent Log — Fortran → C++ Translation

## Group 1: BDK leaf functions (M3bit2, M3bit4, M2bit1, M2bit2, M2bit3)

- [x] software/mcfm/src/BDK/M3bit2.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M3bit4.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M2bit1.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M2bit2.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M2bit3.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)

Build: 272/272 tests PASSED. All originals moved to `deprecated/`.

## Group 2: BDK leaf functions (M3bit3, M3bit1, M3abit1, M3abit2, M1bit1)

- [x] software/mcfm/src/BDK/M3bit3.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M3bit1.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M3abit1.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M3abit2.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)
- [x] software/mcfm/src/BDK/M1bit1.cpp — TRANSLATED (not covered by `u u~ e- e+ g g`; callers still Fortran)

Build: 272/272 tests PASSED. All originals moved to `deprecated/`.

## Session log

### Session 1 (Loop 1)

Translated 5 BDK leaf files (M3bit2, M3bit4, M2bit1, M2bit2, M2bit3) from Fortran to C++.
Created BDK.hpp header, Fortran shims (*_fi.F90), wired into CMakeLists.txt.
Original .f files moved to deprecated/. Added src/BDK to target_include_directories in
software/mcfm/CMakeLists.txt line 97.

### Session 2 (Loop 2)

- Build confirmed: `jobrunner submit tests/mcfm` → 272/272 PASSED.
- Ran coverage verification for all 5 files with process `u u~ e- e+ g g`.
- All 5 returned NOT COVERED — these are leaf-level BDK functions whose callers
  (Master2, Master3, etc.) are still Fortran. They will become VERIFIED-eligible
  once their caller chain is rewritten.
- Marked all 5 as TRANSLATED. Group 1 is complete.

### Session 3 (Loop 5)

- Gate checked: OK (1 completed group waiting, limit 3).
- Selected next 5 ready BDK leaf files: M3bit3, M3bit1, M3abit1, M3abit2, M1bit1.
- Translated all 5 to C++ (.cpp + _fi.F90), updated BDK.hpp and CMakeLists.txt.
- Moved originals to deprecated/.
- Build: `jobrunner submit tests/mcfm` → 272/272 PASSED.
- Coverage verification: all 5 NOT COVERED (callers Master1, Master3, Master3a still Fortran).
- Marked all 5 as TRANSLATED. Group 2 is complete.
