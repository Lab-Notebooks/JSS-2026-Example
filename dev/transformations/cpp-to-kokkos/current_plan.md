# C++ → Kokkos kernel worklist

Amplitudes to port to Pepper kernels. Tick tasks off and record short notes and
per-amplitude outcomes directly in this file; it is the running record shared across
sessions. Port in **dependency order** (a Born before its virtual) so each earlier
kernel's frozen fragments are available for reuse.

Legend: `- [ ]` not yet ported; `- [x]` kernel authored. A kernel is **verified** only
after its doctests pass (`desired_spec.md` §4).

## Running the work

1. **Check reuse and stage-1 readiness first**:
   `python3 dev/tools/closure/calltree_closure.py <name>` lists the call-tree closure from
   the linked objects. A plain-Fortran object in the closure is a stage-1 gap; finish that
   in `dev/transformations/fortran-to-cpp/` before porting.
2. **Port** with the `port` workflow: `args:{projectRoot, transformation:"cpp-to-kokkos",
   target:"<name>"}` for one (or `targets:[...]` in dependency order), or omit the target
   and pass `from:"fortran-to-cpp"` to auto-select the C++ units a human has already
   accepted (VERIFIED) in the stage-1 Plan. It triages the tree, authors the kernel
   (direct or split), cross-checks against `libmcfm` during authoring, then wires and runs
   the doctests.
3. **Verify**: `jobrunner submit tests/pepper` builds Pepper standalone and runs the
   doctests (`desired_spec.md` §4). Verified ⇔ doctests pass.
4. **Record** the outcome below (flip the box, note the worst relative error).

## Seed worklist (bootstrap order)

Smallest cases first; each is a dependency of the next, and reuse across kernels is by
include. The Z Born and single-jet cases already ship as native reference kernels in
`$PEPPER_HOME/src/mcfm_analytics/` (usable as doctest references and for fragment reuse);
`qqb_z2jet` is the open porting target for a demo.

- [x] qqb_z         — Born; closed-form K-factor, no QCDLoop (reference kernel present)
- [x] qqb_z_v       — first virtual; smallest case with real loop functions (reference present)
- [x] qqb_z1jet     — Born, dependency of qqb_z1jet_v (reference present)
- [x] qqb_z1jet_v   — loop functions + heavy-quark axial anomaly (reference present)
- [ ] qqb_z2jet     — Born; larger call tree (exercises the §7 split protocol)
- [ ] qqb_z2jet_v   — virtual; boxes → a §5 threshold-stability decision is required

## Working notes

- Stage-2 validation is *equivalence*, not physics (Spec §6): a kernel is correct by
  construction when it reproduces the MCFM reference values block-by-block and the doctests
  pass. Pepper does not link MCFM; `libmcfm` is only the authoring cross-check.
- Watch the `Kokkos::complex` division caveat (Spec §3): division-heavy paths agree only to
  ~1e-10, not 1e-13.
- Box integrals at higher multiplicity are the open hard case (Spec §5): pick the
  threshold-stability strategy explicitly and record which one, per integral.
- A port that needs a human-guided runtime diff to resolve is escalated to a human and
  noted here.
