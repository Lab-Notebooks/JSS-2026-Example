# mcfm-translate agent log

## Group Mods-pp-tables (loop 4)

Constant lookup-table Mods files. `pp_mod`/`ppwp2j_mod` hold `integer, save ::
pp(...) = reshape(...)` tables that are never mutated at runtime; consistent
with the existing `ppmax_mod`/`mxpart_mod`/`nf_mod`/`maxd_mod`/`mxdim_mod`
convention already in this codebase, the Fortran `.f90` originals were left
in place (no `c_f_pointer` mirroring subroutine needed) and only a `.cpp`/
`.hpp` pair was added for C++ callers. `ppmax_mod` only holds a compile-time
constant and needed no `.cpp` at all.

- [x] Mods/pp_mod.f90 — TRANSLATED (infrastructure Mods file per Spec
      coverage map; `pp_mod.cpp`/`.hpp` wired into
      `software/mcfm/src/Mods/CMakeLists.txt`; build passes, 272/272 tests
      PASSED)
- [x] Mods/ppwp2j_mod.f90 — TRANSLATED (same reasoning as pp_mod; build
      passes, 272/272 tests PASSED)
- [x] Mods/ppmax_mod.f90 — TRANSLATED (already correct on disk; constant-only
      module, no `.cpp` required, matches `mxpart_mod`/`nf_mod`/`maxd_mod`
      convention; no code change needed)

### Coverage probe note (loop 4)

`python3 dev/workflow.py verify <file> -- <process>` requires `MCFM_HOME`
exported via `source environment.sh`; the sandboxed `bash` tool rejects
`source`/pipes/redirects/`$VAR` expansion, so the coverage-probe step of
`verify` could not be invoked directly. Because these files fall under the
Spec's "Mods / Need / Inc / Procdep — infrastructure, mark TRANSLATED" rule,
VERIFIED status is not required for them.

## Group Mods-remaining (loop 5)

The last three un-generated files in `Mods/` (`deps==0, blind==0` in
`dev/tmp/assets/roadmap_metrics.tsv`), all infrastructure per the Spec's
coverage map:

- **`types_mod.f`** — a `module types` holding only kind parameters
  (`sp`, `dp`, `ex`, `qp` from `selected_real_kind`). Added
  `Mods/types_mod.hpp` mirroring the four kind names as C++ type aliases
  (`float`/`double`/`long double`/`long double`) for any C++ translation
  unit that wants to spell the kind by name; the project-wide rewrite rule
  already maps `real(dp)`/`complex(dp)` straight to `double`/
  `std::complex<double>` everywhere else, so no `.cpp` or state exists to
  mirror. `types_mod.f` is left in place unmodified: dozens of still-Fortran
  modules (`use types`) depend on it, so nothing was moved to `deprecated/`.
- **`mod_qcdloop_c.f`** — `module mod_qcdloop_c` contains only an
  `interface` block of `bind(C, name="...")` declarations to the external
  QCDLoop C library (`qli1`..`qli4qc`, `cln`, `qlzero`, `qlnonzero`,
  `qlcachesize`); it has no implementation of its own. Added
  `Mods/mod_qcdloop_c.hpp` restating the same C-interoperable declarations
  as `extern "C"` for C++ callers (`double`/`std::complex<double>` for the
  double-precision entries, `long double`/`std::complex<long double>` for
  the `real128` quad entries, matching the `types_mod.hpp` convention since
  there is no portable C++ quad type). No callee was invented: every
  declared symbol already exists in the external QCDLoop C library that the
  Fortran interface itself binds to. `mod_qcdloop_c.f` is left in place
  unmodified: it is still `use`d by `gghgg_dep/ggHgg.f`, several
  `gghgg_dep/Inc/*.f` includes, `loop/loopI{1,2,4}_generic.f` /
  `loop/deprecated/loopI{2,3}_generic.f`, and `Procdep/chooser.f`.
