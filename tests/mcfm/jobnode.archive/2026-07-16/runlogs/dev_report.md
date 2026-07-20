# MCFM benchmark comparison: `adhruv/Convert_to_c++` vs `pmachado/Convert_to_c++`

_Date: 2026-07-16_

## Summary

Both branches of the MCFM Fortran → C++ transformation were built cleanly
(`gfortran`/`gcc`/`g++`, cmake 3.26) and the full stage-1 benchmark suite from
`tests/mcfm/test.sh` was run on each. **All 10 benchmark processes PASSED on both
branches** at the harness tolerance of `1e-13` (`./test -b`, pole check +
benchmark against the reference values). There are **no pass/fail discrepancies**.

The only discrepancies are **last-digit floating-point differences** between the
two branches, all far below the benchmark tolerance.

## Method

- `software/mcfm` submodule checked out to each branch in turn (same build dir, so
  run sequentially), clean rebuild (`rm -rf install; make clean; cmake; make install`).
- Each benchmark process run independently (rather than `test.sh` directly) so a
  `set -e` abort could not mask later processes — all returned RC=0.
- ANSI codes stripped; 17-significant-digit MCFM values and ratios diffed.
- Archived logs: [`tests/mcfm/jobnode.archive/2026-07-16`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/tree/main/tests/mcfm/jobnode.archive/2026-07-16).

## Artifacts

Run logs archived under [`tests/mcfm/jobnode.archive/2026-07-16/runlogs/`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/tree/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs):

| File | Description |
|---|---|
| [`driver.log`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/blob/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs/driver.log) | Top-level driver output for the comparison run |
| [`orig_branch.txt`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/blob/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs/orig_branch.txt) | Original submodule branch recorded before the run |
| [`adhruv_Convert_to_c++.build.log`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/blob/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs/adhruv_Convert_to_c%2B%2B.build.log) | `adhruv/Convert_to_c++` build log |
| [`adhruv_Convert_to_c++.results.log`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/blob/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs/adhruv_Convert_to_c%2B%2B.results.log) | `adhruv/Convert_to_c++` benchmark results |
| [`pmachado_Convert_to_c++.build.log`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/blob/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs/pmachado_Convert_to_c%2B%2B.build.log) | `pmachado/Convert_to_c++` build log |
| [`pmachado_Convert_to_c++.results.log`](https://github.com/Lab-Notebooks/Agentic-Workflows-Demo/blob/main/tests/mcfm/jobnode.archive/2026-07-16/runlogs/pmachado_Convert_to_c%2B%2B.results.log) | `pmachado/Convert_to_c++` benchmark results |

## Results

Max relative branch-to-branch deviation, per process:

| Process | Directory | Branch-to-branch max Δrel | Status |
|---|---|---|---|
| `u d~ ve e+` | W | — | identical |
| `u d~ ve e+ g` | W1jet | — | identical |
| `u d~ ve e+ g g` | W2jet/BDK/loop | 6.4e-16 | differs (negligible) |
| `u u~ e- e+` | Z | — | identical |
| `u u~ e- e+ g` | Z1jet/loop | — | identical |
| `u u~ e- e+ g g` | Z2jet | — | identical |
| `-Pmodel=heft g g h` | ggH (heft) | 5.0e-15 | differs |
| `g g h` | ggH | 1.6e-16 | differs (negligible) |
| `g g g g g` | ThreeJets | **1.0e-14** | differs (largest) |
| `g g h g g` | gghgg_dep | 9.0e-15 | differs |

## Interpretation

- **Every discrepancy is at the ~1e-16–1e-14 relative level** — floating-point
  rounding noise, one to two orders of magnitude below the `1e-13` benchmark
  tolerance. Numerically the branches agree.
- The processes that differ (W2jet, ggH, ThreeJets, gghgg_dep) line up exactly
  with where the branch source differs: the `git diff` between the branches is
  concentrated in `src/loop/` and `src/gghgg_dep/` (adhruv has C++ ports —
  `loopI*_generic.cpp`, `ppppD*.cpp`, `scp*.cpp` — where pmachado still has the
  `.f` versions). The pure tree-level and Z/W+1jet processes, untouched by those
  modules, are **bit-identical**.
- Largest single deviation: `g g h g g` Born,
  `1.9621447229562655e-07` (adhruv) vs `1.9621447229562477e-07` (pmachado),
  Δrel ≈ 9e-15; and `g g g g g` IR ratio drifting to `1.0000000000000102`.

## Bottom line

**Functionally equivalent** — both branches pass all benchmarks; the only
differences are sub-tolerance rounding in the `loop/` and `gghgg_dep/`-dependent
processes that the two branches translated differently.
