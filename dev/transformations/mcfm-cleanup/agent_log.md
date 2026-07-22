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

## Group 2 — Need/

- [x] software/mcfm/src/Need/ckmfill_fi.F90 — DELETED_SHIM (no active Fortran caller; only reference was chooser.f which is not compiled — Procdep uses chooser_fi.F90+chooser.cpp; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/coupling_fi.F90 — DELETED_SHIM (sole caller chooser.f not compiled; chooser_fi.F90 wraps chooser_wrapper() directly and does not call coupling; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/cplx_fi.F90 — KEPT_SHIM (cplx2() function-called by compiled W2jet/qqb_w2jet_v.f; initial deletion caused linker error `cplx2_`; shim recreated with cplx1_wrapper+cplx2_wrapper bindings and re-wired in CMakeLists; build passes)
- [x] software/mcfm/src/Need/dot_fi.F90 — KEPT_SHIM (dotvec() function-called by compiled gghgg_dep/gg_hgg_mass.f and gg_hgg_mass_tb.f; initial deletion caused linker error `dotvec_`; shim recreated with dot/dotvec/massvec/dotpr wrappers and re-wired in CMakeLists; build passes)
- [x] software/mcfm/src/Need/dotem_fi.F90 — DELETED_SHIM (only caller deprecated/qqb_w_g.f is in deprecated/ and not compiled; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/fixcms_fi.F90 — DELETED_SHIM (sole caller chooser.f not compiled; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/i3m_fi.F90 — DELETED_SHIM (no Fortran callers in any compiled file; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/lfunctions_fi.F90 — DELETED_SHIM (no Fortran callers in any compiled file; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/lnrat_fi.F90 — DELETED_SHIM (no Fortran callers in any compiled file; removed from CMakeLists; build passes)
- [x] software/mcfm/src/Need/spinoru_fi.F90 — KEPT_SHIM (active callers in compiled W2jet/qqb_w2jet_v.f, W2jet/qqb_wp2jetx_new.f, gghgg_dep/gg_hgg_mass.f, gg_hgg_mass_tb.f; retained in CMakeLists throughout; build passes)

## Session log

- 2026-07-25 (Loop-5): Ran full refresh cycle (doxygen 1440 XML, same known parse errors in gghgg_dep/Inc/ — none new; roadmap 391 source / 219 translated / 172 untranslated, 274 shim-delete / 207 move / 125 merge candidates). Gate check: BLOCKED — Group 2 — Need/ is completed with DELETED_SHIM items and has no entry in approvals.toml. No currently open group exists; cannot open Group 3 (BDK/ shim-delete targets) until human approves Group 2. Graceful exit condition met. Human action required: run `python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest-blocking` to approve Group 2 and unblock the gate. After approval, next work is Group 3 targeting BDK/ shim-delete candidates and Mods/ MOVE_F targets per pending steps below.

- 2026-07-24 (Loop-4): Ran full refresh cycle (doxygen 1440 XML, same known parse errors confined to gghgg_dep/Inc/ — none new; roadmap 391/219/172, 274 shim-delete / 207 move / 125 merge candidates). Gate check result: BLOCKED on **Group 2 — Need/** (DELETED_SHIM present, no approval in approvals.toml yet). No currently open group exists — Group 2 is completed and blocking. Cannot open Group 3 until human approves Group 2 via: `python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest-blocking`. Graceful exit condition met (completed group blocks next group). Queued for Group 3 after approval: BDK/ shim-delete targets (FFMPcc, FFMPsc, FFPMcc, FFPMccT, FFPMccTtilde, FFPMsc, FFPMscT, FFPMscTtilde, FFPPcc, FFPPsc, FMPFcc, FMPFsc, FPFMcc, FPFMccTtilde, FPFMsc, FPFMscT, FPFPcc, FPFPsc, FPMFcc, FPMFsc + M1bit1 through M3bit4, Master1-3a, fvs); Mods/ MOVE_F targets (~35 entries: Cabibbo_mod, b0_mod, blha_mod, breit_mod, ckm1_mod, ckm_mod, couple_mod, docheck_mod, epinv2_mod, epinv_mod, ewcharge_mod, ewcouple_mod, ewinput_mod, facscale_mod, first_mod, flags_mod, ggZZ_mod, ggZZcomputemp_mod, ggZZintegrals_mod, hdecaymode_mod, interference_mod, kpart_mod, kprocess_mod, lc_mod, limits_mod, masses_mod, mmsq_cs_mod, mpicommon_mod, mqq_mod, msq_cs_mod, msq_struc_mod, nflav_mod, nlooprun_mod, nodecay_mod, noglue_mod, nplot_mod, nproc_mod, nqcdjets_mod, nwz_mod, part_mod, plabel_mod, pp_mod, ppwp2j_mod, process_mod, qcdcouple_mod, removebr_mod, scalarselect_mod, scale_mod, scheme_mod, sprods_com_mod, sprods_decl_mod, toploops_mod, verbose_mod, virt5ax_mod, yukawas_mod, zcouple_cms_mod, zcouple_mod, zerowidth_mod, zprods_com_mod, zprods_decl_mod); W2jet/ MOVE_F+DELETE_SHIM targets (A6axBDK, A6texact, Acalc, BDKqqbggAxAmp, Ftexact, LRcalc, Ltfunctions, Tri3masscoeff, ZZC012x34LLmp, ZZC01x2LLmp, ZZC01x34LLmp). Note for Group 3: use broad symbol-text search (not only `call <sym>`) to catch function-pointer and direct-call Fortran callers — avoids repeating the cplx2_/dotvec_ linker error from Group 2.
- 2026-07-23 (Loop-3): Ran full refresh cycle (doxygen 1440 XML, no new parse errors; roadmap 391/219/172, 274 shim-delete candidates after Group 2 work). Gate was OPEN (Group 1 approved). Opened **Group 2 — Need/**. Investigated all 10 Need/ shims (ckmfill, coupling, cplx, dot, dotem, fixcms, i3m, lfunctions, lnrat, spinoru). Deleted 7 shims (ckmfill, coupling, dotem, fixcms, i3m, lfunctions, lnrat) — all had no active Fortran callers in compiled code (callers were either in deprecated/ or in chooser.f which is replaced by chooser_fi.F90+chooser.cpp). Kept 3 shims: spinoru_fi.F90 (active callers in W2jet and gghgg_dep); cplx_fi.F90 (cplx2() function-called by W2jet/qqb_w2jet_v.f — initial erroneous deletion caused linker error, restored); dot_fi.F90 (dotvec() function-called by gghgg_dep/gg_hgg_mass.f + gg_hgg_mass_tb.f — initial erroneous deletion caused linker error, restored). CMakeLists.txt updated: removed 7 shim entries, kept cplx_fi.F90, dot_fi.F90, spinoru_fi.F90. `jobrunner submit tests/mcfm` PASSED (3:10). Refreshed doxygen roadmap (consistent, same 1440 XML files). Gate now BLOCKED on Group 2 — Need/ (DELETED_SHIM). Human must approve before Group 3 can start via: `python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest-blocking`. Next candidates for Group 3 (after approval): BDK/ FF*/FP*/M* families (shim-delete + merge), Mods/ MOVE_F targets.
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
