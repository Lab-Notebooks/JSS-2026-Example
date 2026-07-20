# Fortran → C++ to-do list

The files to rewrite in this step. Agents tick boxes off and add a one-line result per
file; this file is the shared record across sessions.

Key: `- [ ]` not started (no `.cpp` yet); `- [x]` rewritten and wired into the build. A
rewritten file counts as **verified** only after the coverage check passes
(`desired_spec.md` §5). Paths are written as `software/mcfm/src/...` (the `$MCFM_HOME/src`
form is only for a normal shell — see the Spec's "Running commands").

**How to record a result (step 2 reads this).** When a file is done, add a tag to its line
so a program can read the result, because step 2's `port … from:fortran-to-cpp` only picks
files tagged `VERIFIED`:

- `- [x] <file> — VERIFIED (worst Δrel <value>)` — the coverage check passed and the numbers match.
- `- [x] <file> — TRANSLATED (<reason>)` — builds, but not verified (not on a test's path,
  it's infrastructure, or the check was left for a normal-shell pass, see Spec §5).
- `- [ ] <file> — FAILED (<what went wrong>)` — a bad rewrite handed to a person.

Only a runner with a normal shell (the `translate` combining step, or a person) may write
`VERIFIED`; a CodeScribe run writes `TRANSLATED` and leaves the upgrade to the check pass.

## How to do the work

1. **Index first** — build the call map once in a normal shell, then rank the files:
   ```
   source environment.sh
   dev/tools/index/generate_doxygen.sh          # one-time, normal shell; writes the call map
   python3 dev/tools/index/build_roadmap.py     # -> dev/tmp/assets/roadmap_metrics.tsv
   ```
   Which files to take, how to group them, and the order all follow the Spec's
   **Resolution** section (ready files are the rows with `deps==0` and `blind==0`). The
   Doxygen step can't run in CodeScribe's limited shell, so do it before starting a run.
2. **Draft, then rewrite** each ready file: `dev/tools/draft/scribe_draft.py <file.f>` for
   the rough draft and rule-9a hints, then the real rewrite following `desired_spec.md` and
   `dev/tools/draft/seed_examples.toml`. The `translate` workflow does this for you
   (index → resolve → bundle → author → integrate) and refreshes the groups below.
3. **Check**: `jobrunner submit tests/mcfm` builds MCFM and runs the test suite;
   `desired_spec.md` §5 adds the coverage check that tells *verified* from *translated*.
4. **Record** the result below — flip the box, add the tag and a one-line note.

## Review bundles

The `translate` workflow refreshes this section. It puts the ready files into review-sized
groups a person can check without being overwhelmed (each group on one topic, one test, and
small), so a person can approve one group at a time. The list below is the ready files
(`deps==0`) from the last index, grouped by the test that runs them; add more as files clear.

### gghgg_dep-1 — gghgg_dep (4 files, test: g g h g g)
- [ ] gghgg_dep/precision.f
- [ ] gghgg_dep/gghgg_dep_params.f
- [ ] gghgg_dep/sprod_com.f
- [ ] gghgg_dep/hgggglabels_mod.f90

### gghgg_dep-2 — gghgg_dep (3 files, test: g g h g g)
- [ ] gghgg_dep/testReal.f
- [ ] gghgg_dep/setreal_mcfm.f
- [ ] gghgg_dep/ggHgg.f

### Mods-1 — Mods (3 files, test: none)
- [ ] Mods/types_mod.f
- [ ] Mods/mod_qcdloop_c.f
- [ ] Mods/Modules_Interface.f90

### W2jet-1 — W2jet (1 file, test: u d~ ve e+ g g)
- [ ] W2jet/qqb_wp2jetx_new.f

### Inc-1 — Inc (1 file, test: none)
- [ ] Inc/ppmax.f

## Notes

- Files in `Mods/Need/Inc/Procdep` have no test that runs them — mark them *translated*,
  never *verified* (Spec §4).
- If a coverage check shows no change, the file just isn't on a test's path yet (Spec §5);
  check it again after a file that calls it is rewritten.
- If you suspect a bad rewrite, mark it FAILED with the symptom instead of guessing; hand a
  small number mismatch to a person and note it here.
