# MCFM test failure fix: target output

This file defines the fix target and correctness bar. The workflow lives in `current_plan.md`.

Paths are written as `software/mcfm/src/...`.

---

## Contract

This pass advances by *settling* failing test processes one at a time: each process is diagnosed,
its root-cause source files are fixed, and then recorded in `agent_log.md` with status `σ` once
the oracle `V` confirms all test cases in that process show **passed**.

Objective `f`. Fix every failing test process in `tests/mcfm/test.sh` so each test case
explicitly shows **passed**. Progress = fraction of test processes where every case shows `passed`
(run `jobrunner submit tests/mcfm` and inspect output).

Invariants `I` (hold after every settled unit):

- Every previously passing process still has all test cases showing `passed`.
- No called symbol is invented; no new translation-era artifacts are introduced.
- Each fixed process shows `passed` for every test case — absence of `FAILED` is not sufficient
  (a silent segfault produces no output at all and would pass that check incorrectly).

Oracle `V`. `jobrunner submit tests/mcfm`; inspect output to confirm each test case in the
settled process explicitly shows `passed`.

Status set `Σ`.

| σ       | class | reversible | runner sets | evidence in log                                    |
|---------|-------|------------|-------------|----------------------------------------------------|
| FIXED   | good  | yes        | yes         | all cases show `passed`; worst Δrel ≤ 1e-13        |
| SKIPPED | good  | yes        | yes         | reason (upstream not yet translated, out of scope) |
| FAILED  | bad   | —          | yes         | symptom; tried and still failing                   |

Risky `σ` = FAILED. Up to 3 completed groups may accumulate before approval. The sections below
elaborate this contract; on conflict the contract governs.

---

## Test processes

All processes are defined in `tests/mcfm/test.sh`. The full list is reproduced here as the
authoritative mapping from process to src/ directory:

| Process | Directory |
|---------|-----------|
| `u d~ ve e+` | W |
| `u d~ ve e+ g` | W1jet |
| `u d~ ve e+ g g` | W2jet / BDK / loop |
| `u u~ e- e+` | Z |
| `u u~ e- e+ g` | Z1jet / loop |
| `u u~ e- e+ g g` | Z2jet / W2jet / BDK / loop |
| `-Pmodel=heft g g h` | ggH |
| `g g h` | ggH |
| `d d d d g` | ThreeJets |
| `d d~ d d~ g` | ThreeJets |
| `d d~ u u~ g` | ThreeJets |
| `d d~ g g g` | ThreeJets |
| `d u d u g` | ThreeJets |
| `d u~ d u~ g` | ThreeJets |
| `d g g d g` | ThreeJets |
| `d~ d d d~ g` | ThreeJets |
| `d~ d u u~ g` | ThreeJets |
| `d~ d g g g` | ThreeJets |
| `d~ d~ d~ d~ g` | ThreeJets |
| `d~ u u d~ g` | ThreeJets |
| `d~ u~ d~ u~ g` | ThreeJets |
| `d~ g g d~ g` | ThreeJets |
| `u d d u g` | ThreeJets |
| `u~ d~ d~ u~ g` | ThreeJets |
| `g d g d g` | ThreeJets |
| `g d~ g d~ g` | ThreeJets |
| `g g d d~ g` | ThreeJets |
| `g g g g g` | ThreeJets |
| `g g h g g` | gghgg_dep |

Infrastructure directories (Mods, Need, Inc, Procdep) have no test process — not covered here.

---

## Units and readiness

A unit is a failing test process or, when multiple failing processes share a root-cause source
file, the set of processes sharing that file. A unit is ready when:

- the failing process and its symptom (segfault, wrong numerics, missing symbol) are identified
- the root-cause source file(s) are known

Work through root-cause files rather than symptoms: fixing the file fixes all processes that
exercise it at once.

---

## Diagnosis

For each failing process:

1. **Silent segfault**: the process exits without printing `passed`. Get a stack trace. Look for
   array out-of-bounds, null dereference, or mis-sized `FArray`. Fix the translation error.
2. **Wrong numerics** (Δrel > 1e-13): binary-search the translated C++ files changed since the
   last passing baseline. The root cause is usually a dropped call, wrong operator precedence,
   or incorrect array indexing.
3. **Missing symbol / link error**: a callee was forward-declared but not linked. Fix includes
   or `CMakeLists.txt` wiring.

---

## Editing rules

Fix only the source files identified as root causes. Do not:

- add new translation-era forward declarations
- change build wiring beyond what is needed to fix the identified failure
- fix style or cleanup concerns (use mcfm-cleanup for that)

After each fix, rebuild and run the specific failing process first, then run the full suite to
confirm no regression.

---

## Silent traps

Check these explicitly:

1. **Silent segfault**: process exits without output — no `FAILED` but also no `passed`. Confirm
   `passed` is present; absence of `FAILED` is not sufficient.
2. Dropped call near a duplicate paired call.
3. Missing parentheses around denominators after `*`/`/` chains.
4. Wrong `FArray` size or bound.
5. 0-based indexing used where 1-based is required.
6. Missing `#include` for a translated sibling's header.
7. Fix for one process introduces a regression in another process.

---

## Correctness bar

A process is settled FIXED only when every test case in that process's `./test -b <args>` run
explicitly shows **passed** in the output. Absence of `FAILED` is not sufficient — a silent
segfault produces no output and would pass that check incorrectly.

Additionally, numerical results must match to **1e-13** (Δrel ≤ 1e-13).

Record results in `agent_log.md`, not here.
