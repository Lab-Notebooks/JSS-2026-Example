# mcfm-translate agent log

## Group 1 — Mods infrastructure (types_mod, mod_qcdloop_c, pp_mod, ppwp2j_mod, Modules_Interface)

**Status: COMPLETE**

Files in this group (all `Mods/` infrastructure — spec says mark TRANSLATED):

- [x] software/mcfm/src/Mods/types_mod.f — TRANSLATED (constants-only module; .hpp with constexpr params; .cpp stub; original .f kept for Fortran callers; deprecated/ copy exists)
- [x] software/mcfm/src/Mods/mod_qcdloop_c.f — TRANSLATED (qcdloop Fortran interface; .hpp marker + .cpp stub; original .f kept for Fortran callers; deprecated/ copy written)
- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (data-only table module; .hpp + .cpp marker stubs; .f90 shim updated with contains pp_mod_init/finalize)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (W+2jet data-table module; .hpp + .cpp marker stubs; .f90 shim updated with contains ppwp2j_mod_init/finalize)
- [x] software/mcfm/src/Mods/Modules_Interface.f90 — TRANSLATED (bind(C) init/finalize shim; renamed to Modules_Interface_fi.F90; .hpp + .cpp stubs added; CMakeLists updated)

Build: `jobrunner submit tests/mcfm` — **SUCCESS** (1m 29s)

---

## Group 2 — W2jet atree/subqcd

**Status: COMPLETE**

Files in this group (W2jet helicity amplitude utilities — spec process `u d~ ve e+ g g`):

- [x] software/mcfm/src/W2jet/atree.cpp — TRANSLATED (build pass, NOT COVERED by `u d~ ve e+ g g`; deprecated/atree.f kept; original deleted from src)
- [x] software/mcfm/src/W2jet/subqcd.cpp — TRANSLATED (build pass, NOT COVERED by `u d~ ve e+ g g`; deprecated/subqcd.f kept; original deleted from src)

---

## Session log

### 2025-01-10 — Session 1

Started first group. No previous log existed. Gate clear (no groups yet). Picked all 5 ready `Mods/` infrastructure files as Group 1.

Action taken: wrote .hpp, .cpp, shims, Modules_Interface_fi.F90; updated CMakeLists.txt; submitted build.

### Session 2 (Loop 1 continuation)

Resumed Group 1 (OPEN from Session 1). Found that `types_mod.cpp/hpp` and `mod_qcdloop_c.cpp/hpp` existed from Session 1 but were not wired into CMakeLists.txt. `pp_mod`, `ppwp2j_mod`, and `Modules_Interface` had no C++ output yet.

Actions taken this session:
- Created `pp_mod.hpp`, `pp_mod.cpp` (marker stubs for data-only module)
- Added `contains pp_mod_init/finalize` to `pp_mod.f90`
- Created `ppwp2j_mod.hpp`, `ppwp2j_mod.cpp` (marker stubs for data-only module)
- Added `contains ppwp2j_mod_init/finalize` to `ppwp2j_mod.f90`
- Created `Modules_Interface.hpp`, `Modules_Interface.cpp` (C++ stubs)
- Created `Modules_Interface_fi.F90` (shim — identical to original `Modules_Interface.f90`)
- Copied `mod_qcdloop_c.f` to `deprecated/mod_qcdloop_c.f`
- Updated `Mods/CMakeLists.txt`:
  - Added `mod_qcdloop_c.cpp`, `types_mod.cpp` after their `.f` entries
  - Added `pp_mod.cpp`, `ppwp2j_mod.cpp` after their `.f90` entries
  - Replaced `Modules_Interface.f90` with `Modules_Interface_fi.F90` + `Modules_Interface.cpp`
- Build: `jobrunner submit tests/mcfm` → **SUCCESS**
- All 5 files marked TRANSLATED (Mods infrastructure — spec coverage map).
- Group 1 closed.
