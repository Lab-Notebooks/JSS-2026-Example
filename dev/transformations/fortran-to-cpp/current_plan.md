# Fortran → C++ worklist

Units for a targeted slice of the stage-1 translation. Agents tick boxes off and add a
one-line outcome per unit; this file is the running record shared across sessions.

Legend: `- [ ]` untouched (no `.cpp` sibling yet); `- [x]` translated and wired into
CMake. A translated unit counts as **verified** only after the coverage probe fires
(`desired_spec.md` §5). Paths are relative to `$MCFM_HOME/src`.

## Running the work

1. **Index first** — generate the call graph, then rank leaves:
   ```
   source environment.sh
   dev/tools/index/generate_doxygen.sh          # Doxygen XML the index reads
   python3 dev/tools/index/build_roadmap.py     # -> dev/tmp/assets/roadmap_metrics.tsv
   ```
   Ready leaves are the rows with `deps==0` and `blind==0`.
2. **Draft, then translate** each leaf: `dev/tools/draft/scribe_draft.py <file.f>` for the
   scaffold and rule-9a hints, then the real translation guided by `desired_spec.md` and
   `dev/tools/draft/seed_examples.toml`. The `translate` workflow automates this
   (index → resolve → bundle → author → integrate) and refreshes the review bundles below.
3. **Verify**: `jobrunner submit tests/mcfm` builds MCFM and runs the benchmark suite;
   `desired_spec.md` §5 adds the coverage probe that separates *verified* from *translated*.
4. **Record** the outcome below — flip the box, add a one-line note.

## Review bundles

The `translate` workflow refreshes this section: it groups the ready leaves into
review-sized bundles that balance throughput against reviewer technical debt (each bundle
coherent, one benchmark, capped in size), so a human can accept one bundle at a time. The
seed below is the genuine ready leaves (`deps==0`) as of the last index, grouped by the
benchmark that exercises them; expand from the roadmap as units clear.

### W2jet  (benchmark: `u d~ ve e+ g g`)
- [ ] W2jet/qqb_wp2jetx_new.f

### gghgg_dep  (benchmark: `g g h g g`)
- [ ] gghgg_dep/spinor.f
- [ ] gghgg_dep/ppmm.f
- [ ] gghgg_dep/pppm.f
- [ ] gghgg_dep/hgggglabels_mod.f90   — a module (Spec §1 module form)

## Working notes

- Units in `Mods/Need/Inc/Procdep` have no exercising benchmark — mark them *translated*,
  never *verified* (Spec §4).
- A unit whose coverage probe is unchanged is only *provisionally* off-path (Spec §5);
  re-probe after its caller becomes C++.
- Report a suspected mistranslation as FAILED with the symptom rather than guessing;
  escalate a subtle numerical disagreement to a human and note it here.
