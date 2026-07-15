# External codebases (obtained separately)

The two scientific codebases under transformation are third-party software and are
**not tracked by this repository** (they are gitignored). `environment.sh` expects
them at fixed paths so the workflows and tools resolve `$MCFM_HOME` and `$PEPPER_HOME`:

| Path | Variable | Role |
|------|----------|------|
| `software/mcfm` | `$MCFM_HOME` | MCFM — Fortran source translated to C++ (stage 1), then the C++ that stage 2 ports and validates against (`libmcfm`). |
| `software/pepper` | `$PEPPER_HOME` | Pepper — Kokkos event generator; stage-2 kernels live in `$PEPPER_HOME/src/mcfm_analytics`. |

## Getting the clones

`jobrunner setup software` runs `setup_mcfm.sh` and `setup_pepper.sh`, which clone
each project to the path above if absent. Edit the URLs/branches in those scripts to
the sources your experiment targets (the scripts are the only tracked part; the
clones are ignored). You can also clone or symlink them by hand.

```
software/
  Jobfile          # jobrunner: setup -> setup_mcfm.sh, setup_pepper.sh
  setup_mcfm.sh    # clone MCFM   -> software/mcfm   (= $MCFM_HOME)
  setup_pepper.sh  # clone Pepper -> software/pepper (= $PEPPER_HOME)
  mcfm/            # clone (gitignored)
  pepper/          # clone (gitignored)
```

## What the tools and workflows expect inside them

- **Index / Stage 1** (`tools/build_roadmap.py`, `mcfm-translate`): `software/mcfm/src`
  with the Fortran sources, and a **Doxygen** call graph under
  `software/mcfm/doxygen_dep/xml` — indexing is Doxygen-based, so generate it once
  (`doxygen` over `src/` with `GENERATE_XML=YES`, `CALL_GRAPH`/`REFERENCES` on). The
  index command fuses it with on-disk state into `tools/assets/roadmap_metrics.tsv`
  and `tools/assets/symbol_index.json`. A working build in `software/mcfm/Bin`
  (`cmake . && make install`) lets `./test -b <process>` and the coverage probe run.
- **Stage 2** (`tools/calltree_closure.py`, `kokkos-translate`): a built
  `software/mcfm/Bin/CMakeFiles/libmcfm.dir/link.txt` and
  `software/mcfm/install/lib/libmcfm.*`; the Pepper clone with `src/mcfm_analytics/`
  and `tests/unit_tests/matrix_elements.cpp`.

Translation outputs (generated `.cpp`/`.hpp`/`_fi.F90`, CMake edits, Kokkos kernel
headers) are written *into these clones*, not into this repository. Per-unit outcomes
are recorded in each transformation's `current_plan.md`.