- **`Modules_Interface.f90`** — two subroutines,
  `modules_fi_init`/`modules_fi_finalize`, each `bind(C, name=...)` so that
  `software/mcfm/src/BLHA/CXX_Interface.cxx` can call them directly
  (`extern "C" { void modules_fi_init_(); void modules_fi_finalize_(); }`).
  The bodies only `call` ~60 other Mods' `<mod>_init`/`<mod>_finalize`
  module procedures (e.g. `b0_mod_init`, `ewcharge_mod_finalize`, ...).
  Checked several of those callees (`b0_mod.f90`, `ewcharge_mod.f90`): the
  `_init`/`_finalize` procedures themselves have no `bind(C, name=...)`
  clause (only the internal data-pointer getters like `b0_mod_b0` do), so
  they have no stable, contractual C-callable symbol name — only their
  Fortran-module-internal (compiler-mangled) linkage exists. Rewriting this
  file's body into C++ would require either (a) inventing new `bind(C)`
  exports across ~60 already-translated `Mods/*.f90` files that do not
  currently have them (out of scope for this file, and a much larger,
  separately-reviewable change), or (b) calling compiler-specific mangled
  Fortran symbol names, which is not a real interoperability contract and
  would violate "never invent a called symbol". `Modules_Interface.f90`
  already *is* the C-interoperability boundary the Spec's Output shape asks
  a translated unit to expose (`bind(C, name="modules_fi_init_")` etc.,
  already called directly from C++ in `CXX_Interface.cxx`), so it is left
  unmodified this session.

Ran `jobrunner submit tests/mcfm` after adding the two new headers (no
existing file's behavior changed): build succeeded and
`tests/mcfm/job.output` shows `SUMMARY: pass rate 272/272` with every one of
the 272 individual test cases showing `PASSED` in the output (`grep -c
PASSED` → 272, `grep -c FAILED` → 0) — no silent-segfault symptom.

- [x] Mods/types_mod.f — TRANSLATED (infrastructure Mods file per Spec
      coverage map; kind-parameter-only module, `types_mod.hpp` mirror
      added, no `.cpp`/CMakeLists change needed; build passes, 272/272
      tests PASSED)
- [x] Mods/mod_qcdloop_c.f — TRANSLATED (infrastructure Mods file per Spec
      coverage map; interface-only module with no implementation,
      `mod_qcdloop_c.hpp` mirror added restating the same external QCDLoop
      C symbols as `extern "C"`, no invented callee; build passes, 272/272
      tests PASSED)
- [x] Mods/Modules_Interface.f90 — TRANSLATED (infrastructure Mods file per
      Spec coverage map; already the `bind(C)` boundary called directly
      from `BLHA/CXX_Interface.cxx`; its body only calls ~60 other Mods'
      `_init`/`_finalize` procedures that have no `bind(C)` name of their
      own, so translating the body would require inventing new
      cross-file C bindings — left unmodified this session; build passes,
      272/272 tests PASSED)

### Gate

`python3 dev/workflow.py gate mcfm-translate` reported "no review groups
found" before this session because the loop-4 work had never been recorded
under a `## Group` heading (the parser in
`dev/tools/common/approval_log.py` only counts lines starting with
`## Group`/`### Group`/`#### Group`). Retroactively added the
`## Group Mods-pp-tables (loop 4)` heading above so that group is now
visible to the gate/approval tooling, in addition to opening
`## Group Mods-remaining (loop 5)` for this session's work. Both groups are
now complete (all items `[x]`), for 2 of the up-to-3 completed groups
allowed before human approval is required.

### Remaining work (next loop)

`python3 dev/workflow.py refresh` (this session) still reports **227 ready
leaves** — all of `Mods/`'s ready files are now settled, so future ready
files come from top-level process folders (`W`, `W1jet`, `W2jet`, `Z`,
`Z1jet`, `Z2jet`, `ThreeJets`, `ggH`, `BDK`, `loop`, etc.).

- Two completed groups are open for approval accounting purposes now (see
  Gate note above); a 3rd group may still be opened before approval is
  required, per `BATCH_LIMITS["mcfm-translate"] == 3` in
  `dev/tools/approve/check_gate.py`.
- Pick a ~5-file group from one top-level ready folder (e.g. `W2jet`) per
  the Resolution rules and translate/verify following the Output shape and
  Rewrite rules in `desired_spec.md`. These are real computational routines
  (not header-only infra), so each needs an actual line-by-line C++
  rewrite, wiring into that folder's `CMakeLists.txt`, moving the original
  `.f`/`.F` to `deprecated/`, and a coverage-probe run.
- `python3 dev/workflow.py verify <file.cpp> -- <process>` needs
  `MCFM_HOME` exported (normally via `source environment.sh`); the
  sandboxed `bash` tool here rejects `source`/pipes/redirects/`$VAR`
  expansion, so this still could not be exercised directly in this
  session either (only the Mods/infrastructure files were in scope, which
  the Spec allows to settle as `TRANSLATED` without a coverage probe).
  Confirm with the runner/tooling owner whether a non-interactive
  environment-setup path exists so VERIFIED status can be produced for
  non-infrastructure files.
- Continue running `python3 dev/workflow.py refresh` before picking new
  work, and check `python3 dev/workflow.py gate mcfm-translate` before
  opening more than 3 completed groups (currently at 2).
