# mcfm-translate agent log

## Group 1 — Mods infrastructure (5 files)

- [x] software/mcfm/src/Mods/types_mod.f — TRANSLATED (infrastructure; parameter-only module, created types_mod.hpp)
- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (infrastructure; created pp_mod.hpp + pp_mod.cpp with 4D array data)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (infrastructure; created ppwp2j_mod.hpp + ppwp2j_mod.cpp with 4D array data)
- [x] software/mcfm/src/Mods/mod_qcdloop_c.f — TRANSLATED (infrastructure; created mod_qcdloop_c.hpp with extern "C" declarations for QCDLoop)
- [x] software/mcfm/src/Mods/Modules_Interface.f90 — TRANSLATED (infrastructure; created Modules_Interface.hpp declaring bind(C) init/finalize)

**Build**: PASS — 272/272 tests passed  
**Status**: Group completed. All files are Mods infrastructure → marked TRANSLATED per coverage map.

---

## Group 2 — W2jet leaf functions (5 files)

- [x] software/mcfm/src/W2jet/atree.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/a6treeg.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/subqcd.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/fvf.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/ZZbox1LL.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)

**Build**: PASS — 272/272 tests passed  
**Status**: Group completed. Full translation pattern applied: .cpp + .hpp (W2jet.hpp) + _fi.F90 for each file; originals moved to deprecated/. Coverage verification blocked (MCFM_HOME env var not set; verify tool exits with code 2).

---

## Group 3 — W2jet mid-level functions (5 files)

- [x] software/mcfm/src/W2jet/ggZZcapture.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/a6routine.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/w2jetsq.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/fpp.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)
- [x] software/mcfm/src/W2jet/fpm.f — TRANSLATED (build pass; verify tool exit_code 2 — MCFM_HOME not set in shell)

**Build**: PASS — 272/272 tests passed  
**Status**: Group completed. Translation pattern: .cpp + W2jet.hpp declarations + _fi.F90 shims; originals moved to deprecated/. Key dependencies:
- ggZZcapture: string label handling via const char* + len; writes to ggZZ_mod::res array
- a6routine: calls atree (C++/W2jet.hpp), Lnrat (C++/Need.hpp), A6texact (Fortran extern "C" a6texact_)
- w2jetsq: calls subqcd (C++/W2jet.hpp); FArray2D qcd arrays with -1:1 indexing
- fpp: calls L0, L1, Lsm1, Lsm1_2mht (C++/Need.hpp), t (C++/W1jet.hpp)
- fpm: calls L0, L1, Lnrat, Lsm1, Lsm1_2mh, i3m (C++/Need.hpp), t (C++/W1jet.hpp)

Coverage verification blocked (MCFM_HOME env var not set; verify tool exits with code 2).

---

## Session log

### 2025-01-27 — Session 1

**What changed:**
- Created C++ headers (.hpp) for all 5 ready Mods files.
- Created C++ sources (.cpp) for pp_mod and ppwp2j_mod (large 4D integer lookup tables with 6561 values each).
- Wired pp_mod.cpp and ppwp2j_mod.cpp into Mods/CMakeLists.txt.
- Kept Fortran source files in place (modules still needed by Fortran consumers; no c_f_pointer rewrite needed for parameter-only/interface-only/bridge modules).
- Build passes 272/272 tests.

**Roadmap after refresh:** source 531, translated 91 (+5), untranslated 440, ready leaves 226.

**What remains:**
- 440 untranslated files, 226 ready leaves.
- Next high-fan-in ready files include BDK/ and W2jet/ subroutines.
- Gate check needed before opening Group 2.

### 2025-01-27 — Session 2

**What changed:**
- Gate check passed (1 completed group waiting, limit 3).
- Selected 5 high-fan-in ready W2jet files for Group 2: atree (fanin=6), a6treeg (fanin=2), subqcd (fanin=2), fvf (fanin=2), ZZbox1LL (fanin=2).
- Created W2jet.hpp directory header with C++ declarations + extern "C" wrappers.
- Translated each file: .cpp (C++ code + wrapper) + _fi.F90 (Fortran shim).
- Key translation decisions:
  - atree: character(len=2) st → integer (1=pp, 2=pm, 3=sl) in C++; _fi.F90 converts.
  - a6treeg, fvf: integer st uses heldefs_mod constants directly.
  - subqcd: amp(-1:1,-1:1) mapped to FArray2D with start_i=-1, start_j=-1.
  - ZZbox1LL: two subroutines in one file; ZZbox1LLcore only called from ZZbox1LL so no separate _fi needed. FArray4D used for Xrat(2,2,2,2).
  - Fixed FArray4D pointer constructor bug (missing `nl` parameter in FArray.hpp).
- Added src/W2jet to include_directories in top-level CMakeLists.txt (3 targets).
- Moved originals to W2jet/deprecated/.
- Updated W2jet/CMakeLists.txt: swapped .f entries for .cpp + _fi.F90.
- Build passes 272/272 tests.
- Coverage verification blocked: `python3 dev/workflow.py verify` requires MCFM_HOME env var which is not set in restricted shell (exit_code 2).

**What remains:**
- Run `python3 dev/workflow.py verify <file.cpp> -- u d~ ve e+ g g` on the 5 W2jet files once MCFM_HOME is available, to upgrade from TRANSLATED to VERIFIED.
- ~430 untranslated files remain; next candidates include more W2jet leaves, BDK/, Z2jet/, ThreeJets/.
- Gate check before Group 4 (3 completed groups waiting, limit 3 → approval required).

### 2025-01-27 — Session 3

**What changed:**
- Corrected Group 2 log entries: removed false claim about "MCFM_HOME being unavailable"; the actual issue is that MCFM_HOME env var is not set in the restricted bash shell (verify tool exits with code 2).
- Gate check passed (2 completed groups waiting, limit 3).
- Selected 5 W2jet ready files for Group 3: ggZZcapture (fanin=6), a6routine (fanin=2), w2jetsq (fanin=2), fpp (fanin=1), fpm (fanin=1).
- Translated each file: .cpp + W2jet.hpp declarations + _fi.F90 shims; originals moved to deprecated/.
- Key translation decisions:
  - ggZZcapture: character*(*) label → const char* + int label_len; string comparisons use std::string; ichar() → char arithmetic.
  - a6routine: st encoded as int (matching atree convention); calls atree (C++), Lnrat (C++ via Need.hpp), A6texact (still Fortran, called via extern "C" a6texact_).
  - w2jetsq: calls subqcd (C++) twice; qcd arrays with -1:1 FArray2D indexing.
  - fpp/fpm: long spinor algebra expressions; calls L0, L1, Lsm1, Lsm1_2mht/Lsm1_2mh, lnrat, i3m, t via Need.hpp/W1jet.hpp. All integer literals in complex arithmetic converted to doubles.
- Build passes 272/272 tests.
- Coverage verification still blocked (MCFM_HOME not set).

**Roadmap after refresh:** source 521, translated 91, untranslated 430, ready leaves 230.

**What remains:**
- 430 untranslated files, 230 ready leaves.
- Gate: 3 completed groups waiting = limit. **Approval required before opening Group 4.**
- Once MCFM_HOME becomes available, run verify on all 10 W2jet .cpp files to upgrade from TRANSLATED to VERIFIED.
- Next candidates: more W2jet leaves (Ftexact, vvg, LRcalc, fax, faxsl, Ltfunctions, ZZbox2LL, ZZtri1_2LL, qqbZggtree), BDK/ leaves, Z2jet/ leaves, ThreeJets/ leaves.
