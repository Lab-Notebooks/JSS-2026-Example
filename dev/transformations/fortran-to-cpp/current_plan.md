# Plan — Fortran → C++ translation

This is the **Plan**: a human-seeded checklist of units for a targeted slice of work,
which agents edit to tick tasks off and record short notes. Together with the Spec it
is the running record human and agent share across sessions, and the place per-file
outcomes (verified / translated / failed) are recorded after a run. It is durable
state — everything here survives an agent's transient context.

Legend: `- [ ]` untouched (no `.cpp` sibling yet); `- [x]` translated and wired into
CMake. A translated unit is **verified** only after the coverage probe fires
(`desired_spec.md` §5). Paths are relative to `$MCFM_HOME/src`.

## How to use

- Run the `mcfm-translate` workflow (`args:{projectRoot, scope:"<dir>"}`): it indexes
  the call graph, resolves the next dependency-free leaf layer, drafts and translates
  each file in parallel, then integrates and verifies serially.
- To refresh readiness by hand: `python3 dev/tools/index/build_roadmap.py`.
- After a run, flip the boxes you cleared and add a one-line outcome note per unit.

## Seed worklist

A short, self-contained starting slice, drawn from MCFM directories a benchmark can
reach. Expand it from the graph as units clear.

### ThreeJets  (benchmark: `g g g g g`)
- [ ] ThreeJets/A5NLO4qg.f
- [ ] ThreeJets/A5NLOqbqggg.f

### W2jet  (benchmark: `u d~ ve e+ g g`)
- [ ] W2jet/qqb_w2jet_v.f
- [ ] W2jet/qqb_wp2jetx_new.f

### Z2jet  (benchmark: `u u~ e- e+ g g`)
- [ ] Z2jet/msq_z2jetx.f

## Working notes

- Units in `Mods/Need/Inc/Procdep` have no exercising benchmark — they can be marked
  *translated*, never *verified* (Spec §4).
- A unit whose coverage probe is unchanged is only *provisionally* off-path (Spec §5);
  re-probe after its caller becomes C++.
- Report a suspected mistranslation as FAILED with the symptom rather than guessing;
  a subtle numerical disagreement is escalated to a human — note it here.
