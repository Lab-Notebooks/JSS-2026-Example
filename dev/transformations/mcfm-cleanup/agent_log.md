# MCFM cleanup agent log

Worklist and per-target status for the cleanup pass described in `current_plan.md` and
`desired_spec.md`. Review groups are headed by lines starting with `Group`. Humans do not edit
this file; approvals are recorded separately in `approvals.toml`.

## Group 1 — ThreeJets

- [x] software/mcfm/src/ThreeJets/A51mmppp5g — DELETED_SHIM (A51mmppp5g_fi.F90 removed, dropped from CMakeLists; .f already in deprecated/; sole live caller A5gfill.cpp uses the wrapper directly)
- [x] software/mcfm/src/ThreeJets/A51mpmpp5g — DELETED_SHIM (A51mpmpp5g_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; unused A51mpmpp5g.hpp also merged away, header_include_count=0)
- [x] software/mcfm/src/ThreeJets/A5NLO4qg — DELETED_SHIM (A5NLO4qg_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; orphaned wrapper stripped; .hpp KEPT_SPLIT as shared interface for two TUs)
- [x] software/mcfm/src/ThreeJets/A5NLOggggg — DELETED_SHIM (A5NLOggggg_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; .hpp KEPT_SPLIT — used by qqb_thrjet_v.cpp)
- [x] software/mcfm/src/ThreeJets/A5NLOqbqggg — KEPT_SHIM (A5NLOqbqggg_fi.F90 retained + still wired; doxygen graph unreliable for this family, conservative fallback; .f moved to deprecated/; .hpp KEPT_SPLIT)
- [x] software/mcfm/src/ThreeJets/A5gfill — KEPT_SHIM (A5gfill_fi.F90 retained + still wired; A5NLOggggg.cpp links raw a5gfill_ symbol via the shim; .f moved to deprecated/; dead A5gfill.hpp merged away)
- [x] software/mcfm/src/ThreeJets/A5qbmgmqpgpgp — DELETED_SHIM (A5qbmgmqpgpgp_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; orphaned wrapper stripped; .hpp KEPT_SPLIT — used by fillamps_qbqggg.cpp)
- [x] software/mcfm/src/ThreeJets/A5qbmgpqpgmgp — DELETED_SHIM (A5qbmgpqpgmgp_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; orphaned wrapper stripped; .hpp KEPT_SPLIT)
- [x] software/mcfm/src/ThreeJets/A5qbmgpqpgpgm — DELETED_SHIM (A5qbmgpqpgpgm_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; .hpp KEPT_SPLIT — used by fillamps_qbqggg.cpp)
- [x] software/mcfm/src/ThreeJets/A5qbmqpgmgpgp — DELETED_SHIM (A5qbmqpgmgpgp_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; .hpp KEPT_SPLIT — used by fillamps_qbqggg.cpp)
- [x] software/mcfm/src/ThreeJets/A5qbmqpgpgmgp — DELETED_SHIM (A5qbmqpgpgmgp_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; orphaned wrapper stripped; .hpp KEPT_SPLIT)
- [x] software/mcfm/src/ThreeJets/A5qbmqpgpgpgm — DELETED_SHIM (A5qbmqpgpgpgm_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; .hpp KEPT_SPLIT — used by fillamps_qbqggg.cpp)
- [x] software/mcfm/src/ThreeJets/fillDij — KEPT_SHIM (fillDij_fi.F90 retained + still wired; doxygen graph incomplete for A5NLO4qg.f caller, conservative fallback; .f moved to deprecated/; .hpp KEPT_SPLIT)
- [x] software/mcfm/src/ThreeJets/fillEij — DELETED_SHIM (fillEij_fi.F90 removed + dropped from CMakeLists; zero referencedby in graph; .f moved to deprecated/; .hpp KEPT_SPLIT — shared with A5NLO4qg.cpp)
- [x] software/mcfm/src/ThreeJets/fillRCij — DELETED_SHIM (fillRCij_fi.F90 removed + dropped from CMakeLists; orphaned wrapper stripped from .cpp; .f already in deprecated/; no .hpp)
- [x] software/mcfm/src/ThreeJets/fillSij — KEPT_SHIM (fillSij_fi.F90 retained + still wired; uncommented call in unarchived A5NLO4qg-era source + doxygen parse failure, conservative fallback; .f already in deprecated/; no .hpp)
- [x] software/mcfm/src/ThreeJets/fillaij0 — DELETED_SHIM (fillaij0_fi.F90 removed + dropped from CMakeLists; orphaned wrapper stripped; only live caller A5NLO4qg.cpp calls C++ fn directly; .f already in deprecated/; no .hpp)
- [x] software/mcfm/src/ThreeJets/fillamps_qbqggg — DELETED_SHIM (fillamps_qbqggg_fi.F90 removed + dropped from CMakeLists; .f moved to deprecated/; .hpp KEPT_SPLIT — shared by A5NLOqbqggg.cpp)
- [x] software/mcfm/src/ThreeJets/helfill — DELETED_SHIM (helfill_fi.F90 removed + dropped from CMakeLists; only Fortran caller A5gfill.f archived; A5gfill.cpp calls helfill_wrapper directly; .f already in deprecated/; no .hpp)
- [x] software/mcfm/src/ThreeJets/qqb_thrjet_v — KEPT_SHIM (qqb_thrjet_v_fi.F90 retained + still wired; BLHA/qqb_thrjet.cxx links qqb_thrjet_v_ symbol; .f moved to deprecated/; qqb_thrjet_v.hpp merged into .cpp — MERGED_CPP)

