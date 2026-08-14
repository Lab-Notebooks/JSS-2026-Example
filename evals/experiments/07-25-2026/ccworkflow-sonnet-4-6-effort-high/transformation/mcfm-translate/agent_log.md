# Agent log — mcfm-translate

## Group 1 — src/Mods (module definitions)

- [x] software/mcfm/src/Mods/types_mod.f — TRANSLATED (parameter-only Mods infrastructure; no coverage process per spec)
- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (Mods infrastructure; produces pp_mod.hpp + pp_mod.cpp + Fortran shim; coverage requires caller rewrite per spec)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (Mods infrastructure; produces ppwp2j_mod.hpp + ppwp2j_mod.cpp + Fortran shim with c_f_pointer bounds remapping; original moved to deprecated/; no coverage process for Mods per spec)
- [x] software/mcfm/src/Mods/mod_qcdloop_c.f — TRANSLATED (infrastructure: pure bind(C) interface module; no coverage process for Mods)
- [x] software/mcfm/src/Mods/Modules_Interface.f90 — TRANSLATED (Mods infrastructure; subroutine-style file with bind(C) entries; C++ owns the C symbols modules_fi_init_/modules_fi_finalize_ and delegates to Fortran shim Modules_Interface_fi.F90 for Fortran module pointer associations; no coverage process for Mods per spec)

## Group 2 — src/W2jet (verify: u d~ ve e+ g g)

- [x] software/mcfm/src/W2jet/ggZZcapture.f — TRANSLATED (build pass, not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/atree.f — TRANSLATED (build pass, not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/ZZbox1LL.f — TRANSLATED (build pass, not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/subqcd.f — TRANSLATED (build pass, not covered by u d~ ve e+ g g)
- [x] software/mcfm/src/W2jet/fvf.f — TRANSLATED (build pass, not covered by u d~ ve e+ g g)

## Group 3 — src/W2jet (verify: u d~ ve e+ g g)

- [ ] software/mcfm/src/W2jet/w2jetsq.f
- [ ] software/mcfm/src/W2jet/a6treeg.f
- [ ] software/mcfm/src/W2jet/a6routine.f
- [ ] software/mcfm/src/W2jet/fpm.f
- [ ] software/mcfm/src/W2jet/LRcalc.f

## Session log

### 2026-07-25 — Integrate: Group 1 (src/Mods)

Wired 5 units into software/mcfm/src/Mods/CMakeLists.txt:
- types_mod.f -> types_mod.f90 (free-form shim; no .cpp, parameter-only module)
- pp_mod.f90 kept, added pp_mod.cpp
- ppwp2j_mod.f90 kept, added ppwp2j_mod.cpp
- mod_qcdloop_c.f -> mod_qcdloop_c.f90, added mod_qcdloop_c.cpp
- Modules_Interface.f90 -> Modules_Interface_fi.F90, added Modules_Interface.cpp

Build fix: mod_qcdloop_c.hpp needed `#include <quadmath.h>` (guarded by `__SIZEOF_FLOAT128__`) for quad-precision type declarations (`__float128`/`__complex128`), matching QCDLoop's own types.h approach. The quad-precision function declarations are also guarded.

Correctness bar: `jobrunner submit tests/mcfm` -- 90/90 PASSED, 0 FAILED. Build clean.

All 5 units are in src/Mods (infrastructure per spec coverage map). Status: TRANSLATED for all. No coverage process applies to Mods.

### 2026-07-25 — Integrate: Group 2 (src/W2jet)

Wired 5 units into software/mcfm/src/W2jet/CMakeLists.txt:
- atree.f -> atree.cpp + atree_fi.f90
- fvf.f -> fvf.cpp + fvf_fi.F90
- ggZZcapture.f -> ggZZcapture.cpp + ggZZcapture_fi.F90
- subqcd.f -> subqcd.cpp + subqcd_fi.F90
- ZZbox1LL.f -> ZZbox1LL.cpp + ZZbox1LL_fi.F90

Build fixes applied during integration:
- atree_fi.f90: added `mxpart` to `import` list inside interface block (Fortran scoping)
- fvf.cpp, ZZbox1LL.cpp, subqcd.cpp: changed `#include <own.hpp>` to `#include "own.hpp"` (local header not on system include path)
- subqcd.cpp: refactored multi-line assignment to single-line `amp(-1,+1) = _v;` so coverage probe can scale it
- fvf.cpp: changed `return result; // @coverage-probe` to `result = result; // @coverage-probe` + separate return (tool requires `lhs = rhs;` format)

Correctness bar: `jobrunner submit tests/mcfm` -- 90/90 PASSED, 0 FAILED. Build clean.

Coverage verification (process: u d~ ve e+ g g):
- ggZZcapture.cpp: NOT COVERED -> TRANSLATED
- atree.cpp: NOT COVERED -> TRANSLATED
- ZZbox1LL.cpp: NOT COVERED -> TRANSLATED
- subqcd.cpp: NOT COVERED -> TRANSLATED
- fvf.cpp: NOT COVERED -> TRANSLATED

All 5 units build and pass tests but are not yet exercised by the coverage process. Callers in W2jet are still Fortran; coverage should improve as upstream callers are translated.
