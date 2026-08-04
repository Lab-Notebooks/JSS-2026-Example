# mcfm-translate agent log

## Group 1 — Mods infrastructure (types_mod, mod_qcdloop_c, pp_mod, ppwp2j_mod, Modules_Interface)

**Status: OPEN**

Files in this group (all `Mods/` infrastructure — spec says mark TRANSLATED):

- [ ] software/mcfm/src/Mods/types_mod.f
- [ ] software/mcfm/src/Mods/mod_qcdloop_c.f
- [ ] software/mcfm/src/Mods/pp_mod.f90
- [ ] software/mcfm/src/Mods/ppwp2j_mod.f90
- [ ] software/mcfm/src/Mods/Modules_Interface.f90

### Translation approach

- `types_mod.f`: constants-only module (`sp`, `dp`, `ex`, `qp` KIND params). C++ header with `constexpr` values; shim keeps original `selected_real_kind` calls; no `c_f_pointer` needed.
- `mod_qcdloop_c.f`: Fortran interface to qcdloop C library. C++ marker header only; Fortran module kept for Fortran code.
- `pp_mod.f90` / `ppwp2j_mod.f90`: large static lookup table. Data kept in Fortran shim; C++ stub marks as settled; shim adds empty `init`/`finalize` subroutines.
- `Modules_Interface.f90`: standalone `bind(C)` subroutines calling all module init/finalize. Renamed to `Modules_Interface_fi.F90`; minimal C++ stub added.

---

## Session log

### 2025-01-10 — Session 1

Started first group. No previous log existed. Gate clear (no groups yet). Picked all 5 ready `Mods/` infrastructure files as Group 1.

Action taken: wrote .hpp, .cpp, shims, Modules_Interface_fi.F90; updated CMakeLists.txt; submitted build.