## Session log

- 2026-07-23 (Loop-1): Ran the full refresh cycle (doxygen → roadmap → cleanup analysis).
  Doxygen wrote 1 440 XML files; parse errors are confined to `gghgg_dep/Inc/` (known, pre-existing noise — none
  in ThreeJets). Roadmap: 391 source files total, 219 translated, 172 untranslated, 15 ready leaves.
  Cleanup candidate totals: 207 move, 281 shim-delete, 125 merge. Gate check: BLOCKED on
  **Group 1 — ThreeJets** (contains DELETED_SHIM + MERGED_CPP); no new group may be opened until
  Group 1 receives human approval via
  `python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest-blocking`.
  Next candidates queued for Group 2 once approved: BDK/ (many FF*/FP*/M* shim-delete + merge),
  Need/ (ckmfill, coupling, cplx, dot, dotem, fixcms, i3m, lfunctions, lnrat, spinoru),
  Mods/ (MOVE_F for Cabibbo_mod, b0_mod, blha_mod, and ~30 others), W2jet/ (A6axBDK, A6texact,
  Acalc, Ftexact, LRcalc, and BDK-related families). Stopping for human review.

- 2026-07-22 (Integrate): Wired all 20 Group 1 units. Removed the 15 deleted `_fi.F90` lines
  from `src/ThreeJets/CMakeLists.txt` (A5NLO4qg, fillaij0, fillEij, fillRCij, fillamps_qbqggg,
  A5NLOggggg, A51mmppp5g, A51mpmpp5g, A5qbmgmqpgpgp, A5qbmgpqpgmgp, A5qbmgpqpgpgm,
  A5qbmqpgmgpgp, A5qbmqpgpgmgp, A5qbmqpgpgpgm, helfill); kept the 5 retained shims wired
  (A5gfill_fi, A5NLOqbqggg_fi, fillDij_fi, fillSij_fi, qqb_thrjet_v_fi). Verified no dangling
  includes of the 3 deleted headers (A51mpmpp5g.hpp, A5gfill.hpp, qqb_thrjet_v.hpp).
  Correctness bar `jobrunner submit tests/mcfm` PASSED (build + benchmark, 3:11). Refreshed the
  doxygen roadmap (`build_roadmap.py --doxygen` then plain) — the only parse error is in an
  unrelated Z2jet/qqb_z2jet_v.f, none of the ThreeJets units. All 20 units non-FAILED; group
  complete. Human still needs to record group approval via approve_group.py (DELETED_SHIM +
  MERGED_CPP present, so the gate blocks the next group until approved).
