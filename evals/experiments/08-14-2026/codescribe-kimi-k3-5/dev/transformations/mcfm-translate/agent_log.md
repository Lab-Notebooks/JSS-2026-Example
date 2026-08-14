# MCFM Fortran → C++ translation log

Worklist, review groups, and per-file statuses for the mcfm-translate pass.

## Ready files

See `dev/tmp/assets/roadmap_metrics.tsv` (regenerate with `python3 dev/workflow.py refresh`).
Ready = `deps == 0`, `blind == 0`, no generated `.cpp` yet.

## Group 1 — pp / ppmax / tri-coefficient infrastructure (Mods + Inc + W2jet/Z2jet consumers)

Scope: the `pp_mod` / `ppwp2j_mod` Fortran modules (large precomputed `pp` tables) and the
`ppmax.f` / `tri123x4x56coeffs.f` include files they depended on, plus the W2jet/Z2jet
consumers that referenced the old include path.

Per-file dispositions:

- [x] software/mcfm/src/Mods/pp_mod.f90 — TRANSLATED (infrastructure: Mods coverage probe NOT COVERED per Spec coverage map; translated to Mods/pp_mod.cpp + Mods/pp_mod.hpp with c_f_pointer mirroring in the .f90 shim; build passes)
- [x] software/mcfm/src/Mods/ppwp2j_mod.f90 — TRANSLATED (infrastructure: Mods coverage probe NOT COVERED per Spec coverage map; translated to Mods/ppwp2j_mod.cpp + Mods/ppwp2j_mod.hpp with c_f_pointer mirroring in the .f90 shim; build passes)
- [x] software/mcfm/src/Inc/ppmax.f — TRANSLATED (include file retired: parameter replaced by `ppmax_mod`=80 already used by all live consumers; original removed from Inc/, remaining references are only in already-deprecated sources under Inc/deprecated/ and Mods/deprecated/; build passes)
- [x] software/mcfm/src/Inc/tri123x4x56coeffs.f — TRANSLATED (include file retired: coeff2 assignments inlined directly into software/mcfm/src/W2jet/qqbggAxtri123x4x56.f; original moved to software/mcfm/src/Inc/deprecated/tri123x4x56coeffs.f; build passes)

Consumer edits (no standalone status; part of Group 1 wiring):

- software/mcfm/src/W2jet/qqb_wp2jetx_new.f — switched to `ppmax_mod`/`ppwp2j_mod` interface; build passes
- software/mcfm/src/Z2jet/qqb_z2jetx_new.f — switched to `ppmax_mod` interface; build passes
- software/mcfm/src/W2jet/qqbggAxtri123x4x56.f — `tri123x4x56coeffs.f` include inlined; build passes
- software/mcfm/src/Mods/CMakeLists.txt, software/mcfm/src/Mods/Modules_Interface.f90 — wired in the new .cpp/.hpp units and shims

Group verification evidence:

- `jobrunner submit tests/mcfm`: SUCCESS, `SUMMARY: pass rate 270/272`
- `python3 dev/workflow.py verify software/mcfm/src/Mods/pp_mod.cpp -- none` → `RESULT: NOT COVERED` → TRANSLATED
- `python3 dev/workflow.py verify software/mcfm/src/Mods/ppwp2j_mod.cpp -- none` → `RESULT: NOT COVERED` → TRANSLATED

Pre-existing test failures (attribution checked, NOT caused by Group 1):

- `d d~ h g g` (hjj, SM) and `d~ d h g g` (hjj, SM) show FAILED in tests/mcfm/job.output.
  Reproduced on the clean baseline tree (all Group 1 changes stashed): same two cases FAILED,
  same 270/272 pass rate. Conclusion: pre-existing failures in the hjj `qq? hgg` channel,
  unrelated to this group's files (no Group 1 file is on the hjj path). Logged here as known
  failures; to be investigated outside Group 1.

## Session log

### 2025 session — Group 1 (loops 1–4)

- Translated `pp_mod` and `ppwp2j_mod` (9x9x9x9 integer permutation tables) from Fortran
  modules to C++ (`pp_mod.cpp/.hpp`, `ppwp2j_mod.cpp/.hpp`) with Fortran shims that mirror
  the `pp` array via `c_f_pointer`, following the existing Mods pattern.
- Retired the `Inc/ppmax.f` include: live code already uses `ppmax_mod` (parameter ppmax=80);
  only deprecated sources still `include 'ppmax.f'`. File removed from `Inc/`.
- Retired `Inc/tri123x4x56coeffs.f`: its `coeff2(...)` assignments were inlined into
  `W2jet/qqbggAxtri123x4x56.f`; original preserved under `Inc/deprecated/`.
- Wired everything into `Mods/CMakeLists.txt` and `Mods/Modules_Interface.f90`; full build
  passes.
- Coverage probes on both new .cpp files came back NOT COVERED (infrastructure; matches the
  Spec's coverage-map row for Mods/Inc) → both marked TRANSLATED.
- Full test suite: 270/272 pass. The two failures (`d d~ h g g`, `d~ d h g g`) are
  pre-existing — verified by rerunning the suite with all Group 1 changes stashed
  (identical 270/272 with the same two FAILED lines), then restoring the changes.
- Group 1 contains no group-attributable FAILED files; ready for gate check / approval.
