# MCFM Translate Agent Log

## Group 1: Mods — infrastructure modules (mark TRANSLATED per Spec coverage map)

Ready files from `software/mcfm/src/Mods`, all in the same folder. Per the Spec coverage map,
`Mods` is infrastructure: there is no representative process, so no coverage probe applies.
Verification for this group is `jobrunner submit tests/mcfm`; each file is recorded
`TRANSLATED` once the restored build passes.

- [x] software/mcfm/src/Mods/types_mod.f — TRANSLATED (mirrored by types_mod.hpp; Mods is infrastructure, no coverage probe applies)
- [x] software/mcfm/src/Mods/mod_qcdloop_c.f — TRANSLATED (mod_qcdloop_c.f90 + .hpp; Mods is infrastructure, no coverage probe applies)
- [ ] software/mcfm/src/Mods/Modules_Interface.f90
- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (pp_mod.cpp/.hpp + c_f_pointer shim; Mods is infrastructure, no coverage probe applies)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (ppwp2j_mod.cpp/.hpp + c_f_pointer shim; Mods is infrastructure, no coverage probe applies)

## Session log

### 2026-08-13 — Group 1 integrate round

Wiring applied in `software/mcfm/src/Mods/` (authors were forbidden to touch shared build
files, so all of it was done once here):

- `CMakeLists.txt` line 2: `mod_qcdloop_c.f` → `mod_qcdloop_c.f90` (the `.f` moved to
  `Mods/deprecated/` per Plan step 5).
- `CMakeLists.txt`: added `pp_mod.cpp` after `pp_mod.f90` and `ppwp2j_mod.cpp` after
  `ppwp2j_mod.f90`, matching the `.f90` + `.cpp` pairing already used for `ewcharge_mod` /
  `msq_cs_mod`.
- `Modules_Interface.f90`: added `use pp_mod, only: pp_mod_init` / `use ppwp2j_mod, only:
  ppwp2j_mod_init` plus the two `call ..._init()` lines to `modules_fi_init`, and the matching
  `_finalize` pairs to `modules_fi_finalize`. This is load-bearing, not cosmetic: without it the
  `pp` pointer in each shim stays null and `Z2jet/qqb_z2jetx_new.f` / `W2jet/qqb_wp2jetx_new.f`
  dereference null — Spec trap 9, a silent segfault that still builds cleanly.
- `types_mod.f` deliberately kept in `CMakeLists.txt` and **not** moved to `deprecated/`: 166
  live Fortran files under `src/` still `use types` for their `real(dp)`/`complex(dp)`
  declarations. The source is mirrored by `types_mod.hpp`, not obsolete, so the Plan's
  deprecated-move precondition is not met. The `.hpp` needs no CMake entry (that list holds only
  `.f`/`.f90`/`.cpp`).

Correctness bar: `jobrunner submit tests/mcfm` — clean configure, full build and install, then
`Bin/bench`. Result: **SUMMARY: pass rate 272/272**, every case printing an explicit `PASSED`
(0 occurrences of `FAILED`, no missing-output case), so Spec trap 9 is ruled out for this round.
Confirmed all four units are in the built objects:
`types_mod.f.o`, `mod_qcdloop_c.f90.o`, `pp_mod.f90.o` + `pp_mod.cpp.o`,
`ppwp2j_mod.f90.o` + `ppwp2j_mod.cpp.o`.

No coverage probe was run and none was added: per the Spec coverage map `Mods` is infrastructure
with no representative process, so `VERIFIED` is unavailable for these files and `TRANSLATED` is
the correct status. No existing `Mods/*.cpp` carries a `@coverage-probe` either.

Open in this group — `software/mcfm/src/Mods/Modules_Interface.f90` is **not settled** and stays
unchecked. It was attempted this round and returned with no files changed: it is not a module but
two free `bind(C)` subroutines (`modules_fi_init_` / `modules_fi_finalize_`) that exist only so
`src/BLHA/CXX_Interface.cxx` can drive Fortran-side pointer binding, and all ~60 callees are
plain Fortran module procedures with no `bind(C)` (`grep -n "_mod_init.*bind(C" src/Mods/*.f90`
returns nothing). Per the Spec's "If a needed module dependency has no usable C binding yet, stop
and rewrite that dependency first" plus "Never invent a called symbol", translating it would
require either adding `bind(C)` to every sibling `_mod` shim or fabricating gfortran-mangled
names, so it is left for a later round. It is deliberately not marked `FAILED`: nothing was
rewritten and nothing regressed. Human decision needed: whether to reclassify it as terminal
Fortran glue for the cleanup step, since 38 non-`Mods` Fortran files still consume the `Mods`
pointer shims and the binding cannot be retired yet.

Reviewer note carried forward from the author of `mod_qcdloop_c`: the Fortran file was named
`mod_qcdloop_c.f90`, not `mod_qcdloop_c_fi.f90`. The Spec's Output shape says `_fi.f90` for
modules, but it also says to follow existing rewritten modules in `src/Mods`, where every
translated module keeps `<modulename>.f90`. The module name is unchanged either way, so the eight
`use mod_qcdloop_c` sites are unaffected; renaming is a one-line CMake change if a reviewer
prefers `_fi`.

Pre-existing defect noted but not fixed (shared header, another unit's file):
`FArray4D`'s Fortran-pointer constructor in `src/Inc/FArray.hpp` takes only three extents and
self-initializes `nl(nl)` from an indeterminate value. Both new `.cpp` files avoid it by using
the allocating four-extent constructor.
