# Verification harnesses

The verification bar for each stage is exercised by tests that ship *inside the
external clones* (see [`software/README.md`](../software/README.md)); this directory
holds the jobrunner wrappers that invoke them. The bar itself is specified in each
transformation's Spec (`desired_spec.md`) and is held fixed across runs.

## Stage 1 — MCFM benchmark + coverage probe

Bar: `dev/fortran-to-cpp/desired_spec.md` §6. `jobrunner submit tests/mcfm` runs
`tests/mcfm/test.sh`, which builds `$MCFM_HOME/Bin` and runs `./test -b <process>`
for each benchmarked channel:

```bash
source environment.sh
jobrunner submit tests/mcfm       # or: bash tests/mcfm/test.sh
```

A unit is **verified** only if a benchmark exercises it (confirmed by the mandatory
coverage probe: perturb the output by 1.5×, relink, re-run, observe a ratio move)
and the four ratios match within `1e-13`; otherwise it is **translated** (unverified).
The directory→benchmark map is `desired_spec.md` §5.

## Stage 2 — libmcfm equivalence + doctests

Bar: `dev/cpp-to-kokkos/desired_spec.md` §4–6. Two layers:

1. **Standalone host validation** — a validator links `libmcfm` and includes the
   kernel header through the math-only Kokkos shim; compare layered (loop functions →
   sub-amplitudes → full |M|²) to ≤`1e-10` relative. Built and run with
   `tools/kokkos/run_validation.sh <validator.cpp>`.
2. **Doctests** — layered `DOCTEST_TEST_CASE`s in
   `$PEPPER_HOME/tests/unit_tests/matrix_elements.cpp`:
   ```bash
   cmake --build "$PEPPER_HOME/build" --target pepper_test -j
   "$PEPPER_HOME/build/tests/unit_tests/pepper_test" --dt-test-case="*<name>*"
   ```

`jobrunner submit tests/pepper` (`tests/pepper/test.sh`) builds Pepper against the
MCFM install. A kernel is **verified** only when its doctests pass; a header that
merely compiles is **translated**.

## Recording outcomes

Record each run's per-unit outcomes in the transformation's `current_plan.md` (flip
the checkboxes, note the worst deviation and any escalations).
