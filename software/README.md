# External codebases (git submodules)

The two scientific codebases under transformation are third-party software, tracked as
**git submodules** pinned to specific commits (mirroring the paper's evaluation
artifact). `environment.sh` expects them at fixed paths so the workflows and tools
resolve `$MCFM_HOME` and `$PEPPER_HOME`:

| Path | Variable | Submodule | Role |
|------|----------|-----------|------|
| `software/mcfm` | `$MCFM_HOME` | [`NeuCol/mcfminterface`](https://github.com/NeuCol/mcfminterface) @ `adhruv/Convert_to_c++` | MCFM — Fortran source translated to C++ (stage 1), then the C++ that stage 2 ports and validates against (`libmcfm`). |
| `software/pepper` | `$PEPPER_HOME` | [`maxkno/pepper-mcfm-amplitudes`](https://github.com/maxkno/pepper-mcfm-amplitudes) @ `43-add-kokkos-mcfm-interface` | Pepper — Kokkos event generator; stage-2 kernels live in `$PEPPER_HOME/src/mcfm_analytics`. |
| `software/qcdloop` | `$QCDLOOP_HOME` | [`ReetBarik/qcdloop`](https://github.com/ReetBarik/qcdloop) @ `master` | Kokkos QCDLoop — header-only, device-portable massive-top one-loop scalar integrals (box/triangle/bubble). Pepper's stage-2 `texact` kernels link it via `-DPEPPER_QCDLOOP_DIR=$QCDLOOP_HOME`. |

## Getting the clones

The submodules are populated at clone time with `--recurse-submodules`, or after the
fact:

```
git submodule update --init            # fetch + check out all three at their pinned commits
```

Each submodule is pinned to a commit but also records its branch in `.gitmodules`, so
you can advance a pin to the tip of that branch and commit the new pointer:

```
git submodule update --remote software/mcfm    # fast-forward to branch tip
git -C software/mcfm checkout adhruv/Convert_to_c++   # if you want to work on the branch
git add software/mcfm && git commit -m "Bump MCFM submodule"
```

```
software/
  mcfm/            # submodule: MCFM  (= $MCFM_HOME)
  pepper/          # submodule: Pepper (= $PEPPER_HOME)
  qcdloop/         # submodule: Kokkos QCDLoop (= $QCDLOOP_HOME)
```

## What the tools and workflows expect inside them

- **Index / Stage 1** (`dev/tools/index/build_roadmap.py`, `mcfm-translate`): `software/mcfm/src`
  with the Fortran sources, and a **Doxygen** call graph under
  `software/mcfm/doxygen_dep/xml` — indexing is Doxygen-based, so generate it once
  (`doxygen` over `src/` with `GENERATE_XML=YES`, `CALL_GRAPH`/`REFERENCES` on). The
  index command fuses it with on-disk state into `dev/tools/assets/roadmap_metrics.tsv`
  and `dev/tools/assets/symbol_index.json`. A working build in `software/mcfm/Bin`
  (`cmake . && make install`) lets `./test -b <process>` and the coverage probe run.
- **Stage 2** (`dev/tools/closure/calltree_closure.py`, `kokkos-translate`): a built
  `software/mcfm/Bin/CMakeFiles/libmcfm.dir/link.txt` and
  `software/mcfm/install/lib/libmcfm.*`; the Pepper clone with `src/mcfm_analytics/`
  and `tests/unit_tests/matrix_elements.cpp`; and, for the massive-top (`texact`) code
  paths, the QCDLoop clone providing `src/qcdloop/{boxGPU,triangleGPU,bubbleGPU}.h`.
  Pepper resolves these when configured with `-DPEPPER_QCDLOOP_DIR=$QCDLOOP_HOME`, which
  adds `$QCDLOOP_HOME/src` (+ `/src/qcdloop`) to the include path and defines
  `PEPPER_QCDLOOP` (enabling the `texact` kernels and their doctests). `tests/pepper`
  passes this automatically.

Translation outputs (generated `.cpp`/`.hpp`/`_fi.F90`, CMake edits, Kokkos kernel
headers) are written *into these clones*, not into this repository. Per-unit outcomes
are recorded in each transformation's `current_plan.md`.
