# C++ → Kokkos to-do list

The amplitudes to rewrite as Pepper kernels. Tick tasks off and write short notes and a
result per amplitude here; this is the shared record across sessions. Do them in **order of
need** (a Born before its virtual) so each earlier kernel's frozen pieces can be reused.

Key: `- [ ]` not done; `- [x]` kernel written. A kernel is **verified** only after its tests
(doctests) pass (`desired_spec.md` §4). Paths are written as
`software/pepper/src/mcfm_analytics/…` (the `$PEPPER_HOME` form is only for a normal shell —
see the Spec's "Running commands").

**How to record a result.** Same as step 1: when an amplitude is done, add a tag —
`- [x] <name> — VERIFIED (maxRelErr <value>)`, `- [x] <name> — TRANSLATED (<reason>)`, or
`- [ ] <name> — FAILED (<what went wrong>)`. Tests pass ⇒ VERIFIED.

## How to do the work

0. **Build MCFM first** — `jobrunner submit tests/mcfm`. Step 2 needs `libmcfm` before it can
   even size a target: the Closure tool and the compare harness both read it (Spec §1.3).
   Skip this and step 1 and every check will fail on a fresh checkout.
1. **Check reuse and step-1 readiness**:
   `python3 dev/tools/closure/calltree_closure.py <name>` lists everything the amplitude
   calls, read from the linked pieces. A still-Fortran piece in that list is a step-1 gap;
   finish it in `dev/transformations/fortran-to-cpp/` before rewriting.
2. **Rewrite** with the `port` workflow: `args:{projectRoot, transformation:"cpp-to-kokkos",
   target:"<name>"}` for one (or `targets:[...]` in order). Auto-pick (`from:"fortran-to-cpp"`,
   no target) rewrites the files the step-1 Plan tags `VERIFIED` whose call tree is fully
   C++; it only finds work once step 1 has verified the target's dependencies, so for the
   list below (whose C++ dependencies already ship) pass an explicit `target:`. It sizes the
   tree, writes the kernel (one pass or split), compares against `libmcfm` while writing,
   then wires up and runs the tests.
3. **Check**: `jobrunner submit tests/pepper` builds Pepper on its own and runs the tests
   (`desired_spec.md` §4). Verified = tests pass.
4. **Record** the result below (flip the box, add the tag and the worst relative error).

## Amounts to do (start small)

Smallest cases first; each is needed by the next, and kernels reuse each other by include.
The Z Born and single-jet cases already ship as ready kernels in
`software/pepper/src/mcfm_analytics/` (use them as test references and to reuse pieces);
`qqb_z2jet` is the open target for a demo.

- [x] qqb_z         — Born; direct K-factor formula, no QCDLoop (kernel present)
- [x] qqb_z_v       — first virtual; smallest case with real loop functions (present)
- [x] qqb_z1jet     — Born, needed by qqb_z1jet_v (present)
- [x] qqb_z1jet_v   — loop functions + heavy-quark axial anomaly (present)
- [ ] qqb_z2jet     — Born; bigger call tree (uses the §7 split plan)
- [ ] qqb_z2jet_v   — virtual; boxes → needs a §5 accuracy-near-threshold decision

## Notes

- The step-2 check is "matches MCFM", not physics (Spec §6): a kernel is correct once it
  reproduces MCFM's reference numbers block by block and the tests pass. Pepper does not link
  MCFM; `libmcfm` is only the compare-while-writing helper.
- Watch the `Kokkos::complex` division catch (Spec §3): division-heavy code only agrees to
  ~1e-10, not 1e-13.
- High-multiplicity box integrals are the open hard case (Spec §5): pick the
  accuracy-near-threshold plan on purpose and write down which one, per integral.
- If a rewrite needs a person to compare runs by hand, hand it to a person and note it here.
