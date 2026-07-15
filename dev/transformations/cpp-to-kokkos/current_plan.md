# Plan — C++ → Kokkos kernel (stage 2)

The **Plan** for stage 2: a human-seeded checklist of amplitudes to port. Agents
tick tasks off and record short notes and per-amplitude outcomes here after a run.

Legend: `- [ ]` not yet ported; `- [x]` kernel authored. A kernel is **verified**
only after its doctests pass (`desired_spec.md` §4–6). Port amplitudes in
**dependency order** (a Born before its virtual) so each earlier kernel's frozen
fragments are available for reuse.

## How to use

- Port with the `kokkos-translate` workflow (`args:{projectRoot, amplitude:"<name>"}`
  for one, or `amplitudes:[...]` in dependency order). Check reuse and stage-1
  readiness first: `python3 dev/tools/closure/calltree_closure.py <name>` (a plain-Fortran
  object in the closure is a stage-1 gap — finish that in `dev/transformations/fortran-to-cpp/` first).
- After a run, flip the boxes you cleared and note the worst relative error per
  amplitude.

## Seed worklist (bootstrap order)

Smallest cases first; each is a dependency of the next. Reuse across kernels via
include.

- [ ] qqb_z         — Born; closed-form K-factor, no QCDLoop (dependency of qqb_z_v)
- [ ] qqb_z_v       — first virtual; smallest case with real loop functions
- [ ] qqb_z1jet     — Born (dependency of qqb_z1jet_v)
- [ ] qqb_z1jet_v   — first case with loop functions + heavy-quark axial anomaly (B0, C0_1m0, F1anom)
- [ ] qqb_z2jet     — Born; larger call tree (exercises the §7 split protocol)
- [ ] qqb_z2jet_v   — virtual; boxes → a §5 threshold-stability decision is required

## Working notes

- Stage-2 validation is *equivalence*, not physics (Spec §6): a kernel is correct
  by construction when it matches `libmcfm` block-by-block and the doctests pass.
- Watch the `Kokkos::complex` division caveat (Spec §3/G3): division-heavy paths
  agree only to ~1e-10, not 1e-13.
- Box integrals at higher multiplicity are the open hard case (Spec §5): pick the
  threshold-stability strategy explicitly and record which one, per integral.
- A port that needs a human-guided runtime diff to resolve is escalated (P2) and
  noted here as escalated.
