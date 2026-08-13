# Agent log — mcfm-translate

## Group 1 — src/Mods

- [x] software/mcfm/src/Mods/types_mod.f — TRANSLATED (infrastructure parameter module, Mods dir; header-only, no coverage process)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (infrastructure data module; produces ppwp2j_mod.hpp + ppwp2j_mod.cpp; original ppwp2j_mod.f90 kept for Fortran callers; Mods infrastructure, no coverage process)
- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (infrastructure data module; produces pp_mod.hpp + pp_mod.cpp + pp_mod.f90 shim; original already in deprecated/; 4D integer array pp(-4:4,-4:4,-4:4,-4:4) initialized from reshape literal; Mods infrastructure, no coverage process)
- [x] software/mcfm/src/Mods/Modules_Interface.f90 — TRANSLATED (infrastructure bootstrap subroutines; callee module procedures lack bind(C) so Fortran shim Modules_Interface_fi.F90 remains the implementation; produces Modules_Interface.hpp + Modules_Interface.cpp + Modules_Interface_fi.F90; original moved to deprecated/; Mods infrastructure, no coverage process)
- [x] software/mcfm/src/Mods/mod_qcdloop_c.f — TRANSLATED (interface-only module; no module variables; produces mod_qcdloop_c.hpp + mod_qcdloop_c.cpp + mod_qcdloop_c.f90 shim; original moved to deprecated/; Mods infrastructure, no coverage process)

### Session log — 2026-07-24 — Integrate Group 1

Wired all 5 units into CMakeLists.txt:
- types_mod.f: kept in build (Fortran callers still `use types`); types_mod.hpp added alongside
- ppwp2j_mod.f90: kept original for Fortran callers, added ppwp2j_mod.cpp
- pp_mod.f90: now the Fortran shim (c_f_pointer bridge to C++ data), added pp_mod.cpp
- Modules_Interface.f90: replaced with Modules_Interface_fi.F90 + Modules_Interface.cpp
- mod_qcdloop_c.f: replaced with mod_qcdloop_c.f90 + mod_qcdloop_c.cpp

Integration fixes applied during wiring:
- pp_mod.f90: fixed rank-remapping error (pointer must have deferred shape; use rank-1 flat intermediate for bounds remapping per Fortran standard)
- mod_qcdloop_c.hpp: removed quad-precision variants from C++ header (no portable extern "C" representation for __complex128; Fortran callers use the .f90 shim)
- Modules_Interface_fi.F90: added pp_mod_init/pp_mod_finalize calls (per author note)

Build + tests: jobrunner submit tests/mcfm — SUCCESS, 272/272 passed.
All 5 units marked TRANSLATED (Mods infrastructure, no coverage process per Spec).

## Group 2 — src/W2jet

- [ ] software/mcfm/src/W2jet/ggZZcapture.f (verify: u d~ ve e+ g g)
- [ ] software/mcfm/src/W2jet/atree.f (verify: u d~ ve e+ g g)
- [ ] software/mcfm/src/W2jet/ZZbox1LL.f (verify: u d~ ve e+ g g)
- [ ] software/mcfm/src/W2jet/subqcd.f (verify: u d~ ve e+ g g)
- [ ] software/mcfm/src/W2jet/fvf.f (verify: u d~ ve e+ g g)
